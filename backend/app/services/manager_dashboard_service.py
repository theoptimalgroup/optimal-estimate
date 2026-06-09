"""Manager dashboard — classify and list locally synced eWorks quotes."""

from __future__ import annotations

import json
import re
from typing import Literal, TypedDict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.eworks_sync import EworksQuote

AWAITING_SUPPLIER_TAG = "Awaiting Supplier Info (Quotes)"
READY_TO_SEND_TAG = "Quotes Ready to send (Quotes)"

QuoteBucket = Literal["new_quotes", "awaiting_supplier", "ready_to_send"]
MatchReason = Literal["draft_no_tags", "tag_awaiting_supplier", "tag_ready_to_send"]

_FETCH_LIMIT = 2000


def normalize_tag_text(tag: str) -> str:
    """Lowercase, trim, and collapse whitespace/punctuation for tag comparisons."""
    text = str(tag).strip().casefold()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r",+", ",", text)
    return text.strip(" ,")


def is_ready_to_send_tag(tag: str) -> bool:
    """True when tag text indicates a Ready to Send bucket tag."""
    norm = normalize_tag_text(tag)
    return "ready to send" in norm and ("quote" in norm or "quotes" in norm)


def is_awaiting_supplier_tag(tag: str) -> bool:
    """True when tag text indicates an Awaiting Supplier bucket tag."""
    return "awaiting supplier" in normalize_tag_text(tag)


def _value_is_one(value: object | None) -> bool:
    if value is None:
        return False
    return str(value).strip() == "1"


def _split_comma_separated_tags(text: str) -> list[str]:
    return [part.strip() for part in text.split(",") if part.strip()]


