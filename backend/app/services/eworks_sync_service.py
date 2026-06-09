"""eWorks sync service: upsert Quotes and Jobs into local DB (read-only from eWorks).

Never writes back to eWorks. Never overwrites local CalculationSession data.
"""

from __future__ import annotations

import logging
import re
import time as _time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.eworks_sync import EworksCustomer, EworksJob, EworksQuote, EworksSyncRun
from app.schemas.eworks_sync_api import EworksSyncBucketSummary, EworksSyncSummary
from app.services.eworks_attachment_sync_service import sync_parent_attachments
from app.services.eworks_customers_api_service import fetch_all_customers
from app.services.eworks_quotes_jobs_api_service import fetch_all_jobs, fetch_all_quotes, fetch_quote_page
from app.services.eworks_sync_run_state import (
    _PROGRESS_COMMIT_EVERY,
    update_sync_run_progress,
)

logger = logging.getLogger(__name__)

SYNC_DEFAULT_DAYS = 7

_FRACTIONAL_SECONDS_RE = re.compile(r"\.\d+")


def _parse_eworks_datetime(value: str | None) -> datetime | None:
    """Parse an eWorks ISO-8601 datetime string to a UTC-aware datetime.

    Handles fractional seconds (e.g. "2024-01-15T10:30:00.123456") by stripping
    them before parsing, matching the behaviour of the verified jq filter.
    Returns None when value is absent, empty, or unparseable (caller counts these).
    """
    if not value:
        return None
    try:
        stripped = _FRACTIONAL_SECONDS_RE.sub("", str(value).strip())
        dt = datetime.fromisoformat(stripped)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, AttributeError):
        return None


def _is_quote_recent(raw: dict[str, Any], cutoff: datetime) -> tuple[bool, bool]:
    """Return (is_recent, has_invalid_date).

    is_recent  – True when created_on OR last_updated_on >= cutoff.
    has_invalid_date – True when at least one date field exists but neither could be parsed.
    """
    created_str = raw.get("created_on")
    updated_str = raw.get("last_updated_on")

    created_dt = _parse_eworks_datetime(created_str)
    updated_dt = _parse_eworks_datetime(updated_str)

    has_invalid_date = bool(
        (created_str and created_dt is None) or (updated_str and updated_dt is None)
    )

    is_recent = (
        (created_dt is not None and created_dt >= cutoff)
        or (updated_dt is not None and updated_dt >= cutoff)
    )
    return is_recent, has_invalid_date


def default_sync_lookback_days() -> int:
    return max(1, int(settings.eworks_sync_lookback_days or SYNC_DEFAULT_DAYS))


def resolve_sync_filters(filters: dict | None = None, *, full: bool = False) -> dict:
    """Apply default rolling date window unless full sync or explicit dates are provided."""
    resolved = dict(filters or {})
    if full:
        return resolved
    if resolved.get("date_from") or resolved.get("date_to"):
        return resolved

    today = datetime.now(timezone.utc).date()
    lookback_days = default_sync_lookback_days()
    resolved["date_from"] = (today - timedelta(days=lookback_days)).isoformat()
    resolved["date_to"] = today.isoformat()
    return resolved


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


def _coerce_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _pick_first_positive_int(*values: Any) -> int | None:
    """Return the first coercible positive integer (treats 0 as unset for eWorks IDs)."""
    for value in values:
        parsed = _safe_int(value)
        if parsed is not None and parsed > 0:
            return parsed
    return None


def _payload_top_level_keys(raw: dict[str, Any]) -> list[str]:
    if not isinstance(raw, dict):
        return []
    return sorted(str(key) for key in raw.keys())


def _first_customer_name(*values: Any, max_len: int = 500) -> str | None:
    for value in values:
        name = _safe_str(value, max_len)
        if name:
            return name
    return None


def extract_customer_id_from_raw(raw: dict[str, Any]) -> int | None:
    """Extract eWorks customer_id from quote/job payloads with flexible key variants."""
    if not isinstance(raw, dict):
        return None

    customer = _coerce_dict(raw.get("customer"))
    quote_customer = _coerce_dict(raw.get("quote_customer"))
    customer_details = _coerce_dict(raw.get("customer_details"))
    billing_customer = _coerce_dict(raw.get("billing_customer"))
    site = _coerce_dict(raw.get("site"))
    contact = _coerce_dict(raw.get("customer_contact") or raw.get("contact"))
    customer_site = _coerce_dict(raw.get("customer_site"))
    property_obj = _coerce_dict(raw.get("property"))

    customer_value = raw.get("customer")
    if not isinstance(customer_value, dict) and customer_value not in (None, ""):
        scalar_id = _pick_first_positive_int(customer_value)
        if scalar_id is not None:
            return scalar_id

    return _pick_first_positive_int(
        customer.get("id"),
        customer.get("customer_id"),
        customer.get("customerId"),
        quote_customer.get("id"),
        quote_customer.get("customer_id"),
        raw.get("customer_id"),
        raw.get("customerId"),
        raw.get("customerID"),
        raw.get("CustomerID"),
        raw.get("Customer_Id"),
        raw.get("Customer"),
        raw.get("client_id"),
        raw.get("clientId"),
        raw.get("client"),
        contact.get("customer_id"),
        site.get("customer_id"),
        property_obj.get("customer_id"),
        customer_site.get("customer_id"),
        customer_details.get("customer_id"),
        customer_details.get("id"),
        billing_customer.get("customer_id"),
        billing_customer.get("id"),
    )


def extract_customer_contact_id_from_raw(raw: dict[str, Any]) -> int | None:
    if not isinstance(raw, dict):
        return None

    contact = _coerce_dict(raw.get("customer_contact") or raw.get("contact"))
    return _pick_first_positive_int(
        raw.get("customer_contact_id"),
        raw.get("customerContactId"),
        raw.get("Customer_Contact_Id"),
        contact.get("id"),
        contact.get("customer_contact_id"),
    )


