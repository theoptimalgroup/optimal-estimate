"""eWorks Customer API client for bulk read-only sync.

Uses GET {EWORKS_BASE_URL}/{EWORKS_CUSTOMERS_RESOURCE_PATH} with pagination.
Default resource path is ``Customer`` (same as on-demand lookup in eworks_api_service).
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import AppError
from app.schemas.eworks_sync_api import EworksSyncApiResponse
from app.services.eworks_quotes_jobs_api_service import _DEFAULT_PER_PAGE, _MAX_PAGES, _fetch_page, _require_eworks_credentials

logger = logging.getLogger(__name__)


def customers_resource_path() -> str:
    return (settings.eworks_customers_resource_path or "Customer").strip().strip("/") or "Customer"


def fetch_customers(
    *,
    page: int = 1,
    per_page: int = _DEFAULT_PER_PAGE,
    filters: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], int, int]:
    """Fetch one page of Customer records. Returns (records, current_page, last_page)."""
    base_url, api_key = _require_eworks_credentials()
    resource = customers_resource_path()
    url = f"{base_url}/{resource}"
    extra = dict(filters or {})

    with httpx.Client(timeout=settings.eworks_api_timeout_seconds) as client:
        result = _fetch_page(
            client,
            url=url,
            api_key=api_key,
            page=page,
            per_page=per_page,
            extra_params=extra,
        )
    return result.records, result.current_page, result.last_page


def fetch_all_customers(
    *,
    filters: dict[str, Any] | None = None,
    page_limit: int | None = None,
    on_page_fetched: Any | None = None,
) -> list[dict[str, Any]]:
    """Fetch all Customer pages from eWorks (read-only)."""
    base_url, api_key = _require_eworks_credentials()
    resource = customers_resource_path()
    url = f"{base_url}/{resource}"
    extra = dict(filters or {})
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
                per_page=_DEFAULT_PER_PAGE,
                extra_params=extra,
            )
            last_page = result.last_page
            all_records.extend(result.records)
            pages_fetched += 1

            logger.info(
                "eWorks %s: fetched page %s/%s (%s records, total so far: %s)",
                resource,
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

    if pages_fetched >= ceiling:
        logger.warning(
            "eWorks %s: hit page_limit=%s safety ceiling; may not have fetched all records",
            resource,
            ceiling,
        )

    return all_records
