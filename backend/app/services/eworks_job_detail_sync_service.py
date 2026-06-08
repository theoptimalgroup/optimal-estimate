"""Fetch eWorks Job detail payloads and sync appointment rows."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Query, Session

from app.core.config import settings
from app.models.eworks_sync import EworksJob
from app.services.eworks_job_appointment_service import (
    extract_job_appointments_from_raw,
    sync_job_appointments,
)
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
    appointments_found: int = 0
    sales_appointments_found: int = 0
    detail_fetches_attempted: int = 0
    detail_fetches_success: int = 0
    detail_fetches_failed: int = 0
    appointments_created: int = 0
    appointments_updated: int = 0
    failed: int = 0
    skipped: int = 0
    next_offset: int = 0
    has_more: bool = False
    elapsed_seconds: float = 0.0
    stopped_reason: str = "completed"


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


def _stored_detail_has_appointments(job: EworksJob) -> bool:
    if not isinstance(job.raw_detail_payload, dict):
        return False
    extracted = extract_job_appointments_from_raw(job.raw_detail_payload)
    return len(extracted) > 0


def _count_sales_appointments(appointments: list[dict[str, Any]]) -> int:
    return sum(1 for item in appointments if item.get("is_sales_appointment"))


def apply_job_detail_payload(
    db: Session,
    job: EworksJob,
    detail_payload: dict[str, Any],
    *,
    synced_at: datetime | None = None,
) -> tuple[int, int, int]:
    """Store detail payload and sync appointments. Returns (found, created, updated)."""
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

    extracted = extract_job_appointments_from_raw(detail_payload)
    sync_job_appointments(db, job, raw_payload=detail_payload, synced_at=synced)
    db.flush()

    after_rows = (
        db.query(EworksJobAppointment)
        .filter(EworksJobAppointment.eworks_job_id == job.eworks_job_id)
        .all()
    )
    created = sum(1 for row in after_rows if row.id not in before_ids)
    updated = sum(1 for row in after_rows if row.id in before_ids)
    return len(extracted), created, updated


def fetch_and_apply_job_detail(
    db: Session,
    job: EworksJob,
    *,
    synced_at: datetime | None = None,
) -> tuple[bool, int, int, int]:
    """Fetch job detail from eWorks and apply appointments. Returns (success, found, created, updated)."""
    detail, _rate_limited = fetch_job_detail(job.eworks_job_id)
    found, created, updated = apply_job_detail_payload(db, job, detail, synced_at=synced_at)
    return True, found, created, updated


def sync_job_appointments_from_stored_detail(
    db: Session,
    job: EworksJob,
    *,
    synced_at: datetime | None = None,
) -> tuple[int, int, int]:
    """Sync appointments from an already stored raw_detail_payload."""
    if not isinstance(job.raw_detail_payload, dict):
        return 0, 0, 0
    return apply_job_detail_payload(db, job, job.raw_detail_payload, synced_at=synced_at)


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
            "Failed to fetch/apply eWorks Job detail for id=%s ref=%s; continuing job sync",
            job.eworks_job_id,
            job.job_ref or "—",
        )
        if stats is not None:
            stats.failed += 1


def _build_job_backfill_query(
    db: Session,
    *,
    job_ref: str | None = None,
    eworks_job_id: int | None = None,
) -> Query:
    query = db.query(EworksJob).order_by(EworksJob.synced_at.desc())
    if job_ref:
        return query.filter(EworksJob.job_ref == job_ref)
    if eworks_job_id is not None:
        return query.filter(EworksJob.eworks_job_id == eworks_job_id)
    return query


def _process_job_appointment_backfill(
    db: Session,
    job: EworksJob,
    summary: JobAppointmentBackfillSummary,
    *,
    fetch_missing: bool,
    synced: datetime,
) -> None:
    if not job.eworks_job_id:
        summary.skipped += 1
        return

    try:
        if _stored_detail_has_appointments(job):
            summary.jobs_with_total_appointments += 1
            found, created, updated = sync_job_appointments_from_stored_detail(db, job, synced_at=synced)
            summary.appointments_found += found
            summary.sales_appointments_found += _count_sales_appointments(
                extract_job_appointments_from_raw(job.raw_detail_payload)
            )
            summary.appointments_created += created
            summary.appointments_updated += updated
            return

        if not fetch_missing:
            summary.skipped += 1
            return

        if not job_needs_detail_fetch(job):
            summary.skipped += 1
            return

        summary.jobs_with_total_appointments += 1
        summary.detail_fetches_attempted += 1
        success, found, created, updated = fetch_and_apply_job_detail(db, job, synced_at=synced)
        if success:
            summary.detail_fetches_success += 1
            summary.appointments_found += found
            summary.sales_appointments_found += _count_sales_appointments(
                extract_job_appointments_from_raw(job.raw_detail_payload)
            )
            summary.appointments_created += created
            summary.appointments_updated += updated
    except Exception:
        logger.exception(
            "Backfill failed for eWorks job id=%s ref=%s",
            job.eworks_job_id,
            job.job_ref or "—",
        )
        summary.failed += 1
        summary.detail_fetches_failed += 1


def backfill_job_appointments_from_details(
    db: Session,
    *,
    job_ref: str | None = None,
    eworks_job_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
    timeout_seconds: float = 60.0,
    fetch_missing: bool = False,
) -> JobAppointmentBackfillSummary:
    """Scan synced jobs and upsert appointment rows from stored detail payloads."""
    started = time.monotonic()
    summary = JobAppointmentBackfillSummary()
    batch_limit = max(1, limit)
    base_query = _build_job_backfill_query(db, job_ref=job_ref, eworks_job_id=eworks_job_id)
    total_matching = base_query.count()
    rows = base_query.offset(max(0, offset)).limit(batch_limit).all()
    synced = datetime.now(timezone.utc)
    for job in rows:
        if time.monotonic() - started >= timeout_seconds:
            summary.stopped_reason = "timeout"
            summary.next_offset = offset + summary.jobs_scanned
            summary.has_more = summary.next_offset < total_matching
            break

        summary.jobs_scanned += 1
        _process_job_appointment_backfill(
            db,
            job,
            summary,
            fetch_missing=fetch_missing,
            synced=synced,
        )
    else:
        processed_offset = offset + summary.jobs_scanned
        summary.next_offset = processed_offset
        summary.has_more = processed_offset < total_matching
        if summary.has_more:
            summary.stopped_reason = "batch_complete"
        else:
            summary.stopped_reason = "completed"

    db.commit()
    summary.elapsed_seconds = round(time.monotonic() - started, 2)
    logger.info(
        "eWorks job appointment backfill finished: scanned=%s appointments_found=%s created=%s updated=%s "
        "sales=%s failed=%s skipped=%s stopped=%s has_more=%s elapsed=%ss",
        summary.jobs_scanned,
        summary.appointments_found,
        summary.appointments_created,
        summary.appointments_updated,
        summary.sales_appointments_found,
        summary.failed,
        summary.skipped,
        summary.stopped_reason,
        summary.has_more,
        summary.elapsed_seconds,
    )
    return summary
