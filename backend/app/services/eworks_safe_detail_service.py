"""Build manager-safe grouped detail views from synced eWorks quote/job records."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.calculation_session import CalculationSession
from app.models.eworks_sync import EworksJob, EworksQuote
from app.services.eworks_acceptance_sync_service import resolve_eworks_quote_id
from app.services.eworks_job_appointment_service import serialize_job_appointments
from app.services.eworks_job_appointment_service import (
    get_active_job_appointment_assignee,
    merge_quote_sales_appointments,
    serialize_appointment_assignee_safe_detail,
    serialize_linked_job_appointments_for_quote,
)
from app.services.eworks_linked_job_sync_service import maybe_auto_sync_linked_jobs_for_quote
from app.services.eworks_quote_appointment_service import serialize_quote_appointments
from app.services.eworks_quote_status import resolve_eworks_quote_status_label
from app.services.eworks_sync_service import (
    _extract_tags_from_raw,
    extract_customer_contact_id_from_raw,
    extract_customer_id_from_raw,
    extract_customer_name_from_raw,
    extract_customer_site_id_from_raw,
)

REDACTED = "***REDACTED***"

_SENSITIVE_KEY_PARTS = (
    "password",
    "password_hash",
    "token",
    "session_token",
    "public_quote_token",
    "api_key",
    "secret",
    "authorization",
    "dashboard_password",
    "bearer",
    "access_token",
    "refresh_token",
    "connection_string",
)

_INTERNAL_KEY_PARTS = (
    "formula",
    "profit",
    "margin",
    "denominator",
    "rate_rule",
    "audit_snapshot",
)


def _is_sensitive_key(key: str) -> bool:
    normalized = re.sub(r"[^a-z0-9_]", "_", str(key).lower())
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS + _INTERNAL_KEY_PARTS)


def redact_sensitive_data(value: Any) -> Any:
    """Recursively redact sensitive keys in nested structures."""
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if _is_sensitive_key(str(key)):
                redacted[str(key)] = REDACTED
            else:
                redacted[str(key)] = redact_sensitive_data(item)
        return redacted
    if isinstance(value, list):
        return [redact_sensitive_data(item) for item in value]
    return value


def _serialize_tags(tags: list | None) -> list[str]:
    from app.services.manager_dashboard_service import _parse_tags_value

    return _parse_tags_value(tags)


def _pick(raw: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in raw and raw[key] not in (None, ""):
            return raw[key]
    return None


def _pick_nested(raw: dict[str, Any], *paths: str) -> Any:
    for path in paths:
        current: Any = raw
        for part in path.split("."):
            if not isinstance(current, dict):
                current = None
                break
            current = current.get(part)
        if current not in (None, ""):
            return current
    return None


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_custom_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return str(redact_sensitive_data(value))
    return str(value)


def _build_site_address(raw: dict[str, Any]) -> str | None:
    site = raw.get("site")
    if isinstance(site, dict):
        parts = [
            _as_str(site.get("address_1") or site.get("address1") or site.get("address")),
            _as_str(site.get("address_2") or site.get("address2")),
            _as_str(site.get("city")),
            _as_str(site.get("county")),
            _as_str(site.get("postcode") or site.get("zip")),
        ]
        joined = ", ".join(part for part in parts if part)
        if joined:
            return joined
    parts = [
        _as_str(_pick(raw, "site_address", "address", "address_1")),
        _as_str(_pick(raw, "city")),
        _as_str(_pick(raw, "postcode")),
    ]
    joined = ", ".join(part for part in parts if part)
    return joined or None


def _extract_line_items(raw: dict[str, Any]) -> list[dict[str, str | None]]:
    items_raw = None
    for key in ("quote_items", "items", "lines", "products", "job_items"):
        candidate = raw.get(key)
        if isinstance(candidate, list) and candidate:
            items_raw = candidate
            break

    items: list[dict[str, str | None]] = []
    for row in items_raw or []:
        if not isinstance(row, dict):
            continue
        item = {
            "name": _as_str(_pick(row, "name", "item_name", "product_name", "title", "line_name")),
            "description": _as_str(_pick(row, "description", "item_description", "details", "notes")),
            "quantity": _as_str(_pick(row, "quantity", "qty", "amount", "units")),
            "unit_price": _as_str(_pick(row, "unit_price", "price", "rate", "unit_cost", "sell_price")),
            "total": _as_str(_pick(row, "total", "line_total", "amount_total", "sub_total", "subtotal")),
        }
        if any(item.values()):
            items.append(item)
    return items


def _extract_custom_fields(raw: dict[str, Any]) -> list[dict[str, str]]:
    fields: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    def add_field(label: str | None, field_key: str | None, value: Any) -> None:
        label_text = _as_str(label) or _as_str(field_key) or "Field"
        key_text = _as_str(field_key) or label_text
        if value in (None, ""):
            return
        if _is_sensitive_key(key_text) or _is_sensitive_key(label_text):
            value_text = REDACTED
        else:
            value_text = _format_custom_value(redact_sensitive_data(value))
        entry = (label_text, key_text, value_text)
        if entry in seen:
            return
        seen.add(entry)
        fields.append({"label": label_text, "field_key": key_text, "value": value_text})

    for source_key in ("custom_fields", "cf_data", "custom_field_values"):
        source = raw.get(source_key)
        if isinstance(source, dict):
            for key, value in source.items():
                add_field(str(key), str(key), value)
        elif isinstance(source, list):
            for item in source:
                if not isinstance(item, dict):
                    add_field(None, None, item)
                    continue
                label = _as_str(item.get("label") or item.get("name") or item.get("field") or item.get("key"))
                field_key = _as_str(item.get("field_key") or item.get("key") or item.get("name") or label)
                value = item.get("value")
                if value is None:
                    value = item.get("values") or item.get("display_value")
                add_field(label, field_key, value)

    return fields


def _session_matches_quote(session: CalculationSession, quote: EworksQuote) -> bool:
    resolved_id = resolve_eworks_quote_id(session)
    if resolved_id and quote.eworks_quote_id and resolved_id == quote.eworks_quote_id:
        return True

    step1 = session.step1_snapshot or {}
    payload = session.payload_snapshot or {}
    session_ref = _as_str(step1.get("quote_number") or payload.get("quote_number"))
    if session_ref and quote.quote_ref and session_ref.upper() == quote.quote_ref.upper():
        return True
    return False


def _session_matches_job(session: CalculationSession, job: EworksJob) -> bool:
    step1 = session.step1_snapshot or {}
    payload = session.payload_snapshot or {}
    session_job = _as_str(step1.get("job_number") or payload.get("job_number"))
    if session_job and job.job_ref and session_job.upper() == job.job_ref.upper():
        return True

    if job.eworks_quote_id:
        resolved_id = resolve_eworks_quote_id(session)
        if resolved_id and resolved_id == job.eworks_quote_id:
            return True
    return False


def _find_linked_estimate(db: Session, *, quote: EworksQuote | None = None, job: EworksJob | None = None) -> dict[str, Any]:
    candidates = db.scalars(
        select(CalculationSession)
        .where(CalculationSession.status.in_(("submitted", "in_progress")))
        .order_by(CalculationSession.updated_at.desc())
        .limit(300)
    ).all()

    for session in candidates:
        matched = False
        if quote is not None and _session_matches_quote(session, quote):
            matched = True
        if job is not None and _session_matches_job(session, job):
            matched = True
        if matched:
            return {
                "has_estimate_session": True,
                "session_id": str(session.id),
                "status": session.status,
                "client_accepted_at": str(session.client_accepted_at) if session.client_accepted_at else None,
            }

    return {
        "has_estimate_session": False,
        "session_id": None,
        "status": None,
        "client_accepted_at": None,
    }


def _resolve_display_customer_name(quote: EworksQuote, raw: dict[str, Any]) -> str | None:
    return _as_str(quote.customer_name) or extract_customer_name_from_raw(raw)


def _resolve_display_status(quote: EworksQuote, raw: dict[str, Any]) -> str | None:
    return resolve_eworks_quote_status_label(
        status=_as_str(quote.status) or _as_str(_pick(raw, "status", "Status")),
        status_name=quote.status_name,
        raw_payload=raw,
    )


def _resolve_display_tags(quote: EworksQuote, raw: dict[str, Any]) -> list[str]:
    tags = _serialize_tags(quote.tags) or _extract_tags_from_raw(raw)
    return tags


def _resolve_display_total(quote: EworksQuote, raw: dict[str, Any]) -> float | None:
    if quote.total is not None:
        return _as_float(quote.total)
    return _as_float(_pick(raw, "total", "quote_total", "grand_total", "total_amount"))


def _resolve_display_quote_date(quote: EworksQuote, raw: dict[str, Any]) -> str | None:
    return _as_str(quote.quote_date) or _as_str(_pick(raw, "quote_date", "Quote_Date"))


def build_quote_list_display_fields(quote: EworksQuote) -> dict[str, Any]:
    """Resolve manager-safe list display fields with raw_payload fallbacks."""
    raw = quote.raw_payload if isinstance(quote.raw_payload, dict) else {}
    return {
        "display_customer_name": _resolve_display_customer_name(quote, raw),
        "display_status": _resolve_display_status(quote, raw),
        "display_tags": _resolve_display_tags(quote, raw),
        "display_total": _resolve_display_total(quote, raw),
        "display_quote_date": _resolve_display_quote_date(quote, raw),
    }


def serialize_quote_list_item(quote: EworksQuote) -> dict[str, Any]:
    """Serialize a synced quote for list endpoints without exposing raw_payload."""
    from app.schemas.eworks_sync_api import EworksQuoteRead

    display = build_quote_list_display_fields(quote)
    return EworksQuoteRead(
        id=quote.id,
        eworks_quote_id=quote.eworks_quote_id,
        quote_ref=quote.quote_ref,
        customer_id=quote.customer_id,
        customer_name=display["display_customer_name"],
        status=quote.status,
        status_name=display["display_status"],
        quote_date=display["display_quote_date"],
        expiry_date=quote.expiry_date,
        description=quote.description,
        customer_ref=quote.customer_ref,
        po_ref=quote.po_ref,
        wo_ref=quote.wo_ref,
        subtotal=float(quote.subtotal) if quote.subtotal is not None else None,
        vat=float(quote.vat) if quote.vat is not None else None,
        total=display["display_total"],
        tags=display["display_tags"],
        synced_at=str(quote.synced_at) if quote.synced_at else None,
        display_customer_name=display["display_customer_name"],
        display_status=display["display_status"],
        display_tags=display["display_tags"],
        display_total=display["display_total"],
        display_quote_date=display["display_quote_date"],
    ).model_dump()


def build_quote_safe_detail(
    db: Session,
    quote: EworksQuote,
    *,
    auto_sync_linked_jobs: bool = True,
) -> dict[str, Any]:
    if auto_sync_linked_jobs:
        maybe_auto_sync_linked_jobs_for_quote(db, quote, opened_directly=True)

    raw = quote.raw_payload if isinstance(quote.raw_payload, dict) else {}
    customer = raw.get("customer") if isinstance(raw.get("customer"), dict) else {}
    contact = raw.get("customer_contact") if isinstance(raw.get("customer_contact"), dict) else {}
    site = raw.get("site") if isinstance(raw.get("site"), dict) else {}

    tags = _serialize_tags(quote.tags) or _extract_tags_from_raw(raw)

    detail = {
        "identity": {
            "id": quote.id,
            "eworks_quote_id": quote.eworks_quote_id,
            "quote_ref": quote.quote_ref or _as_str(_pick(raw, "quote_ref", "Quote_Ref")),
            "status": quote.status or _as_str(_pick(raw, "status", "Status")),
            "status_name": resolve_eworks_quote_status_label(
                status=quote.status or _as_str(_pick(raw, "status", "Status")),
                status_name=quote.status_name,
                raw_payload=raw,
            ),
            "synced_at": str(quote.synced_at) if quote.synced_at else None,
        },
        "customer": {
            "customer_id": quote.customer_id or extract_customer_id_from_raw(raw),
            "customer_name": _as_str(quote.customer_name) or extract_customer_name_from_raw(raw),
            "customer_contact_id": quote.customer_contact_id or extract_customer_contact_id_from_raw(raw),
            "customer_contact_name": _as_str(
                _pick(raw, "customer_contact_name")
                or _pick(contact, "full_name", "name", "contact_name")
            ),
            "customer_site_id": quote.customer_site_id or extract_customer_site_id_from_raw(raw),
            "site_name": _as_str(_pick(raw, "site_name") or _pick(site, "site_name", "name")),
            "site_address": _build_site_address(raw),
            "customer_ref": quote.customer_ref or _as_str(_pick(raw, "customer_ref")),
            "po_ref": quote.po_ref or _as_str(_pick(raw, "po_ref")),
            "wo_ref": quote.wo_ref or _as_str(_pick(raw, "wo_ref")),
        },
        "quote_details": {
            "quote_type_id": quote.quote_type_id or _pick(raw, "quote_type_id"),
            "quote_source_id": quote.quote_source_id or _pick(raw, "quote_source_id"),
            "project_id": quote.project_id or _pick(raw, "project_id"),
            "quote_date": quote.quote_date or _as_str(_pick(raw, "quote_date", "Quote_Date")),
            "expiry_date": quote.expiry_date or _as_str(_pick(raw, "expiry_date", "Expiry_Date")),
            "preferred_date": _as_str(_pick(raw, "preferred_date", "Preferred_Date")),
            "preferred_time": _as_str(_pick(raw, "preferred_time", "Preferred_Time")),
            "description": quote.description or _as_str(_pick(raw, "description")),
            "notes": quote.notes or _as_str(_pick(raw, "notes")),
            "customer_notes": quote.customer_notes or _as_str(_pick(raw, "customer_notes")),
            "terms": quote.terms or _as_str(_pick(raw, "terms")),
        },
        "financials": {
            "subtotal": _as_float(quote.subtotal) if quote.subtotal is not None else _as_float(_pick(raw, "subtotal", "sub_total")),
            "vat": _as_float(quote.vat) if quote.vat is not None else _as_float(_pick(raw, "vat", "vat_amount")),
            "total": _as_float(quote.total) if quote.total is not None else _as_float(_pick(raw, "total", "quote_total")),
            "discount_type": _as_str(_pick(raw, "discount_type")),
            "discount_value": _as_str(_pick(raw, "discount_value", "discount")),
            "currency": _as_str(_pick(raw, "currency", "Currency")) or "GBP",
        },
        "tags": tags,
        "items": _extract_line_items(raw),
        "custom_fields": _extract_custom_fields(raw),
        "dates": {
            "created_on": _as_str(_pick(raw, "created_on", "created_at", "Created_On")),
            "updated_on": _as_str(_pick(raw, "updated_on", "updated_at", "Updated_On", "timestamp")),
            "converted_date": _as_str(_pick(raw, "converted_date", "Converted_Date")),
            "accepted_date": _as_str(_pick(raw, "accepted_date", "Accepted_Date")),
        },
        "linked_estimate": _find_linked_estimate(db, quote=quote),
        "sales_appointments": merge_quote_sales_appointments(
            serialize_quote_appointments(db, quote),
            serialize_linked_job_appointments_for_quote(db, quote),
        ),
    }
    assignee = get_active_job_appointment_assignee(
        db,
        quote_id=quote.id,
        quote_ref=quote.quote_ref,
        eworks_quote_id=quote.eworks_quote_id,
    )
    if assignee is not None:
        detail["appointment_assignee"] = serialize_appointment_assignee_safe_detail(assignee)
    return redact_sensitive_data(detail)


def build_job_safe_detail(db: Session, job: EworksJob) -> dict[str, Any]:
    raw = job.raw_payload if isinstance(job.raw_payload, dict) else {}
    customer = raw.get("customer") if isinstance(raw.get("customer"), dict) else {}
    contact = raw.get("customer_contact") if isinstance(raw.get("customer_contact"), dict) else {}

    tags = _serialize_tags(job.tags) or _extract_tags_from_raw(raw)
    related_quote_ref = None
    if job.eworks_quote_id:
        related = db.query(EworksQuote).filter(EworksQuote.eworks_quote_id == job.eworks_quote_id).one_or_none()
        if related:
            related_quote_ref = related.quote_ref

    detail = {
        "identity": {
            "id": job.id,
            "eworks_job_id": job.eworks_job_id,
            "job_ref": job.job_ref or _as_str(_pick(raw, "job_ref", "Job_Ref")),
            "status": job.status or _as_str(_pick(raw, "status", "Status")),
            "status_name": job.status_name
            or _as_str(_pick_nested(raw, "job_status.job_status", "Status_Name", "status_name")),
            "synced_at": str(job.synced_at) if job.synced_at else None,
        },
        "customer": {
            "customer_id": job.customer_id or extract_customer_id_from_raw(raw),
            "customer_name": _as_str(job.customer_name) or extract_customer_name_from_raw(raw),
            "customer_contact_id": _pick(raw, "customer_contact_id") or _pick(contact, "id"),
            "customer_contact_name": _as_str(
                _pick(raw, "customer_contact_name")
                or _pick(contact, "full_name", "name", "contact_name")
            ),
            "customer_site_id": _pick(raw, "customer_site_id"),
            "site_name": _as_str(_pick(raw, "site_name")),
            "site_address": job.address or _build_site_address(raw),
        },
        "related_quote": {
            "eworks_quote_id": job.eworks_quote_id or _pick(raw, "quote_id", "eworks_quote_id"),
            "quote_ref": related_quote_ref or _as_str(_pick(raw, "quote_ref")),
        },
        "job_details": {
            "job_date": job.job_date or _as_str(_pick(raw, "job_date", "start_date")),
            "description": job.description or _as_str(_pick(raw, "description")),
            "notes": job.notes or _as_str(_pick(raw, "notes")),
        },
        "financials": {
            "subtotal": _as_float(job.subtotal) if job.subtotal is not None else _as_float(_pick(raw, "subtotal", "sub_total")),
            "vat": _as_float(job.vat) if job.vat is not None else _as_float(_pick(raw, "vat", "vat_amount")),
            "total": _as_float(job.total) if job.total is not None else _as_float(_pick(raw, "total", "job_total")),
            "discount_type": _as_str(_pick(raw, "discount_type")),
            "discount_value": _as_str(_pick(raw, "discount_value", "discount")),
            "currency": _as_str(_pick(raw, "currency", "Currency")) or "GBP",
        },
        "tags": tags,
        "items": _extract_line_items(raw),
        "custom_fields": _extract_custom_fields(raw),
        "dates": {
            "created_on": _as_str(_pick(raw, "created_on", "created_at")),
            "updated_on": _as_str(_pick(raw, "updated_on", "updated_at", "timestamp")),
            "completed_date": _as_str(_pick(raw, "completed_date", "completion_date")),
        },
        "linked_estimate": _find_linked_estimate(db, job=job),
        "appointments": serialize_job_appointments(db, job),
    }
    return redact_sensitive_data(detail)