def extract_customer_site_id_from_raw(raw: dict[str, Any]) -> int | None:
    if not isinstance(raw, dict):
        return None

    site = _coerce_dict(raw.get("site"))
    customer_site = _coerce_dict(raw.get("customer_site"))
    return _pick_first_positive_int(
        raw.get("customer_site_id"),
        raw.get("customerSiteId"),
        raw.get("Customer_Site_Id"),
        site.get("id"),
        site.get("customer_site_id"),
        customer_site.get("id"),
        customer_site.get("customer_site_id"),
    )


def extract_customer_name_from_raw(raw: dict[str, Any]) -> str | None:
    """Extract company/customer name from an eWorks quote/job payload.

    Prefers explicit customer/company fields over site or contact names.
    Returns None when only customer_id is present (no usable name fields).
    """
    if not isinstance(raw, dict):
        return None

    customer = _coerce_dict(raw.get("customer"))
    quote_customer = _coerce_dict(raw.get("quote_customer"))
    customer_details = _coerce_dict(raw.get("customer_details"))
    billing_customer = _coerce_dict(raw.get("billing_customer"))
    site = _coerce_dict(raw.get("site"))
    delivery = _coerce_dict(raw.get("delivery"))
    billing = _coerce_dict(raw.get("billing"))
    contact = _coerce_dict(raw.get("customer_contact") or raw.get("contact"))

    company_name = _first_customer_name(
        raw.get("customer_name"),
        customer.get("customer_name"),
        quote_customer.get("customer_name"),
        quote_customer.get("full_name"),
        quote_customer.get("name"),
        raw.get("client_name"),
        customer.get("full_name"),
        customer.get("name"),
        customer.get("display_name"),
        raw.get("full_name"),
        raw.get("name"),
        customer_details.get("customer_name"),
        customer_details.get("name"),
        customer_details.get("full_name"),
        billing_customer.get("customer_name"),
        billing_customer.get("name"),
        billing_customer.get("full_name"),
        site.get("customer_name"),
        site.get("client_name"),
        site.get("company_name"),
        delivery.get("company_name"),
        delivery.get("customer_name"),
        billing.get("company_name"),
    )
    if company_name:
        return company_name

    return _first_customer_name(
        contact.get("full_name"),
        contact.get("name"),
        contact.get("contact_name"),
    )


def log_unresolved_quote_customer(raw: dict[str, Any], fields: dict[str, Any]) -> None:
    """Debug-safe log when a quote's customer identity could not be resolved."""
    if fields.get("customer_id") or fields.get("customer_name"):
        return
    logger.debug(
        "eWorks quote customer unresolved: quote_ref=%s eworks_quote_id=%s payload_keys=%s",
        fields.get("quote_ref"),
        fields.get("eworks_quote_id"),
        _payload_top_level_keys(raw),
    )


def extract_customer_name_from_customer_record(raw: dict[str, Any]) -> str | None:
    """Resolve display name from a synced eWorks Customer record."""
    return _first_customer_name(
        raw.get("customer_name"),
        raw.get("full_name"),
        raw.get("company_name"),
        raw.get("name"),
        raw.get("display_name"),
    )


def lookup_customer_name_by_id(db: Session, customer_id: int | None) -> str | None:
    if customer_id is None:
        return None
    row = (
        db.query(EworksCustomer)
        .filter(EworksCustomer.eworks_customer_id == customer_id)
        .one_or_none()
    )
    if row is None:
        return None
    return _first_customer_name(row.customer_name, row.full_name, row.company_name)


def enrich_customer_name_on_fields(db: Session, fields: dict[str, Any]) -> None:
    """Fill customer_name on quote/job fields using synced eworks_customers when missing."""
    if fields.get("customer_name"):
        return
    customer_id = fields.get("customer_id")
    if customer_id is None:
        return
    name = lookup_customer_name_by_id(db, customer_id)
    if name:
        fields["customer_name"] = name


def enrich_existing_quotes_customer_names(db: Session) -> int:
    """Backfill eworks_quotes.customer_name from eworks_customers for rows missing a name."""
    updated = 0
    rows = (
        db.query(EworksQuote)
        .filter(EworksQuote.customer_id.isnot(None))
        .filter(or_(EworksQuote.customer_name.is_(None), func.trim(EworksQuote.customer_name) == ""))
        .all()
    )
    for quote in rows:
        name = lookup_customer_name_by_id(db, quote.customer_id)
        if name:
            quote.customer_name = name
            updated += 1
    if updated:
        db.flush()
    return updated


def enrich_existing_jobs_customer_names(db: Session) -> int:
    updated = 0
    rows = (
        db.query(EworksJob)
        .filter(EworksJob.customer_id.isnot(None))
        .filter(or_(EworksJob.customer_name.is_(None), func.trim(EworksJob.customer_name) == ""))
        .all()
    )
    for job in rows:
        name = lookup_customer_name_by_id(db, job.customer_id)
        if name:
            job.customer_name = name
            updated += 1
    if updated:
        db.flush()
    return updated


def _apply_extracted_customer_fields(target: EworksQuote | EworksJob, fields: dict[str, Any]) -> bool:
    changed = False
    for key in ("customer_id", "customer_name", "customer_contact_id", "customer_site_id"):
        if key not in fields or not hasattr(target, key):
            continue
        new_value = fields[key]
        if new_value is None:
            if key.endswith("_id") and getattr(target, key) in (0, "0"):
                setattr(target, key, None)
                changed = True
            continue
        if getattr(target, key) != new_value:
            setattr(target, key, new_value)
            changed = True
    return changed


