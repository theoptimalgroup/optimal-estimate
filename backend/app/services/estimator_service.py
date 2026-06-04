from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from app.models.calculation_session import CalculationSession
from app.models.client import Client
from app.models.client_alias import ClientAlias
from app.models.product import Product
from app.models.support import AuditLog
from app.schemas.eworks_link import Step1Snapshot, Step2Snapshot, WorkBlockSnapshot
from app.schemas.estimator import (
    EstimatorClientRead,
    EstimatorDashboardRead,
    EstimatorKpis,
    EstimatorNeedsAttentionItem,
    EstimatorProductRead,
    EstimatorQuoteDetailRead,
    EstimatorQuoteRow,
    EstimatorResumeRead,
)
from app.schemas.quote_acceptance import QuoteAcceptanceStatusRead
from app.services.quote_acceptance_helpers import staff_acceptance_from_session
from app.services.report_service import _extract_final_total, _has_internal_notes, _step1

_ZERO = Decimal("0.00")


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _step2(session: CalculationSession) -> Step2Snapshot:
    if not session.step2_snapshot:
        return Step2Snapshot()
    return Step2Snapshot.model_validate(session.step2_snapshot)


def _work_count(session: CalculationSession) -> int:
    return len(_step2(session).works)


def _reopened_session_ids(db: Session) -> set[UUID]:
    rows = db.scalars(
        select(AuditLog.entity_id).where(
            AuditLog.action == "quote_reopened",
            AuditLog.entity_type == "calculation_session",
            AuditLog.entity_id.is_not(None),
        )
    ).all()
    return {row for row in rows if row is not None}


def _is_reopened(session_id: UUID, reopened_ids: set[UUID]) -> bool:
    return session_id in reopened_ids


def _session_to_row(
    session: CalculationSession,
    *,
    reopened_ids: set[UUID],
) -> EstimatorQuoteRow:
    step1 = _step1(session)
    total = _extract_final_total(session)
    reopened = _is_reopened(session.id, reopened_ids)
    status = session.status
    can_resume = status == "in_progress"
    can_view_review = status == "submitted"

    return EstimatorQuoteRow(
        session_id=session.id,
        quote_ref=step1.quote_number,
        client_name=step1.client_name,
        trade_name=step1.trade_name,
        status=status,
        total=total,
        updated_at=session.updated_at,
        submitted_at=session.submitted_at,
        has_notes=_has_internal_notes(session),
        work_count=_work_count(session),
        can_resume=can_resume,
        can_view_review=can_view_review,
        is_reopened=reopened,
        acceptance=staff_acceptance_from_session(session),
    )


def _missing_scope(step2: Step2Snapshot) -> bool:
    if not step2.works:
        return True
    return any(not (work.scope and str(work.scope).strip()) for work in step2.works)


def _missing_material_cost(work: WorkBlockSnapshot) -> bool:
    if work.shelf_materials and str(work.shelf_materials).strip() and work.shelf_materials_cost <= 0:
        return True
    for row in work.shelf_materials_rows:
        if row.link and str(row.link).strip() and row.cost <= 0:
            return True
    for supplier in work.materials_to_order:
        for link in supplier.links:
            if link.link and str(link.link).strip() and link.cost <= 0:
                return True
    return False


def _needs_attention_for_session(
    session: CalculationSession,
    *,
    reopened_ids: set[UUID],
) -> list[EstimatorNeedsAttentionItem]:
    step1 = _step1(session)
    step2 = _step2(session)
    items: list[EstimatorNeedsAttentionItem] = []

    if _is_reopened(session.id, reopened_ids) and session.status == "in_progress":
        items.append(
            EstimatorNeedsAttentionItem(
                session_id=session.id,
                quote_ref=step1.quote_number,
                reason="Reopened by manager",
            )
        )

    if session.status == "in_progress" and _missing_scope(step2):
        items.append(
            EstimatorNeedsAttentionItem(
                session_id=session.id,
                quote_ref=step1.quote_number,
                reason="Missing scope",
            )
        )

    if session.status == "in_progress":
        for work in step2.works:
            if _missing_material_cost(work):
                items.append(
                    EstimatorNeedsAttentionItem(
                        session_id=session.id,
                        quote_ref=step1.quote_number,
                        reason="Missing material cost",
                    )
                )
                break

    return items


def _apply_quote_filters(
    query,
    *,
    search: str | None,
    status: str | None,
    client_id: UUID | None,
    trade_id: UUID | None,
    date_from: datetime | None,
    date_to: datetime | None,
    reopened_ids: set[UUID],
):
    if status and status != "all":
        if status == "reopened":
            query = query.where(
                CalculationSession.status == "in_progress",
                CalculationSession.id.in_(reopened_ids) if reopened_ids else CalculationSession.id.is_(None),
            )
        else:
            query = query.where(CalculationSession.status == status)

    if client_id is not None:
        query = query.where(CalculationSession.client_id == client_id)
    if trade_id is not None:
        query = query.where(CalculationSession.trade_id == trade_id)

    if date_from is not None:
        query = query.where(CalculationSession.updated_at >= _ensure_utc(date_from))
    if date_to is not None:
        query = query.where(CalculationSession.updated_at <= _ensure_utc(date_to))

    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        snapshot_text = func.lower(cast(CalculationSession.step1_snapshot, String))
        query = query.where(snapshot_text.like(term))

    return query


