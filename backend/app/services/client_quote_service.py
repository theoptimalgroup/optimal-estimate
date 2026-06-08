from __future__ import annotations

import secrets
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.calculation_session import CalculationSession
from app.schemas.calculation import CalculationBreakdown
from app.schemas.client_quote import (
    ClientQuoteAcceptRequest,
    ClientQuoteAcceptResponse,
    PublicClientQuoteRead,
    PublicQuoteLinkRead,
    PublicQuoteSummaryRead,
    PublicQuoteWorkRead,
)
from app.schemas.eworks_link import Step1Snapshot, Step2Snapshot
from app.utils.work_label import format_work_label
from app.services.quote_acceptance_helpers import public_acceptance_from_session
from app.services.calculation_session_pdf_service import render_session_quote_pdf
from app.services.pdf_calculation_context_service import build_pdf_calculation_context


def _generate_public_quote_token() -> str:
    return secrets.token_urlsafe(32)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _get_breakdown_and_works(db: Session, session: CalculationSession):
    pdf_ctx = build_pdf_calculation_context(
        db,
        session,
        allow_recalculate=session.status != "submitted" and not session.locked,
        view_type="public_client",
    )
    return (
        pdf_ctx.breakdown,
        pdf_ctx.step1,
        pdf_ctx.step2,
        pdf_ctx.work_breakdowns,
    )


def _line_total(lines) -> Decimal:
    if not lines:
        return Decimal("0")
    return sum((Decimal(str(line.total)) for line in lines), Decimal("0"))


def _materials_summary_for_work(block) -> str | None:
    parts: list[str] = []
    if block.product_name:
        parts.append(str(block.product_name))
    if block.shelf_materials and str(block.shelf_materials).strip():
        parts.append(str(block.shelf_materials).strip())
    return " · ".join(parts) if parts else None


def _build_public_quote(
    session: CalculationSession,
    breakdown: CalculationBreakdown,
    step1: Step1Snapshot,
    step2: Step2Snapshot,
) -> PublicClientQuoteRead:
    combined_scope = "\n\n".join(
        block.scope.strip() for block in step2.works if block.scope and str(block.scope).strip()
    )
    works: list[PublicQuoteWorkRead] = []
    for index, block in enumerate(step2.works):
        works.append(
            PublicQuoteWorkRead(
                title=format_work_label(
                    product_name=block.product_name,
                    product_code=block.product_code,
                    scope=block.scope,
                    index=index,
                ),
                product_name=block.product_name,
                scope=block.scope,
                description=step1.quote_description or block.other_notes,
                materials_summary=_materials_summary_for_work(block),
                attachments=[],
            )
        )

    summary = PublicQuoteSummaryRead(
        work_charges=_line_total(breakdown.labour),
        materials=_line_total(breakdown.materials),
        additional_charges=_line_total(breakdown.charges),
        subtotal=breakdown.subtotal,
        vat=breakdown.vat_total,
        total=breakdown.final_total,
    )

    return PublicClientQuoteRead(
        quote_ref=step1.quote_number,
        client_name=step1.client_name,
        trade_name=step1.trade_name,
        status=session.status,
        scope_of_work=combined_scope or step2.scope,
        works=works,
        summary=summary,
        terms="This quote is provided for review purposes. Please contact The Optimal Group to accept or discuss changes.",
        created_at=session.created_at,
        submitted_at=session.submitted_at,
        acceptance=public_acceptance_from_session(session),
    )


def _assert_public_token_allowed(session: CalculationSession, public_token: str) -> None:
    if public_token == session.session_token:
        raise AppError("INVALID_PUBLIC_TOKEN", "Invalid public quote token", 404)
    if session.public_quote_token_revoked_at is not None:
        raise AppError("PUBLIC_LINK_REVOKED", "This client quote link has been revoked", 410)
    if session.public_quote_expires_at is not None:
        if _ensure_utc(session.public_quote_expires_at) < _utcnow():
            raise AppError("PUBLIC_LINK_EXPIRED", "This client quote link has expired", 410)