def backfill_existing_quotes_customer_fields(db: Session) -> int:
    """Re-extract customer fields from stored raw_payload for quotes missing identity."""
    updated = 0
    rows = (
        db.query(EworksQuote)
        .filter(
            or_(
                EworksQuote.customer_id.is_(None),
                EworksQuote.customer_name.is_(None),
                func.trim(EworksQuote.customer_name) == "",
                EworksQuote.customer_site_id == 0,
                EworksQuote.customer_contact_id == 0,
            )
        )
        .filter(EworksQuote.raw_payload.isnot(None))
        .all()
    )
    for quote in rows:
        raw = quote.raw_payload if isinstance(quote.raw_payload, dict) else None
        if not raw:
            continue
        fields = {
            "customer_id": extract_customer_id_from_raw(raw),
            "customer_name": extract_customer_name_from_raw(raw),
            "customer_contact_id": extract_customer_contact_id_from_raw(raw),
            "customer_site_id": extract_customer_site_id_from_raw(raw),
        }
        enrich_customer_name_on_fields(db, fields)
        if _apply_extracted_customer_fields(quote, fields):
            updated += 1
    if updated:
        db.flush()
    return updated


def backfill_existing_jobs_customer_fields(db: Session) -> int:
    updated = 0
    rows = (
        db.query(EworksJob)
        .filter(
            or_(
                EworksJob.customer_id.is_(None),
                EworksJob.customer_name.is_(None),
                func.trim(EworksJob.customer_name) == "",
            )
        )
        .filter(EworksJob.raw_payload.isnot(None))
        .all()
    )
    for job in rows:
        raw = job.raw_payload if isinstance(job.raw_payload, dict) else None
        if not raw:
            continue
        fields = {
            "customer_id": extract_customer_id_from_raw(raw),
            "customer_name": extract_customer_name_from_raw(raw),
        }
        enrich_customer_name_on_fields(db, fields)
        if _apply_extracted_customer_fields(job, fields):
            updated += 1
    if updated:
        db.flush()
    return updated


def _extract_customer_fields(raw: dict[str, Any]) -> dict[str, Any]:
    billing = _coerce_dict(raw.get("billing_customer"))
    address = _coerce_dict(raw.get("address") or raw.get("site"))
    display_name = extract_customer_name_from_customer_record(raw)
    return {
        "eworks_customer_id": _safe_int(raw.get("id")),
        "customer_name": display_name,
        "full_name": _safe_str(raw.get("full_name"), 500),
        "company_name": _safe_str(raw.get("company_name"), 500),
        "email": _safe_str(raw.get("email") or raw.get("customer_email"), 320),
        "phone": _safe_str(raw.get("phone") or raw.get("telephone") or raw.get("mobile"), 100),
        "billing_email": _safe_str(billing.get("email") or raw.get("billing_email"), 320),
        "address_1": _safe_str(address.get("address_1") or address.get("line1"), 500),
        "address_2": _safe_str(address.get("address_2") or address.get("line2"), 500),
        "city": _safe_str(address.get("city"), 200),
        "county": _safe_str(address.get("county"), 200),
        "postcode": _safe_str(address.get("postcode") or address.get("post_code"), 50),
        "raw_payload": raw,
    }


def _upsert_customers(
    db: Session,
    records: list[dict[str, Any]],
    *,
    run: EworksSyncRun | None = None,
) -> EworksSyncBucketSummary:
    summary = EworksSyncBucketSummary(fetched=len(records))
    now = datetime.now(timezone.utc)

    if run is not None:
        update_sync_run_progress(
            db,
            run,
            phase="upserting",
            fetched=summary.fetched,
            created=0,
            updated=0,
            failed=0,
        )

    for index, raw in enumerate(records, start=1):
        try:
            fields = _extract_customer_fields(raw)
            eworks_id = fields.get("eworks_customer_id")
            if not eworks_id:
                logger.warning("eWorks Customer record missing id; skipping: %s", raw)
                summary.failed += 1
                continue

            existing = (
                db.query(EworksCustomer)
                .filter(EworksCustomer.eworks_customer_id == eworks_id)
                .one_or_none()
            )
            fields["synced_at"] = now

            if existing is None:
                db.add(EworksCustomer(**fields))
                summary.created += 1
            else:
                for key, val in fields.items():
                    if key == "eworks_customer_id":
                        continue
                    setattr(existing, key, val)
                summary.updated += 1
        except Exception as exc:
            logger.exception("Failed to upsert eWorks Customer id=%s: %s", raw.get("id"), exc)
            summary.failed += 1

        if run is not None and index % _PROGRESS_COMMIT_EVERY == 0:
            update_sync_run_progress(
                db,
                run,
                phase="upserting",
                fetched=summary.fetched,
                created=summary.created,
                updated=summary.updated,
                failed=summary.failed,
            )

    db.flush()
    return summary


def _normalize_tag_string(value: str) -> str | None:
    cleaned = value.strip()
    return cleaned or None


def _extract_tag_from_object(obj: Any) -> str | None:
    if isinstance(obj, str):
        return _normalize_tag_string(obj)
    if isinstance(obj, dict):
        for key in ("name", "title", "label", "value", "tag"):
            val = obj.get(key)
            if val is not None:
                tag = _normalize_tag_string(str(val))
                if tag:
                    return tag
    return None


def _normalize_tags(value: Any) -> list[str]:
    """Normalize eWorks tag-like values into a deduplicated list of strings."""
    if value is None:
        return []
    if isinstance(value, str):
        return [part for part in (_normalize_tag_string(p) for p in value.split(",")) if part]
    if isinstance(value, list):
        tags: list[str] = []
        for item in value:
            tag = _extract_tag_from_object(item)
            if tag and tag not in tags:
                tags.append(tag)
        return tags
    if isinstance(value, dict):
        tag = _extract_tag_from_object(value)
        return [tag] if tag else []
    tag = _normalize_tag_string(str(value))
    return [tag] if tag else []


