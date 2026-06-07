"""Fetch eWorks Job detail payloads and sync appointment rows."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.eworks_sync import EworksJob
from app.services.eworks_job_appointment_service import sync_job_appointments
from app.services.eworks_quotes_jobs_api_service import fetch_job_detail
from app.services.eworks_sync_service import _safe_float, _safe_int, _safe_str

logger = logging.getLogger(__name__)


@dataclass
class JobDetailFetchStats:
    attempted: int = 0
    success: int = 0
    failed: int = 0


@dataclass
class JobAppointmentBackfillSummary:
    jobs_scanned: int = 0
    jobs_with_total_appointments: int = 0
    detail_fetches_attempted: int = 0
    detail_fetches_success: int = 0
    detail_fetches_failed: int = 0
    appointments_created: int = 0
    appointments_updated: int = 0


def parse_total_appointments(raw: dict[str, Any] | None) -> int:
    if not isinstance(raw, dict):
        return 0
    value = raw.get("total_appointments")
    if value is None or value == "":
        return 0
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return 0


def extract_job_appointment_summary_fields(raw: dict[str, Any]) -> dict[str, Any]:
    completed = raw.get("completed_appointments")
    completed_count = None
    if completed is not None and completed != "":
        try:
            completed_count = max(int(completed), 0)
        except (TypeError, ValueError):
            completed_count = None

    return {
        "total_appointments": parse_total_appointments(raw),
        "completed_appointments": completed_count,
        "total_appointment_time": _safe_str(raw.get("total_appointment_time"), 100),
        "total_appointment_cost": _safe_float(raw.get("total_appointment_cost")),
    }


def should_fetch_job_detail(list_payload: dict[str, Any]) -> bool:
    if not settings.eworks_sync_job_details_enabled:
        return False
    if settings.eworks_sync_job_details_only_with_appointments:
        return parse_total_appointments(list_payload) > 0
    return True


def job_needs_detail_fetch(job: EworksJob) -> bool:
    total = job.total_appointments
    if total is None and isinstance(job.raw_payload, dict):
        total = parse_total_appointments(job.raw_payload)
    if settings.eworks_sync_job_details_only_with_appointments:
        return bool(total and total > 0)
    return True


def apply_job_detail_payload(
    db: Session,
    job: EworksJob,
    detail_payload: dict[str, Any],
    *,
    synced_at: datetime | None = None,
) -> tuple[int, int]:
    """Store detail payload and sync appointments. Returns (created, updated) appointment counts."""
    from app.models.eworks_sync import EworksJobAppointment

    synced = synced_at or datetime.now(timezone.utc)
    before_ids = {
        row.id
        for row in db.query(EworksJobAppointment.id)
        .filter(EworksJobAppointment.eworks_job_id == job.eworks_job_id)
        .all()
    }

    job.raw_detail_payload = detail_payload
    job.detail_synced_at = synced
    summary_fields = extract_job_appointment_summary_fields(detail_payload)
    for key, value in summary_fields.items():
        setattr(job, key, value)

    sync_job_appointments(db, job, raw_payload=detail_payload, synced_at=synced)
    db.flush()

    after_rows = (
        db.query(EworksJobAppointment)
        .filter(EworksJobAppointment.eworks_job_id == job.eworks_job_id)
        .all()
    )
    created = sum(1 for row in after_rows if row.id not in before_ids)
    updated = sum(1 for row in after_rows if row.id in before_ids)
    return created, updated


def fetch_and_apply_job_detail(
    db: Session,
    job: EworksJob,
    *,
    synced_at: datetime | None = None,
) -> tuple[bool, int, int]:
    """Fetch job detail from eWorks and apply appointments. Returns (success, created, updated)."""
    detail = fetch_job_detail(job.eworks_job_id)
    created, updated = apply_job_detail_payload(db, job, detail, synced_at=synced_at)
    return True, created, updated


def maybe_fetch_job_detail_after_list_upsert(
    db: Session,
    job: EworksJob,
    list_payload: dict[str, Any],
    *,
    synced_at: datetime | None = None,
    stats: JobDetailFetchStats | None = None,
    limit_remaining: int | None = None,
) -> None:
    if not should_fetch_job_detail(list_payload):
        return
    if limit_remaining is not None and limit_remaining <= 0:
        return

    if stats is not None:
        stats.attempted += 1

    try:
        fetch_and_apply_job_detail(db, job, synced_at=synced_at)
        if stats is not None:
            stats.success += 1
    except Exception:
        logger.exception(
            "Failed to fetch/apply eWorks Job detail for id=%s; continuing job sync",
            job.eworks_job_id,
        )
        if stats is not None:
            stats.failed += 1


def backfill_job_appointments_from_details(
    db: Session,
    *,
    limit: int | None = None,
) -> JobAppointmentBackfillSummary:
    summary = JobAppointmentBackfillSummary()
    rows = db.query(EworksJob).order_by(EworksJob.synced_at.desc()).all()
    synced = datetime.now(timezone.utc)

    for job in rows:
        summary.jobs_scanned += 1
        if not job_needs_detail_fetch(job):
            continue
        summary.jobs_with_total_appointments += 1
        if limit is not None and summary.detail_fetches_attempted >= limit:
            break

        summary.detail_fetches_attempted += 1
        try:
            success, created, updated = fetch_and_apply_job_detail(db, job, synced_at=synced)
            if success:
                summary.detail_fetches_success += 1
                summary.appointments_created += created
                summary.appointments_updated += updated
        except Exception:
            logger.exception("Backfill failed for eWorks job id=%s", job.eworks_job_id)
            summary.detail_fetches_failed += 1

    db.commit()
    return summary
