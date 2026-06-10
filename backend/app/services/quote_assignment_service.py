"""Create and manage local eWorks quote assignments (no eWorks writes)."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from urllib.parse import urlencode

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.types import AuthenticatedUser
from app.core.security import UserRole
from app.models.calculation_session import CalculationSession
from app.models.eworks_sync import EworksQuote
from app.models.quote_assignment import EworksQuoteAssignment
from app.models.trade import Trade
from app.models.user import User
from app.schemas.eworks_link import EworksLinkPayload, SessionUiState, Step2Snapshot
from app.services.audit_helpers import record_audit
from app.services.client_service import get_or_create_client_for_import
from app.services.eworks_job_appointment_service import (
    apply_appointment_engineer_name_to_step1,
    get_active_job_appointment_assignee,
)
from app.services.eworks_link_service import payload_to_step1, try_resolve_rate_rule
from app.services.eworks_questionnaire_service import apply_questionnaire_defaults
from app.services.manager_dashboard_service import extract_all_tags
from app.services.eworks_sync_service import lookup_customer_name_by_id
from app.utils.html_text import html_to_plain_text

ASSIGNMENT_STATUSES = frozenset({"assigned", "in_progress", "submitted", "cancelled"})
DEFAULT_TOKEN_DAYS = 30


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _quote_summary(quote: EworksQuote) -> dict[str, Any]:
    address = None
    if isinstance(quote.raw_payload, dict):
        address = quote.raw_payload.get("site_address") or quote.raw_payload.get("address")
    return {
        "synced_quote_id": quote.id,
        "eworks_quote_id": quote.eworks_quote_id,
        "quote_ref": quote.quote_ref,
        "customer_name": quote.customer_name,
        "site_address": address if isinstance(address, str) else None,
        "quote_date": quote.quote_date,
        "expiry_date": quote.expiry_date,
        "description": quote.description,
        "tags": extract_all_tags(quote),
    }


def _assignment_link(token: str | None) -> str | None:
    if not token:
        return None
    return f"/assignment/{token}"


def _linked_session_submission_fields(
    db: Session,
    session_id: UUID | None,
) -> tuple[str | None, str | None]:
    if session_id is None:
        return None, None
    session = db.get(CalculationSession, session_id)
    if session is None:
        return None, None
    submitted_at = str(session.submitted_at) if session.submitted_at else None
    final_total = None
    ui_state = session.ui_state if isinstance(session.ui_state, dict) else {}
    last_result = ui_state.get("last_result") if isinstance(ui_state.get("last_result"), dict) else {}
    breakdown = last_result.get("breakdown") if isinstance(last_result.get("breakdown"), dict) else {}
    raw_total = breakdown.get("final_total")
    if raw_total is not None:
        final_total = str(raw_total)
    return submitted_at, final_total


def _find_assignment_for_session(db: Session, session_id: UUID) -> EworksQuoteAssignment | None:
    return db.scalar(
        select(EworksQuoteAssignment)
        .where(EworksQuoteAssignment.calculation_session_id == session_id)
        .order_by(EworksQuoteAssignment.id.desc())
        .limit(1)
    )


def _effective_assignment_status(row: EworksQuoteAssignment, session: CalculationSession | None) -> str:
    if row.status == "cancelled":
        return "cancelled"
    if session is not None and session.submitted_at is not None:
        if session.status in {"submitted", "revision_in_progress"} or session.locked:
            return "submitted"
    return row.status


def mark_linked_assignment_submitted(db: Session, session_id: UUID) -> EworksQuoteAssignment | None:
    """Mark the quote assignment linked to a submitted calculation session as submitted."""
    assignment = _find_assignment_for_session(db, session_id)
    if assignment is None or assignment.status == "cancelled":
        return None

    before_status = assignment.status
    if assignment.status != "submitted":
        assignment.status = "submitted"
        record_audit(
            db,
            actor=None,
            action="quote_assignment_submitted",
            entity_type="quote_assignment",
            entity_id=assignment.id,
            before={"status": before_status},
            after={"status": "submitted", "calculation_session_id": str(session_id)},
            metadata={
                "assignment_id": assignment.id,
                "quote_ref": assignment.quote_ref,
                "assignment_type": assignment.assignment_type,
            },
        )
        db.flush()
    return assignment


def _normalize_email(email: str | None) -> str | None:
    if not email:
        return None
    normalized = email.strip().lower()
    return normalized or None


def _serialize_appointment_assignment(
    assignee: dict[str, Any],
    *,
    quote: EworksQuote,
) -> dict[str, Any]:
    """Serialize an eWorks appointment assignee as a read-only assignment row."""
    appointment_id = assignee.get("appointment_id")
    synthetic_id = -(int(appointment_id)) if appointment_id is not None else -1
    return {
        "id": synthetic_id,
        "synced_quote_id": quote.id,
        "eworks_quote_id": quote.eworks_quote_id,
        "quote_ref": quote.quote_ref,
        "assigned_user_id": assignee.get("registered_user_id"),
        "assigned_user_email": assignee.get("user_email"),
        "assigned_user_name": assignee.get("user_name"),
        "assignment_type": "engineer",
        "assignee_kind": assignee.get("assignee_kind") or "external",
        "status": "assigned",
        "assignment_token": None,
        "assignment_token_created_at": None,
        "assignment_token_expires_at": None,
        "assignment_token_revoked_at": None,
        "assigned_by_user_id": None,
        "assigned_by_email": None,
        "assigned_at": assignee.get("start_at"),
        "notes": None,
        "source": "eworks_appointment",
        "is_derived": True,
        "is_read_only": True,
        "appointment_id": appointment_id,
        "appointment_start_at": assignee.get("start_at"),
        "appointment_end_at": assignee.get("end_at"),
        "appointment_status": assignee.get("status"),
        "appointment_type": assignee.get("appointment_type"),
        "job_ref": assignee.get("job_ref"),
        "assignment_link": None,
        "has_calculation_session": False,
        "calculation_session_id": None,
        "can_start_estimate": False,
        "can_view_submission": False,
    }


def _serialize_assignment(
    row: EworksQuoteAssignment,
    *,
    quote: EworksQuote | None = None,
    include_token: bool = False,
    current_user: AuthenticatedUser | None = None,
    db: Session | None = None,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": row.id,
        "synced_quote_id": row.synced_quote_id,
        "eworks_quote_id": row.eworks_quote_id,
        "quote_ref": row.quote_ref,
        "assigned_user_id": str(row.assigned_user_id) if row.assigned_user_id else None,
        "assigned_user_email": row.assigned_user_email,
        "assigned_user_name": row.assigned_user_name,
        "assignment_type": row.assignment_type,
        "assignee_kind": row.assignee_kind,
        "status": row.status,
        "assignment_token_created_at": str(row.assignment_token_created_at)
        if row.assignment_token_created_at
        else None,
        "assignment_token_expires_at": str(row.assignment_token_expires_at)
        if row.assignment_token_expires_at
        else None,
        "assignment_token_revoked_at": str(row.assignment_token_revoked_at)
        if row.assignment_token_revoked_at
        else None,
        "assigned_by_user_id": str(row.assigned_by_user_id) if row.assigned_by_user_id else None,
        "assigned_by_email": row.assigned_by_email,
        "assigned_at": str(row.assigned_at) if row.assigned_at else None,
        "notes": row.notes,
        "source": "manual",
        "is_derived": False,
        "is_read_only": False,
    }
    if include_token:
        data["assignment_token"] = row.assignment_token
    data["assignment_link"] = _assignment_link(row.assignment_token)
    data["has_calculation_session"] = row.calculation_session_id is not None
    data["calculation_session_id"] = str(row.calculation_session_id) if row.calculation_session_id else None
    data["can_start_estimate"] = _can_user_start_assignment(current_user, row) if current_user else False
    data["can_view_submission"] = False
    if db is not None and row.calculation_session_id is not None:
        submitted_at, final_total = _linked_session_submission_fields(db, row.calculation_session_id)
        data["submitted_at"] = submitted_at
        data["final_total"] = final_total
        session = db.get(CalculationSession, row.calculation_session_id)
        if session is not None:
            data["status"] = _effective_assignment_status(row, session)
            data["current_version_number"] = max(session.current_version_number, 1 if session.submitted_at else 0)
            data["revision_in_progress"] = session.revision_in_progress
            data["active_revision_reason"] = session.active_revision_reason
            data["can_revise"] = (
                session.status == "submitted" and session.locked and not session.revision_in_progress
            )
            data["can_continue_revision"] = session.revision_in_progress and not session.locked
            data["can_view_submission"] = bool(
                session.submitted_at is not None
                and session.status in ("submitted", "revision_in_progress")
            )
    if quote is not None:
        data["quote_summary"] = _quote_summary(quote)
    return data


def _get_quote_or_404(db: Session, quote_id: int) -> EworksQuote:
    quote = db.query(EworksQuote).filter(EworksQuote.id == quote_id).one_or_none()
    if quote is None:
        raise HTTPException(status_code=404, detail="Quote not found")
    return quote


def _as_uuid(value: UUID | str | None) -> UUID | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def _validate_assignee_user(db: Session, user_id: UUID | str, assignment_type: str) -> User:
    user_uuid = _as_uuid(user_id)
    user = db.query(User).filter(User.id == user_uuid, User.is_active.is_(True)).one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="Assigned user not found")
    expected_role = UserRole.ESTIMATOR.value if assignment_type == "estimator" else UserRole.ENGINEER.value
    if user.role != expected_role:
        raise HTTPException(
            status_code=400,
            detail=f"Assigned user must have role {expected_role} for assignment_type={assignment_type}",
        )
    return user


def list_assignable_users(db: Session) -> list[dict[str, Any]]:
    rows = (
        db.query(User)
        .filter(
            User.is_active.is_(True),
            User.role.in_([UserRole.ESTIMATOR.value, UserRole.ENGINEER.value]),
        )
        .order_by(User.full_name.asc(), User.email.asc())
        .all()
    )
    return [
        {
            "id": str(row.id),
            "name": row.full_name,
            "email": row.email,
            "role": row.role,
            "is_active": row.is_active,
        }
        for row in rows
    ]


def _list_manual_assignments_for_quote(db: Session, quote: EworksQuote) -> list[EworksQuoteAssignment]:
    return (
        db.query(EworksQuoteAssignment)
        .filter(EworksQuoteAssignment.synced_quote_id == quote.id)
        .order_by(EworksQuoteAssignment.assigned_at.desc(), EworksQuoteAssignment.id.desc())
        .all()
    )


def _find_active_manual_duplicate(
    db: Session,
    *,
    quote_id: int,
    assignment_type: str,
    email: str | None,
) -> EworksQuoteAssignment | None:
    normalized = _normalize_email(email)
    if not normalized:
        return None
    rows = (
        db.query(EworksQuoteAssignment)
        .filter(
            EworksQuoteAssignment.synced_quote_id == quote_id,
            EworksQuoteAssignment.assignment_type == assignment_type,
            EworksQuoteAssignment.status != "cancelled",
        )
        .all()
    )
    for row in rows:
        if _normalize_email(row.assigned_user_email) == normalized:
            return row
    return None


def build_unified_assignments_for_quote(db: Session, quote_id: int) -> list[dict[str, Any]]:
    """Return appointment-derived and manual assignments for manager display."""
    quote = _get_quote_or_404(db, quote_id)
    manual_rows = _list_manual_assignments_for_quote(db, quote)
    manual_items = [_serialize_assignment(row, quote=quote, include_token=True) for row in manual_rows]

    assignee = get_active_job_appointment_assignee(
        db,
        quote_id=quote.id,
        quote_ref=quote.quote_ref,
        eworks_quote_id=quote.eworks_quote_id,
    )
    items: list[dict[str, Any]] = []
    if assignee is not None:
        items.append(_serialize_appointment_assignment(assignee, quote=quote))
    items.extend(manual_items)
    return items


def list_assignments_for_quote(db: Session, quote_id: int) -> list[dict[str, Any]]:
    """Return manual quote assignments only; appointment assignee comes from safe detail."""
    quote = _get_quote_or_404(db, quote_id)
    rows = _list_manual_assignments_for_quote(db, quote)
    return [_serialize_assignment(row, quote=quote, include_token=True) for row in rows]


def _prepare_assignee_fields(
    db: Session,
    *,
    assignment_type: str,
    assignee_kind: str,
    assigned_user_id: Any,
    assigned_user_email: str | None,
    assigned_user_name: str | None,
    expires_at: datetime | None,
) -> tuple[Any, str | None, str | None, str | None, datetime | None, datetime | None]:
    token: str | None = None
    token_created_at: datetime | None = None
    token_expires_at: datetime | None = None

    if assignee_kind == "registered":
        user = _validate_assignee_user(db, assigned_user_id, assignment_type)
        assigned_user_id = user.id
        assigned_user_email = user.email
        assigned_user_name = user.full_name
    else:
        assigned_user_id = None
        token = secrets.token_urlsafe(32)
        token_created_at = _now()
        token_expires_at = expires_at or (token_created_at + timedelta(days=DEFAULT_TOKEN_DAYS))

    return (
        assigned_user_id,
        assigned_user_email,
        assigned_user_name,
        token,
        token_created_at,
        token_expires_at,
    )


def create_assignment(
    db: Session,
    *,
    quote_id: int,
    payload: dict[str, Any],
    current_user: AuthenticatedUser,
) -> dict[str, Any]:
    quote = _get_quote_or_404(db, quote_id)
    assignment_type = payload["assignment_type"]
    assignee_kind = payload["assignee_kind"]

    assigned_user_id = payload.get("assigned_user_id")
    assigned_user_email = payload.get("assigned_user_email")
    assigned_user_name = payload.get("assigned_user_name")
    notes = payload.get("notes")
    expires_at = payload.get("expires_at")

    if assignee_kind == "registered":
        user = _validate_assignee_user(db, assigned_user_id, assignment_type)
        assigned_user_email = user.email
    resolved_email = assigned_user_email

    existing = _find_active_manual_duplicate(
        db,
        quote_id=quote.id,
        assignment_type=assignment_type,
        email=resolved_email,
    )
    if existing is not None:
        before = _serialize_assignment(existing, quote=quote)
        if notes:
            existing.notes = notes
        existing.assigned_at = _now()
        db.flush()
        record_audit(
            db,
            actor=current_user,
            action="quote_assignment_updated",
            entity_type="quote_assignment",
            entity_id=existing.id,
            before=before,
            after=_serialize_assignment(existing, quote=quote),
            metadata={
                "quote_ref": quote.quote_ref,
                "reason": "duplicate_email_assignment_type",
            },
        )
        db.commit()
        db.refresh(existing)
        return _serialize_assignment(existing, quote=quote, include_token=True)

    (
        assigned_user_id,
        assigned_user_email,
        assigned_user_name,
        token,
        token_created_at,
        token_expires_at,
    ) = _prepare_assignee_fields(
        db,
        assignment_type=assignment_type,
        assignee_kind=assignee_kind,
        assigned_user_id=assigned_user_id,
        assigned_user_email=assigned_user_email,
        assigned_user_name=assigned_user_name,
        expires_at=expires_at,
    )

    row = EworksQuoteAssignment(
        synced_quote_id=quote.id,
        eworks_quote_id=quote.eworks_quote_id,
        quote_ref=quote.quote_ref,
        assigned_user_id=assigned_user_id,
        assigned_user_email=str(assigned_user_email) if assigned_user_email else None,
        assigned_user_name=assigned_user_name,
        assignment_type=assignment_type,
        assignee_kind=assignee_kind,
        status="assigned",
        assignment_token=token,
        assignment_token_created_at=token_created_at,
        assignment_token_expires_at=token_expires_at,
        assigned_by_user_id=_as_uuid(current_user.id),
        assigned_by_email=current_user.email,
        assigned_at=_now(),
        notes=notes,
    )
    db.add(row)
    db.flush()

    audit_after = _serialize_assignment(row, quote=quote)
    audit_after.pop("assignment_token", None)
    audit_after.pop("assignment_link", None)

    record_audit(
        db,
        actor=current_user,
        action="quote_assignment_created",
        entity_type="quote_assignment",
        entity_id=row.id,
        after=audit_after,
        metadata={
            "quote_ref": quote.quote_ref,
            "eworks_quote_id": quote.eworks_quote_id,
            "assignment_type": assignment_type,
            "assignee_kind": assignee_kind,
            "assigned_user_email": row.assigned_user_email,
        },
    )
    db.commit()
    db.refresh(row)
    return _serialize_assignment(row, quote=quote, include_token=True)


def override_assignment(
    db: Session,
    *,
    quote_id: int,
    payload: dict[str, Any],
    current_user: AuthenticatedUser,
) -> dict[str, Any]:
    """Explicitly replace active manual assignments of the same type; does not remove eWorks appointment."""
    quote = _get_quote_or_404(db, quote_id)
    assignment_type = payload["assignment_type"]
    assignee_kind = payload["assignee_kind"]
    assigned_user_id = payload.get("assigned_user_id")
    assigned_user_email = payload.get("assigned_user_email")
    assigned_user_name = payload.get("assigned_user_name")
    notes = payload.get("notes")
    expires_at = payload.get("expires_at")

    active_rows = (
        db.query(EworksQuoteAssignment)
        .filter(
            EworksQuoteAssignment.synced_quote_id == quote.id,
            EworksQuoteAssignment.assignment_type == assignment_type,
            EworksQuoteAssignment.status != "cancelled",
        )
        .all()
    )
    for row in active_rows:
        before = _serialize_assignment(row, quote=quote)
        row.status = "cancelled"
        row.assignment_token_revoked_at = _now()
        record_audit(
            db,
            actor=current_user,
            action="quote_assignment_revoked",
            entity_type="quote_assignment",
            entity_id=row.id,
            before=before,
            after=_serialize_assignment(row, quote=quote),
            metadata={
                "quote_ref": quote.quote_ref,
                "reason": "override_replacement",
            },
        )

    (
        assigned_user_id,
        assigned_user_email,
        assigned_user_name,
        token,
        token_created_at,
        token_expires_at,
    ) = _prepare_assignee_fields(
        db,
        assignment_type=assignment_type,
        assignee_kind=assignee_kind,
        assigned_user_id=assigned_user_id,
        assigned_user_email=assigned_user_email,
        assigned_user_name=assigned_user_name,
        expires_at=expires_at,
    )

    row = EworksQuoteAssignment(
        synced_quote_id=quote.id,
        eworks_quote_id=quote.eworks_quote_id,
        quote_ref=quote.quote_ref,
        assigned_user_id=assigned_user_id,
        assigned_user_email=str(assigned_user_email) if assigned_user_email else None,
        assigned_user_name=assigned_user_name,
        assignment_type=assignment_type,
        assignee_kind=assignee_kind,
        status="assigned",
        assignment_token=token,
        assignment_token_created_at=token_created_at,
        assignment_token_expires_at=token_expires_at,
        assigned_by_user_id=_as_uuid(current_user.id),
        assigned_by_email=current_user.email,
        assigned_at=_now(),
        notes=notes,
    )
    db.add(row)
    db.flush()

    audit_after = _serialize_assignment(row, quote=quote)
    audit_after.pop("assignment_token", None)
    audit_after.pop("assignment_link", None)

    record_audit(
        db,
        actor=current_user,
        action="quote_assignment_overridden",
        entity_type="quote_assignment",
        entity_id=row.id,
        after=audit_after,
        metadata={
            "quote_ref": quote.quote_ref,
            "eworks_quote_id": quote.eworks_quote_id,
            "assignment_type": assignment_type,
            "assignee_kind": assignee_kind,
            "assigned_user_email": row.assigned_user_email,
            "replaced_manual_count": len(active_rows),
        },
    )
    db.commit()
    db.refresh(row)
    return _serialize_assignment(row, quote=quote, include_token=True)


def list_assignments_for_user(db: Session, user: AuthenticatedUser) -> list[dict[str, Any]]:
    q = db.query(EworksQuoteAssignment, EworksQuote).join(
        EworksQuote, EworksQuote.id == EworksQuoteAssignment.synced_quote_id
    )
    if user.role == UserRole.ADMIN:
        rows = q.order_by(EworksQuoteAssignment.assigned_at.desc()).all()
    elif user.role == UserRole.ESTIMATOR:
        rows = (
            q.filter(
                EworksQuoteAssignment.assigned_user_id == _as_uuid(user.id),
                EworksQuoteAssignment.assignment_type == "estimator",
                EworksQuoteAssignment.status != "cancelled",
            )
            .order_by(EworksQuoteAssignment.assigned_at.desc())
            .all()
        )
    elif user.role == UserRole.ENGINEER:
        rows = (
            q.filter(
                EworksQuoteAssignment.assigned_user_id == _as_uuid(user.id),
                EworksQuoteAssignment.assignment_type == "engineer",
                EworksQuoteAssignment.status != "cancelled",
            )
            .order_by(EworksQuoteAssignment.assigned_at.desc())
            .all()
        )
    else:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    return [
        _serialize_assignment(assignment, quote=quote, current_user=user, db=db)
        for assignment, quote in rows
    ]


def get_assignment_by_token(db: Session, token: str) -> EworksQuoteAssignment:
    row = (
        db.query(EworksQuoteAssignment)
        .filter(EworksQuoteAssignment.assignment_token == token)
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if row.assignment_token_revoked_at is not None:
        raise HTTPException(status_code=410, detail="Assignment link has been revoked")
    expires_at = _as_utc(row.assignment_token_expires_at)
    if expires_at and expires_at < _now():
        raise HTTPException(status_code=410, detail="Assignment link has expired")
    if row.status == "cancelled":
        raise HTTPException(status_code=410, detail="Assignment has been cancelled")
    return row


def build_public_assignment_read(db: Session, row: EworksQuoteAssignment) -> dict[str, Any]:
    quote = _get_quote_or_404(db, row.synced_quote_id)
    summary = _quote_summary(quote)
    assigned_by_name = row.assigned_by_email
    if row.assigned_by_user_id:
        assigner = db.query(User).filter(User.id == row.assigned_by_user_id).one_or_none()
        if assigner:
            assigned_by_name = assigner.full_name or assigner.email
    return {
        "assignment_id": row.id,
        "assignment_type": row.assignment_type,
        "assignee_kind": row.assignee_kind,
        "status": row.status,
        "assigned_user_name": row.assigned_user_name,
        "assigned_user_email": row.assigned_user_email,
        "assigned_by_name": assigned_by_name,
        "assigned_at": str(row.assigned_at) if row.assigned_at else None,
        "notes": row.notes,
        "quote_ref": summary["quote_ref"],
        "customer_name": summary["customer_name"],
        "site_address": summary["site_address"],
        "quote_date": summary["quote_date"],
        "expiry_date": summary["expiry_date"],
        "description": summary["description"],
        "tags": summary["tags"],
    }


def revoke_assignment(db: Session, assignment_id: int, current_user: AuthenticatedUser) -> dict[str, Any]:
    row = db.query(EworksQuoteAssignment).filter(EworksQuoteAssignment.id == assignment_id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    before = _serialize_assignment(row)
    row.status = "cancelled"
    row.assignment_token_revoked_at = _now()
    db.flush()
    record_audit(
        db,
        actor=current_user,
        action="quote_assignment_revoked",
        entity_type="quote_assignment",
        entity_id=row.id,
        before=before,
        after=_serialize_assignment(row),
        metadata={
            "quote_ref": row.quote_ref,
            "eworks_quote_id": row.eworks_quote_id,
            "assignment_type": row.assignment_type,
            "assignee_kind": row.assignee_kind,
            "assigned_user_email": row.assigned_user_email,
        },
    )
    db.commit()
    db.refresh(row)
    return _serialize_assignment(row, include_token=True)


def update_assignment_status(
    db: Session,
    assignment_id: int,
    status: str,
    current_user: AuthenticatedUser,
) -> dict[str, Any]:
    if status not in ASSIGNMENT_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid assignment status")
    row = db.query(EworksQuoteAssignment).filter(EworksQuoteAssignment.id == assignment_id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if current_user.role not in {UserRole.ADMIN, UserRole.MANAGER}:
        if row.assigned_user_id != _as_uuid(current_user.id):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        if current_user.role == UserRole.ESTIMATOR and row.assignment_type != "estimator":
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        if current_user.role == UserRole.ENGINEER and row.assignment_type != "engineer":
            raise HTTPException(status_code=403, detail="Insufficient permissions")

    before = _serialize_assignment(row)
    row.status = status
    db.flush()
    record_audit(
        db,
        actor=current_user,
        action="quote_assignment_status_updated",
        entity_type="quote_assignment",
        entity_id=row.id,
        before=before,
        after=_serialize_assignment(row),
        metadata={
            "quote_ref": row.quote_ref,
            "eworks_quote_id": row.eworks_quote_id,
            "assignment_type": row.assignment_type,
            "status": status,
        },
    )
    db.commit()
    db.refresh(row)
    quote = _get_quote_or_404(db, row.synced_quote_id)
    return _serialize_assignment(row, quote=quote)


def submit_public_assignment(db: Session, token: str, notes: str | None) -> dict[str, Any]:
    row = get_assignment_by_token(db, token)
    before = _serialize_assignment(row)
    row.status = "submitted"
    if notes:
        existing = row.notes or ""
        row.notes = f"{existing}\nExternal note: {notes}".strip()
    db.flush()
    record_audit(
        db,
        actor=None,
        action="quote_assignment_status_updated",
        entity_type="quote_assignment",
        entity_id=row.id,
        before=before,
        after=_serialize_assignment(row),
        metadata={
            "quote_ref": row.quote_ref,
            "eworks_quote_id": row.eworks_quote_id,
            "assignment_type": row.assignment_type,
            "status": "submitted",
            "source": "public_submit",
        },
    )
    db.commit()
    db.refresh(row)
    return build_public_assignment_read(db, row)


def _build_resume_url(session_id: UUID, session_token: str) -> str:
    params = urlencode({"session_id": str(session_id), "token": session_token})
    return f"/eworks/calculate?{params}"


def _can_user_start_assignment(user: AuthenticatedUser | None, row: EworksQuoteAssignment) -> bool:
    if user is None:
        return False
    if row.status == "cancelled" or row.assignee_kind != "registered":
        return False
    if user.role == UserRole.ADMIN:
        return True
    if row.assigned_user_id != _as_uuid(user.id):
        return False
    if user.role == UserRole.ESTIMATOR and row.assignment_type == "estimator":
        return True
    if user.role == UserRole.ENGINEER and row.assignment_type == "engineer":
        return True
    return False


def _assert_user_can_start_assignment(user: AuthenticatedUser, row: EworksQuoteAssignment) -> None:
    if row.status == "cancelled":
        raise HTTPException(status_code=410, detail="Assignment has been cancelled")
    if row.assignee_kind != "registered":
        raise HTTPException(status_code=403, detail="Only registered assignments can start an estimate")
    if user.role == UserRole.MANAGER:
        raise HTTPException(status_code=403, detail="Managers cannot start assignments")
    if user.role == UserRole.CLIENT:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if not _can_user_start_assignment(user, row):
        raise HTTPException(status_code=403, detail="Insufficient permissions")


def _quote_site_address(quote: EworksQuote) -> str:
    summary = _quote_summary(quote)
    address = summary.get("site_address")
    if isinstance(address, str) and address.strip():
        return address.strip()
    return "Address not specified"


def _quote_expires_at(quote: EworksQuote) -> datetime:
    default = _now() + timedelta(days=DEFAULT_TOKEN_DAYS)
    raw = quote.expiry_date
    if raw:
        text = str(raw).strip()
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
            try:
                parsed = datetime.strptime(text.replace("Z", ""), fmt.replace("Z", ""))
                candidate = parsed.replace(tzinfo=timezone.utc) + timedelta(hours=23, minutes=59)
                if candidate > _now():
                    return candidate
            except ValueError:
                continue
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            if parsed > _now():
                return parsed
        except ValueError:
            pass
    return default


def _default_trade(db: Session) -> Trade:
    trade = db.scalar(select(Trade).where(Trade.is_active.is_(True)).order_by(Trade.name).limit(1))
    if trade is None:
        trade = db.scalar(select(Trade).order_by(Trade.name).limit(1))
    if trade is None:
        raise HTTPException(status_code=400, detail="No trade configured for estimate session")
    return trade


def _resolve_quote_customer_name(db: Session, quote: EworksQuote) -> str:
    name = (quote.customer_name or "").strip()
    if name:
        return name
    if quote.customer_id is not None:
        looked_up = lookup_customer_name_by_id(db, quote.customer_id)
        if looked_up:
            return looked_up
    return "Unknown Customer"


def _create_calculation_session_for_assignment(
    db: Session,
    *,
    assignment: EworksQuoteAssignment,
    quote: EworksQuote,
) -> CalculationSession:
    customer_name = _resolve_quote_customer_name(db, quote)
    client, _, _ = get_or_create_client_for_import(db, customer_name)
    trade = _default_trade(db)
    rule = try_resolve_rate_rule(db, client.id, trade.id)

    quote_ref = quote.quote_ref or f"Q{quote.eworks_quote_id}"
    job_number = str(quote.eworks_quote_id)
    property_address = _quote_site_address(quote)
    description = (quote.description or "").strip() or None
    scope_plain = html_to_plain_text(description) if description else None
    notes = (assignment.notes or "").strip() or None

    payload = EworksLinkPayload(
        source="assignment",
        quote_number=quote_ref,
        job_number=job_number,
        external_job_id=str(quote.eworks_quote_id),
        client=customer_name,
        trade=trade.name,
        property_address=property_address,
        original_job_description=description,
        quote_description=description,
        scope=scope_plain,
        other_notes=notes,
        expires_at=_quote_expires_at(quote),
    )
    step1 = payload_to_step1(payload, client, trade, client_display_name=customer_name)
    step1 = apply_appointment_engineer_name_to_step1(
        db,
        step1,
        quote_ref=quote_ref,
        eworks_quote_id=quote.eworks_quote_id,
    )
    payload_dict = payload.model_dump(mode="json")
    payload_dict["eworks_quote_id"] = quote.eworks_quote_id
    payload_dict["assignment_id"] = assignment.id
    payload_dict["synced_quote_id"] = quote.id

    initial_step2 = Step2Snapshot(scope=scope_plain) if scope_plain else Step2Snapshot()
    initial_step2 = apply_questionnaire_defaults(initial_step2, trade_name=trade.name, default_skill=True)

    session = CalculationSession(
        session_token=secrets.token_hex(32),
        idempotency_key=f"assignment.session.{assignment.id}",
        source="assignment",
        payload_snapshot=payload_dict,
        step1_snapshot=step1.model_dump(mode="json"),
        step2_snapshot=initial_step2.model_dump(mode="json"),
        ui_state=SessionUiState().model_dump(mode="json"),
        client_id=client.id,
        trade_id=trade.id,
        rate_rule_id=rule.id if rule else None,
        eworks_customer_snapshot=None,
        expires_at=_as_utc(payload.expires_at) or _now() + timedelta(days=DEFAULT_TOKEN_DAYS),
    )
    db.add(session)
    db.flush()
    return session


def _get_linked_session(db: Session, row: EworksQuoteAssignment) -> CalculationSession | None:
    if row.calculation_session_id is None:
        return None
    return db.get(CalculationSession, row.calculation_session_id)


def _build_start_estimate_response(row: EworksQuoteAssignment, session: CalculationSession) -> dict[str, Any]:
    return {
        "session_id": str(session.id),
        "session_token": session.session_token,
        "resume_url": _build_resume_url(session.id, session.session_token),
        "assignment_id": row.id,
        "quote_ref": row.quote_ref,
    }


def _ensure_assignment_calculation_session(
    db: Session,
    row: EworksQuoteAssignment,
    *,
    actor: AuthenticatedUser | None,
    audit_action: str,
    audit_metadata: dict[str, Any] | None = None,
) -> tuple[CalculationSession, bool]:
    quote = _get_quote_or_404(db, row.synced_quote_id)
    existing = _get_linked_session(db, row)
    created = False
    if existing is None:
        existing = _create_calculation_session_for_assignment(db, assignment=row, quote=quote)
        row.calculation_session_id = existing.id
        if row.status == "assigned":
            row.status = "in_progress"
        created = True
        metadata = {
            "assignment_id": row.id,
            "quote_ref": row.quote_ref,
            "eworks_quote_id": row.eworks_quote_id,
            "assignment_type": row.assignment_type,
            "assigned_user_email": row.assigned_user_email,
            **(audit_metadata or {}),
        }
        record_audit(
            db,
            actor=actor,
            action=audit_action,
            entity_type="quote_assignment",
            entity_id=row.id,
            after={
                "assignment_id": row.id,
                "calculation_session_id": str(existing.id),
                "quote_ref": row.quote_ref,
                "status": row.status,
            },
            metadata=metadata,
        )
    return existing, created


def start_assignment_estimate(
    db: Session,
    assignment_id: int,
    current_user: AuthenticatedUser,
) -> dict[str, Any]:
    row = db.query(EworksQuoteAssignment).filter(EworksQuoteAssignment.id == assignment_id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Assignment not found")

    _assert_user_can_start_assignment(current_user, row)
    session, created = _ensure_assignment_calculation_session(
        db,
        row,
        actor=current_user,
        audit_action="quote_assignment_started",
    )

    db.commit()
    db.refresh(row)
    db.refresh(session)

    response = _build_start_estimate_response(row, session)
    response["created"] = created
    return response


def start_public_assignment_estimate(db: Session, assignment_token: str) -> dict[str, Any]:
    row = get_assignment_by_token(db, assignment_token)
    if row.assignee_kind != "external":
        raise HTTPException(
            status_code=403,
            detail="Public estimate start is only available for external assignments",
        )

    session, _created = _ensure_assignment_calculation_session(
        db,
        row,
        actor=None,
        audit_action="quote_assignment_public_started",
        audit_metadata={"assignee_kind": "external"},
    )

    db.commit()
    db.refresh(row)
    db.refresh(session)
    return _build_start_estimate_response(row, session)