def _append_tags(tags: list[str], values: Any) -> None:
    for tag in _normalize_tags(values):
        if tag not in tags:
            tags.append(tag)


def _extract_tags_from_raw(raw: dict[str, Any]) -> list[str]:
    """Extract normalized tags from common eWorks payload fields."""
    tags: list[str] = []
    for field in ("tags", "tag", "tag_names", "labels", "categories"):
        _append_tags(tags, raw.get(field))

    custom_fields = raw.get("custom_fields")
    if isinstance(custom_fields, dict):
        for field in ("tags", "tag", "tag_names", "labels", "categories"):
            _append_tags(tags, custom_fields.get(field))
    elif isinstance(custom_fields, list):
        for item in custom_fields:
            if not isinstance(item, dict):
                _append_tags(tags, item)
                continue
            field_name = str(
                item.get("name") or item.get("label") or item.get("field") or item.get("key") or ""
            ).lower()
            if field_name and ("tag" in field_name or field_name in {"labels", "categories"}):
                _append_tags(tags, item.get("value") or item.get("values") or item)

    return tags


def _extract_quote_fields(raw: dict[str, Any]) -> dict[str, Any]:
    """Map a raw eWorks Quote dict to local EworksQuote column values."""
    status_obj = raw.get("quote_status") or {}
    fields = {
        "eworks_quote_id": _safe_int(raw.get("id")),
        "quote_ref": _safe_str(raw.get("quote_ref"), 100),
        "customer_id": extract_customer_id_from_raw(raw),
        "customer_name": extract_customer_name_from_raw(raw),
        "customer_contact_id": extract_customer_contact_id_from_raw(raw),
        "customer_site_id": extract_customer_site_id_from_raw(raw),
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
        "tags": _extract_tags_from_raw(raw),
        "raw_payload": raw,
    }
    log_unresolved_quote_customer(raw, fields)
    return fields


def _extract_job_fields(raw: dict[str, Any]) -> dict[str, Any]:
    """Map a raw eWorks Job dict to local EworksJob column values."""
    status_obj = raw.get("job_status") or {}
    address_obj = raw.get("site") or raw.get("address") or {}
    address_parts = []
    if isinstance(address_obj, dict):
        for k in ("address_1", "address_2", "city", "county", "postcode"):
            v = address_obj.get(k)
            if v:
                address_parts.append(str(v).strip())
    address_str = ", ".join(address_parts) if address_parts else _safe_str(raw.get("address"))

    from app.services.eworks_job_detail_sync_service import extract_job_appointment_summary_fields

    summary_fields = extract_job_appointment_summary_fields(raw)

    return {
        "eworks_job_id": _safe_int(raw.get("id")),
        "job_ref": _safe_str(raw.get("job_ref"), 100),
        "eworks_quote_id": _safe_int(raw.get("quote_id") or raw.get("eworks_quote_id")),
        "customer_id": extract_customer_id_from_raw(raw),
        "customer_name": extract_customer_name_from_raw(raw),
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
        "tags": _extract_tags_from_raw(raw),
        "raw_payload": raw,
        **summary_fields,
    }


# ---------------------------------------------------------------------------
# Core upsert helpers
# ---------------------------------------------------------------------------

def _upsert_quotes(
    db: Session,
    records: list[dict[str, Any]],
    *,
    run: EworksSyncRun | None = None,
    skip_child_sync: bool = False,
) -> EworksSyncBucketSummary:
    """Upsert a list of raw eWorks Quote payloads into the local DB.

    skip_child_sync=True skips per-quote attachment and appointment API calls.
    When False, per-quote calls are also gated by
    eworks_sync_attachments_during_quote_sync / eworks_sync_quote_appointments_during_quote_sync.
    """
    summary = EworksSyncBucketSummary(fetched=len(records))
    now = datetime.now(timezone.utc)

    fetch_attachments = (
        not skip_child_sync and settings.eworks_sync_attachments_during_quote_sync
    )
    fetch_appointments = (
        not skip_child_sync and settings.eworks_sync_quote_appointments_during_quote_sync
    )

    if run is not None:
        update_sync_run_progress(
            db,
            run,
            phase="upserting",
            fetched=summary.fetched,
            created=0,
            updated=0,
            failed=0,
        )

    for index, raw in enumerate(records, start=1):
        try:
            fields = _extract_quote_fields(raw)
            eworks_id = fields.get("eworks_quote_id")
            if not eworks_id:
                logger.warning("eWorks Quote record missing id; skipping: %s", raw)
                summary.failed += 1
                continue

            enrich_customer_name_on_fields(db, fields)

            existing = db.query(EworksQuote).filter(EworksQuote.eworks_quote_id == eworks_id).one_or_none()
            fields["synced_at"] = now

            if existing is None:
                row = EworksQuote(**fields)
                db.add(row)
                db.flush()
                summary.created += 1
            else:
                for key, val in fields.items():
                    if key == "eworks_quote_id":
                        continue
                    setattr(existing, key, val)
                row = existing
                db.flush()
                summary.updated += 1

            # Always sync lightweight embedded attachment metadata from the list payload
            sync_parent_attachments(
                db,
                parent_type="quote",
                parent_eworks_id=eworks_id,
                parent_local_id=row.id,
                raw_payload=raw,
            )

            if fetch_attachments:
                try:
                    from app.services.eworks_quote_attachment_sync_service import (
                        maybe_fetch_quote_attachments_after_list_upsert,
                    )

                    maybe_fetch_quote_attachments_after_list_upsert(db, row, raw)
                except Exception:
                    logger.exception(
                        "Failed to fetch quote attachments for eWorks Quote id=%s; continuing quote upsert",
                        eworks_id,
                    )

            if fetch_appointments:
                try:
                    from app.services.eworks_quote_appointment_service import (
                        maybe_fetch_quote_sales_appointments_after_list_upsert,
                    )

                    maybe_fetch_quote_sales_appointments_after_list_upsert(db, row, raw)
                except Exception:
                    logger.exception(
                        "Failed to fetch quote sales appointments for eWorks Quote id=%s; continuing quote upsert",
                        eworks_id,
                    )

        except Exception as exc:
            logger.exception("Failed to upsert eWorks Quote id=%s: %s", raw.get("id"), exc)
            summary.failed += 1

        if run is not None and index % _PROGRESS_COMMIT_EVERY == 0:
            update_sync_run_progress(
                db,
                run,
                phase="upserting",
                fetched=summary.fetched,
                created=summary.created,
                updated=summary.updated,
                failed=summary.failed,
            )

    db.flush()
    return summary


