"""Helpers for filtering/classifying eWorks quotes used across services."""

from __future__ import annotations

from sqlalchemy import Integer, String, and_, cast, or_

from app.models.eworks_sync import EworksQuote
from app.services.eworks_quote_status import EWORKS_QUOTE_STATUS_LABELS, resolve_eworks_quote_status_label

_RAW_STATUS_KEYS = ("status", "Status")
_RAW_QUOTE_STATUS_KEYS = ("quote_status", "QuoteStatus")
_RAW_QUOTE_STATUS_FIELDS = ("id", "status", "quote_status_id")
_RAW_TAG_KEYS = ("tags", "tag_names", "labels", "categories")


def _value_is_one(value: object | None) -> bool:
    if value is None:
        return False
    return str(value).strip() == "1"


def _value_equals_code(value: object | None, code: str) -> bool:
    if value is None:
        return False
    return str(value).strip() == str(code).strip()


def _json_field_equals_code(json_col, path: tuple[str, ...], code: str):
    """Exact JSON path equality — no substring/LIKE matching on raw_payload."""
    field = json_col
    for key in path:
        field = field[key]
    text_code = str(code).strip()
    clauses = [cast(field, String) == text_code]
    if text_code.isdigit():
        clauses.append(cast(field, Integer) == int(text_code))
    return or_(*clauses)


def _raw_payload_has_status_code(raw_payload_col, code: str):
    """Match status code in known raw_payload fields only (exact JSON paths)."""
    if raw_payload_col is None:
        return False
    clauses: list = []
    for key in _RAW_STATUS_KEYS:
        clauses.append(_json_field_equals_code(raw_payload_col, (key,), code))
    for qs_key in _RAW_QUOTE_STATUS_KEYS:
        for field in _RAW_QUOTE_STATUS_FIELDS:
            clauses.append(_json_field_equals_code(raw_payload_col, (qs_key, field), code))
    return or_(*clauses)


def _quote_is_draft_sql_clause(status_col, raw_payload_col):
    """SQL clause mirroring quote_is_draft() — numeric status code 1 only, no status_name."""
    col_match = or_(status_col == "1", cast(status_col, String) == "1", cast(status_col, Integer) == 1)
    if raw_payload_col is None:
        return col_match
    return or_(col_match, _raw_payload_has_status_code(raw_payload_col, "1"))


def _normalized_status_column_empty(status_col):
    return or_(status_col.is_(None), status_col == "")


def _quote_status_code_sql_clause(status_col, raw_payload_col, code: str):
    """Match quotes whose normalized status code equals ``code`` (column preferred over raw)."""
    col_match = or_(status_col == code, cast(status_col, String) == code)
    if code.isdigit():
        col_match = or_(col_match, cast(status_col, Integer) == int(code))
    if raw_payload_col is None:
        return col_match
    raw_match = _raw_payload_has_status_code(raw_payload_col, code)
    return or_(col_match, and_(_normalized_status_column_empty(status_col), raw_match))


def _normalize_status_filter_value(status: str) -> str | None:
    value = str(status).strip()
    if not value:
        return None
    if value.isdigit():
        return value
    for code, label in EWORKS_QUOTE_STATUS_LABELS.items():
        if label.casefold() == value.casefold():
            return code
    return None


def _tag_sql_clause(tag_text: str, column):
    """Build SQL clause for a tag filter on a single JSON/text column."""
    from app.services.manager_dashboard_service import (
        is_awaiting_supplier_tag,
        is_booked_tag,
        is_ready_to_send_tag,
    )

    col = cast(column, String)
    if is_booked_tag(tag_text):
        return col.ilike("%booked%")
    if is_awaiting_supplier_tag(tag_text):
        return col.ilike("%awaiting supplier%")
    if is_ready_to_send_tag(tag_text):
        return and_(
            col.ilike("%ready to send%"),
            or_(col.ilike("%quote%"), col.ilike("%quotes%")),
        )
    return col.ilike(f"%{tag_text}%")


def apply_eworks_quote_status_filter(q, status: str | None, status_col, raw_payload_col=None):
    """Apply server-side eWorks quote status filtering for list queries."""
    code = _normalize_status_filter_value(status) if status else None
    if code is None:
        return q
    if code == "1":
        return q.filter(_quote_is_draft_sql_clause(status_col, raw_payload_col))
    return q.filter(_quote_status_code_sql_clause(status_col, raw_payload_col, code))


def apply_eworks_quote_tag_filter(q, tag: str | None, tags_col, raw_payload_col=None):
    """Apply server-side tag filtering using known tag fields (AND-safe with status filter)."""
    if not tag or not str(tag).strip():
        return q
    tag_text = str(tag).strip()
    clauses = [_tag_sql_clause(tag_text, tags_col)]
    if raw_payload_col is not None:
        for key in _RAW_TAG_KEYS:
            clauses.append(_tag_sql_clause(tag_text, raw_payload_col[key]))
    return q.filter(or_(*clauses))


