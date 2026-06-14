"""Sales pipeline dashboard for processed eWorks quotes (local-only, not synced to eWorks)."""

from __future__ import annotations

import re
import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.auth.dependencies import AuthenticatedUser
from app.core.exceptions import AppError
from app.models.eworks_sync import EworksQuote
from app.models.processed_sales_pipeline import ProcessedQuoteSalesPipeline
from app.schemas.processed_dashboard import SalesPipelinePatch
from app.services.eworks_quote_status import resolve_eworks_quote_status_label
from app.services.manager_dashboard_service import extract_all_tags
from app.services.quote_search_service import (
    quote_is_sales_pipeline_accepted_closed,
    quote_is_sales_pipeline_active,
    quote_is_sales_pipeline_rejected_closed,
)

SalesBucket = Literal["pending", "possible", "strong", "dormant"]
FollowUpStatus = Literal["overdue", "due_today", "due_this_week", "no_followup", "future"]
SALES_BUCKETS: tuple[SalesBucket, ...] = ("pending", "possible", "strong", "dormant")
_FETCH_LIMIT = 5000


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _parse_dt(value: object | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(text[:26], fmt.replace(".%f", "") if ".%f" not in text else fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _quote_processed_at(quote: EworksQuote) -> datetime:
    raw = quote.raw_payload if isinstance(quote.raw_payload, dict) else {}
    for key in ("processed_on", "Processed_On", "last_updated_on", "Last_Updated_On", "updated_on", "quote_date"):
        dt = _parse_dt(raw.get(key))
        if dt:
            return dt
    if quote.synced_at:
        return quote.synced_at if quote.synced_at.tzinfo else quote.synced_at.replace(tzinfo=timezone.utc)
    if quote.created_at:
        return quote.created_at if quote.created_at.tzinfo else quote.created_at.replace(tzinfo=timezone.utc)
    return _utcnow()


def _extract_site_address(quote: EworksQuote) -> str | None:
    from app.services.eworks_site_address_service import extract_site_address_from_quote

    return extract_site_address_from_quote(quote)


def _days_between(start: datetime, end: datetime) -> int:
    start_d = start.astimezone(timezone.utc).date()
    end_d = end.astimezone(timezone.utc).date()
    return max(0, (end_d - start_d).days)


def _classify_follow_up(next_follow_up_at: datetime | None, now: datetime) -> FollowUpStatus:
    if next_follow_up_at is None:
        return "no_followup"
    fu = next_follow_up_at.astimezone(timezone.utc)
    today = now.astimezone(timezone.utc).date()
    fu_date = fu.date()
    if fu_date < today:
        return "overdue"
    if fu_date == today:
        return "due_today"
    week_end = today + timedelta(days=(6 - today.weekday()))
    if fu_date <= week_end:
        return "due_this_week"
    return "future"


def _aging_key(days: int) -> str:
    if days <= 7:
        return "0_7_days"
    if days <= 14:
        return "8_14_days"
    if days <= 30:
        return "15_30_days"
    if days <= 60:
        return "31_60_days"
    return "60_plus_days"


_QUOTE_VALUE_KEYS: tuple[str, ...] = (
    "final_total",
    "quote_total",
    "total_amount",
    "total",
    "amount",
    "value",
)


def _coerce_quote_numeric(value: object | None) -> float | None:
    """Parse int/float/Decimal/numeric/currency strings; null/empty -> missing."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        cleaned = re.sub(r"[£$€,\s]", "", text)
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _quote_value(quote: EworksQuote) -> float:
    """Resolve monetary value from synced quote columns then raw_payload fallbacks."""
    for key in _QUOTE_VALUE_KEYS:
        parsed = _coerce_quote_numeric(getattr(quote, key, None))
        if parsed is not None:
            return parsed

    raw = quote.raw_payload if isinstance(quote.raw_payload, dict) else {}
    for key in _QUOTE_VALUE_KEYS:
        parsed = _coerce_quote_numeric(raw.get(key))
        if parsed is not None:
            return parsed

    return 0.0


def _quote_detail_link(synced_id: int) -> str:
    return f"/manager/quotes?quote_id={synced_id}"


def _pipeline_map(db: Session) -> dict[int, ProcessedQuoteSalesPipeline]:
    rows = db.query(ProcessedQuoteSalesPipeline).limit(_FETCH_LIMIT).all()
    return {row.eworks_quote_id: row for row in rows}


def _ensure_pipeline_row(
    db: Session,
    quote: EworksQuote,
    pipeline_by_eworks: dict[int, ProcessedQuoteSalesPipeline],
    *,
    persist: bool = False,
) -> ProcessedQuoteSalesPipeline:
    existing = pipeline_by_eworks.get(quote.eworks_quote_id)
    if existing:
        if existing.synced_quote_id is None:
            existing.synced_quote_id = quote.id
        return existing

    processed_at = _quote_processed_at(quote)
    row = ProcessedQuoteSalesPipeline(
        id=uuid.uuid4(),
        synced_quote_id=quote.id,
        eworks_quote_id=quote.eworks_quote_id,
        quote_ref=quote.quote_ref,
        sales_bucket="pending",
        processed_at=processed_at,
        bucket_changed_at=processed_at,
    )
    if persist:
        db.add(row)
        db.flush()
    pipeline_by_eworks[quote.eworks_quote_id] = row
    return row


def _sync_closed_fields(row: ProcessedQuoteSalesPipeline, quote: EworksQuote, now: datetime) -> None:
    if quote_is_sales_pipeline_active(quote):
        return
    if quote_is_sales_pipeline_accepted_closed(quote):
        if row.accepted_at is None:
            row.accepted_at = now
        row.closed_at = row.closed_at or row.accepted_at
        row.closed_reason = row.closed_reason or "accepted"
    elif quote_is_sales_pipeline_rejected_closed(quote):
        if row.rejected_at is None:
            row.rejected_at = now
        row.closed_at = row.closed_at or row.rejected_at
        row.closed_reason = row.closed_reason or "rejected"


def _pipeline_closed_outcome(
    row: ProcessedQuoteSalesPipeline,
    quote: EworksQuote,
) -> Literal["accepted", "rejected"] | None:
    if row.accepted_at or row.closed_reason == "accepted":
        return "accepted"
    if row.rejected_at or row.closed_reason == "rejected":
        return "rejected"
    if quote_is_sales_pipeline_accepted_closed(quote):
        return "accepted"
    if quote_is_sales_pipeline_rejected_closed(quote):
        return "rejected"
    return None


def _closed_at_for_pipeline_row(row: ProcessedQuoteSalesPipeline, now: datetime) -> datetime:
    return row.accepted_at or row.rejected_at or row.closed_at or now


def _build_quote_row(
    quote: EworksQuote,
    pipeline: ProcessedQuoteSalesPipeline,
    now: datetime,
) -> dict[str, Any]:
    processed_at = pipeline.processed_at or _quote_processed_at(quote)
    bucket_changed_at = pipeline.bucket_changed_at or processed_at
    days_since = _days_between(processed_at, now)
    days_in_bucket = _days_between(bucket_changed_at, now)
    next_fu = pipeline.next_follow_up_at
    status_code = quote.status
    status_name = resolve_eworks_quote_status_label(
        status=quote.status,
        status_name=quote.status_name,
        raw_payload=quote.raw_payload if isinstance(quote.raw_payload, dict) else None,
    )
    bucket = pipeline.sales_bucket if pipeline.sales_bucket in SALES_BUCKETS else "pending"
    return {
        "id": quote.id,
        "quote_ref": quote.quote_ref,
        "eworks_quote_id": quote.eworks_quote_id,
        "customer_name": quote.customer_name,
        "site_address": _extract_site_address(quote),
        "quote_value": _quote_value(quote),
        "processed_at": _iso(processed_at),
        "days_since_processed": days_since,
        "days_in_current_bucket": days_in_bucket,
        "last_follow_up_at": _iso(pipeline.last_follow_up_at),
        "next_follow_up_at": _iso(next_fu),
        "follow_up_status": _classify_follow_up(next_fu, now),
        "sales_bucket": bucket,
        "sales_note": pipeline.sales_note,
        "assigned_sales_name": pipeline.assigned_sales_name,
        "assigned_sales_email": pipeline.assigned_sales_email,
        "assigned_sales_user_id": str(pipeline.assigned_sales_user_id) if pipeline.assigned_sales_user_id else None,
        "eworks_status": status_code,
        "eworks_status_name": status_name,
        "tags": extract_all_tags(quote),
        "quote_detail_link": _quote_detail_link(quote.id),
    }


def _empty_category() -> dict[str, Any]:
    return {"count": 0, "value": 0.0, "average_age_days": 0.0, "overdue_followups": 0, "quotes": []}


def _add_to_category(cat: dict[str, Any], row: dict[str, Any]) -> None:
    cat["count"] += 1
    cat["value"] += float(row.get("quote_value") or 0)
    cat["average_age_days"] += float(row.get("days_since_processed") or 0)
    if row.get("follow_up_status") == "overdue":
        cat["overdue_followups"] += 1
    cat["quotes"].append(row)


def _finalize_category(cat: dict[str, Any]) -> dict[str, Any]:
    if cat["count"] > 0:
        cat["average_age_days"] = round(cat["average_age_days"] / cat["count"], 1)
    cat["value"] = round(cat["value"], 2)
    return cat


def get_processed_dashboard(db: Session, *, search: str | None = None) -> dict[str, Any]:
    now = _utcnow()
    pipeline_by_eworks = _pipeline_map(db)

    quotes_q = db.query(EworksQuote).order_by(EworksQuote.synced_at.desc()).limit(_FETCH_LIMIT)
    all_quotes = quotes_q.all()

    if search:
        term = search.strip().casefold()
        all_quotes = [
            q
            for q in all_quotes
            if term in (q.quote_ref or "").casefold()
            or term in (q.customer_name or "").casefold()
        ]

    active_quotes = [q for q in all_quotes if quote_is_sales_pipeline_active(q)]
    quotes_by_eworks_id = {q.eworks_quote_id: q for q in all_quotes}

    for quote in active_quotes:
        _ensure_pipeline_row(db, quote, pipeline_by_eworks, persist=False)

    categories: dict[str, dict[str, Any]] = {b: _empty_category() for b in SALES_BUCKETS}
    aging: dict[str, dict[str, Any]] = {
        k: {"count": 0, "value": 0.0}
        for k in ("0_7_days", "8_14_days", "15_30_days", "31_60_days", "60_plus_days")
    }
    reminders: dict[str, list[dict[str, Any]]] = {
        "overdue": [],
        "due_today": [],
        "due_this_week": [],
        "no_followup_set": [],
    }

    active_rows: list[dict[str, Any]] = []
    for quote in active_quotes:
        pipeline = _ensure_pipeline_row(db, quote, pipeline_by_eworks, persist=False)
        row = _build_quote_row(quote, pipeline, now)
        active_rows.append(row)
        bucket = row["sales_bucket"]
        if bucket in categories:
            _add_to_category(categories[bucket], row)
        aging_key = _aging_key(row["days_since_processed"])
        aging[aging_key]["count"] += 1
        aging[aging_key]["value"] += float(row.get("quote_value") or 0)
        fu_status = row["follow_up_status"]
        reminder_key = "no_followup_set" if fu_status == "no_followup" else fu_status
        if reminder_key in reminders:
            reminders[reminder_key].append(row)
        elif fu_status == "future":
            pass

    for bucket in SALES_BUCKETS:
        categories[bucket] = _finalize_category(categories[bucket])

    for key in aging:
        aging[key]["value"] = round(aging[key]["value"], 2)

    pipeline_value = sum(float(r.get("quote_value") or 0) for r in active_rows)
    strong_value = sum(
        float(r.get("quote_value") or 0) for r in active_rows if r.get("sales_bucket") == "strong"
    )
    dormant_quotes = categories["dormant"]["count"]
    overdue_count = len(reminders["overdue"])
    due_today_count = len(reminders["due_today"])
    no_followup_count = len(reminders["no_followup_set"])
    avg_age = (
        round(sum(r["days_since_processed"] for r in active_rows) / len(active_rows), 1)
        if active_rows
        else 0.0
    )

    accepted_count = 0
    rejected_count = 0
    accepted_value = 0.0
    rejected_value = 0.0
    trend_by_month: dict[str, dict[str, float | int]] = defaultdict(
        lambda: {
            "accepted_count": 0,
            "rejected_count": 0,
            "accepted_value": 0.0,
            "rejected_value": 0.0,
            "new_processed_value": 0.0,
            "active_pipeline_value": 0.0,
            "strong_pipeline_value": 0.0,
        }
    )

    for row in pipeline_by_eworks.values():
        quote = quotes_by_eworks_id.get(row.eworks_quote_id)
        if quote is None or quote_is_sales_pipeline_active(quote):
            continue
        outcome = _pipeline_closed_outcome(row, quote)
        if outcome is None:
            continue
        val = _quote_value(quote)
        closed_dt = _closed_at_for_pipeline_row(row, now)
        month = closed_dt.strftime("%Y-%m")
        if outcome == "accepted":
            accepted_count += 1
            accepted_value += val
            trend_by_month[month]["accepted_count"] += 1
            trend_by_month[month]["accepted_value"] += val
        else:
            rejected_count += 1
            rejected_value += val
            trend_by_month[month]["rejected_count"] += 1
            trend_by_month[month]["rejected_value"] += val

    for row in active_rows:
        month = (row.get("processed_at") or "")[:7]
        if month:
            trend_by_month[month]["new_processed_value"] += float(row.get("quote_value") or 0)
            trend_by_month[month]["active_pipeline_value"] += float(row.get("quote_value") or 0)
            if row.get("sales_bucket") == "strong":
                trend_by_month[month]["strong_pipeline_value"] += float(row.get("quote_value") or 0)

    closed_total = accepted_count + rejected_count
    conversion_rate = round((accepted_count / closed_total) * 100, 1) if closed_total else 0.0

    perf: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "salesperson_name": None,
            "salesperson_email": None,
            "assigned_count": 0,
            "pipeline_value": 0.0,
            "strong_value": 0.0,
            "accepted_count": 0,
            "rejected_count": 0,
            "overdue_followups": 0,
            "days_to_close_total": 0,
            "days_to_close_count": 0,
        }
    )

    for row in active_rows:
        key = row.get("assigned_sales_email") or row.get("assigned_sales_name") or "unassigned"
        p = perf[key]
        p["salesperson_name"] = row.get("assigned_sales_name")
        p["salesperson_email"] = row.get("assigned_sales_email")
        p["assigned_count"] += 1
        p["pipeline_value"] += float(row.get("quote_value") or 0)
        if row.get("sales_bucket") == "strong":
            p["strong_value"] += float(row.get("quote_value") or 0)
        if row.get("follow_up_status") == "overdue":
            p["overdue_followups"] += 1

    for row in pipeline_by_eworks.values():
        quote = quotes_by_eworks_id.get(row.eworks_quote_id)
        if quote is None or quote_is_sales_pipeline_active(quote):
            continue
        outcome = _pipeline_closed_outcome(row, quote)
        if outcome is None:
            continue
        key = row.assigned_sales_email or row.assigned_sales_name or "unassigned"
        p = perf[key]
        p["salesperson_name"] = row.assigned_sales_name
        p["salesperson_email"] = row.assigned_sales_email
        if outcome == "accepted":
            p["accepted_count"] += 1
        else:
            p["rejected_count"] += 1
        if row.processed_at and row.closed_at:
            p["days_to_close_total"] += _days_between(row.processed_at, row.closed_at)
            p["days_to_close_count"] += 1

    salesperson_performance = []
    for p in perf.values():
        closed = p["accepted_count"] + p["rejected_count"]
        salesperson_performance.append(
            {
                "salesperson_name": p["salesperson_name"],
                "salesperson_email": p["salesperson_email"],
                "assigned_count": p["assigned_count"],
                "pipeline_value": round(p["pipeline_value"], 2),
                "strong_value": round(p["strong_value"], 2),
                "accepted_count": p["accepted_count"],
                "rejected_count": p["rejected_count"],
                "conversion_rate": round((p["accepted_count"] / closed) * 100, 1) if closed else 0.0,
                "overdue_followups": p["overdue_followups"],
                "average_days_to_close": (
                    round(p["days_to_close_total"] / p["days_to_close_count"], 1)
                    if p["days_to_close_count"]
                    else None
                ),
            }
        )
    salesperson_performance.sort(key=lambda x: (-x["pipeline_value"], x["salesperson_email"] or ""))

    months_sorted = sorted(trend_by_month.keys())
    accepted_rejected_trend = [
        {
            "month": m,
            "accepted_count": int(trend_by_month[m]["accepted_count"]),
            "rejected_count": int(trend_by_month[m]["rejected_count"]),
            "accepted_value": round(float(trend_by_month[m]["accepted_value"]), 2),
            "rejected_value": round(float(trend_by_month[m]["rejected_value"]), 2),
        }
        for m in months_sorted
    ]
    monthly_pipeline_value = [
        {
            "month": m,
            "new_processed_value": round(float(trend_by_month[m]["new_processed_value"]), 2),
            "active_pipeline_value": round(float(trend_by_month[m]["active_pipeline_value"]), 2),
            "strong_pipeline_value": round(float(trend_by_month[m]["strong_pipeline_value"]), 2),
            "accepted_value": round(float(trend_by_month[m]["accepted_value"]), 2),
            "rejected_value": round(float(trend_by_month[m]["rejected_value"]), 2),
        }
        for m in months_sorted
    ]

    return {
        "totals": {
            "processed_quotes": len(active_rows),
            "pipeline_value": round(pipeline_value, 2),
            "strong_value": round(strong_value, 2),
            "dormant_quotes": dormant_quotes,
            "overdue_followups": overdue_count,
            "due_today_followups": due_today_count,
            "no_followup_set": no_followup_count,
            "average_age_days": avg_age,
            "conversion_rate": conversion_rate,
            "accepted_count": accepted_count,
            "rejected_count": rejected_count,
            "accepted_value": round(accepted_value, 2),
            "rejected_value": round(rejected_value, 2),
        },
        "categories": {b: categories[b] for b in SALES_BUCKETS},
        "aging": aging,
        "follow_up_reminders": reminders,
        "salesperson_performance": salesperson_performance,
        "accepted_rejected_trend": accepted_rejected_trend,
        "monthly_pipeline_value": monthly_pipeline_value,
    }


def patch_sales_pipeline(
    db: Session,
    synced_quote_id: int,
    payload: SalesPipelinePatch,
    actor: AuthenticatedUser,
) -> ProcessedQuoteSalesPipeline:
    quote = db.query(EworksQuote).filter(EworksQuote.id == synced_quote_id).first()
    if quote is None:
        raise AppError("quote_not_found", "Quote not found", status_code=404)

    pipeline_by_eworks = _pipeline_map(db)
    if not (
        quote_is_sales_pipeline_active(quote)
        or quote.eworks_quote_id in pipeline_by_eworks
    ):
        raise AppError(
            "quote_not_in_pipeline",
            "Sales pipeline is only available for processed, accepted, or rejected quotes",
            status_code=400,
        )

    row = _ensure_pipeline_row(db, quote, pipeline_by_eworks, persist=True)
    now = _utcnow()

    if payload.sales_bucket is not None:
        if payload.sales_bucket not in SALES_BUCKETS:
            raise AppError("invalid_bucket", "Invalid sales bucket", status_code=400)
        if row.sales_bucket != payload.sales_bucket:
            row.sales_bucket = payload.sales_bucket
            row.bucket_changed_at = now
    if payload.sales_note is not None:
        row.sales_note = payload.sales_note.strip() or None
    if payload.assigned_sales_user_id is not None:
        row.assigned_sales_user_id = uuid.UUID(payload.assigned_sales_user_id) if payload.assigned_sales_user_id else None
    if payload.assigned_sales_email is not None:
        row.assigned_sales_email = payload.assigned_sales_email.strip() or None
    if payload.assigned_sales_name is not None:
        row.assigned_sales_name = payload.assigned_sales_name.strip() or None
    if payload.last_follow_up_at is not None:
        row.last_follow_up_at = _parse_dt(payload.last_follow_up_at) if payload.last_follow_up_at else None
    if payload.next_follow_up_at is not None:
        row.next_follow_up_at = _parse_dt(payload.next_follow_up_at) if payload.next_follow_up_at else None

    row.last_activity_at = now
    row.updated_by = uuid.UUID(str(actor.id))
    if row.created_by is None:
        row.created_by = uuid.UUID(str(actor.id))
    row.synced_quote_id = quote.id
    row.quote_ref = quote.quote_ref
    _sync_closed_fields(row, quote, now)

    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def pipeline_row_to_read(row: ProcessedQuoteSalesPipeline) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "synced_quote_id": row.synced_quote_id,
        "eworks_quote_id": row.eworks_quote_id,
        "quote_ref": row.quote_ref,
        "sales_bucket": row.sales_bucket,
        "sales_note": row.sales_note,
        "assigned_sales_user_id": str(row.assigned_sales_user_id) if row.assigned_sales_user_id else None,
        "assigned_sales_email": row.assigned_sales_email,
        "assigned_sales_name": row.assigned_sales_name,
        "processed_at": _iso(row.processed_at),
        "last_follow_up_at": _iso(row.last_follow_up_at),
        "next_follow_up_at": _iso(row.next_follow_up_at),
        "bucket_changed_at": _iso(row.bucket_changed_at),
        "accepted_at": _iso(row.accepted_at),
        "rejected_at": _iso(row.rejected_at),
        "closed_at": _iso(row.closed_at),
    }