def _upsert_jobs(
    db: Session,
    records: list[dict[str, Any]],
    *,
    run: EworksSyncRun | None = None,
) -> EworksSyncBucketSummary:
    summary = EworksSyncBucketSummary(fetched=len(records))
    now = datetime.now(timezone.utc)

    from app.core.config import settings as cfg
    from app.services.eworks_job_detail_sync_service import JobDetailFetchStats, maybe_fetch_job_detail_after_list_upsert

    detail_stats = JobDetailFetchStats()
    detail_limit = cfg.eworks_sync_job_details_limit_per_run
    detail_remaining = detail_limit

    if run is not None:
        update_sync_run_progress(
            db,
            run,
            phase="upserting",
            fetched=summary.fetched,
            created=0,
            updated=0,
            failed=0,
        )

    for index, raw in enumerate(records, start=1):
        try:
            fields = _extract_job_fields(raw)
            eworks_id = fields.get("eworks_job_id")
            if not eworks_id:
                logger.warning("eWorks Job record missing id; skipping: %s", raw)
                summary.failed += 1
                continue

            enrich_customer_name_on_fields(db, fields)

            existing = db.query(EworksJob).filter(EworksJob.eworks_job_id == eworks_id).one_or_none()
            fields["synced_at"] = now

            if existing is None:
                row = EworksJob(**fields)
                db.add(row)
                db.flush()
                summary.created += 1
            else:
                for key, val in fields.items():
                    if key == "eworks_job_id":
                        continue
                    setattr(existing, key, val)
                row = existing
                db.flush()
                summary.updated += 1

            sync_parent_attachments(
                db,
                parent_type="job",
                parent_eworks_id=eworks_id,
                parent_local_id=row.id,
                raw_payload=raw,
            )

            try:
                from app.services.eworks_job_appointment_service import sync_job_appointments

                sync_job_appointments(db, row, raw_payload=raw, synced_at=now)
            except Exception:
                logger.exception(
                    "Failed to sync appointments for eWorks Job id=%s; continuing job upsert",
                    eworks_id,
                )

            maybe_fetch_job_detail_after_list_upsert(
                db,
                row,
                raw,
                synced_at=now,
                stats=detail_stats,
                limit_remaining=detail_remaining,
            )
            if detail_limit is not None and detail_stats.attempted >= detail_limit:
                detail_remaining = 0
            elif detail_limit is not None:
                detail_remaining = max(detail_limit - detail_stats.attempted, 0)

        except Exception as exc:
            logger.exception("Failed to upsert eWorks Job id=%s: %s", raw.get("id"), exc)
            summary.failed += 1

        if run is not None and index % _PROGRESS_COMMIT_EVERY == 0:
            update_sync_run_progress(
                db,
                run,
                phase="upserting",
                fetched=summary.fetched,
                created=summary.created,
                updated=summary.updated,
                failed=summary.failed,
            )

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
    if run.status != "running":
        return
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

def sync_customers_from_eworks(
    db: Session,
    *,
    filters: dict | None = None,
    user_id: uuid.UUID | None = None,
    run: EworksSyncRun | None = None,
) -> tuple[EworksSyncBucketSummary, EworksSyncRun]:
    """Fetch all eWorks Customers and upsert into local DB."""
    filters = filters or {}
    if run is None:
        run = _start_run(db, sync_type="customers", user_id=user_id)

    summary = EworksSyncBucketSummary()

    def _fetch_heartbeat(_page: int, _last_page: int, total_so_far: int) -> None:
        update_sync_run_progress(db, run, phase="fetching", fetched=total_so_far)

    try:
        update_sync_run_progress(db, run, phase="fetching")
        records = fetch_all_customers(
            filters={k: v for k, v in filters.items() if k in {"page_limit"}},
            page_limit=filters.get("page_limit"),
            on_page_fetched=_fetch_heartbeat,
        )
        update_sync_run_progress(db, run, phase="upserting", fetched=len(records))
        summary = _upsert_customers(db, records, run=run)
        enrich_existing_quotes_customer_names(db)
        enrich_existing_jobs_customer_names(db)
        backfill_existing_quotes_customer_fields(db)
        backfill_existing_jobs_customer_fields(db)
        status = "success" if summary.failed == 0 else "partial"
        _finish_run(
            db,
            run,
            status=status,
            fetched=summary.fetched,
            created=summary.created,
            updated=summary.updated,
            failed=summary.failed,
        )
        run.metadata_ = {**(run.metadata_ or {}), "summary": summary.model_dump()}
        logger.info(
            "eWorks customers sync finished: fetched=%s created=%s updated=%s failed=%s",
            summary.fetched,
            summary.created,
            summary.updated,
            summary.failed,
        )
    except Exception as exc:
        _finish_run(
            db,
            run,
            status="failed",
            fetched=summary.fetched,
            created=summary.created,
            updated=summary.updated,
            failed=summary.failed,
            error_message=str(exc),
        )
        run.metadata_ = {
            **(run.metadata_ or {}),
            "summary": summary.model_dump() if summary.fetched else {"fetched": 0, "created": 0, "updated": 0, "failed": 0},
        }
        raise
    finally:
        if run.status == "running":
            _finish_run(
                db,
                run,
                status="failed",
                fetched=summary.fetched,
                created=summary.created,
                updated=summary.updated,
                failed=summary.failed,
                error_message="Sync ended without completing.",
            )

    return summary, run


