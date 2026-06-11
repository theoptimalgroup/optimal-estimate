"""Call Back dashboard for eWorks Call Back quotes (local-only, not synced to eWorks)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.auth.dependencies import AuthenticatedUser
from app.core.exceptions import AppError
from app.models.call_back_tracking import CallBackQuoteTracking
from app.models.eworks_sync import EworksQuote
from app.schemas.call_back_dashboard import CallBackTrackingPatch
from app.services.eworks_quote_status import resolve_eworks_quote_status_label
from app.services.manager_dashboard_service import extract_all_tags
from app.services.processed_dashboard_service import (
    _days_between,
    _extract_site_address,
    _iso,
    _parse_dt,
    _quote_value,
    _utcnow,
)
from app.services.quote_search_service import quote_is_call_back

CallBackBucket = Literal["overdue", "due_today", "upcoming", "no_call_date"]
CallBackStatus = Literal["overdue", "due_today", "upcoming", "no_call_date", "completed"]
CALL_BACK_BUCKETS: tuple[CallBackBucket, ...] = ("overdue", "due_today", "upcoming", "no_call_date")
_FETCH_LIMIT = 5000


def _quote_updated_at(quote: EworksQuote) -> datetime:
    raw = quote.raw_payload if isinstance(quote.raw_payload, dict) else {}
    for key in ("last_updated_on", "Last_Updated_On", "updated_on", "quote_date"):
        dt = _parse_dt(raw.get(key))
        if dt:
            return dt
    if quote.updated_at:
        return quote.updated_at if quote.updated_at.tzinfo else quote.updated_at.replace(tzinfo=timezone.utc)
    if quote.synced_at:
        return quote.synced_at if quote.synced_at.tzinfo else quote.synced_at.replace(tzinfo=timezone.utc)
    return _utcnow()


def _quote_created_on(quote: EworksQuote) -> str | None:
    raw = quote.raw_payload if isinstance(quote.raw_payload, dict) else {}
    for key in ("created_on", "Created_On", "quote_date", "Quote_Date"):
        val = raw.get(key)
        if val:
            return str(val)
    if quote.created_at:
        return _iso(quote.created_at)
    return None


def _quote_last_updated_on(quote: EworksQuote) -> str | None:
    raw = quote.raw_payload if isinstance(quote.raw_payload, dict) else {}
    for key in ("last_updated_on", "Last_Updated_On", "updated_on"):
        val = raw.get(key)
        if val:
            return str(val)
    return _iso(_quote_updated_at(quote))


def _classify_call_bucket(next_call_at: datetime | None, now: datetime) -> CallBackBucket:
    if next_call_at is None:
        return "no_call_date"
    call_date = next_call_at.astimezone(timezone.utc).date()
    today = now.astimezone(timezone.utc).date()
    if call_date < today:
        return "overdue"
    if call_date == today:
        return "due_today"
    return "upcoming"


def _resolve_call_status(
    tracking: CallBackQuoteTracking | None,
    next_call_at: datetime | None,
    now: datetime,
) -> CallBackStatus:
    if tracking and tracking.call_status == "completed":
        return "completed"
    return _classify_call_bucket(next_call_at, now)


def _quote_detail_link(synced_id: int) -> str:
    return f"/manager/quotes?quote_id={synced_id}"


def _tracking_map(db: Session) -> dict[int, CallBackQuoteTracking]:
    rows = db.query(CallBackQuoteTracking).limit(_FETCH_LIMIT).all()
    return {row.eworks_quote_id: row for row in rows}


def _ensure_tracking_row(
    db: Session,
    quote: EworksQuote,
    tracking_by_eworks: dict[int, CallBackQuoteTracking],
    *,
    persist: bool = False,
) -> CallBackQuoteTracking:
    existing = tracking_by_eworks.get(quote.eworks_quote_id)
    if existing:
        if existing.synced_quote_id is None:
            existing.synced_quote_id = quote.id
        return existing

    row = CallBackQuoteTracking(
        id=uuid.uuid4(),
        synced_quote_id=quote.id,
        eworks_quote_id=quote.eworks_quote_id,
        quote_ref=quote.quote_ref,
        call_status="no_call_date",
    )
    if persist:
        db.add(row)
        db.flush()
    tracking_by_eworks[quote.eworks_quote_id] = row
    return row


def _empty_category() -> dict[str, Any]:
    return {"count": 0, "value": 0.0, "quotes": []}


def _add_to_category(cat: dict[str, Any], row: dict[str, Any]) -> None:
    cat["count"] += 1
    cat["value"] += float(row.get("quote_value") or 0)
    cat["quotes"].append(row)


def _build_quote_row(
    quote: EworksQuote,
    tracking: CallBackQuoteTracking,
    now: datetime,
) -> dict[str, Any]:
    updated_at = _quote_updated_at(quote)
    next_call = tracking.next_call_at
    status_code = quote.status
    status_name = resolve_eworks_quote_status_label(
        status=quote.status,
        status_name=quote.status_name,
        raw_payload=quote.raw_payload if isinstance(quote.raw_payload, dict) else None,
    )
    bucket = _classify_call_bucket(next_call, now)
    return {
        "id": quote.id,
        "quote_ref": quote.quote_ref,
        "eworks_quote_id": quote.eworks_quote_id,
        "customer_name": quote.customer_name,
        "site_address": _extract_site_address(quote),
        "quote_value": _quote_value(quote),
        "status": status_code,
        "status_name": status_name,
        "tags": extract_all_tags(quote),
        "created_on": _quote_created_on(quote),
        "last_updated_on": _quote_last_updated_on(quote),
        "days_since_updated": _days_between(updated_at, now),
        "assigned_name": tracking.assigned_name,
        "assigned_email": tracking.assigned_email,
        "call_note": tracking.call_note,
        "last_called_at": _iso(tracking.last_called_at),
        "next_call_at": _iso(next_call),
        "call_status": _resolve_call_status(tracking, next_call, now),
        "quote_detail_link": _quote_detail_link(quote.id),
        "_bucket": bucket,
    }


def get_call_back_dashboard(db: Session, *, search: str | None = None) -> dict[str, Any]:
    now = _utcnow()
    tracking_by_eworks = _tracking_map(db)

    all_quotes = db.query(EworksQuote).order_by(EworksQuote.synced_at.desc()).limit(_FETCH_LIMIT).all()

    if search:
        term = search.strip().casefold()
        all_quotes = [
            q
            for q in all_quotes
            if term in (q.quote_ref or "").casefold()
            or term in (q.customer_name or "").casefold()
        ]

    call_back_quotes = [q for q in all_quotes if quote_is_call_back(q)]

    categories: dict[str, dict[str, Any]] = {b: _empty_category() for b in CALL_BACK_BUCKETS}
    quote_rows: list[dict[str, Any]] = []

    for quote in call_back_quotes:
        tracking = _ensure_tracking_row(db, quote, tracking_by_eworks, persist=False)
        row = _build_quote_row(quote, tracking, now)
        bucket = row.pop("_bucket")
        quote_rows.append(row)
        if bucket in categories:
            _add_to_category(categories[bucket], row)

    for bucket in CALL_BACK_BUCKETS:
        categories[bucket]["value"] = round(categories[bucket]["value"], 2)

    total_value = sum(float(r.get("quote_value") or 0) for r in quote_rows)
    avg_age = (
        round(sum(r["days_since_updated"] for r in quote_rows) / len(quote_rows), 1)
        if quote_rows
        else 0.0
    )

    return {
        "totals": {
            "call_back_quotes": len(quote_rows),
            "total_quote_value": round(total_value, 2),
            "overdue_calls": categories["overdue"]["count"],
            "due_today_calls": categories["due_today"]["count"],
            "upcoming_calls": categories["upcoming"]["count"],
            "no_call_date": categories["no_call_date"]["count"],
            "average_age_days": avg_age,
        },
        "categories": {b: categories[b] for b in CALL_BACK_BUCKETS},
    }


def patch_call_back_tracking(
    db: Session,
    synced_quote_id: int,
    payload: CallBackTrackingPatch,
    actor: AuthenticatedUser,
) -> CallBackQuoteTracking:
    quote = db.query(EworksQuote).filter(EworksQuote.id == synced_quote_id).first()
    if quote is None:
        raise AppError("quote_not_found", "Quote not found", status_code=404)

    if not quote_is_call_back(quote):
        raise AppError(
            "quote_not_call_back",
            "Call Back tracking is only available for Call Back quotes",
            status_code=400,
        )

    tracking_by_eworks = _tracking_map(db)
    row = _ensure_tracking_row(db, quote, tracking_by_eworks, persist=True)
    now = _utcnow()

    if payload.assigned_user_id is not None:
        row.assigned_user_id = uuid.UUID(payload.assigned_user_id) if payload.assigned_user_id else None
    if payload.assigned_name is not None:
        row.assigned_name = payload.assigned_name.strip() or None
    if payload.assigned_email is not None:
        row.assigned_email = payload.assigned_email.strip() or None
    if payload.call_note is not None:
        row.call_note = payload.call_note.strip() or None
    if payload.last_called_at is not None:
        row.last_called_at = _parse_dt(payload.last_called_at) if payload.last_called_at else None
    if payload.next_call_at is not None:
        row.next_call_at = _parse_dt(payload.next_call_at) if payload.next_call_at else None

    if row.next_call_at:
        row.call_status = _classify_call_bucket(row.next_call_at, now)
    elif row.last_called_at and payload.last_called_at:
        row.call_status = "completed"
    else:
        row.call_status = "no_call_date"
    row.updated_by = uuid.UUID(str(actor.id))
    if row.created_by is None:
        row.created_by = uuid.UUID(str(actor.id))
    row.synced_quote_id = quote.id
    row.quote_ref = quote.quote_ref

    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def tracking_row_to_read(row: CallBackQuoteTracking) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "synced_quote_id": row.synced_quote_id,
        "eworks_quote_id": row.eworks_quote_id,
        "quote_ref": row.quote_ref,
        "assigned_user_id": str(row.assigned_user_id) if row.assigned_user_id else None,
        "assigned_name": row.assigned_name,
        "assigned_email": row.assigned_email,
        "call_note": row.call_note,
        "last_called_at": _iso(row.last_called_at),
        "next_call_at": _iso(row.next_call_at),
        "call_status": row.call_status,
    }
