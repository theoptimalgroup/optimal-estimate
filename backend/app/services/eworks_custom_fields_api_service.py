"""eWorks CustomFields API client (read-only)."""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings
from app.core.exceptions import AppError
from app.services.eworks_quotes_jobs_api_service import _fetch_all

logger = logging.getLogger(__name__)


def custom_fields_resource_path() -> str:
    return (settings.eworks_custom_fields_resource_path or "CustomFields").strip().strip("/") or "CustomFields"


def fetch_all_custom_field_definitions(
    *,
    page_limit: int | None = None,
) -> list[dict[str, Any]]:
    """Fetch all CustomFields definition records from eWorks (read-only)."""
    if not settings.eworks_api_enabled:
        raise AppError("EWORKS_API_DISABLED", "eWorks API is disabled (EWORKS_API_ENABLED=false)", 503)

    records = _fetch_all(
        resource_path=custom_fields_resource_path(),
        page_limit=page_limit,
    )
    logger.info("eWorks CustomFields: fetched %s definition records", len(records))
    return records
