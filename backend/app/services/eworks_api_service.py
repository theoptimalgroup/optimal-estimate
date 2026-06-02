from __future__ import annotations

import logging

import httpx

from app.core.config import settings
from app.core.exceptions import AppError
from app.schemas.eworks_api import (
    EworksCustomerApiResponse,
    EworksCustomerSnapshot,
    build_customer_snapshot,
)

logger = logging.getLogger(__name__)


def fetch_customer_by_name(customer_name: str) -> EworksCustomerSnapshot:
    if not settings.eworks_api_enabled:
        raise AppError("EWORKS_API_DISABLED", "eWorks Customer API is disabled", 503)

    base_url = (settings.eworks_base_url or "").rstrip("/")
    api_key = settings.eworks_api_key
    if not base_url or not api_key:
        raise AppError(
            "EWORKS_API_MISCONFIGURED",
            "eWorks Customer API is enabled but EWORKS_BASE_URL or EWORKS_API_KEY is missing",
            503,
        )

    query_name = customer_name.strip()
    if not query_name:
        raise AppError("EWORKS_CUSTOMER_NOT_FOUND", "Customer name is required", 404)

    url = f"{base_url}/Customer"
    headers = {"api_key": api_key, "Accept": "application/json"}
    params = {"customer_name": query_name}

    try:
        with httpx.Client(timeout=settings.eworks_api_timeout_seconds) as client:
            response = client.get(url, headers=headers, params=params)
    except httpx.TimeoutException as exc:
        raise AppError(
            "EWORKS_API_UNAVAILABLE",
            "eWorks Customer API timed out",
            502,
        ) from exc
    except httpx.HTTPError as exc:
        raise AppError(
            "EWORKS_API_UNAVAILABLE",
            "Could not reach eWorks Customer API",
            502,
        ) from exc

    if response.status_code >= 500:
        raise AppError(
            "EWORKS_API_UNAVAILABLE",
            f"eWorks Customer API returned {response.status_code}",
            502,
        )
    if response.status_code >= 400:
        raise AppError(
            "EWORKS_CUSTOMER_NOT_FOUND",
            f"Customer not found in eWorks: {query_name}",
            404,
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise AppError(
            "EWORKS_API_UNAVAILABLE",
            "eWorks Customer API returned invalid JSON",
            502,
        ) from exc

    parsed = EworksCustomerApiResponse.model_validate(payload)
    if parsed.status != 1 or not parsed.collection.data or parsed.collection.meta.total < 1:
        raise AppError(
            "EWORKS_CUSTOMER_NOT_FOUND",
            f"Customer not found in eWorks: {query_name}",
            404,
        )

    if parsed.collection.meta.total > 1:
        logger.warning(
            "eWorks Customer API returned %s matches for customer_name=%r; using first row",
            parsed.collection.meta.total,
            query_name,
        )

    return build_customer_snapshot(parsed.collection.data[0])
