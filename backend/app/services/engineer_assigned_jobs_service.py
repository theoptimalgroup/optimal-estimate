"""Engineer assigned jobs sourced from synced eWorks job appointments (read-only)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.auth.types import AuthenticatedUser
from app.models.eworks_sync import EworksJob, EworksJobAppointment
from app.services.engineer_assignment_routing import is_quote_linked_assignment, resolve_quote_ref_for_job
from app.services.eworks_job_appointment_service import is_cancelled_appointment_status
from app.services.quote_assignment_service import _as_uuid, _normalize_email
from app.utils.html_text import html_to_plain_text


def _appointment_user_matches(
    appointment: EworksJobAppointment,
    *,
    user: AuthenticatedUser,
) -> bool:
    """Match appointment assignee to logged-in engineer by email only."""
    if not appointment.user_email:
        return False
    return _normalize_email(appointment.user_email) == _normalize_email(user.email)


def build_engineer_assigned_job_read(
    db: Session,
    job: EworksJob,
    appointment: EworksJobAppointment,
) -> dict:
    total = None
    if job.total is not None:
        total = str(job.total)
    return {
        "id": job.id,
        "eworks_job_id": job.eworks_job_id,
        "job_ref": job.job_ref,
        "eworks_quote_id": job.eworks_quote_id,
        "quote_ref": resolve_quote_ref_for_job(db, job),
        "customer_name": job.customer_name,
        "address": job.address,
        "status": job.status,
        "status_name": job.status_name,
        "job_date": job.job_date,
        "description": html_to_plain_text(job.description) or None,
        "total": total,
        "appointment_user_name": appointment.user_name,
        "appointment_user_email": appointment.user_email,
        "appointment_type": appointment.appointment_type,
        "appointment_status": appointment.status,
        "appointment_start_at": appointment.start_at,
        "appointment_end_at": appointment.end_at,
        "source": "eworks_appointment",
    }


def list_assigned_jobs_for_engineer(db: Session, user: AuthenticatedUser) -> list[dict]:
    user_id = _as_uuid(user.id)
    if user_id is None:
        return []

    rows = (
        db.query(EworksJob, EworksJobAppointment)
        .join(EworksJobAppointment, EworksJob.active_appointment_id == EworksJobAppointment.id)
        .order_by(EworksJobAppointment.start_at.desc(), EworksJob.synced_at.desc())
        .all()
    )

    results: list[dict] = []
    for job, appointment in rows:
        if is_cancelled_appointment_status(appointment.status):
            continue
        if not _appointment_user_matches(appointment, user=user):
            continue
        if is_quote_linked_assignment(db, job, appointment):
            continue
        results.append(build_engineer_assigned_job_read(db, job, appointment))
    return results
