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
    prepare_product_sync_fields,
    sanitize_sync_error,
)
from app.schemas.product import ProductSyncItemError, ProductSyncSummary

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

    logger.info("eWorks product sync fetched %s total records", len(all_records))
    return all_records


def _item_display_name(record) -> str:
    name = (getattr(record, "item_name", None) or "").strip()
    if name:
        return name[:200]
    item_id = getattr(record, "id", None)
    return str(item_id) if item_id is not None else "unknown"


def _log_failed_item(record, error: str) -> None:
    logger.warning(
        "eWorks product sync failed item id=%s name=%s reason=%s",
        getattr(record, "id", None),
        _item_display_name(record),
        error,
    )


def _append_sync_error(
    errors: list[ProductSyncItemError],
    record,
    error: str,
) -> None:
    safe_error = sanitize_sync_error(error)
    errors.append(
        ProductSyncItemError(
            eworks_item_id=str(getattr(record, "id", "") or ""),
            item_name=_item_display_name(record),
            error=safe_error,
        )
    )
    _log_failed_item(record, safe_error)


def sync_products_from_eworks(db: Session) -> ProductSyncSummary:
    records = fetch_all_eworks_items()
    created = 0
    updated = 0
    skipped = 0
    failed = 0
    errors: list[ProductSyncItemError] = []
    seen_item_ids: set[int] = set()
    product_candidates = 0

    for record in records:
        if not is_products_item(record):
            skipped += 1
            continue

        product_candidates += 1
        item_id = record.id

        if item_id in seen_item_ids:
            failed += 1
            _append_sync_error(errors, record, "duplicate eworks_item_id in sync batch")
            continue
        seen_item_ids.add(item_id)

        fields, prep_error = prepare_product_sync_fields(record)
        if prep_error or fields is None:
            failed += 1
            _append_sync_error(errors, record, prep_error or "invalid item data")
            continue

        try:
            with db.begin_nested():
                existing = db.query(Product).filter(Product.eworks_item_id == item_id).one_or_none()
                if existing is None:
                    db.add(Product(**fields))
                    created += 1
                else:
                    for key, value in fields.items():
                        if key == "eworks_item_id":
                            continue
                        setattr(existing, key, value)
                    updated += 1
                db.flush()
        except Exception as exc:
            failed += 1
            _append_sync_error(errors, record, str(exc))

    summary = ProductSyncSummary(
        fetched=len(records),
        created=created,
        updated=updated,
        skipped=skipped,
        failed=failed,
        errors=errors,
    )
    logger.info(
        "eWorks product sync completed: fetched=%s candidates=%s created=%s updated=%s skipped=%s failed=%s",
        summary.fetched,
        product_candidates,
        summary.created,
        summary.updated,
        summary.skipped,
        summary.failed,
    )
    return summary
