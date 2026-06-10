"""Classify engineer eWorks appointments as assigned estimates vs assigned jobs."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.eworks_sync import EworksJob, EworksJobAppointment, EworksQuote


def resolve_quote_ref_for_job(db: Session, job: EworksJob) -> str | None:
    if job.eworks_quote_id is None:
        return None
    quote = (
        db.query(EworksQuote)
        .filter(EworksQuote.eworks_quote_id == job.eworks_quote_id)
        .order_by(EworksQuote.id.desc())
        .first()
    )
    if quote is None:
        return None
    return (quote.quote_ref or "").strip() or None


def is_quote_linked_assignment(
    db: Session,
    job: EworksJob,
    _appointment: EworksJobAppointment,
    *,
    quote_ref: str | None = None,
) -> bool:
    """True when an appointment belongs on Assigned Estimates, not Assigned Jobs."""
    if job.eworks_quote_id is not None:
        return True
    resolved_ref = (quote_ref or "").strip() or resolve_quote_ref_for_job(db, job)
    return bool(resolved_ref)
