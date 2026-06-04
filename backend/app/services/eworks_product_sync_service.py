from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppError
from app.models.product import Product
from app.schemas.eworks_item_api import (
    EworksItemApiResponse,
    is_products_item,
    map_item_to_product_fields,
)
from app.schemas.product import ProductSyncSummary

logger = logging.getLogger(__name__)


@dataclass
class _FetchPageResult:
    records: list
    current_page: int
    last_page: int


def _require_eworks_credentials() -> tuple[str, str]:
    base_url = (settings.eworks_base_url or "").rstrip("/")
    api_key = settings.eworks_api_key
    if not base_url:
        raise AppError("EWORKS_API_MISCONFIGURED", "EWORKS_BASE_URL is missing", 503)
    if not api_key:
        raise AppError("EWORKS_API_MISCONFIGURED", "EWORKS_API_KEY is missing", 503)
    return base_url, api_key


def _fetch_item_page(client: httpx.Client, *, base_url: str, api_key: str, page: int) -> _FetchPageResult:
    url = f"{base_url}/Item"
    headers = {"api_key": api_key, "Accept": "application/json"}
    params = {"page": page}

    try:
        response = client.get(url, headers=headers, params=params)
    except httpx.TimeoutException as exc:
        raise AppError("EWORKS_API_UNAVAILABLE", "eWorks Item API timed out", 502) from exc
    except httpx.HTTPError as exc:
        raise AppError("EWORKS_API_UNAVAILABLE", "Failed to fetch products from eWorks", 502) from exc

    if response.status_code >= 500:
        raise AppError(
            "EWORKS_API_UNAVAILABLE",
            f"eWorks Item API returned {response.status_code}",
            502,
        )
    if response.status_code >= 400:
        raise AppError("EWORKS_API_UNAVAILABLE", "Failed to fetch products from eWorks", 502)

    try:
        payload = response.json()
    except ValueError as exc:
        raise AppError("EWORKS_API_UNAVAILABLE", "eWorks Item API returned invalid JSON", 502) from exc

    parsed = EworksItemApiResponse.model_validate(payload)
    if parsed.status != 1:
        raise AppError("EWORKS_API_UNAVAILABLE", "Failed to fetch products from eWorks", 502)

    meta = parsed.collection.meta
    return _FetchPageResult(
        records=parsed.collection.data,
        current_page=meta.current_page or page,
        last_page=meta.last_page or 1,
    )


def fetch_all_eworks_items() -> list:
    base_url, api_key = _require_eworks_credentials()
    logger.info("eWorks product sync started")
    all_records: list = []
    page = 1
    last_page = 1

    with httpx.Client(timeout=settings.eworks_api_timeout_seconds) as client:
        while page <= last_page:
            result = _fetch_item_page(client, base_url=base_url, api_key=api_key, page=page)
            last_page = max(result.last_page, 1)
            all_records.extend(result.records)
            logger.info(
                "eWorks product sync fetched page %s/%s (%s records on page)",
                result.current_page,
                last_page,
                len(result.records),
            )
            if result.current_page >= last_page:
                break
            page = result.current_page + 1

    return all_records


def sync_products_from_eworks(db: Session) -> ProductSyncSummary:
    records = fetch_all_eworks_items()
    inserted = 0
    updated = 0
    skipped = 0

    for record in records:
        if not is_products_item(record):
            skipped += 1
            continue

        fields = map_item_to_product_fields(record)
        eworks_item_id = fields["eworks_item_id"]
        existing = db.query(Product).filter(Product.eworks_item_id == eworks_item_id).one_or_none()

        if existing is None:
            db.add(Product(**fields))
            inserted += 1
        else:
            for key, value in fields.items():
                if key == "eworks_item_id":
                    continue
                setattr(existing, key, value)
            updated += 1

    db.flush()
    summary = ProductSyncSummary(
        total_fetched=len(records),
        inserted=inserted,
        updated=updated,
        skipped=skipped,
    )
    logger.info(
        "eWorks product sync completed: fetched=%s inserted=%s updated=%s skipped=%s",
        summary.total_fetched,
        summary.inserted,
        summary.updated,
        summary.skipped,
    )
    return summary
