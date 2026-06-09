"""Helpers for filtering/classifying eWorks quotes used across services."""

from __future__ import annotations

from app.models.eworks_sync import EworksQuote


def _value_is_one(value: object | None) -> bool:
    if value is None:
        return False
    return str(value).strip() == "1"


def quote_is_draft(quote: EworksQuote) -> bool:
    """True when quote status code = 1 (Draft/New) based on quote object fields only.

    Checks the quote's own status fields — NOT the top-level eWorks API response status.
    Returns True when any recognised status field contains numeric 1 or string "1".
    """
    if _value_is_one(quote.status):
        return True

    raw = quote.raw_payload
    if isinstance(raw, dict):
        for key in ("status", "Status"):
            if _value_is_one(raw.get(key)):
                return True

        for qs_key in ("quote_status", "QuoteStatus"):
            qs = raw.get(qs_key)
            if isinstance(qs, dict):
                for field in ("id", "status", "quote_status_id"):
                    if _value_is_one(qs.get(field)):
                        return True

    return False


def quote_has_no_tags(quote: EworksQuote) -> bool:
    """True when the quote has no tags in any recognised field."""
    from app.services.manager_dashboard_service import extract_all_tags

    return len(extract_all_tags(quote)) == 0
