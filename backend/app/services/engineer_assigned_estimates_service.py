"""Engineer assigned estimates: manual quote assignments and quote-linked appointments."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.auth.types import AuthenticatedUser
from app.core.security import UserRole
from app.models.eworks_sync import EworksJob, EworksJobAppointment, EworksQuote, EworksQuoteAppointment
from app.models.quote_assignment import EworksQuoteAssignment
from app.services.engineer_assignment_routing import is_quote_linked_assignment
from app.services.eworks_job_appointment_service import is_cancelled_appointment_status
from app.services.quote_assignment_service import (
    _as_uuid,
    _normalize_email,
    _serialize_appointment_assignment,
    _serialize_assignment,
)


def _appointment_user_matches(
    db: Session,
    appointment: EworksJobAppointment | EworksQuoteAppointment,
    *,
    user: AuthenticatedUser,
) -> bool:
    user_id = _as_uuid(user.id)
    if user_id is not None and appointment.user_email:
        from app.services.eworks_job_appointment_service import _match_registered_user_by_email

        matched_user = _match_registered_user_by_email(db, appointment.user_email)
        if matched_user is not None and matched_user.id == user_id:
            return True

    if not appointment.user_email:
        return False
    return _normalize_email(appointment.user_email) == _normalize_email(user.email)


def _quote_for_job(db: Session, job: EworksJob) -> EworksQuote | None:
    if job.eworks_quote_id is None:
        return None
    return (
        db.query(EworksQuote)
        .filter(EworksQuote.eworks_quote_id == job.eworks_quote_id)
        .order_by(EworksQuote.id.desc())
        .first()
    )


def _build_assignee_from_job_appointment(
    db: Session,
    *,
    job: EworksJob,
    appointment: EworksJobAppointment,
) -> dict[str, Any]:
    from app.services.eworks_job_appointment_service import _build_assignee_from_appointment, _appointment_row_to_safe

    safe = _appointment_row_to_safe(appointment)
    return dict(_build_assignee_from_appointment(db, job=job, appointment=safe))


def _build_assignee_from_quote_appointment(
    db: Session,
    *,
    quote: EworksQuote,
    appointment: EworksQuoteAppointment,
) -> dict[str, Any]:
    from app.services.eworks_job_appointment_service import _match_registered_user_by_email

    matched_user = _match_registered_user_by_email(db, appointment.user_email)
    assignee_kind = "registered" if matched_user is not None else "external"
    return {
        "user_name": appointment.user_name,
        "user_email": appointment.user_email,
        "appointment_type": appointment.appointment_type,
        "status": appointment.status,
        "start_at": appointment.start_at,
        "end_at": appointment.end_at,
        "is_sales_appointment": appointment.is_sales_appointment,
        "source": "eworks_appointment",
        "appointment_id": appointment.appointment_id,
        "registered_user_id": str(matched_user.id) if matched_user is not None else None,
        "assignee_kind": assignee_kind,
        "job_ref": None,
    }


def _list_manual_engineer_assignments(db: Session, user: AuthenticatedUser) -> list[dict[str, Any]]:
    user_id = _as_uuid(user.id)
    if user_id is None:
        return []
    rows = (
        db.query(EworksQuoteAssignment, EworksQuote)
        .join(EworksQuote, EworksQuote.id == EworksQuoteAssignment.synced_quote_id)
        .filter(
            EworksQuoteAssignment.assigned_user_id == user_id,
            EworksQuoteAssignment.assignment_type == "engineer",
            EworksQuoteAssignment.status != "cancelled",
        )
        .order_by(EworksQuoteAssignment.assigned_at.desc())
        .all()
    )
    return [
        _serialize_assignment(assignment, quote=quote, current_user=user, db=db)
        for assignment, quote in rows
    ]


def _list_appointment_estimate_assignments(db: Session, user: AuthenticatedUser) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen: set[tuple[int, int | None]] = set()

    job_rows = (
        db.query(EworksJob, EworksJobAppointment)
        .join(EworksJobAppointment, EworksJob.active_appointment_id == EworksJobAppointment.id)
        .order_by(EworksJobAppointment.start_at.desc(), EworksJob.synced_at.desc())
        .all()
    )
    for job, appointment in job_rows:
        if is_cancelled_appointment_status(appointment.status):
            continue
        if not _appointment_user_matches(db, appointment, user=user):
            continue
        if not is_quote_linked_assignment(db, job, appointment):
            continue
        quote = _quote_for_job(db, job)
        if quote is None:
            continue
        key = (quote.id, appointment.appointment_id)
        if key in seen:
            continue
        seen.add(key)
        assignee = _build_assignee_from_job_appointment(db, job=job, appointment=appointment)
        assignee["eworks_job_id"] = job.eworks_job_id
        item = _serialize_appointment_assignment(
            assignee, quote=quote, current_user=user, db=db
        )
        results.append(item)

    quote_rows = (
        db.query(EworksQuoteAppointment, EworksQuote)
        .join(EworksQuote, EworksQuote.eworks_quote_id == EworksQuoteAppointment.eworks_quote_id)
        .order_by(EworksQuoteAppointment.start_at.desc(), EworksQuoteAppointment.id.desc())
        .all()
    )
    for appointment, quote in quote_rows:
        if is_cancelled_appointment_status(appointment.status):
            continue
        if not _appointment_user_matches(db, appointment, user=user):
            continue
        key = (quote.id, appointment.appointment_id)
        if key in seen:
            continue
        seen.add(key)
        assignee = _build_assignee_from_quote_appointment(db, quote=quote, appointment=appointment)
        item = _serialize_appointment_assignment(
            assignee, quote=quote, current_user=user, db=db
        )
        results.append(item)

    return results


def list_assigned_estimates_for_engineer(db: Session, user: AuthenticatedUser) -> list[dict[str, Any]]:
    if user.role != UserRole.ENGINEER:
        return []
    manual_items = _list_manual_engineer_assignments(db, user)
    appointment_items = _list_appointment_estimate_assignments(db, user)
    manual_quote_ids = {item["synced_quote_id"] for item in manual_items}
    merged = list(manual_items)
    for item in appointment_items:
        if item["synced_quote_id"] in manual_quote_ids:
            continue
        merged.append(item)
    merged.sort(
        key=lambda row: row.get("assigned_at") or row.get("appointment_start_at") or "",
        reverse=True,
    )
    return merged