def needs_python_quote_filters(status: str | None, tag: str | None) -> bool:
    """True when status or tag filters require Python predicates (avoids risky JSON SQL)."""
    if status and str(status).strip():
        return True
    return bool(tag and str(tag).strip())


def quote_matches_list_filters(quote: EworksQuote, status: str | None, tag: str | None) -> bool:
    """Strict AND of status + tag filters using quote object fields (list endpoint)."""
    return quote_matches_status_filter(quote, status) and quote_matches_tag_filter(quote, tag)


def filter_quotes_in_python(
    rows: list[EworksQuote],
    status: str | None,
    tag: str | None,
) -> list[EworksQuote]:
    """Apply status/tag predicates in Python (stage 2 of two-stage quote list filtering)."""
    if not needs_python_quote_filters(status, tag):
        return rows
    return [row for row in rows if quote_matches_list_filters(row, status, tag)]


def paginate_eworks_quotes(
    q,
    *,
    status: str | None,
    tag: str | None,
    limit: int,
    offset: int,
    order_col,
):
    """Paginate quote list queries; status/tag use Python predicates when present."""
    if not needs_python_quote_filters(status, tag):
        total = q.count()
        rows = q.order_by(order_col.desc()).offset(offset).limit(limit).all()
        return rows, total

    ordered = q.order_by(order_col.desc()).all()
    filtered = filter_quotes_in_python(ordered, status, tag)
    total = len(filtered)
    return filtered[offset : offset + limit], total


def quote_is_draft(quote: EworksQuote) -> bool:
    """True when quote status code = 1 (Draft/New) based on quote object fields only.

    Checks the quote's own status fields — NOT the top-level eWorks API response status.
    Returns True when any recognised status field contains numeric 1 or string "1".
    """
    if _value_is_one(quote.status):
        return True

    raw = quote.raw_payload
    if isinstance(raw, dict):
        for key in _RAW_STATUS_KEYS:
            if _value_is_one(raw.get(key)):
                return True

        for qs_key in _RAW_QUOTE_STATUS_KEYS:
            qs = raw.get(qs_key)
            if isinstance(qs, dict):
                for field in _RAW_QUOTE_STATUS_FIELDS:
                    if _value_is_one(qs.get(field)):
                        return True

    return False


def quote_matches_status_filter(quote: EworksQuote, status: str | None) -> bool:
    """Python equivalent of apply_eworks_quote_status_filter for unit tests."""
    code = _normalize_status_filter_value(status) if status else None
    if code is None:
        return True
    if code == "1":
        return quote_is_draft(quote)
    if _value_equals_code(quote.status, code):
        return True
    if quote.status and str(quote.status).strip():
        return False

    raw = quote.raw_payload
    if not isinstance(raw, dict):
        return False
    for key in _RAW_STATUS_KEYS:
        if _value_equals_code(raw.get(key), code):
            return True
    for qs_key in _RAW_QUOTE_STATUS_KEYS:
        qs = raw.get(qs_key)
        if isinstance(qs, dict):
            for field in _RAW_QUOTE_STATUS_FIELDS:
                if _value_equals_code(qs.get(field), code):
                    return True
    return False


def quote_matches_tag_filter(quote: EworksQuote, tag: str | None) -> bool:
    """Python equivalent of apply_eworks_quote_tag_filter for unit tests."""
    from app.services.manager_dashboard_service import quote_matches_tag_filter as _matches

    return _matches(quote, tag or "")


def quote_has_no_tags(quote: EworksQuote) -> bool:
    """True when the quote has no tags in any recognised field."""
    from app.services.manager_dashboard_service import extract_all_tags

    return len(extract_all_tags(quote)) == 0


def quote_has_booked_tag(quote: EworksQuote) -> bool:
    """True when the quote has a Booked tag (case-insensitive flexible matching)."""
    from app.services.manager_dashboard_service import extract_all_tags, is_booked_tag

    tags = extract_all_tags(quote)
    return any(is_booked_tag(t) for t in tags)


# Sales pipeline eWorks status codes (Optimal tenant — local DB mapping).
# Active pipeline: status 2 / display name "Pending" (processed quote awaiting client decision).
# Not to be confused with the local sales_bucket value "pending".
EWORKS_STATUS_PROCESSED = "2"
EWORKS_PIPELINE_ACTIVE_STATUS_NAME = "pending"

# Excluded from active sales pipeline (status codes and display names).
_SALES_PIPELINE_EXCLUDED_STATUS_CODES = frozenset({"1", "3", "4", "5", "6", "7", "8", "9"})
_SALES_PIPELINE_EXCLUDED_STATUS_NAMES = frozenset({"draft", "approved", "call back", "closed", "rejected", "converted", "sent", "processed"})

# Closed outcomes for tracked pipeline rows (left active Pending/2 state).
_SALES_PIPELINE_ACCEPTED_CODES = frozenset({"3", "4"})
_SALES_PIPELINE_ACCEPTED_NAMES = frozenset({"approved", "processed"})
_SALES_PIPELINE_REJECTED_CODES = frozenset({"5", "6", "9"})
_SALES_PIPELINE_REJECTED_NAMES = frozenset({"call back", "rejected", "closed"})

