"""Service for manager selected-estimate decisions (local only; not eWorks job assignment)."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.types import AuthenticatedUser
from app.core.exceptions import AppError
from app.models.calculation_session import CalculationSession
from app.models.quote_assignment import EworksQuoteAssignment
from app.models.selected_estimate_decision import SelectedEstimateDecision
from app.schemas.dashboard_quote_groups import DashboardSelectedEstimateDecision
from app.schemas.selected_estimate_decision import SelectEstimateRequest, SelectedEstimateDecisionRead
from app.services.audit_helpers import record_audit, snapshot_model
from app.services.calculation_session_service import (
    _quote_group_identity,
    _session_final_total,
)
from app.schemas.eworks_link import Step1Snapshot
from app.services.quote_assignment_service import _as_uuid


def _normalize_quote_ref(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def get_selected_estimate_for_quote(
    db: Session,
    *,
    quote_ref: str | None = None,
    eworks_quote_id: int | None = None,
) -> SelectedEstimateDecision | None:
    normalized_ref = _normalize_quote_ref(quote_ref)
    query = db.query(SelectedEstimateDecision)
    if normalized_ref:
        row = (
            query.filter(SelectedEstimateDecision.quote_ref == normalized_ref)
            .order_by(SelectedEstimateDecision.id.desc())
            .first()
        )
        if row is not None:
            return row
    if eworks_quote_id is not None:
        return (
            query.filter(SelectedEstimateDecision.eworks_quote_id == eworks_quote_id)
            .order_by(SelectedEstimateDecision.id.desc())
            .first()
        )
    return None


def build_selected_estimate_decision_read(
    db: Session,
    row: SelectedEstimateDecision,
) -> SelectedEstimateDecisionRead:
    selected_by_name = None
    if row.selected_by_user_id is not None:
        from app.models.user import User

        user = db.get(User, row.selected_by_user_id)
        if user is not None:
            selected_by_name = user.full_name or user.email
    final_total = str(row.final_total) if row.final_total is not None else None
    return SelectedEstimateDecisionRead(
        id=row.id,
        quote_ref=row.quote_ref,
        eworks_quote_id=row.eworks_quote_id,
        selected_session_id=row.selected_session_id,
        selected_assignment_id=row.selected_assignment_id,
        selected_assignee_name=row.selected_assignee_name,
        selected_assignee_email=row.selected_assignee_email,
        selected_assignee_type=row.selected_assignee_type,
        final_total=final_total,
        selected_at=row.selected_at,
        selected_by_name=selected_by_name,
        selected_by_email=row.selected_by_email,
    )


def build_dashboard_selected_estimate_decision(
    db: Session,
    row: SelectedEstimateDecision | None,
) -> DashboardSelectedEstimateDecision | None:
    if row is None:
        return None
    read = build_selected_estimate_decision_read(db, row)
    return DashboardSelectedEstimateDecision(
        id=read.id,
        selected_session_id=read.selected_session_id,
        assignee_name=read.selected_assignee_name,
        assignee_email=read.selected_assignee_email,
        assignment_id=read.selected_assignment_id,
        assignee_type=read.selected_assignee_type,
        final_total=read.final_total,
        selected_at=read.selected_at,
        selected_by_name=read.selected_by_name,
        selected_by_email=read.selected_by_email,
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


def _resolve_selected_assignment_id(payload: SelectEstimateRequest) -> int | None:
    return payload.selected_assignment_id


def _derive_assignee_from_assignment(assignment: EworksQuoteAssignment) -> tuple[str, str | None, str | None]:
    name = (assignment.assigned_user_name or "").strip()
    if not name:
        name = (assignment.assigned_user_email or "").strip()
    if not name:
        name = "Unknown"
    assignee_type = assignment.assignment_type if assignment.assignment_type in {"estimator", "engineer"} else None
    return name, assignment.assigned_user_email, assignee_type


def _derive_assignee_from_session(db: Session, session: CalculationSession) -> tuple[str, str | None, str | None]:
    payload = session.payload_snapshot if isinstance(session.payload_snapshot, dict) else {}
    assignment_id = payload.get("assignment_id")
    if assignment_id is not None:
        try:
            assignment = db.get(EworksQuoteAssignment, int(assignment_id))
        except (TypeError, ValueError):
            assignment = None
        if assignment is not None:
            return _derive_assignee_from_assignment(assignment)

    submitter_name = (session.submitted_by_name or "").strip()
    if submitter_name:
        return submitter_name, session.submitted_by_email, None

    return "Unknown", None, None


def select_quote_estimate(
    db: Session,
    *,
    quote_ref: str,
    payload: SelectEstimateRequest,
    actor: AuthenticatedUser,
) -> SelectedEstimateDecisionRead:
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

    selected_assignment_id = _resolve_selected_assignment_id(payload)
    assignment: EworksQuoteAssignment | None = None
    if selected_assignment_id is not None:
        assignment = db.get(EworksQuoteAssignment, selected_assignment_id)
        if assignment is None:
            raise AppError("ASSIGNMENT_NOT_FOUND", "Linked assignment not found", 404)
        if assignment.calculation_session_id != payload.selected_session_id:
            raise AppError(
                "ASSIGNMENT_SESSION_MISMATCH",
                "Assignment is not linked to the selected session",
                400,
            )

    assignee_name = (payload.assignee_name or "").strip()
    assignee_email = (payload.assignee_email or "").strip() or None
    assignee_type: str | None = None
    if assignee_name:
        if assignment is not None:
            _, _, assignee_type = _derive_assignee_from_assignment(assignment)
    elif assignment is not None:
        assignee_name, assignee_email, assignee_type = _derive_assignee_from_assignment(assignment)
    else:
        assignee_name, assignee_email, assignee_type = _derive_assignee_from_session(db, session)

    if not assignee_name or assignee_name == "Unknown":
        raise AppError("ASSIGNEE_REQUIRED", "Could not determine assignee for selected estimate", 400)

    final_total = _session_final_total(db, session)

    existing = get_selected_estimate_for_quote(
        db,
        quote_ref=normalized_ref,
        eworks_quote_id=session_eworks_id,
    )
    before = snapshot_model(existing) if existing is not None else None

    if existing is None:
        row = SelectedEstimateDecision(
            quote_ref=session_quote_ref or normalized_ref,
            eworks_quote_id=session_eworks_id,
            group_key=group_key,
            selected_session_id=payload.selected_session_id,
            selected_assignee_name=assignee_name,
            selected_assignee_email=assignee_email,
            selected_assignee_type=assignee_type,
            final_total=final_total,
            selected_assignment_id=selected_assignment_id,
            selected_by_user_id=_as_uuid(actor.id),
            selected_by_email=actor.email,
        )
        db.add(row)
        db.flush()
    else:
        existing.selected_session_id = payload.selected_session_id
        existing.selected_assignee_name = assignee_name
        existing.selected_assignee_email = assignee_email
        existing.selected_assignee_type = assignee_type
        existing.final_total = final_total
        existing.selected_assignment_id = selected_assignment_id
        existing.selected_by_user_id = _as_uuid(actor.id)
        existing.selected_by_email = actor.email
        if session_quote_ref:
            existing.quote_ref = session_quote_ref
        if session_eworks_id is not None:
            existing.eworks_quote_id = session_eworks_id
        existing.group_key = group_key
        db.flush()
        row = existing

    after = snapshot_model(row)
    after.pop("selected_by_user_id", None)

    record_audit(
        db,
        actor=actor,
        action="quote_estimate_selected",
        entity_type="selected_estimate_decision",
        entity_id=row.id,
        before=before,
        after=after,
        metadata={
            "quote_ref": row.quote_ref,
            "eworks_quote_id": row.eworks_quote_id,
            "selected_session_id": str(row.selected_session_id),
            "selected_assignee_name": row.selected_assignee_name,
        },
    )

    db.commit()
    db.refresh(row)
    return build_selected_estimate_decision_read(db, row)
