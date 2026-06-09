"""eWorks API client: fetch Quote and Job records with safe pagination.

Read-only from eWorks — this module never writes to eWorks.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import AppError
from app.schemas.eworks_sync_api import EworksSyncApiResponse

logger = logging.getLogger(__name__)

_DEFAULT_PER_PAGE = 100
_MAX_PAGES = 500  # legacy fallback; overridden by EWORKS_API_MAX_PAGES (0 = unlimited)


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


def _api_request_delay() -> None:
    delay = float(settings.eworks_api_request_delay_seconds or 0)
    if delay > 0:
        time.sleep(delay)


def _get_with_retry(
    client: httpx.Client,
    *,
    url: str,
    headers: dict[str, str],
    params: dict[str, Any] | None = None,
) -> tuple[httpx.Response, int]:
    """GET with exponential backoff on HTTP 429. Returns (response, rate_limit_hits)."""
    max_retries = max(0, int(settings.eworks_api_max_retries))
    backoff = float(settings.eworks_api_retry_backoff_seconds or 0)
    rate_limited_hits = 0

    for attempt in range(max_retries + 1):
        try:
            response = client.get(url, headers=headers, params=params)
        except httpx.TimeoutException as exc:
            raise AppError("EWORKS_API_UNAVAILABLE", f"eWorks API timed out: {url}", 502) from exc
        except httpx.HTTPError as exc:
            raise AppError("EWORKS_API_UNAVAILABLE", f"Cannot reach eWorks API: {url}", 502) from exc

        if response.status_code != 429:
            _api_request_delay()
            return response, rate_limited_hits

        rate_limited_hits += 1
        if attempt >= max_retries:
            raise AppError(
                "EWORKS_RATE_LIMITED",
                f"eWorks API rate limited after {max_retries} retries: {url}",
                429,
            )

        wait = backoff * (2**attempt)
        logger.warning(
            "eWorks API 429 for %s; retry %s/%s in %.1fs",
            url,
            attempt + 1,
            max_retries,
            wait,
        )
        time.sleep(wait)

    raise AppError("EWORKS_RATE_LIMITED", f"eWorks API rate limited: {url}", 429)


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

    response, _rate_limited = _get_with_retry(client, url=url, headers=headers, params=params)

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


def _effective_max_pages() -> int:
    """Return the page ceiling: EWORKS_API_MAX_PAGES if set, else _MAX_PAGES fallback. 0 means unlimited."""
    configured = int(settings.eworks_api_max_pages or 0)
    if configured > 0:
        return configured
    if configured == 0:
        return 0
    return _MAX_PAGES


def _fetch_all(
    *,
    resource_path: str,
    extra_params: dict[str, Any] | None = None,
    page_limit: int | None = None,
    on_page_fetched: Any | None = None,
) -> list[dict[str, Any]]:
    """Fetch all pages from an eWorks paginated endpoint."""
    if not settings.eworks_api_enabled:
        raise AppError("EWORKS_API_DISABLED", "eWorks API is disabled (EWORKS_API_ENABLED=false)", 503)

    base_url, api_key = _require_eworks_credentials()
    url = f"{base_url}/{resource_path.lstrip('/')}"
    effective_max = _effective_max_pages()
    if page_limit is not None:
        ceiling = page_limit if effective_max == 0 else min(page_limit, effective_max)
    elif effective_max > 0:
        ceiling = effective_max
    else:
        ceiling = None  # truly unlimited

    all_records: list[dict[str, Any]] = []
    page = 1
    last_page = 1
    pages_fetched = 0

    with httpx.Client(timeout=settings.eworks_api_timeout_seconds) as client:
        while page <= last_page and (ceiling is None or pages_fetched < ceiling):
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

            if on_page_fetched is not None:
                on_page_fetched(result.current_page, last_page, len(all_records))

            if not result.records or result.current_page >= last_page:
                break

            page = result.current_page + 1

    if ceiling is not None and pages_fetched >= ceiling:
        logger.warning(
            "eWorks %s: hit page_limit=%s ceiling; may not have fetched all records",
            resource_path,
            ceiling,
        )

    return all_records


@dataclass
class QuotePageResult:
    """Single-page fetch result for incremental sync loops."""
    records: list[dict[str, Any]]
    current_page: int
    last_page: int


def fetch_quote_page(
    page: int = 1,
    *,
    per_page: int = _DEFAULT_PER_PAGE,
    extra_params: dict[str, Any] | None = None,
) -> QuotePageResult:
    """Fetch a single page of Quotes from eWorks. Used by incremental sync."""
    if not settings.eworks_api_enabled:
        raise AppError("EWORKS_API_DISABLED", "eWorks API is disabled (EWORKS_API_ENABLED=false)", 503)

    base_url, api_key = _require_eworks_credentials()
    url = f"{base_url}/Quote"
    with httpx.Client(timeout=settings.eworks_api_timeout_seconds) as client:
        result = _fetch_page(
            client, url=url, api_key=api_key, page=page,
            per_page=per_page, extra_params=extra_params,
        )
    return QuotePageResult(
        records=result.records,
        current_page=result.current_page,
        last_page=result.last_page,
    )


def fetch_all_quotes(
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    status: str | None = None,
    page_limit: int | None = None,
    on_page_fetched: Any | None = None,
) -> list[dict[str, Any]]:
    """Fetch all Quote records from eWorks (read-only)."""
    extra: dict[str, Any] = {}
    if date_from:
        extra["date_from"] = date_from
    if date_to:
        extra["date_to"] = date_to
    if status:
        extra["status"] = status
    return _fetch_all(
        resource_path="Quote",
        extra_params=extra or None,
        page_limit=page_limit,
        on_page_fetched=on_page_fetched,
    )


def fetch_all_jobs(
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    status: str | None = None,
    page_limit: int | None = None,
    on_page_fetched: Any | None = None,
) -> list[dict[str, Any]]:
    """Fetch all Job records from eWorks (read-only)."""
    extra: dict[str, Any] = {}
    if date_from:
        extra["date_from"] = date_from
    if date_to:
        extra["date_to"] = date_to
    if status:
        extra["status"] = status
    return _fetch_all(
        resource_path="Job",
        extra_params=extra or None,
        page_limit=page_limit,
        on_page_fetched=on_page_fetched,
    )


def fetch_quote_attachments(
    eworks_quote_id: int,
) -> list[dict[str, Any]]:
    """Fetch attachments from eWorks Quote attachments endpoint (read-only, paginated)."""
    return fetch_attachments(parent_type="QUOTE", parent_id=eworks_quote_id)


def fetch_job_attachments(
    eworks_job_id: int,
) -> list[dict[str, Any]]:
    """Fetch attachments from eWorks Job attachments endpoint (read-only, paginated)."""
    return fetch_attachments(parent_type="JOB", parent_id=eworks_job_id)


def fetch_attachments(
    *,
    parent_type: str,
    parent_id: int,
) -> list[dict[str, Any]]:
    """Fetch attachment records for a quote or job parent (read-only, paginated)."""
    if not settings.eworks_api_enabled:
        raise AppError("EWORKS_API_DISABLED", "eWorks API is disabled (EWORKS_API_ENABLED=false)", 503)

    normalized = parent_type.strip().upper()
    if normalized == "QUOTE":
        resource_path = f"Quote/{parent_id}/Attachments"
    elif normalized == "JOB":
        resource_path = f"Job/{parent_id}/Attachments"
    else:
        raise AppError("EWORKS_API_ERROR", f"Unsupported attachment parent_type: {parent_type}", 400)

    base_url, api_key = _require_eworks_credentials()
    url = f"{base_url}/{resource_path}"
    all_records: list[dict[str, Any]] = []
    page = 1
    last_page = 1

    with httpx.Client(timeout=settings.eworks_api_timeout_seconds) as client:
        while page <= last_page:
            result = _fetch_page(client, url=url, api_key=api_key, page=page, per_page=100)
            last_page = result.last_page
            all_records.extend(result.records)
            if not result.records or result.current_page >= last_page:
                break
            page = result.current_page + 1

    return all_records


def _unwrap_single_record(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise AppError("EWORKS_API_UNAVAILABLE", "eWorks Job detail response has unexpected structure", 502)

    collection = payload.get("collection")
    if isinstance(collection, dict):
        data = collection.get("data")
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return data[0]
        if isinstance(data, dict):
            return data

    data = payload.get("data")
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0]
    if isinstance(data, dict):
        return data

    if payload.get("id") is not None or payload.get("job_ref") is not None or payload.get("quote_ref") is not None:
        return payload

    raise AppError("EWORKS_API_UNAVAILABLE", "eWorks detail response has unexpected structure", 502)


def fetch_quote_detail(eworks_quote_id: int) -> tuple[dict[str, Any], int]:
    """Fetch a single Quote detail record from eWorks (read-only). Returns (payload, rate_limit_hits)."""
    if not settings.eworks_api_enabled:
        raise AppError("EWORKS_API_DISABLED", "eWorks API is disabled (EWORKS_API_ENABLED=false)", 503)

    base_url, api_key = _require_eworks_credentials()
    url = f"{base_url}/Quote/{eworks_quote_id}"
    headers = {"api_key": api_key, "Accept": "application/json"}

    with httpx.Client(timeout=settings.eworks_api_timeout_seconds) as client:
        response, rate_limited = _get_with_retry(client, url=url, headers=headers)

    if response.status_code >= 500:
        raise AppError(
            "EWORKS_API_UNAVAILABLE",
            f"eWorks Quote detail API returned {response.status_code} from {url}",
            502,
        )
    if response.status_code >= 400:
        raise AppError(
            "EWORKS_API_ERROR",
            f"eWorks Quote detail API returned {response.status_code} from {url}",
            502,
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise AppError("EWORKS_API_UNAVAILABLE", "eWorks Quote detail API returned invalid JSON", 502) from exc

    return _unwrap_single_record(payload), rate_limited


def fetch_job_detail(eworks_job_id: int) -> tuple[dict[str, Any], int]:
    """Fetch a single Job detail record from eWorks (read-only). Returns (payload, rate_limit_hits)."""
    if not settings.eworks_api_enabled:
        raise AppError("EWORKS_API_DISABLED", "eWorks API is disabled (EWORKS_API_ENABLED=false)", 503)

    base_url, api_key = _require_eworks_credentials()
    url = f"{base_url}/Job/{eworks_job_id}"
    headers = {"api_key": api_key, "Accept": "application/json"}

    with httpx.Client(timeout=settings.eworks_api_timeout_seconds) as client:
        response, rate_limited = _get_with_retry(client, url=url, headers=headers)

    if response.status_code >= 500:
        raise AppError(
            "EWORKS_API_UNAVAILABLE",
            f"eWorks Job detail API returned {response.status_code} from {url}",
            502,
        )
    if response.status_code >= 400:
        raise AppError(
            "EWORKS_API_ERROR",
            f"eWorks Job detail API returned {response.status_code} from {url}",
            502,
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise AppError("EWORKS_API_UNAVAILABLE", "eWorks Job detail API returned invalid JSON", 502) from exc

    return _unwrap_single_record(payload), rate_limited