def sync_quotes_from_eworks(
    db: Session,
    *,
    filters: dict | None = None,
    user_id: uuid.UUID | None = None,
    run: EworksSyncRun | None = None,
) -> tuple[EworksSyncBucketSummary, EworksSyncRun]:
    """Fetch all eWorks Quotes and upsert into local DB."""
    filters = filters or {}
    if run is None:
        run = _start_run(db, sync_type="quotes", user_id=user_id)

    summary = EworksSyncBucketSummary()

    def _fetch_heartbeat(_page: int, _last_page: int, total_so_far: int) -> None:
        update_sync_run_progress(db, run, phase="fetching", fetched=total_so_far)

    try:
        update_sync_run_progress(db, run, phase="fetching")
        records = fetch_all_quotes(
            date_from=filters.get("date_from"),
            date_to=filters.get("date_to"),
            status=filters.get("status"),
            page_limit=filters.get("page_limit"),
            on_page_fetched=_fetch_heartbeat,
        )
        update_sync_run_progress(db, run, phase="upserting", fetched=len(records))
        summary = _upsert_quotes(db, records, run=run)
        backfill_existing_quotes_customer_fields(db)
        enrich_existing_quotes_customer_names(db)
        status = "success" if summary.failed == 0 else "partial"
        _finish_run(
            db,
            run,
            status=status,
            fetched=summary.fetched,
            created=summary.created,
            updated=summary.updated,
            failed=summary.failed,
        )
        run.metadata_ = {**(run.metadata_ or {}), "summary": summary.model_dump()}
        logger.info(
            "eWorks quotes sync finished: fetched=%s created=%s updated=%s failed=%s",
            summary.fetched,
            summary.created,
            summary.updated,
            summary.failed,
        )
    except Exception as exc:
        _finish_run(
            db,
            run,
            status="failed",
            fetched=summary.fetched,
            created=summary.created,
            updated=summary.updated,
            failed=summary.failed,
            error_message=str(exc),
        )
        run.metadata_ = {
            **(run.metadata_ or {}),
            "summary": summary.model_dump() if summary.fetched else {"fetched": 0, "created": 0, "updated": 0, "failed": 0},
        }
        raise
    finally:
        if run.status == "running":
            _finish_run(
                db,
                run,
                status="failed",
                fetched=summary.fetched,
                created=summary.created,
                updated=summary.updated,
                failed=summary.failed,
                error_message="Sync ended without completing.",
            )

    return summary, run