def get_session_by_public_token(db: Session, public_token: str) -> CalculationSession:
    session = db.scalar(select(CalculationSession).where(CalculationSession.public_quote_token == public_token))
    if session is None:
        raise AppError("PUBLIC_QUOTE_NOT_FOUND", "Quote not found", 404)
    _assert_public_token_allowed(session, public_token)
    if session.status != "submitted":
        raise AppError("QUOTE_NOT_AVAILABLE", "Quote is not available for client viewing", 404)
    return session


def get_public_client_quote(db: Session, public_token: str) -> PublicClientQuoteRead:
    session = get_session_by_public_token(db, public_token)
    breakdown, step1, step2, _ = _get_breakdown_and_works(db, session)
    return _build_public_quote(session, breakdown, step1, step2)


def render_public_client_quote_pdf(db: Session, public_token: str) -> tuple[bytes, str, str]:
    session = get_session_by_public_token(db, public_token)
    return render_session_quote_pdf(
        db,
        session_id=session.id,
        session_token=session.session_token,
        is_draft=False,
        read_only=True,
        show_internal_notes=False,
    )


def create_or_get_public_link(db: Session, session_id: UUID) -> PublicQuoteLinkRead:
    session = db.get(CalculationSession, session_id)
    if session is None:
        raise AppError("SESSION_NOT_FOUND", "Quote session not found", 404)
    if session.status != "submitted":
        raise AppError("SESSION_NOT_SUBMITTED", "Only submitted quotes can be shared with clients", 409)

    now = _utcnow()
    if (
        session.public_quote_token
        and session.public_quote_token_revoked_at is None
        and (
            session.public_quote_expires_at is None
            or _ensure_utc(session.public_quote_expires_at) >= now
        )
    ):
        token = session.public_quote_token
    else:
        token = _generate_public_quote_token()
        while token == session.session_token or db.scalar(
            select(CalculationSession.id).where(CalculationSession.public_quote_token == token)
        ):
            token = _generate_public_quote_token()
        session.public_quote_token = token
        session.public_quote_token_created_at = now
        session.public_quote_token_revoked_at = None
        db.flush()

    return PublicQuoteLinkRead(
        public_url=f"/client/quote/{token}",
        public_token=token,
        expires_at=session.public_quote_expires_at,
    )


def revoke_public_link(db: Session, session_id: UUID) -> None:
    session = db.get(CalculationSession, session_id)
    if session is None:
        raise AppError("SESSION_NOT_FOUND", "Quote session not found", 404)
    if not session.public_quote_token or session.public_quote_token_revoked_at is not None:
        raise AppError("PUBLIC_LINK_NOT_FOUND", "No active public link for this quote", 404)
    session.public_quote_token_revoked_at = _utcnow()
    db.flush()


def accept_public_client_quote(
    db: Session,
    public_token: str,
    payload: ClientQuoteAcceptRequest,
    *,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[ClientQuoteAcceptResponse, CalculationSession, bool]:
    """Returns response, session, and whether this call newly recorded acceptance."""
    session = get_session_by_public_token(db, public_token)
    step1 = Step1Snapshot.model_validate(session.step1_snapshot)

    if session.client_accepted_at is not None:
        return (
            ClientQuoteAcceptResponse(
                accepted=True,
                already_accepted=True,
                accepted_at=session.client_accepted_at,
                quote_ref=step1.quote_number,
            ),
            session,
            False,
        )

    now = _utcnow()
    session.client_accepted_at = now
    session.client_acceptance_name = payload.name.strip()
    session.client_acceptance_email = str(payload.email).strip()
    session.client_acceptance_notes = payload.notes.strip() if payload.notes else None
    session.client_acceptance_ip = ip_address
    session.client_acceptance_user_agent = user_agent
    db.flush()

    return (
        ClientQuoteAcceptResponse(
            accepted=True,
            already_accepted=False,
            accepted_at=now,
            quote_ref=step1.quote_number,
        ),
        session,
        True,
    )
