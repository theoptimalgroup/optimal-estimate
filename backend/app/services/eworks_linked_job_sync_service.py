"""Sync eWorks jobs linked to a quote and their appointment rows."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.eworks_sync import EworksJob, EworksQuote
from app.services.eworks_job_appointment_service import (
    _resolve_eworks_quote_id,
    serialize_linked_job_appointments_for_quote,
)
from app.services.eworks_job_detail_sync_service import fetch_and_apply_job_detail
from app.services.eworks_quotes_jobs_api_service import fetch_jobs_for_quote
from app.services.eworks_sync_service import _extract_job_fields, _safe_int

logger = logging.getLogger(__name__)

AUTO_SYNC_RETRY_WINDOW_SECONDS = 15 * 60
AUTO_SYNC_TIMEOUT_SECONDS = 30.0

_auto_sync_attempts: dict[int, datetime] = {}


def clear_linked_job_auto_sync_attempts() -> None:
    """Clear in-memory auto-sync attempt timestamps (for tests)."""
    _auto_sync_attempts.clear()


def _record_auto_sync_attempt(eworks_quote_id: int) -> None:
    _auto_sync_attempts[eworks_quote_id] = datetime.now(timezone.utc)


def _recent_auto_sync_attempt(eworks_quote_id: int) -> bool:
    attempted_at = _auto_sync_attempts.get(eworks_quote_id)
    if attempted_at is None:
        return False
    return datetime.now(timezone.utc) - attempted_at < timedelta(seconds=AUTO_SYNC_RETRY_WINDOW_SECONDS)


def quote_has_local_linked_job_appointments(db: Session, quote: EworksQuote) -> bool:
    return bool(serialize_linked_job_appointments_for_quote(db, quote))


def should_attempt_linked_job_auto_sync(
    db: Session,
    quote: EworksQuote,
    *,
    opened_directly: bool = True,
) -> str | None:
    from app.services.quote_search_service import quote_is_draft

    if not settings.eworks_api_enabled:
        return "eworks_api_disabled"
    if not quote.eworks_quote_id:
        return "missing_eworks_quote_id"
    if not (quote_is_draft(quote) or opened_directly):
        return "not_draft_or_direct_open"
    if quote_has_local_linked_job_appointments(db, quote):
        return "linked_job_appointments_exist"
    if _recent_auto_sync_attempt(quote.eworks_quote_id):
        return "recent_attempt"
    return None


def maybe_auto_sync_linked_jobs_for_quote(
    db: Session,
    quote: EworksQuote,
    *,
    opened_directly: bool = True,
) -> LinkedJobSyncSummary | None:
    """Lightweight linked-job sync for quote detail when local job appointments are missing."""
    skip_reason = should_attempt_linked_job_auto_sync(db, quote, opened_directly=opened_directly)
    if skip_reason:
        logger.info(
            "Linked job auto-sync skipped quote_ref=%s eworks_quote_id=%s reason=%s",
            quote.quote_ref or "—",
            quote.eworks_quote_id if quote.eworks_quote_id is not None else "—",
            skip_reason,
        )
        return None

    assert quote.eworks_quote_id is not None
    _record_auto_sync_attempt(quote.eworks_quote_id)

    try:
        summary = sync_linked_jobs_for_quote(
            db,
            quote_id=quote.id,
            max_elapsed_seconds=AUTO_SYNC_TIMEOUT_SECONDS,
        )
    except Exception:
        logger.exception(
            "Linked job auto-sync failed quote_ref=%s eworks_quote_id=%s",
            quote.quote_ref or "—",
            quote.eworks_quote_id,
        )
        return None

    logger.info(
        "Linked job auto-sync finished quote_ref=%s eworks_quote_id=%s jobs_found=%s "
        "appointments_synced=%s failed=%s skipped=%s stopped=%s",
        summary.quote_ref or "—",
        summary.eworks_quote_id if summary.eworks_quote_id is not None else "—",
        summary.jobs_found_in_eworks,
        summary.appointments_found,
        summary.failed,
        summary.skipped,
        summary.stopped_reason,
    )
    return summary


@dataclass
class LinkedJobSyncSummary:
    quote_ref: str | None = None
    eworks_quote_id: int | None = None
    jobs_found_in_eworks: int = 0
    jobs_upserted: int = 0
    jobs_created: int = 0
    jobs_updated: int = 0
    detail_fetches_attempted: int = 0
    detail_fetches_success: int = 0
    detail_fetches_failed: int = 0
    appointments_found: int = 0
    appointments_created: int = 0
    appointments_updated: int = 0
    failed: int = 0
    skipped: int = 0
    elapsed_seconds: float = 0.0
    stopped_reason: str = "completed"


def _resolve_quote(
    db: Session,
    *,
    quote_id: int | None = None,
    quote_ref: str | None = None,
    eworks_quote_id: int | None = None,
) -> EworksQuote | None:
    if quote_id is not None:
        return db.query(EworksQuote).filter(EworksQuote.id == quote_id).one_or_none()
    resolved_id = _resolve_eworks_quote_id(
        db,
        quote_ref=quote_ref,
        eworks_quote_id=eworks_quote_id,
    )
    if resolved_id is None:
        return None
    return (
        db.query(EworksQuote)
        .filter(EworksQuote.eworks_quote_id == resolved_id)
        .order_by(EworksQuote.id.desc())
        .first()
    )


def _job_matches_quote(raw: dict[str, Any], eworks_quote_id: int) -> bool:
    linked_quote_id = _safe_int(raw.get("quote_id") or raw.get("eworks_quote_id"))
    return linked_quote_id == eworks_quote_id


def _collect_remote_job_payloads(eworks_quote_id: int) -> list[dict[str, Any]]:
    if not settings.eworks_api_enabled:
        return []
    records = fetch_jobs_for_quote(eworks_quote_id)
    matched = [raw for raw in records if isinstance(raw, dict) and _job_matches_quote(raw, eworks_quote_id)]
    return matched


def _upsert_linked_job_from_list_payload(
    db: Session,
    raw: dict[str, Any],
    *,
    synced_at: datetime,
) -> tuple[EworksJob | None, int, int]:
    """Upsert one linked job list payload without full sync side effects."""
    fields = _extract_job_fields(raw)
    eworks_job_id = fields.get("eworks_job_id")
    if not eworks_job_id:
        return None, 0, 0

    existing = (
        db.query(EworksJob)
        .filter(EworksJob.eworks_job_id == eworks_job_id)
        .one_or_none()
    )
    fields["synced_at"] = synced_at

    if existing is None:
        row = EworksJob(**fields)
        db.add(row)
        db.flush()
        return row, 1, 0

    for key, value in fields.items():
        if key == "eworks_job_id":
            continue
        setattr(existing, key, value)
    db.flush()
    return existing, 0, 1


def sync_linked_jobs_for_quote(
    db: Session,
    *,
    quote_id: int | None = None,
    quote_ref: str | None = None,
    eworks_quote_id: int | None = None,
    fetch_detail: bool = True,
    max_elapsed_seconds: float | None = None,
) -> LinkedJobSyncSummary:
    """Find jobs linked to a quote in eWorks, upsert locally, and sync appointments."""
    started = time.monotonic()
    summary = LinkedJobSyncSummary()
    quote = _resolve_quote(
        db,
        quote_id=quote_id,
        quote_ref=quote_ref,
        eworks_quote_id=eworks_quote_id,
    )
    if quote is None or quote.eworks_quote_id is None:
        summary.skipped = 1
        summary.stopped_reason = "quote_not_found"
        summary.elapsed_seconds = round(time.monotonic() - started, 2)
        return summary

    summary.quote_ref = quote.quote_ref
    summary.eworks_quote_id = quote.eworks_quote_id

    remote_payloads = _collect_remote_job_payloads(quote.eworks_quote_id)
    summary.jobs_found_in_eworks = len(remote_payloads)

    if not remote_payloads:
        local_jobs = (
            db.query(EworksJob)
            .filter(EworksJob.eworks_quote_id == quote.eworks_quote_id)
            .order_by(EworksJob.synced_at.desc(), EworksJob.id.desc())
            .all()
        )
        if not local_jobs:
            summary.skipped = 1
            summary.stopped_reason = "no_linked_jobs"
            summary.elapsed_seconds = round(time.monotonic() - started, 2)
            return summary
        remote_payloads = [
            job.raw_payload if isinstance(job.raw_payload, dict) else {"id": job.eworks_job_id}
            for job in local_jobs
        ]

    synced_at = datetime.now(timezone.utc)
    for raw in remote_payloads:
        if max_elapsed_seconds is not None and time.monotonic() - started >= max_elapsed_seconds:
            summary.stopped_reason = "timeout"
            break

        if not isinstance(raw, dict):
            summary.skipped += 1
            continue

        try:
            job, created, updated = _upsert_linked_job_from_list_payload(db, raw, synced_at=synced_at)
            if job is None:
                summary.skipped += 1
                continue
            summary.jobs_upserted += 1
            summary.jobs_created += created
            summary.jobs_updated += updated

            if not fetch_detail:
                continue

            summary.detail_fetches_attempted += 1
            try:
                success, found, created, updated = fetch_and_apply_job_detail(db, job, synced_at=synced_at)
            except Exception:
                logger.exception(
                    "Failed to fetch linked job detail for quote_ref=%s eworks_quote_id=%s job_ref=%s",
                    quote.quote_ref or "—",
                    quote.eworks_quote_id,
                    job.job_ref or "—",
                )
                summary.detail_fetches_failed += 1
                summary.failed += 1
                continue

            if success:
                summary.detail_fetches_success += 1
                summary.appointments_found += found
                summary.appointments_created += created
                summary.appointments_updated += updated
            else:
                summary.detail_fetches_failed += 1
        except Exception:
            logger.exception(
                "Failed to sync linked job for quote_ref=%s eworks_quote_id=%s",
                quote.quote_ref or "—",
                quote.eworks_quote_id,
            )
            summary.failed += 1

    db.commit()
    summary.elapsed_seconds = round(time.monotonic() - started, 2)
    logger.info(
        "Linked job sync for quote_ref=%s eworks_quote_id=%s: jobs_found=%s upserted=%s "
        "detail_success=%s appointments_found=%s failed=%s skipped=%s elapsed=%ss",
        summary.quote_ref or "—",
        summary.eworks_quote_id if summary.eworks_quote_id is not None else "—",
        summary.jobs_found_in_eworks,
        summary.jobs_upserted,
        summary.detail_fetches_success,
        summary.appointments_found,
        summary.failed,
        summary.skipped,
        summary.elapsed_seconds,
    )
    return summary