def sync_quotes_incremental_recent(
    db: Session,
    *,
    window_minutes: int = 60,
    timeout_seconds: int = 120,
    user_id: uuid.UUID | None = None,
    run: EworksSyncRun | None = None,
) -> tuple[EworksSyncBucketSummary, EworksSyncRun]:
    """Incremental quote sync: upsert only quotes created or updated in the last window_minutes.

    Strategy:
    - Fetches Quote list pages from eWorks without walking all history.
    - Applies local filtering: created_on >= cutoff OR last_updated_on >= cutoff.
    - Stops early when a page yields zero recent records (assumes API returns newest first)
      or when the hard timeout is reached.
    - Does NOT fetch per-quote attachments or sales appointments (skip_child_sync=True).
    """
    if run is None:
        run = _start_run(db, sync_type="quotes", user_id=user_id)

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=window_minutes)
    deadline = _time.monotonic() + timeout_seconds

    summary = EworksSyncBucketSummary()
    source_records_seen = 0
    skipped_old = 0
    skipped_invalid_date = 0
    stopped_reason = "completed"
    recent_records: list[dict[str, Any]] = []

    run.metadata_ = {
        **(run.metadata_ or {}),
        "mode": "incremental_recent",
        "recent_window_minutes": window_minutes,
        "timeout_seconds": timeout_seconds,
        "started_cutoff": cutoff.isoformat(),
        "attachments_during_sync": False,
        "quote_appointments_during_sync": False,
        "phase": "fetching",
    }
    db.flush()

    try:
        update_sync_run_progress(db, run, phase="fetching")

        page = 1
        last_page = 1

        while page <= last_page:
            if _time.monotonic() > deadline:
                stopped_reason = "timeout"
                logger.warning(
                    "Incremental quotes sync: reached %ss timeout at page %s/%s; stopping cleanly",
                    timeout_seconds, page, last_page,
                )
                break

            page_result = fetch_quote_page(page)
            last_page = page_result.last_page
            source_records_seen += len(page_result.records)

            recent_on_page = 0
            for raw in page_result.records:
                is_recent, has_invalid = _is_quote_recent(raw, cutoff)
                if has_invalid:
                    skipped_invalid_date += 1
                    continue
                if is_recent:
                    recent_records.append(raw)
                    recent_on_page += 1
                else:
                    skipped_old += 1

            update_sync_run_progress(
                db, run,
                phase="fetching",
                fetched=len(recent_records),
            )

            logger.info(
                "Incremental quotes sync: page %s/%s — seen=%s recent=%s total_recent_so_far=%s",
                page_result.current_page, last_page,
                len(page_result.records), recent_on_page, len(recent_records),
            )

            # Early stop: if this page returned no recent records, eWorks API likely returns
            # records sorted newest-first so all remaining pages will also have no recent records.
            if recent_on_page == 0 and len(page_result.records) > 0:
                logger.info(
                    "Incremental quotes sync: page %s had no recent records; stopping early",
                    page_result.current_page,
                )
                break

            if not page_result.records or page_result.current_page >= last_page:
                break

            page = page_result.current_page + 1

        # Upsert only the matched recent records; skip expensive per-quote child API calls
        update_sync_run_progress(db, run, phase="upserting", fetched=len(recent_records))
        summary = _upsert_quotes(db, recent_records, run=run, skip_child_sync=True)

        if stopped_reason == "timeout":
            run_status = "partial"
        elif summary.failed > 0:
            run_status = "partial"
        else:
            run_status = "success"

        _finish_run(
            db, run,
            status=run_status,
            fetched=summary.fetched,
            created=summary.created,
            updated=summary.updated,
            failed=summary.failed,
        )
        run.metadata_ = {
            **(run.metadata_ or {}),
            "mode": "incremental_recent",
            "recent_window_minutes": window_minutes,
            "timeout_seconds": timeout_seconds,
            "started_cutoff": cutoff.isoformat(),
            "source_records_seen": source_records_seen,
            "recent_records_matched": len(recent_records),
            "skipped_old": skipped_old,
            "skipped_invalid_date": skipped_invalid_date,
            "attachments_during_sync": False,
            "quote_appointments_during_sync": False,
            "stopped_reason": stopped_reason,
        }
        db.flush()

        logger.info(
            "Incremental quotes sync finished: seen=%s matched=%s created=%s updated=%s "
            "failed=%s skipped_old=%s skipped_invalid=%s stopped=%s",
            source_records_seen, len(recent_records),
            summary.created, summary.updated, summary.failed,
            skipped_old, skipped_invalid_date, stopped_reason,
        )

    except Exception as exc:
        stopped_reason = "api_error"
        _finish_run(
            db, run,
            status="failed",
            fetched=summary.fetched,
            created=summary.created,
            updated=summary.updated,
            failed=summary.failed,
            error_message=str(exc),
        )
        run.metadata_ = {
            **(run.metadata_ or {}),
            "stopped_reason": stopped_reason,
            "source_records_seen": source_records_seen,
            "skipped_old": skipped_old,
            "skipped_invalid_date": skipped_invalid_date,
        }
        raise
    finally:
        if run.status == "running":
            _finish_run(
                db, run,
                status="failed",
                fetched=summary.fetched,
                created=summary.created,
                updated=summary.updated,
                failed=summary.failed,
                error_message="Sync ended without completing.",
            )

    return summary, run


def sync_jobs_from_eworks(
    db: Session,
    *,
    filters: dict | None = None,
    user_id: uuid.UUID | None = None,
    run: EworksSyncRun | None = None,
) -> tuple[EworksSyncBucketSummary, EworksSyncRun]:
    """Fetch all eWorks Jobs and upsert into local DB."""
    filters = filters or {}
    if run is None:
        run = _start_run(db, sync_type="jobs", user_id=user_id)

    summary = EworksSyncBucketSummary()

    def _fetch_heartbeat(_page: int, _last_page: int, total_so_far: int) -> None:
        update_sync_run_progress(db, run, phase="fetching", fetched=total_so_far)

    try:
        update_sync_run_progress(db, run, phase="fetching")
        records = fetch_all_jobs(
            date_from=filters.get("date_from"),
            date_to=filters.get("date_to"),
            status=filters.get("status"),
            page_limit=filters.get("page_limit"),
            on_page_fetched=_fetch_heartbeat,
        )
        update_sync_run_progress(db, run, phase="upserting", fetched=len(records))
        summary = _upsert_jobs(db, records, run=run)
        backfill_existing_jobs_customer_fields(db)
        enrich_existing_jobs_customer_names(db)
        status = "success" if summary.failed == 0 else "partial"
        _finish_run(
            db,
            run,
            status=status,
            fetched=summary.fetched,
            created=summary.created,
            updated=summary.updated,
            failed=summary.failed,
        )
        run.metadata_ = {**(run.metadata_ or {}), "summary": summary.model_dump()}
        logger.info(
            "eWorks jobs sync finished: fetched=%s created=%s updated=%s failed=%s",
            summary.fetched,
            summary.created,
            summary.updated,
            summary.failed,
        )
    except Exception as exc:
        _finish_run(
            db,
            run,
            status="failed",
            fetched=summary.fetched,
            created=summary.created,
            updated=summary.updated,
            failed=summary.failed,
            error_message=str(exc),
        )
        run.metadata_ = {
            **(run.metadata_ or {}),
            "summary": summary.model_dump() if summary.fetched else {"fetched": 0, "created": 0, "updated": 0, "failed": 0},
        }
        raise
    finally:
        if run.status == "running":
            _finish_run(
                db,
                run,
                status="failed",
                fetched=summary.fetched,
                created=summary.created,
                updated=summary.updated,
                failed=summary.failed,
                error_message="Sync ended without completing.",
            )

    return summary, run