def _parse_tags_value(value: object | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        tags: list[str] = []
        for tag in value:
            if tag is None:
                continue
            text = str(tag).strip()
            if not text:
                continue
            if text.startswith("[") or text.startswith("{"):
                try:
                    parsed = json.loads(text)
                    tags.extend(_parse_tags_value(parsed))
                    continue
                except json.JSONDecodeError:
                    pass
            if "," in text:
                tags.extend(_split_comma_separated_tags(text))
            else:
                tags.append(text)
        return tags
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if text.startswith("[") or text.startswith("{"):
            try:
                parsed = json.loads(text)
                return _parse_tags_value(parsed)
            except json.JSONDecodeError:
                pass
        if "," in text:
            return _split_comma_separated_tags(text)
        return [text]
    text = str(value).strip()
    if not text:
        return []
    if "," in text:
        return _split_comma_separated_tags(text)
    return [text]


def extract_all_tags(quote: EworksQuote) -> list[str]:
    """Collect tags from normalized column and safe raw_payload fields (internal use only)."""
    tags: list[str] = []
    tags.extend(_parse_tags_value(quote.tags))

    raw = quote.raw_payload
    if isinstance(raw, dict):
        for key in ("tags", "tag_names", "labels", "categories"):
            tags.extend(_parse_tags_value(raw.get(key)))

    seen: set[str] = set()
    normalized: list[str] = []
    for tag in tags:
        folded = normalize_tag_text(tag)
        if folded and folded not in seen:
            seen.add(folded)
            normalized.append(tag.strip())
    return normalized


def _normalize_tags_for_response(tags: list | None) -> list[str]:
    return _parse_tags_value(tags)


def _quote_is_status_one(quote: EworksQuote) -> bool:
    candidates: list[object] = [quote.status, quote.status_name]

    raw = quote.raw_payload
    if isinstance(raw, dict):
        for key in ("status", "Status"):
            if key in raw:
                candidates.append(raw.get(key))
        status_obj = raw.get("quote_status")
        if isinstance(status_obj, dict):
            candidates.extend([status_obj.get("id"), status_obj.get("quote_status")])

    return any(_value_is_one(value) for value in candidates if value is not None)


def quote_matches_tag_filter(quote: EworksQuote, tag: str) -> bool:
    """Flexible tag filter matching for /manager/quotes list queries."""
    filter_text = str(tag).strip()
    if not filter_text:
        return True

    tags = extract_all_tags(quote)
    if is_ready_to_send_tag(filter_text):
        return any(is_ready_to_send_tag(item) for item in tags)
    if is_awaiting_supplier_tag(filter_text):
        return any(is_awaiting_supplier_tag(item) for item in tags)

    target = normalize_tag_text(filter_text)
    return any(target in normalize_tag_text(item) for item in tags)


def classify_eworks_quote_bucket(quote: EworksQuote) -> QuoteBucket | None:
    """Classify a quote into an operational bucket (priority: ready > awaiting > status 1)."""
    bucket, _ = classify_eworks_quote_bucket_with_reason(quote)
    return bucket


def classify_eworks_quote_bucket_with_reason(
    quote: EworksQuote,
) -> tuple[QuoteBucket | None, MatchReason | None]:
    from app.services.quote_search_service import quote_is_draft, quote_has_no_tags

    if not quote_is_draft(quote):
        return None, None  # non-draft: excluded entirely

    tags = extract_all_tags(quote)

    if any(is_ready_to_send_tag(tag) for tag in tags):
        return "ready_to_send", "tag_ready_to_send"

    if any(is_awaiting_supplier_tag(tag) for tag in tags):
        return "awaiting_supplier", "tag_awaiting_supplier"

    if quote_has_no_tags(quote):
        return "new_quotes", "draft_no_tags"

    return None, None  # draft but has unrecognised tags: not shown


def _serialize_dashboard_quote(row: EworksQuote, *, matched_reason: MatchReason | None = None) -> dict:
    data = {
        "id": row.id,
        "eworks_quote_id": row.eworks_quote_id,
        "quote_ref": row.quote_ref,
        "customer_name": row.customer_name,
        "status": row.status,
        "status_name": row.status_name,
        "tags": _normalize_tags_for_response(row.tags) or extract_all_tags(row),
        "quote_date": row.quote_date,
        "expiry_date": row.expiry_date,
        "total": float(row.total) if row.total is not None else None,
        "synced_at": str(row.synced_at) if row.synced_at else None,
    }
    if matched_reason is not None:
        data["matched_reason"] = matched_reason
    return data


def _sort_key(row: EworksQuote) -> tuple:
    quote_date = row.quote_date or ""
    synced_ts = row.synced_at.timestamp() if row.synced_at else 0.0
    return (quote_date, synced_ts)


class DashboardCategory(TypedDict):
    count: int
    filtered_count: int | None
    quotes: list[dict]


class ManagerDashboardData(TypedDict):
    categories: dict[QuoteBucket, DashboardCategory]
    last_synced_at: str | None
    totals: dict[str, int]
    quotes_excluded_non_draft: int


def _as_search_text(value: object | None) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return text


def _collect_raw_search_parts(raw: dict) -> list[str]:
    """Collect searchable site/contact strings from raw_payload (internal use only)."""
    parts: list[str] = []
    for key in (
        "site_address",
        "address",
        "address_1",
        "address_2",
        "site_name",
        "contact_name",
        "customer_contact_name",
        "city",
        "county",
        "postcode",
    ):
        value = raw.get(key)
        if value is not None and not isinstance(value, (dict, list)):
            parts.append(str(value).strip())

    site = raw.get("site") or raw.get("address")
    if isinstance(site, dict):
        for key in (
            "name",
            "site_name",
            "address_1",
            "address1",
            "address",
            "address_2",
            "address2",
            "city",
            "county",
            "postcode",
        ):
            value = site.get(key)
            if value is not None:
                parts.append(str(value).strip())

    contact = raw.get("contact") or raw.get("customer_contact")
    if isinstance(contact, dict):
        for key in ("name", "contact_name", "email", "phone"):
            value = contact.get(key)
            if value is not None:
                parts.append(str(value).strip())

    return parts


def build_quote_search_text(quote: EworksQuote) -> str:
    """Build a case-insensitive haystack for dashboard search (internal use only)."""
    parts = [
        _as_search_text(quote.quote_ref),
        _as_search_text(quote.eworks_quote_id),
        _as_search_text(quote.customer_name),
        _as_search_text(quote.quote_date),
        _as_search_text(quote.expiry_date),
        _as_search_text(quote.status),
        _as_search_text(quote.status_name),
        _as_search_text(quote.customer_ref),
        _as_search_text(quote.po_ref),
        _as_search_text(quote.wo_ref),
    ]
    parts.extend(extract_all_tags(quote))

    raw = quote.raw_payload
    if isinstance(raw, dict):
        parts.extend(_collect_raw_search_parts(raw))

    return " ".join(part for part in parts if part).casefold()


def quote_matches_search(quote: EworksQuote, search: str | None) -> bool:
    """True when quote matches optional dashboard search text."""
    if search is None or not str(search).strip():
        return True
    needle = str(search).strip().casefold()
    return needle in build_quote_search_text(quote)


def get_manager_dashboard(
    db: Session,
    *,
    limit_per_category: int = 10,
    search: str | None = None,
) -> ManagerDashboardData:
    """Build manager dashboard from local eWorks quote mirror only."""
    rows = (
        db.query(EworksQuote)
        .order_by(EworksQuote.quote_date.desc(), EworksQuote.synced_at.desc())
        .limit(_FETCH_LIMIT)
        .all()
    )

    from app.services.quote_search_service import quote_is_draft

    buckets: dict[QuoteBucket, list[tuple[EworksQuote, MatchReason | None]]] = {
        "new_quotes": [],
        "awaiting_supplier": [],
        "ready_to_send": [],
    }

    quotes_excluded_non_draft = 0
    for row in rows:
        if not quote_is_draft(row):
            quotes_excluded_non_draft += 1
            continue
        bucket, reason = classify_eworks_quote_bucket_with_reason(row)
        if bucket is not None:
            buckets[bucket].append((row, reason))

    for bucket_rows in buckets.values():
        bucket_rows.sort(key=lambda item: _sort_key(item[0]), reverse=True)

    search_active = search is not None and bool(str(search).strip())
    last_sync = db.query(func.max(EworksQuote.synced_at)).scalar()

    categories: dict[QuoteBucket, DashboardCategory] = {}
    for key, bucket_rows in buckets.items():
        total_count = len(bucket_rows)
        if search_active:
            matched_rows = [
                item for item in bucket_rows if quote_matches_search(item[0], search)
            ]
            filtered_count = len(matched_rows)
            display_rows = matched_rows[:limit_per_category]
        else:
            filtered_count = None
            display_rows = bucket_rows[:limit_per_category]

        categories[key] = {
            "count": total_count,
            "filtered_count": filtered_count,
            "quotes": [
                _serialize_dashboard_quote(row, matched_reason=reason)
                for row, reason in display_rows
            ],
        }

    return {
        "categories": categories,
        "last_synced_at": str(last_sync) if last_sync else None,
        "totals": {
            "all_open_quotes": sum(len(b) for b in buckets.values()),
        },
        "quotes_excluded_non_draft": quotes_excluded_non_draft,
    }
