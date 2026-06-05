"""eWorks API client: fetch Quote and Job records with safe pagination.

Read-only from eWorks — this module never writes to eWorks.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import AppError
from app.schemas.eworks_sync_api import EworksSyncApiResponse

logger = logging.getLogger(__name__)

_DEFAULT_PER_PAGE = 100
_MAX_PAGES = 500  # safety ceiling


@dataclass
class _PageResult:
    records: list[dict[str, Any]]
    current_page: int
    last_page: int


def _require_eworks_credentials() -> tuple[str, str]:
    base_url = (settings.eworks_base_url or "").rstrip("/")
    api_key = settings.eworks_api_key or ""
    if not base_url:
        raise AppError("EWORKS_API_MISCONFIGURED", "EWORKS_BASE_URL is not configured", 503)
    if not api_key:
        raise AppError("EWORKS_API_MISCONFIGURED", "EWORKS_API_KEY is not configured", 503)
    return base_url, api_key


def _fetch_page(
    client: httpx.Client,
    *,
    url: str,
    api_key: str,
    page: int,
    per_page: int = _DEFAULT_PER_PAGE,
    extra_params: dict[str, Any] | None = None,
) -> _PageResult:
    headers = {"api_key": api_key, "Accept": "application/json"}
    params: dict[str, Any] = {"page": page, "per_page": per_page}
    if extra_params:
        params.update({k: v for k, v in extra_params.items() if v is not None})

    try:
        response = client.get(url, headers=headers, params=params)
    except httpx.TimeoutException as exc:
        raise AppError("EWORKS_API_UNAVAILABLE", f"eWorks API timed out: {url}", 502) from exc
    except httpx.HTTPError as exc:
        raise AppError("EWORKS_API_UNAVAILABLE", f"Cannot reach eWorks API: {url}", 502) from exc

    if response.status_code >= 500:
        raise AppError(
            "EWORKS_API_UNAVAILABLE",
            f"eWorks API returned {response.status_code} from {url}",
            502,
        )
    if response.status_code >= 400:
        raise AppError(
            "EWORKS_API_ERROR",
            f"eWorks API returned {response.status_code} from {url}",
            502,
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise AppError("EWORKS_API_UNAVAILABLE", "eWorks API returned invalid JSON", 502) from exc

    try:
        parsed = EworksSyncApiResponse.model_validate(payload)
    except Exception as exc:
        raise AppError("EWORKS_API_UNAVAILABLE", "eWorks API response has unexpected structure", 502) from exc

    meta = parsed.collection.meta
    return _PageResult(
        records=parsed.collection.data,
        current_page=meta.current_page or page,
        last_page=max(meta.last_page or 1, 1),
    )


def _fetch_all(
    *,
    resource_path: str,
    extra_params: dict[str, Any] | None = None,
    page_limit: int | None = None,
) -> list[dict[str, Any]]:
    """Fetch all pages from an eWorks paginated endpoint."""
    if not settings.eworks_api_enabled:
        raise AppError("EWORKS_API_DISABLED", "eWorks API is disabled (EWORKS_API_ENABLED=false)", 503)

    base_url, api_key = _require_eworks_credentials()
    url = f"{base_url}/{resource_path.lstrip('/')}"
    ceiling = min(page_limit or _MAX_PAGES, _MAX_PAGES)

    all_records: list[dict[str, Any]] = []
    page = 1
    last_page = 1
    pages_fetched = 0

    with httpx.Client(timeout=settings.eworks_api_timeout_seconds) as client:
        while page <= last_page and pages_fetched < ceiling:
            result = _fetch_page(
                client,
                url=url,
                api_key=api_key,
                page=page,
                extra_params=extra_params,
            )
            last_page = result.last_page
            all_records.extend(result.records)
            pages_fetched += 1

            logger.info(
                "eWorks %s: fetched page %s/%s (%s records, total so far: %s)",
                resource_path,
                result.current_page,
                last_page,
                len(result.records),
                len(all_records),
            )

            if not result.records or result.current_page >= last_page:
                break

            page = result.current_page + 1

    if pages_fetched >= ceiling:
        logger.warning(
            "eWorks %s: hit page_limit=%s safety ceiling; may not have fetched all records",
            resource_path,
            ceiling,
        )

    return all_records


def fetch_all_quotes(
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    status: str | None = None,
    page_limit: int | None = None,
) -> list[dict[str, Any]]:
    """Fetch all Quote records from eWorks (read-only)."""
    extra: dict[str, Any] = {}
    if date_from:
        extra["date_from"] = date_from
    if date_to:
        extra["date_to"] = date_to
    if status:
        extra["status"] = status
    return _fetch_all(resource_path="Quote", extra_params=extra or None, page_limit=page_limit)


def fetch_all_jobs(
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    status: str | None = None,
    page_limit: int | None = None,
) -> list[dict[str, Any]]:
    """Fetch all Job records from eWorks (read-only)."""
    extra: dict[str, Any] = {}
    if date_from:
        extra["date_from"] = date_from
    if date_to:
        extra["date_to"] = date_to
    if status:
        extra["status"] = status
    return _fetch_all(resource_path="Job", extra_params=extra or None, page_limit=page_limit)