def sync_all_eworks(
    db: Session,
    *,
    filters: dict | None = None,
    user_id: uuid.UUID | None = None,
    run: EworksSyncRun | None = None,
) -> EworksSyncSummary:
    """Fetch eWorks Customers, Quotes, and Jobs and upsert into local DB."""
    filters = filters or {}
    errors: list[str] = []
    c_summary = EworksSyncBucketSummary()
    q_summary = EworksSyncBucketSummary()
    j_summary = EworksSyncBucketSummary()

    if run is None:
        run = _start_run(db, sync_type="all", user_id=user_id)

    try:
        run.metadata_ = {**(run.metadata_ or {}), "phase": "customers"}
        update_sync_run_progress(db, run, phase="fetching_customers")

        def _customers_fetch_heartbeat(_page: int, _last_page: int, total_so_far: int) -> None:
            update_sync_run_progress(db, run, phase="fetching_customers", fetched=total_so_far)

        try:
            records = fetch_all_customers(
                page_limit=filters.get("page_limit"),
                on_page_fetched=_customers_fetch_heartbeat,
            )
            update_sync_run_progress(db, run, phase="upserting_customers", fetched=len(records))
            c_summary = _upsert_customers(db, records, run=run)
            enrich_existing_quotes_customer_names(db)
            enrich_existing_jobs_customer_names(db)
            backfill_existing_quotes_customer_fields(db)
            backfill_existing_jobs_customer_fields(db)
        except Exception as exc:
            logger.exception("eWorks all-sync: customers failed: %s", exc)
            errors.append(f"Customers: {exc}")

        run.metadata_ = {**(run.metadata_ or {}), "phase": "quotes", "customers": c_summary.model_dump()}
        update_sync_run_progress(
            db,
            run,
            phase="fetching_quotes",
            fetched=c_summary.fetched,
            created=c_summary.created,
            updated=c_summary.updated,
            failed=c_summary.failed,
        )

        def _quotes_fetch_heartbeat(_page: int, _last_page: int, total_so_far: int) -> None:
            update_sync_run_progress(
                db,
                run,
                phase="fetching_quotes",
                fetched=c_summary.fetched + total_so_far,
            )

        try:
            records = fetch_all_quotes(
                date_from=filters.get("date_from"),
                date_to=filters.get("date_to"),
                status=filters.get("status"),
                page_limit=filters.get("page_limit"),
                on_page_fetched=_quotes_fetch_heartbeat,
            )
            update_sync_run_progress(db, run, phase="upserting_quotes", fetched=c_summary.fetched + len(records))
            q_summary = _upsert_quotes(db, records, run=run)
            backfill_existing_quotes_customer_fields(db)
            enrich_existing_quotes_customer_names(db)
        except Exception as exc:
            logger.exception("eWorks all-sync: quotes failed: %s", exc)
            errors.append(f"Quotes: {exc}")

        run.metadata_ = {**(run.metadata_ or {}), "phase": "jobs", "quotes": q_summary.model_dump()}
        update_sync_run_progress(
            db,
            run,
            phase="fetching_jobs",
            fetched=c_summary.fetched + q_summary.fetched,
            created=q_summary.created,
            updated=q_summary.updated,
            failed=q_summary.failed,
        )

        def _jobs_fetch_heartbeat(_page: int, _last_page: int, total_so_far: int) -> None:
            update_sync_run_progress(
                db,
                run,
                phase="fetching_jobs",
                fetched=c_summary.fetched + q_summary.fetched + total_so_far,
            )

        try:
            records = fetch_all_jobs(
                date_from=filters.get("date_from"),
                date_to=filters.get("date_to"),
                status=filters.get("status"),
                page_limit=filters.get("page_limit"),
                on_page_fetched=_jobs_fetch_heartbeat,
            )
            update_sync_run_progress(
                db,
                run,
                phase="upserting_jobs",
                fetched=c_summary.fetched + q_summary.fetched + len(records),
            )
            j_summary = _upsert_jobs(db, records, run=run)
            backfill_existing_jobs_customer_fields(db)
            enrich_existing_jobs_customer_names(db)
        except Exception as exc:
            logger.exception("eWorks all-sync: jobs failed: %s", exc)
            errors.append(f"Jobs: {exc}")

        total_fetched = c_summary.fetched + q_summary.fetched + j_summary.fetched
        total_created = c_summary.created + q_summary.created + j_summary.created
        total_updated = c_summary.updated + q_summary.updated + j_summary.updated
        total_failed = c_summary.failed + q_summary.failed + j_summary.failed

        if errors and total_fetched == 0:
            run_status = "failed"
        elif errors or total_failed > 0:
            run_status = "partial"
        else:
            run_status = "success"

        _finish_run(
            db,
            run,
            status=run_status,
            fetched=total_fetched,
            created=total_created,
            updated=total_updated,
            failed=total_failed,
            error_message="; ".join(errors) if errors else None,
        )
        run.metadata_ = {
            **(run.metadata_ or {}),
            "phase": "completed",
            "customers": c_summary.model_dump(),
            "quotes": q_summary.model_dump(),
            "jobs": j_summary.model_dump(),
            "errors": errors,
        }

        logger.info(
            "eWorks all-sync finished: customers_fetched=%s quotes_fetched=%s jobs_fetched=%s errors=%s",
            c_summary.fetched,
            q_summary.fetched,
            j_summary.fetched,
            len(errors),
        )
    except Exception as exc:
        _finish_run(
            db,
            run,
            status="failed",
            fetched=c_summary.fetched + q_summary.fetched + j_summary.fetched,
            created=c_summary.created + q_summary.created + j_summary.created,
            updated=c_summary.updated + q_summary.updated + j_summary.updated,
            failed=c_summary.failed + q_summary.failed + j_summary.failed,
            error_message=str(exc),
        )
        raise
    finally:
        if run.status == "running":
            _finish_run(
                db,
                run,
                status="failed",
                fetched=c_summary.fetched + q_summary.fetched + j_summary.fetched,
                created=c_summary.created + q_summary.created + j_summary.created,
                updated=c_summary.updated + q_summary.updated + j_summary.updated,
                failed=c_summary.failed + q_summary.failed + j_summary.failed,
                error_message="Sync ended without completing.",
            )

    return EworksSyncSummary(customers=c_summary, quotes=q_summary, jobs=j_summary, errors=errors)
