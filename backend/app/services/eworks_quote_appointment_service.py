"""Extract and store eWorks quote sales appointments from quote detail payloads."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Query, Session

from app.core.config import settings
from app.core.exceptions import AppError
from app.models.eworks_sync import EworksQuote, EworksQuoteAppointment
from app.services.eworks_job_appointment_service import (
    SafeJobAppointment,
    _appointment_list_from_raw,
    _build_dedupe_key,
    _build_safe_snapshot,
    _parse_appointment_row,
)
from app.services.eworks_quotes_jobs_api_service import fetch_quote_detail

logger = logging.getLogger(__name__)

SYNC_LOCK_TYPE = "quote_sales_appointments"
_PROGRESS_LOG_EVERY = 25

_QUOTE_APPOINTMENT_LIST_KEYS = (
    "sales_appointments",
    "salesAppointments",
    "survey_appointments",
    "appointments",
    "Appointments",
    "diary",
    "visits",
)


def _quote_appointment_list_from_raw(raw_payload: dict[str, Any] | None) -> list[tuple[dict[str, Any], bool]]:
    if not isinstance(raw_payload, dict):
        return []
    items: list[tuple[dict[str, Any], bool]] = []
    seen_ids: set[int] = set()
    for key in _QUOTE_APPOINTMENT_LIST_KEYS:
        value = raw_payload.get(key)
        if not isinstance(value, list):
            continue
        from_sales_list = key in {"sales_appointments", "salesAppointments"}
        for item in value:
            if not isinstance(item, dict):
                continue
            appointment_id = item.get("id") or item.get("appointment_id")
            if appointment_id is not None:
                try:
                    dedupe_id = int(appointment_id)
                    if dedupe_id in seen_ids:
                        continue
                    seen_ids.add(dedupe_id)
                except (TypeError, ValueError):
                    pass
            items.append((item, from_sales_list))
    if items:
        return items
    return _appointment_list_from_raw(raw_payload)


def extract_quote_appointments_from_raw(
    raw_payload: dict[str, Any] | None,
    *,
    sales_only: bool = True,
) -> list[SafeJobAppointment]:
    """Return safe appointment rows extracted from a synced quote payload."""
    appointments: list[SafeJobAppointment] = []
    for item, from_sales_list in _quote_appointment_list_from_raw(raw_payload):
        parsed = _parse_appointment_row(item, from_sales_list=from_sales_list)
        if parsed is None:
            continue
        if sales_only and not parsed.get("is_sales_appointment"):
            continue
        appointments.append(parsed)
    return appointments


def sync_quote_appointments(
    db: Session,
    quote: EworksQuote,
    *,
    raw_payload: dict[str, Any],
    synced_at: datetime | None = None,
    sales_only: bool = True,
) -> tuple[int, int]:
    """Upsert quote appointment rows. Returns (created, updated)."""
    synced = synced_at or datetime.now(timezone.utc)
    before_ids = {
        row.id
        for row in db.query(EworksQuoteAppointment.id)
        .filter(EworksQuoteAppointment.eworks_quote_id == quote.eworks_quote_id)
        .all()
    }

    try:
        extracted = extract_quote_appointments_from_raw(raw_payload, sales_only=sales_only)
    except Exception:
        logger.exception(
            "Failed to extract quote appointments for eworks_quote_id=%s ref=%s",
            quote.eworks_quote_id,
            quote.quote_ref or "—",
        )
        extracted = []

    seen_keys: set[str] = set()
    for appointment in extracted:
        dedupe_key = _build_dedupe_key(appointment)
        seen_keys.add(dedupe_key)
        existing = (
            db.query(EworksQuoteAppointment)
            .filter(
                EworksQuoteAppointment.eworks_quote_id == quote.eworks_quote_id,
                EworksQuoteAppointment.dedupe_key == dedupe_key,
            )
            .one_or_none()
        )
        fields = {
            "appointment_id": appointment.get("appointment_id"),
            "quote_ref": quote.quote_ref,
            "user_id": appointment.get("user_id"),
            "user_name": appointment.get("user_name"),
            "user_email": appointment.get("user_email"),
            "user_mobile": appointment.get("user_mobile"),
            "user_telephone": appointment.get("user_telephone"),
            "appointment_type": appointment.get("appointment_type"),
            "status": appointment.get("status"),
            "is_sales_appointment": appointment.get("is_sales_appointment"),
            "start_at": appointment.get("start_at"),
            "end_at": appointment.get("end_at"),
            "duration_minutes": appointment.get("duration_minutes"),
            "raw_safe_snapshot": _build_safe_snapshot(appointment),
            "synced_at": synced,
        }
        if existing is None:
            db.add(
                EworksQuoteAppointment(
                    eworks_quote_id=quote.eworks_quote_id,
                    dedupe_key=dedupe_key,
                    **fields,
                )
            )
        else:
            for key, value in fields.items():
                setattr(existing, key, value)

    stale_rows = (
        db.query(EworksQuoteAppointment)
        .filter(EworksQuoteAppointment.eworks_quote_id == quote.eworks_quote_id)
        .all()
    )
    for row in stale_rows:
        if row.dedupe_key not in seen_keys:
            db.delete(row)

    db.flush()
    after_rows = (
        db.query(EworksQuoteAppointment)
        .filter(EworksQuoteAppointment.eworks_quote_id == quote.eworks_quote_id)
        .all()
    )
    created = sum(1 for row in after_rows if row.id not in before_ids)
    updated = sum(1 for row in after_rows if row.id in before_ids)
    return created, updated


def serialize_quote_appointments(db: Session, quote: EworksQuote) -> list[dict[str, Any]]:
    rows = (
        db.query(EworksQuoteAppointment)
        .filter(EworksQuoteAppointment.eworks_quote_id == quote.eworks_quote_id)
        .order_by(EworksQuoteAppointment.start_at.desc(), EworksQuoteAppointment.id.desc())
        .all()
    )
    return [
        {
            "appointment_id": row.appointment_id,
            "user_name": row.user_name,
            "user_email": row.user_email,
            "user_id": row.user_id,
            "user_mobile": row.user_mobile,
            "user_telephone": row.user_telephone,
            "appointment_type": row.appointment_type,
            "status": row.status,
            "is_sales_appointment": row.is_sales_appointment,
            "start_at": row.start_at,
            "end_at": row.end_at,
            "duration_minutes": row.duration_minutes,
        }
        for row in rows
    ]


def sync_quote_sales_appointments_from_eworks(
    db: Session,
    quote: EworksQuote,
    *,
    fetch_detail: bool = True,
) -> tuple[int, int, int]:
    """Fetch quote detail if needed and sync sales appointments. Returns (found, created, updated)."""
    if not settings.eworks_sync_sales_appointments_enabled:
        return 0, 0, 0
    if not quote.eworks_quote_id:
        return 0, 0, 0

    raw_payload: dict[str, Any] | None = None
    if fetch_detail and settings.eworks_sync_quote_details_for_appointments_enabled:
        raw_payload, _rate_limited = fetch_quote_detail(quote.eworks_quote_id)
    elif isinstance(quote.raw_payload, dict):
        raw_payload = quote.raw_payload

    if not isinstance(raw_payload, dict):
        return 0, 0, 0

    extracted = extract_quote_appointments_from_raw(raw_payload, sales_only=True)
    created, updated = sync_quote_appointments(db, quote, raw_payload=raw_payload, sales_only=True)
    logger.info(
        "eWorks quote sales appointments: quote_ref=%s eworks_quote_id=%s count=%s created=%s updated=%s",
        quote.quote_ref or "—",
        quote.eworks_quote_id,
        len(extracted),
        created,
        updated,
    )
    return len(extracted), created, updated


@dataclass
class QuoteSalesAppointmentBackfillSummary:
    quotes_scanned: int = 0
    quote_details_fetched: int = 0
    appointments_found: int = 0
    appointments_created: int = 0
    appointments_updated: int = 0
    sales_appointments_found: int = 0
    failed: int = 0
    skipped: int = 0
    next_offset: int = 0
    has_more: bool = False
    elapsed_seconds: float = 0.0
    stopped_reason: str = "completed"
    rate_limited_count: int = 0


def maybe_fetch_quote_sales_appointments_after_list_upsert(
    db: Session,
    quote: EworksQuote,
    list_payload: dict[str, Any],
) -> None:
    """During quote list sync, fetch quote detail for sales appointments when enabled."""
    if not settings.eworks_sync_sales_appointments_enabled:
        return
    if not settings.eworks_sync_quote_details_for_appointments_enabled:
        embedded = extract_quote_appointments_from_raw(list_payload, sales_only=True)
        if embedded:
            sync_quote_appointments(db, quote, raw_payload=list_payload, sales_only=True)
        return
    sync_quote_sales_appointments_from_eworks(db, quote, fetch_detail=True)


def _build_quote_backfill_query(
    db: Session,
    *,
    quote_ref: str | None = None,
    eworks_quote_id: int | None = None,
    lookback_days: int | None = None,
) -> Query:
    query = db.query(EworksQuote).order_by(EworksQuote.synced_at.desc())
    if quote_ref:
        return query.filter(EworksQuote.quote_ref == quote_ref)
    if eworks_quote_id is not None:
        return query.filter(EworksQuote.eworks_quote_id == eworks_quote_id)
    if lookback_days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, lookback_days))
        query = query.filter(EworksQuote.synced_at >= cutoff)
    return query


def _log_backfill_progress(summary: QuoteSalesAppointmentBackfillSummary, *, force: bool = False) -> None:
    if not force and summary.quotes_scanned % _PROGRESS_LOG_EVERY != 0:
        return
    logger.info(
        "eWorks quote sales appointment backfill progress: scanned=%s fetched=%s found=%s "
        "sales_found=%s failed=%s rate_limited=%s",
        summary.quotes_scanned,
        summary.quote_details_fetched,
        summary.appointments_found,
        summary.sales_appointments_found,
        summary.failed,
        summary.rate_limited_count,
    )


def _fetch_quote_detail_for_backfill(eworks_quote_id: int) -> tuple[dict[str, Any] | None, int]:
    """Fetch quote detail for appointment backfill. Never calls attachment endpoints."""
    try:
        payload, rate_limited = fetch_quote_detail(eworks_quote_id)
        return payload, rate_limited
    except AppError as exc:
        if exc.code == "EWORKS_RATE_LIMITED":
            raise
        logger.exception(
            "Failed to fetch quote detail for sales appointments eworks_quote_id=%s",
            eworks_quote_id,
        )
        raise


def backfill_quote_sales_appointments_from_eworks(
    db: Session,
    *,
    quote_ref: str | None = None,
    eworks_quote_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
    lookback_days: int | None = None,
    timeout_seconds: float = 60.0,
    dry_run: bool = False,
    fetch_attachments: bool = False,
) -> QuoteSalesAppointmentBackfillSummary:
    """Batch backfill quote sales appointments from eWorks quote detail payloads."""
    started = time.monotonic()
    summary = QuoteSalesAppointmentBackfillSummary()

    if fetch_attachments:
        logger.warning(
            "fetch_attachments=true ignored; quote sales appointment backfill never calls attachment endpoints"
        )

    if not settings.eworks_sync_sales_appointments_enabled:
        summary.stopped_reason = "disabled"
        summary.elapsed_seconds = round(time.monotonic() - started, 2)
        return summary

    batch_limit = max(1, limit)
    base_query = _build_quote_backfill_query(
        db,
        quote_ref=quote_ref,
        eworks_quote_id=eworks_quote_id,
        lookback_days=lookback_days,
    )
    total_matching = base_query.count()
    rows = base_query.offset(max(0, offset)).limit(batch_limit).all()

    for quote in rows:
        if time.monotonic() - started >= timeout_seconds:
            summary.stopped_reason = "timeout"
            summary.next_offset = offset + summary.quotes_scanned
            summary.has_more = summary.next_offset < total_matching
            break

        summary.quotes_scanned += 1
        if not quote.eworks_quote_id:
            summary.skipped += 1
            _log_backfill_progress(summary)
            continue

        try:
            raw_payload, rate_limited = _fetch_quote_detail_for_backfill(quote.eworks_quote_id)
            summary.rate_limited_count += rate_limited
            summary.quote_details_fetched += 1

            if not isinstance(raw_payload, dict):
                summary.skipped += 1
                _log_backfill_progress(summary)
                continue

            extracted = extract_quote_appointments_from_raw(raw_payload, sales_only=True)
            summary.appointments_found += len(extracted)
            summary.sales_appointments_found += len(extracted)

            if not dry_run:
                created, updated = sync_quote_appointments(
                    db,
                    quote,
                    raw_payload=raw_payload,
                    sales_only=True,
                )
                summary.appointments_created += created
                summary.appointments_updated += updated
        except AppError as exc:
            if exc.code == "EWORKS_RATE_LIMITED":
                summary.rate_limited_count += 1
            summary.failed += 1
            _log_backfill_progress(summary, force=True)
            continue
        except Exception:
            logger.exception(
                "Backfill failed for quote sales appointments eworks_quote_id=%s",
                quote.eworks_quote_id,
            )
            summary.failed += 1
            _log_backfill_progress(summary, force=True)
            continue

        _log_backfill_progress(summary)
    else:
        processed_offset = offset + summary.quotes_scanned
        summary.next_offset = processed_offset
        summary.has_more = processed_offset < total_matching
        if summary.has_more:
            summary.stopped_reason = "batch_complete"
        else:
            summary.stopped_reason = "completed"

    if not dry_run:
        db.commit()

    summary.elapsed_seconds = round(time.monotonic() - started, 2)
    logger.info(
        "eWorks quote sales appointment backfill finished: scanned=%s fetched=%s found=%s sales=%s "
        "created=%s updated=%s failed=%s skipped=%s rate_limited=%s stopped=%s has_more=%s elapsed=%ss",
        summary.quotes_scanned,
        summary.quote_details_fetched,
        summary.appointments_found,
        summary.sales_appointments_found,
        summary.appointments_created,
        summary.appointments_updated,
        summary.failed,
        summary.skipped,
        summary.rate_limited_count,
        summary.stopped_reason,
        summary.has_more,
        summary.elapsed_seconds,
    )
    return summary
