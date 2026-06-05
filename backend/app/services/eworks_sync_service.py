"""eWorks sync service: upsert Quotes and Jobs into local DB (read-only from eWorks).

Never writes back to eWorks. Never overwrites local CalculationSession data.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.eworks_sync import EworksJob, EworksQuote, EworksSyncRun
from app.schemas.eworks_sync_api import EworksSyncBucketSummary, EworksSyncSummary
from app.services.eworks_quotes_jobs_api_service import fetch_all_jobs, fetch_all_quotes

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers: field extraction from raw eWorks payloads
# ---------------------------------------------------------------------------

def _safe_int(val: Any) -> int | None:
    """Coerce to int or return None."""
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _safe_float(val: Any) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_str(val: Any, max_len: int | None = None) -> str | None:
    if val is None:
        return None
    s = str(val).strip() or None
    if s and max_len:
        s = s[:max_len]
    return s


def _extract_quote_fields(raw: dict[str, Any]) -> dict[str, Any]:
    """Map a raw eWorks Quote dict to local EworksQuote column values."""
    customer = raw.get("customer") or {}
    status_obj = raw.get("quote_status") or {}
    return {
        "eworks_quote_id": _safe_int(raw.get("id")),
        "quote_ref": _safe_str(raw.get("quote_ref"), 100),
        "customer_id": _safe_int(customer.get("id") if isinstance(customer, dict) else raw.get("customer_id")),
        "customer_name": _safe_str(
            customer.get("customer_name") if isinstance(customer, dict) else raw.get("customer_name"), 500
        ),
        "customer_contact_id": _safe_int(raw.get("customer_contact_id")),
        "customer_site_id": _safe_int(raw.get("customer_site_id")),
        "project_id": _safe_int(raw.get("project_id")),
        "quote_type_id": _safe_int(raw.get("quote_type_id")),
        "quote_source_id": _safe_int(raw.get("quote_source_id")),
        "quote_date": _safe_str(raw.get("quote_date"), 30),
        "expiry_date": _safe_str(raw.get("expiry_date"), 30),
        "status": _safe_str(
            status_obj.get("id") if isinstance(status_obj, dict) else raw.get("status"), 100
        ),
        "status_name": _safe_str(
            status_obj.get("quote_status") if isinstance(status_obj, dict) else raw.get("status_name"), 200
        ),
        "description": _safe_str(raw.get("description")),
        "notes": _safe_str(raw.get("notes")),
        "customer_notes": _safe_str(raw.get("customer_notes")),
        "terms": _safe_str(raw.get("terms")),
        "customer_ref": _safe_str(raw.get("customer_ref"), 200),
        "po_ref": _safe_str(raw.get("po_ref"), 200),
        "wo_ref": _safe_str(raw.get("wo_ref"), 200),
        "subtotal": _safe_float(raw.get("sub_total") or raw.get("subtotal")),
        "vat": _safe_float(raw.get("vat")),
        "total": _safe_float(raw.get("total")),
        "raw_payload": raw,
    }


def _extract_job_fields(raw: dict[str, Any]) -> dict[str, Any]:
    """Map a raw eWorks Job dict to local EworksJob column values."""
    customer = raw.get("customer") or {}
    status_obj = raw.get("job_status") or {}
    address_obj = raw.get("site") or raw.get("address") or {}
    address_parts = []
    if isinstance(address_obj, dict):
        for k in ("address_1", "address_2", "city", "county", "postcode"):
            v = address_obj.get(k)
            if v:
                address_parts.append(str(v).strip())
    address_str = ", ".join(address_parts) if address_parts else _safe_str(raw.get("address"))

    return {
        "eworks_job_id": _safe_int(raw.get("id")),
        "job_ref": _safe_str(raw.get("job_ref"), 100),
        "eworks_quote_id": _safe_int(raw.get("quote_id") or raw.get("eworks_quote_id")),
        "customer_id": _safe_int(customer.get("id") if isinstance(customer, dict) else raw.get("customer_id")),
        "customer_name": _safe_str(
            customer.get("customer_name") if isinstance(customer, dict) else raw.get("customer_name"), 500
        ),
        "status": _safe_str(
            status_obj.get("id") if isinstance(status_obj, dict) else raw.get("status"), 100
        ),
        "status_name": _safe_str(
            status_obj.get("job_status") if isinstance(status_obj, dict) else raw.get("status_name"), 200
        ),
        "job_date": _safe_str(raw.get("job_date") or raw.get("start_date"), 30),
        "description": _safe_str(raw.get("description")),
        "notes": _safe_str(raw.get("notes")),
        "address": address_str,
        "subtotal": _safe_float(raw.get("sub_total") or raw.get("subtotal")),
        "vat": _safe_float(raw.get("vat")),
        "total": _safe_float(raw.get("total")),
        "raw_payload": raw,
    }


# ---------------------------------------------------------------------------
# Core upsert helpers
# ---------------------------------------------------------------------------

def _upsert_quotes(db: Session, records: list[dict[str, Any]]) -> EworksSyncBucketSummary:
    summary = EworksSyncBucketSummary(fetched=len(records))
    now = datetime.now(timezone.utc)

    for raw in records:
        try:
            fields = _extract_quote_fields(raw)
            eworks_id = fields.get("eworks_quote_id")
            if not eworks_id:
                logger.warning("eWorks Quote record missing id; skipping: %s", raw)
                summary.failed += 1
                continue

            existing = db.query(EworksQuote).filter(EworksQuote.eworks_quote_id == eworks_id).one_or_none()
            fields["synced_at"] = now

            if existing is None:
                db.add(EworksQuote(**fields))
                summary.created += 1
            else:
                for key, val in fields.items():
                    if key == "eworks_quote_id":
                        continue
                    setattr(existing, key, val)
                summary.updated += 1

        except Exception as exc:
            logger.exception("Failed to upsert eWorks Quote id=%s: %s", raw.get("id"), exc)
            summary.failed += 1

    db.flush()
    return summary


def _upsert_jobs(db: Session, records: list[dict[str, Any]]) -> EworksSyncBucketSummary:
    summary = EworksSyncBucketSummary(fetched=len(records))
    now = datetime.now(timezone.utc)

    for raw in records:
        try:
            fields = _extract_job_fields(raw)
            eworks_id = fields.get("eworks_job_id")
            if not eworks_id:
                logger.warning("eWorks Job record missing id; skipping: %s", raw)
                summary.failed += 1
                continue

            existing = db.query(EworksJob).filter(EworksJob.eworks_job_id == eworks_id).one_or_none()
            fields["synced_at"] = now

            if existing is None:
                db.add(EworksJob(**fields))
                summary.created += 1
            else:
                for key, val in fields.items():
                    if key == "eworks_job_id":
                        continue
                    setattr(existing, key, val)
                summary.updated += 1

        except Exception as exc:
            logger.exception("Failed to upsert eWorks Job id=%s: %s", raw.get("id"), exc)
            summary.failed += 1

    db.flush()
    return summary


# ---------------------------------------------------------------------------
# Sync run tracking helpers
# ---------------------------------------------------------------------------

def _start_run(db: Session, *, sync_type: str, user_id: uuid.UUID | None) -> EworksSyncRun:
    run = EworksSyncRun(
        id=uuid.uuid4(),
        sync_type=sync_type,
        status="running",
        requested_by_user_id=user_id,
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.flush()
    return run


def _finish_run(
    db: Session,
    run: EworksSyncRun,
    *,
    status: str,
    fetched: int,
    created: int,
    updated: int,
    failed: int,
    error_message: str | None = None,
) -> None:
    run.status = status
    run.finished_at = datetime.now(timezone.utc)
    run.fetched_count = fetched
    run.created_count = created
    run.updated_count = updated
    run.failed_count = failed
    run.error_message = error_message
    db.flush()


# ---------------------------------------------------------------------------
# Public sync functions
# ---------------------------------------------------------------------------

def sync_quotes_from_eworks(
    db: Session,
    *,
    filters: dict | None = None,
    user_id: uuid.UUID | None = None,
) -> tuple[EworksSyncBucketSummary, EworksSyncRun]:
    """Fetch all eWorks Quotes and upsert into local DB."""
    filters = filters or {}
    run = _start_run(db, sync_type="quotes", user_id=user_id)

    try:
        records = fetch_all_quotes(
            date_from=filters.get("date_from"),
            date_to=filters.get("date_to"),
            status=filters.get("status"),
            page_limit=filters.get("page_limit"),
        )
    except Exception as exc:
        _finish_run(
            db, run,
            status="failed",
            fetched=0, created=0, updated=0, failed=0,
            error_message=str(exc),
        )
        raise

    summary = _upsert_quotes(db, records)
    status = "success" if summary.failed == 0 else "partial"
    _finish_run(
        db, run,
        status=status,
        fetched=summary.fetched,
        created=summary.created,
        updated=summary.updated,
        failed=summary.failed,
    )

    logger.info(
        "eWorks quotes sync finished: fetched=%s created=%s updated=%s failed=%s",
        summary.fetched, summary.created, summary.updated, summary.failed,
    )
    return summary, run


def sync_jobs_from_eworks(
    db: Session,
    *,
    filters: dict | None = None,
    user_id: uuid.UUID | None = None,
) -> tuple[EworksSyncBucketSummary, EworksSyncRun]:
    """Fetch all eWorks Jobs and upsert into local DB."""
    filters = filters or {}
    run = _start_run(db, sync_type="jobs", user_id=user_id)

    try:
        records = fetch_all_jobs(
            date_from=filters.get("date_from"),
            date_to=filters.get("date_to"),
            status=filters.get("status"),
            page_limit=filters.get("page_limit"),
        )
    except Exception as exc:
        _finish_run(
            db, run,
            status="failed",
            fetched=0, created=0, updated=0, failed=0,
            error_message=str(exc),
        )
        raise

    summary = _upsert_jobs(db, records)
    status = "success" if summary.failed == 0 else "partial"
    _finish_run(
        db, run,
        status=status,
        fetched=summary.fetched,
        created=summary.created,
        updated=summary.updated,
        failed=summary.failed,
    )

    logger.info(
        "eWorks jobs sync finished: fetched=%s created=%s updated=%s failed=%s",
        summary.fetched, summary.created, summary.updated, summary.failed,
    )
    return summary, run


def sync_all_eworks(
    db: Session,
    *,
    filters: dict | None = None,
    user_id: uuid.UUID | None = None,
) -> EworksSyncSummary:
    """Fetch all eWorks Quotes and Jobs and upsert both into local DB."""
    errors: list[str] = []

    try:
        q_summary, _ = sync_quotes_from_eworks(db, filters=filters, user_id=user_id)
    except Exception as exc:
        logger.exception("eWorks all-sync: quotes failed: %s", exc)
        q_summary = EworksSyncBucketSummary()
        errors.append(f"Quotes: {exc}")

    try:
        j_summary, _ = sync_jobs_from_eworks(db, filters=filters, user_id=user_id)
    except Exception as exc:
        logger.exception("eWorks all-sync: jobs failed: %s", exc)
        j_summary = EworksSyncBucketSummary()
        errors.append(f"Jobs: {exc}")

    return EworksSyncSummary(quotes=q_summary, jobs=j_summary, errors=errors)
