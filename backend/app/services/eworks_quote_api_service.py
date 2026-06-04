from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import AppError

logger = logging.getLogger(__name__)

SENSITIVE_VALUE_PATTERN = re.compile(
    r"(api[_-]?key|session[_-]?token|password|secret|authorization|public[_-]?quote[_-]?token)",
    re.IGNORECASE,
)


class EworksQuoteApiError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _api_headers() -> dict[str, str]:
    return {
        "api_key": settings.eworks_api_key or "",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _ensure_api_configured() -> tuple[str, str]:
    if not settings.eworks_api_enabled:
        raise EworksQuoteApiError("eWorks API is disabled")
    base_url = (settings.eworks_base_url or "").rstrip("/")
    api_key = settings.eworks_api_key
    if not base_url or not api_key:
        raise EworksQuoteApiError("eWorks API base URL or API key is not configured")
    return base_url, api_key


def redact_sync_record(data: Any) -> Any:
    if isinstance(data, dict):
        redacted: dict[str, Any] = {}
        for key, value in data.items():
            if SENSITIVE_VALUE_PATTERN.search(str(key)):
                redacted[key] = "***REDACTED***"
            elif isinstance(value, str) and SENSITIVE_VALUE_PATTERN.search(value):
                redacted[key] = "***REDACTED***"
            else:
                redacted[key] = redact_sync_record(value)
        return redacted
    if isinstance(data, list):
        return [redact_sync_record(item) for item in data]
    if isinstance(data, str) and SENSITIVE_VALUE_PATTERN.search(data):
        return "***REDACTED***"
    return data


def build_custom_field_payload(field_key: str, value: str) -> dict[str, Any]:
    """Minimal cf_data-only payload for custom field updates."""
    return {"cf_data": {field_key: value}}


def update_quote_custom_field(quote_id: int, field_key: str, value: str) -> dict[str, Any]:
    """Update a single eWorks Quote custom field via cf_data.

    Uses PUT /Quote/{id} with a minimal cf_data payload only.
    Callers must catch EworksQuoteApiError; acceptance must never depend on this succeeding.
    """
    base_url, _ = _ensure_api_configured()
    url = f"{base_url}/Quote/{quote_id}"
    payload = build_custom_field_payload(field_key, value)

    try:
        with httpx.Client(timeout=settings.eworks_api_timeout_seconds) as client:
            response = client.put(url, headers=_api_headers(), json=payload)
    except httpx.TimeoutException as exc:
        raise EworksQuoteApiError("eWorks Quote API timed out") from exc
    except httpx.HTTPError as exc:
        raise EworksQuoteApiError("Could not reach eWorks Quote API") from exc

    if response.status_code >= 500:
        raise EworksQuoteApiError(
            f"eWorks Quote API returned {response.status_code}",
            status_code=response.status_code,
        )
    if response.status_code >= 400:
        detail = response.text[:500] if response.text else f"HTTP {response.status_code}"
        raise EworksQuoteApiError(
            f"eWorks Quote API rejected update: {detail}",
            status_code=response.status_code,
        )

    try:
        body = response.json()
    except ValueError:
        body = {"status": "ok", "raw": response.text[:500] if response.text else ""}

    logger.info(
        "Updated eWorks quote custom field quote_id=%s field_key=%s",
        quote_id,
        field_key,
    )
    return redact_sync_record(body if isinstance(body, dict) else {"response": body})