# Legacy aliases used by older tests/spec wording.
EWORKS_STATUS_ACCEPTED = "4"
EWORKS_STATUS_REJECTED = "5"


def _normalized_status_name(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text.casefold() if text else None


def _quote_resolved_status_name(quote: EworksQuote) -> str | None:
    raw = quote.raw_payload if isinstance(quote.raw_payload, dict) else None
    label = resolve_eworks_quote_status_label(
        status=quote.status,
        status_name=quote.status_name,
        raw_payload=raw,
    )
    return _normalized_status_name(label) or _normalized_status_name(quote.status_name)


def resolve_quote_status_code(quote: EworksQuote) -> str | None:
    """Return normalised numeric eWorks quote status code from quote fields."""
    if quote.status and str(quote.status).strip().isdigit():
        return str(quote.status).strip()
    if quote_matches_status_filter(quote, "1"):
        return "1"
    for code in (
        EWORKS_STATUS_PROCESSED,
        *sorted(_SALES_PIPELINE_EXCLUDED_STATUS_CODES),
    ):
        if quote_matches_status_filter(quote, code):
            return code
    status = (quote.status or "").strip()
    return status if status.isdigit() else None


def quote_is_sales_pipeline_excluded(quote: EworksQuote) -> bool:
    """True when quote must not appear in the active sales pipeline."""
    code = resolve_quote_status_code(quote)
    name = _quote_resolved_status_name(quote)
    if code in _SALES_PIPELINE_EXCLUDED_STATUS_CODES:
        return True
    if name in _SALES_PIPELINE_EXCLUDED_STATUS_NAMES:
        return True
    return False


def quote_is_sales_pipeline_active(quote: EworksQuote) -> bool:
    """True for eWorks processed quotes: status 2 and/or display status Pending."""
    if quote_is_sales_pipeline_excluded(quote):
        return False

    code = resolve_quote_status_code(quote)
    if code == EWORKS_STATUS_PROCESSED:
        return True
    if quote_matches_status_filter(quote, EWORKS_STATUS_PROCESSED):
        return True

    name = _quote_resolved_status_name(quote)
    if name == EWORKS_PIPELINE_ACTIVE_STATUS_NAME:
        return True
    return False


def quote_is_sales_pipeline_accepted_closed(quote: EworksQuote) -> bool:
    code = resolve_quote_status_code(quote)
    name = _quote_resolved_status_name(quote)
    return code in _SALES_PIPELINE_ACCEPTED_CODES or name in _SALES_PIPELINE_ACCEPTED_NAMES


def quote_is_sales_pipeline_rejected_closed(quote: EworksQuote) -> bool:
    code = resolve_quote_status_code(quote)
    name = _quote_resolved_status_name(quote)
    return code in _SALES_PIPELINE_REJECTED_CODES or name in _SALES_PIPELINE_REJECTED_NAMES


def quote_is_processed(quote: EworksQuote) -> bool:
    """Sales pipeline active filter (eWorks status 2 / Pending)."""
    return quote_is_sales_pipeline_active(quote)


def quote_is_accepted(quote: EworksQuote) -> bool:
    return quote_is_sales_pipeline_accepted_closed(quote)


def quote_is_rejected(quote: EworksQuote) -> bool:
    return quote_is_sales_pipeline_rejected_closed(quote)


# Call Back dashboard — eWorks status 5 / display name "Call Back".
EWORKS_CALL_BACK_STATUS = "5"
EWORKS_CALL_BACK_STATUS_NAME = "call back"

_CALL_BACK_EXCLUDED_STATUS_CODES = frozenset({"1", "2", "3", "4", "6", "7", "8", "9"})
_CALL_BACK_EXCLUDED_STATUS_NAMES = frozenset(
    {"draft", "pending", "approved", "processed", "closed", "rejected", "converted", "sent"}
)


def quote_is_call_back_excluded(quote: EworksQuote) -> bool:
    """True when quote must not appear on the Call Back dashboard."""
    code = resolve_quote_status_code(quote)
    name = _quote_resolved_status_name(quote)
    if code in _CALL_BACK_EXCLUDED_STATUS_CODES:
        return True
    if name in _CALL_BACK_EXCLUDED_STATUS_NAMES:
        return True
    return False


def quote_is_call_back(quote: EworksQuote) -> bool:
    """True for eWorks Call Back quotes: status 5 and/or display status Call Back."""
    if quote_is_call_back_excluded(quote):
        return False

    code = resolve_quote_status_code(quote)
    if code == EWORKS_CALL_BACK_STATUS:
        return True
    if quote_matches_status_filter(quote, EWORKS_CALL_BACK_STATUS):
        return True

    name = _quote_resolved_status_name(quote)
    if name == EWORKS_CALL_BACK_STATUS_NAME:
        return True
    return False
