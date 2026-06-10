"""Resolve eWorks quote status IDs to human-readable labels."""

from __future__ import annotations

from typing import Any

# Numeric quote_status.id values from eWorks Manager (Optimal tenant).
EWORKS_QUOTE_STATUS_LABELS: dict[str, str] = {
    "1": "Draft",
    "2": "Pending",
    "3": "Approved",
    "4": "Processed",
    "5": "Call Back",
    "6": "Rejected",
    "7": "Converted",
    "8": "Sent",
    "9": "Closed",
}


def _as_str(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _pick(raw: dict[str, Any] | None, *keys: str) -> object | None:
    if not isinstance(raw, dict):
        return None
    for key in keys:
        if key in raw and raw[key] is not None:
            return raw[key]
    return None


def _pick_nested(raw: dict[str, Any] | None, *paths: str) -> object | None:
    if not isinstance(raw, dict):
        return None
    for path in paths:
        current: object = raw
        for part in path.split("."):
            if not isinstance(current, dict):
                current = None
                break
            current = current.get(part)
        if current is not None:
            return current
    return None


def _meaningful_status_name(value: object | None) -> str | None:
    text = _as_str(value)
    if text is None or text.isdigit():
        return None
    return text


def _resolve_status_id(
    status: str | None,
    raw_payload: dict[str, Any] | None,
) -> str | None:
    status_id = _as_str(status) or _as_str(_pick(raw_payload, "status", "Status"))
    if status_id:
        return status_id
    nested_id = _pick_nested(raw_payload, "quote_status.id", "QuoteStatus.id")
    return _as_str(nested_id)


def resolve_eworks_quote_status_label(
    *,
    status: str | None,
    status_name: str | None = None,
    raw_payload: dict[str, Any] | None = None,
) -> str | None:
    """Return a display label for an eWorks quote status.

    Prefers explicit names from sync data, then maps numeric IDs via
    ``EWORKS_QUOTE_STATUS_LABELS``, then falls back to the raw ID string.
    """
    for candidate in (
        status_name,
        _pick(raw_payload, "status_name", "Status_Name"),
        _pick_nested(raw_payload, "quote_status.quote_status", "quote_status.name", "QuoteStatus.quote_status"),
    ):
        label = _meaningful_status_name(candidate)
        if label:
            return label

    status_id = _resolve_status_id(status, raw_payload)
    if status_id and status_id in EWORKS_QUOTE_STATUS_LABELS:
        return EWORKS_QUOTE_STATUS_LABELS[status_id]

    return status_id