def get_estimator_dashboard(db: Session) -> EstimatorDashboardRead:
    reopened_ids = _reopened_session_ids(db)
    sessions = db.scalars(
        select(CalculationSession).where(CalculationSession.status.in_(("in_progress", "submitted")))
    ).all()

    draft_count = sum(1 for s in sessions if s.status == "in_progress" and s.id not in reopened_ids)
    submitted_count = sum(1 for s in sessions if s.status == "submitted")
    reopened_count = sum(1 for s in sessions if s.status == "in_progress" and s.id in reopened_ids)
    accepted_count = sum(1 for s in sessions if s.status == "submitted" and s.client_accepted_at is not None)

    submitted_totals = [
        total
        for s in sessions
        if s.status == "submitted"
        for total in [_extract_final_total(s)]
        if total is not None
    ]
    accepted_totals = [
        total
        for s in sessions
        if s.status == "submitted" and s.client_accepted_at is not None
        for total in [_extract_final_total(s)]
        if total is not None
    ]
    total_submitted_value = sum(submitted_totals, _ZERO)
    accepted_value = sum(accepted_totals, _ZERO)
    average_quote_value = (
        (total_submitted_value / len(submitted_totals)).quantize(Decimal("0.01"))
        if submitted_totals
        else _ZERO
    )

    recent = sorted(sessions, key=lambda s: s.updated_at, reverse=True)[:10]
    recent_quotes = [_session_to_row(session, reopened_ids=reopened_ids) for session in recent]

    needs_attention: list[EstimatorNeedsAttentionItem] = []
    for session in sessions:
        if session.status != "in_progress":
            continue
        needs_attention.extend(_needs_attention_for_session(session, reopened_ids=reopened_ids))

    return EstimatorDashboardRead(
        kpis=EstimatorKpis(
            draft_count=draft_count,
            submitted_count=submitted_count,
            reopened_count=reopened_count,
            total_submitted_value=total_submitted_value,
            average_quote_value=average_quote_value,
            accepted_count=accepted_count,
        ),
        recent_quotes=recent_quotes,
        needs_attention=needs_attention[:20],
    )


def list_estimator_quotes(
    db: Session,
    *,
    search: str | None = None,
    status: str | None = None,
    client_id: UUID | None = None,
    trade_id: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[EstimatorQuoteRow], int]:
    reopened_ids = _reopened_session_ids(db)
    base = select(CalculationSession).where(CalculationSession.status.in_(("in_progress", "submitted")))
    filtered = _apply_quote_filters(
        base,
        search=search,
        status=status,
        client_id=client_id,
        trade_id=trade_id,
        date_from=date_from,
        date_to=date_to,
        reopened_ids=reopened_ids,
    )

    total = db.scalar(select(func.count()).select_from(filtered.subquery())) or 0
    sessions = db.scalars(filtered.order_by(CalculationSession.updated_at.desc()).offset(offset).limit(limit)).all()
    items = [_session_to_row(session, reopened_ids=reopened_ids) for session in sessions]
    return items, int(total)


def list_estimator_approvals(
    db: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[EstimatorQuoteRow], int]:
    return list_estimator_quotes(db, status="submitted", limit=limit, offset=offset)


def get_estimator_quote(db: Session, session_id: UUID) -> EstimatorQuoteDetailRead | None:
    session = db.get(CalculationSession, session_id)
    if session is None or session.status not in {"in_progress", "submitted"}:
        return None
    reopened_ids = _reopened_session_ids(db)
    row = _session_to_row(session, reopened_ids=reopened_ids)
    step1 = _step1(session)
    return EstimatorQuoteDetailRead(
        **row.model_dump(),
        job_number=step1.job_number,
        property_address=step1.property_address,
    )


def get_estimator_resume(db: Session, session_id: UUID) -> EstimatorResumeRead | None:
    session = db.get(CalculationSession, session_id)
    if session is None or session.status != "in_progress":
        return None
    return EstimatorResumeRead(session_id=session.id, session_token=session.session_token)


def list_estimator_clients(db: Session) -> list[EstimatorClientRead]:
    clients = db.scalars(select(Client).where(Client.is_active.is_(True)).order_by(Client.name)).all()
    aliases_by_client: dict[UUID, list[str]] = {}
    for alias in db.scalars(select(ClientAlias)).all():
        aliases_by_client.setdefault(alias.client_id, []).append(alias.alias_name)

    return [
        EstimatorClientRead(
            id=client.id,
            name=client.name,
            is_active=client.is_active,
            aliases=sorted(aliases_by_client.get(client.id, [])),
        )
        for client in clients
    ]


def list_estimator_products(
    db: Session,
    *,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[EstimatorProductRead], int]:
    query = select(Product).where(Product.is_active.is_(True))
    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(Product.product_name).like(term),
                func.lower(Product.product_code).like(term),
                func.lower(Product.category).like(term),
            )
        )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    products = db.scalars(query.order_by(Product.product_name).offset(offset).limit(limit)).all()
    items = [
        EstimatorProductRead(
            id=product.id,
            product_name=product.product_name,
            product_code=product.product_code,
            category=product.category,
            scope_of_work=product.scope_of_work,
            is_active=product.is_active,
        )
        for product in products
    ]
    return items, int(total)
