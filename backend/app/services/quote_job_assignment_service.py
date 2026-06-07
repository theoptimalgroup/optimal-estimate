"""Service for manager selected-estimate decisions (local only; not eWorks job assignment)."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.types import AuthenticatedUser
from app.core.exceptions import AppError
from app.models.calculation_session import CalculationSession
from app.models.quote_assignment import EworksQuoteAssignment
from app.models.quote_job_assignment import QuoteJobAssignment
from app.schemas.dashboard_quote_groups import (
    DashboardQuoteGroupComparisonChargeLine,
    DashboardQuoteGroupComparisonSummary,
    DashboardQuoteGroupComparisonWorkBreakdown,
    DashboardQuoteJobAssignmentDecision,
)
from app.schemas.eworks_link import Step1Snapshot, Step2Snapshot
from app.schemas.quote_job_assignment import AssignQuoteJobRequest, QuoteJobAssignmentDecisionRead
from app.services.audit_helpers import record_audit, snapshot_model
from app.services.calculation_session_service import (
    _dashboard_last_result,
    _dashboard_quote_summary_breakdown,
    _quote_group_identity,
    _resolve_work_product_fields,
    _session_final_total,
    _work_subtotals_from_breakdown,
)
from app.services.quote_assignment_service import _as_uuid


def _normalize_quote_ref(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def get_job_assignment_for_quote(
    db: Session,
    *,
    quote_ref: str | None = None,
    eworks_quote_id: int | None = None,
) -> QuoteJobAssignment | None:
    normalized_ref = _normalize_quote_ref(quote_ref)
    query = db.query(QuoteJobAssignment)
    if normalized_ref:
        row = query.filter(QuoteJobAssignment.quote_ref == normalized_ref).order_by(QuoteJobAssignment.id.desc()).first()
        if row is not None:
            return row
    if eworks_quote_id is not None:
        return (
            query.filter(QuoteJobAssignment.eworks_quote_id == eworks_quote_id)
            .order_by(QuoteJobAssignment.id.desc())
            .first()
        )
    return None


def build_job_assignment_decision_read(
    db: Session,
    row: QuoteJobAssignment,
) -> QuoteJobAssignmentDecisionRead:
    assigned_by_name = None
    if row.assigned_by_user_id is not None:
        from app.models.user import User

        user = db.get(User, row.assigned_by_user_id)
        if user is not None:
            assigned_by_name = user.full_name or user.email
    return QuoteJobAssignmentDecisionRead(
        id=row.id,
        selected_session_id=row.selected_session_id,
        assignee_name=row.assignee_name,
        assignee_email=row.assignee_email,
        assignment_id=row.assignment_id,
        assigned_at=row.assigned_at,
        assigned_by_name=assigned_by_name,
        assigned_by_email=row.assigned_by_email,
    )


def build_dashboard_job_assignment_decision(
    db: Session,
    row: QuoteJobAssignment | None,
) -> DashboardQuoteJobAssignmentDecision | None:
    if row is None:
        return None
    read = build_job_assignment_decision_read(db, row)
    return DashboardQuoteJobAssignmentDecision(
        id=read.id,
        selected_session_id=read.selected_session_id,
        assignee_name=read.assignee_name,
        assignee_email=read.assignee_email,
        assignment_id=read.assignment_id,
        assigned_at=read.assigned_at,
        assigned_by_name=read.assigned_by_name,
        assigned_by_email=read.assigned_by_email,
    )


def _session_belongs_to_quote(
    session: CalculationSession,
    *,
    quote_ref: str | None,
    eworks_quote_id: int | None,
) -> bool:
    step1 = Step1Snapshot.model_validate(session.step1_snapshot)
    _, session_quote_ref, session_eworks_id = _quote_group_identity(session, step1)
    normalized_ref = _normalize_quote_ref(quote_ref)
    if normalized_ref and _normalize_quote_ref(session_quote_ref) == normalized_ref:
        return True
    if eworks_quote_id is not None and session_eworks_id == eworks_quote_id:
        return True
    return False


_COMPARISON_CHARGE_LABELS = ("Parking", "Congestion", "Travel", "Other")
_EXCLUDED_COMPARISON_CHARGE_LABELS = frozenset({"ULEZ", "Waste Disposal"})


def _comparison_charge_label(raw_label: str) -> str | None:
    normalized = (raw_label or "").strip()
    if not normalized or normalized in _EXCLUDED_COMPARISON_CHARGE_LABELS:
        return None
    for label in _COMPARISON_CHARGE_LABELS:
        if normalized == label or normalized.startswith(f"{label} "):
            return label
    if normalized == "Other charge":
        return "Other"
    return None


def _comparison_charge_lines(breakdown: dict) -> list[DashboardQuoteGroupComparisonChargeLine]:
    amounts = {label: Decimal("0") for label in _COMPARISON_CHARGE_LABELS}
    for line in breakdown.get("charges") or []:
        mapped_label = _comparison_charge_label(str(line.get("label") or ""))
        if mapped_label is None or line.get("total") is None:
            continue
        amounts[mapped_label] += Decimal(str(line["total"]))
    return [
        DashboardQuoteGroupComparisonChargeLine(label=label, amount=amounts[label])
        for label in _COMPARISON_CHARGE_LABELS
    ]


def _comparison_additional_charges_total(charge_lines: list[DashboardQuoteGroupComparisonChargeLine]) -> Decimal:
    return sum((line.amount for line in charge_lines), Decimal("0"))


def _comparison_work_rows(
    db: Session,
    *,
    step2: Step2Snapshot,
    breakdown_map: dict[int, dict],
) -> list[DashboardQuoteGroupComparisonWorkBreakdown]:
    rows: list[DashboardQuoteGroupComparisonWorkBreakdown] = []
    for index, block in enumerate(step2.works):
        work_result = breakdown_map.get(index, {})
        work_breakdown = work_result.get("breakdown") or {}
        labour_subtotal, materials_subtotal = _work_subtotals_from_breakdown(work_breakdown)
        work_subtotal = None
        if labour_subtotal is not None or materials_subtotal is not None:
            work_subtotal = (labour_subtotal or Decimal("0")) + (materials_subtotal or Decimal("0"))
        product_name, product_code = _resolve_work_product_fields(db, block)
        scope_preview = (block.scope or "").strip() or None
        rows.append(
            DashboardQuoteGroupComparisonWorkBreakdown(
                product_name=product_name,
                product_code=product_code,
                scope_preview=scope_preview,
                labour_subtotal=labour_subtotal,
                materials_subtotal=materials_subtotal,
                work_subtotal=work_subtotal,
            )
        )
    return rows


def _session_comparison_summary(db: Session, session: CalculationSession) -> DashboardQuoteGroupComparisonSummary | None:
    last_result = _dashboard_last_result(db, session)
    if not last_result:
        return None

    breakdown = last_result.get("breakdown") or {}
    summary = _dashboard_quote_summary_breakdown(breakdown)
    if summary is None:
        return None

    step2 = Step2Snapshot.model_validate(session.step2_snapshot) if session.step2_snapshot else Step2Snapshot()
    work_breakdowns = last_result.get("work_breakdowns") or []
    breakdown_map = {item["work_index"]: item for item in work_breakdowns}

    labour_total = Decimal("0")
    materials_total = Decimal("0")
    has_labour = False
    has_materials = False
    for index, block in enumerate(step2.works):
        work_result = breakdown_map.get(index, {})
        work_breakdown = work_result.get("breakdown") or {}
        labour_subtotal, materials_subtotal = _work_subtotals_from_breakdown(work_breakdown)
        if labour_subtotal is not None:
            labour_total += labour_subtotal
            has_labour = True
        if materials_subtotal is not None:
            materials_total += materials_subtotal
            has_materials = True

    scope_preview = None
    product_preview = None
    if step2.works:
        first_block = step2.works[0]
        scope_preview = (first_block.scope or "").strip() or None
        product_name, product_code = _resolve_work_product_fields(db, first_block)
        if product_name:
            product_preview = product_name
        elif product_code:
            product_preview = product_code

    charge_lines = _comparison_charge_lines(breakdown)
    vat_rate = breakdown.get("vat_rate")
    return DashboardQuoteGroupComparisonSummary(
        final_total=Decimal(str(breakdown["final_total"])),
        works_subtotal=summary.works_subtotal,
        labour_subtotal=labour_total if has_labour else None,
        materials_subtotal=materials_total if has_materials else None,
        additional_charges_total=_comparison_additional_charges_total(charge_lines),
        vat_total=summary.vat_total,
        vat_rate=Decimal(str(vat_rate)) if vat_rate is not None else None,
        scope_preview=scope_preview,
        product_preview=product_preview,
        works=_comparison_work_rows(db, step2=step2, breakdown_map=breakdown_map),
        additional_charges=charge_lines,
    )


def assign_quote_job(
    db: Session,
    *,
    quote_ref: str,
    payload: AssignQuoteJobRequest,
    actor: AuthenticatedUser,
) -> QuoteJobAssignmentDecisionRead:
    normalized_ref = _normalize_quote_ref(quote_ref)
    if not normalized_ref:
        raise AppError("QUOTE_REF_REQUIRED", "Quote reference is required", 400)

    session = db.get(CalculationSession, payload.selected_session_id)
    if session is None:
        raise AppError("SESSION_NOT_FOUND", "Selected submission session not found", 404)
    if session.status != "submitted" or session.submitted_at is None:
        raise AppError("SESSION_NOT_SUBMITTED", "Selected session is not a submitted estimate", 400)

    step1 = Step1Snapshot.model_validate(session.step1_snapshot)
    group_key, session_quote_ref, session_eworks_id = _quote_group_identity(session, step1)
    if not _session_belongs_to_quote(
        session,
        quote_ref=normalized_ref,
        eworks_quote_id=session_eworks_id,
    ):
        raise AppError("SESSION_QUOTE_MISMATCH", "Selected session does not belong to this quote", 400)

    assignee_name = payload.assignee_name.strip()
    if not assignee_name:
        raise AppError("ASSIGNEE_REQUIRED", "Assignee name is required", 400)

    if payload.assignment_id is not None:
        assignment = db.get(EworksQuoteAssignment, payload.assignment_id)
        if assignment is None:
            raise AppError("ASSIGNMENT_NOT_FOUND", "Linked assignment not found", 404)
        if assignment.calculation_session_id != payload.selected_session_id:
            raise AppError(
                "ASSIGNMENT_SESSION_MISMATCH",
                "Assignment is not linked to the selected session",
                400,
            )

    existing = get_job_assignment_for_quote(
        db,
        quote_ref=normalized_ref,
        eworks_quote_id=session_eworks_id,
    )
    before = snapshot_model(existing) if existing is not None else None

    if existing is None:
        row = QuoteJobAssignment(
            quote_ref=session_quote_ref or normalized_ref,
            eworks_quote_id=session_eworks_id,
            group_key=group_key,
            selected_session_id=payload.selected_session_id,
            assignee_name=assignee_name,
            assignee_email=(payload.assignee_email or "").strip() or None,
            assignment_id=payload.assignment_id,
            assigned_by_user_id=_as_uuid(actor.id),
            assigned_by_email=actor.email,
        )
        db.add(row)
        db.flush()
    else:
        existing.selected_session_id = payload.selected_session_id
        existing.assignee_name = assignee_name
        existing.assignee_email = (payload.assignee_email or "").strip() or None
        existing.assignment_id = payload.assignment_id
        existing.assigned_by_user_id = _as_uuid(actor.id)
        existing.assigned_by_email = actor.email
        if session_quote_ref:
            existing.quote_ref = session_quote_ref
        if session_eworks_id is not None:
            existing.eworks_quote_id = session_eworks_id
        existing.group_key = group_key
        db.flush()
        row = existing

    after = snapshot_model(row)
    after.pop("assigned_by_user_id", None)

    record_audit(
        db,
        actor=actor,
        action="quote_estimate_selected",
        entity_type="quote_job_assignment",
        entity_id=row.id,
        before=before,
        after=after,
        metadata={
            "quote_ref": row.quote_ref,
            "eworks_quote_id": row.eworks_quote_id,
            "selected_session_id": str(row.selected_session_id),
            "assignee_name": row.assignee_name,
        },
    )

    # TODO: Phase 2 — push selected estimate decision to eWorks when integration is ready.

    db.commit()
    db.refresh(row)
    return build_job_assignment_decision_read(db, row)


def _engineer_owns_job_assignment(
    db: Session,
    row: QuoteJobAssignment,
    *,
    user_id: UUID,
    user_email: str,
) -> bool:
    assignee_email = (row.assignee_email or "").strip().lower()
    if assignee_email:
        return assignee_email == user_email
    if row.assignment_id is not None:
        assignment = db.get(EworksQuoteAssignment, row.assignment_id)
        if assignment is not None and assignment.assigned_user_id == user_id:
            return True
    return False


def _quote_customer_and_address(db: Session, row: QuoteJobAssignment, step1: Step1Snapshot) -> tuple[str | None, str | None]:
    customer_name = (step1.client_name or "").strip() or None
    address = (step1.property_address or "").strip() or None
    if row.eworks_quote_id is not None:
        from app.models.eworks_sync import EworksQuote

        quote = (
            db.query(EworksQuote)
            .filter(EworksQuote.eworks_quote_id == row.eworks_quote_id)
            .order_by(EworksQuote.id.desc())
            .first()
        )
        if quote is not None:
            if not customer_name and quote.customer_name:
                customer_name = quote.customer_name.strip() or None
            if not address and isinstance(quote.raw_payload, dict):
                raw_address = quote.raw_payload.get("site_address") or quote.raw_payload.get("address")
                if isinstance(raw_address, str) and raw_address.strip():
                    address = raw_address.strip()
    return customer_name, address


def build_engineer_assigned_job_read(db: Session, row: QuoteJobAssignment) -> dict:
    session = db.get(CalculationSession, row.selected_session_id)
    step1 = Step1Snapshot.model_validate(session.step1_snapshot) if session is not None else Step1Snapshot()
    customer_name, address = _quote_customer_and_address(db, row, step1)
    job_ref = (step1.job_number or step1.external_job_id or "").strip() or None
    selected_total = None
    if session is not None:
        total = _session_final_total(db, session)
        if total is not None:
            selected_total = str(total)
    return {
        "id": row.id,
        "quote_ref": row.quote_ref,
        "eworks_quote_id": row.eworks_quote_id,
        "job_ref": job_ref,
        "customer_name": customer_name,
        "address": address,
        "selected_at": row.assigned_at,
        "selected_estimate_total": selected_total,
        "selected_session_id": row.selected_session_id,
        "status": "assigned",
        "assignment_id": row.assignment_id,
    }


def list_assigned_jobs_for_engineer(db: Session, user: AuthenticatedUser) -> list[dict]:
    user_id = _as_uuid(user.id)
    if user_id is None:
        return []
    user_email = (user.email or "").strip().lower()
    rows = db.query(QuoteJobAssignment).order_by(QuoteJobAssignment.assigned_at.desc()).all()
    results: list[dict] = []
    for row in rows:
        if not _engineer_owns_job_assignment(db, row, user_id=user_id, user_email=user_email):
            continue
        results.append(build_engineer_assigned_job_read(db, row))
    return results
