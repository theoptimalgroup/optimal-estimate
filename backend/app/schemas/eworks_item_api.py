from __future__ import annotations

import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import BaseModel, Field


class EworksItemTypeRef(BaseModel):
    id: int | None = None
    item_type: str | None = None


class EworksItemCategoryRef(BaseModel):
    id: int | None = None
    item_category: str | None = None


class EworksItemRecord(BaseModel):
    id: int
    item_name: str = ""
    item_code: str | None = None
    item_description: str | None = None
    cost_price: str | float | int | None = None
    price: str | float | int | None = None
    item_margin: str | float | int | None = None
    tax_rate_id: str | int | None = None
    track_stock_level: str | int | bool | None = None
    current_stock_level: str | float | int | None = None
    created_on: str | None = None
    last_updated_on: str | None = None
    item_type: EworksItemTypeRef | None = None
    item_category: EworksItemCategoryRef | None = None

    model_config = {"extra": "allow"}


class EworksItemCollectionMeta(BaseModel):
    total: int = 0
    last_page: int = 1
    current_page: int = 1
    from_: int | None = Field(default=None, alias="from")
    to: int | None = None
    per_page: int = 25
    sort_key: str | None = None
    sort_order: str | None = None

    model_config = {"populate_by_name": True}


class EworksItemCollection(BaseModel):
    meta: EworksItemCollectionMeta = Field(default_factory=EworksItemCollectionMeta)
    data: list[EworksItemRecord] = Field(default_factory=list)


class EworksItemApiResponse(BaseModel):
    status: int
    collection: EworksItemCollection = Field(default_factory=EworksItemCollection)


PRODUCT_FIELD_MAX_LENGTHS: dict[str, int] = {
    "product_name": 500,
    "product_code": 100,
    "category": 255,
    "type_": 100,
    "tax_rate_id": 50,
}

_SENSITIVE_ERROR_PATTERN = re.compile(
    r"(api_key|secret|password|token|authorization|dashboard_password)",
    re.IGNORECASE,
)


def sanitize_sync_error(message: str | None) -> str:
    text = (message or "").strip()
    if not text:
        return "invalid item data"
    if _SENSITIVE_ERROR_PATTERN.search(text):
        return "invalid item data"
    return text[:200]


def truncate_text(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) <= max_length:
        return text
    return text[:max_length]


def build_safe_raw_payload(record: EworksItemRecord) -> dict | None:
    try:
        payload = record.model_dump(mode="json")
        return json.loads(json.dumps(payload, default=str))
    except Exception:
        return {
            "id": record.id,
            "item_name": truncate_text(record.item_name, PRODUCT_FIELD_MAX_LENGTHS["product_name"]),
            "item_code": truncate_text(record.item_code, PRODUCT_FIELD_MAX_LENGTHS["product_code"])
            if record.item_code
            else None,
        }


def normalize_product_field_lengths(fields: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(fields)
    for key, max_length in PRODUCT_FIELD_MAX_LENGTHS.items():
        if key not in normalized or normalized[key] is None:
            continue
        normalized[key] = truncate_text(str(normalized[key]), max_length)
    return normalized


def parse_decimal(value: str | float | int | None) -> Decimal:
    if value is None:
        return Decimal("0")
    text = str(value).strip()
    if not text:
        return Decimal("0")
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return Decimal("0")


def parse_bool(value: str | int | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y"}


def parse_stock_level(value: str | float | int | None) -> Decimal:
    return parse_decimal(value)


def parse_eworks_datetime(value: str | None) -> datetime | None:
    if not value or not str(value).strip():
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def is_products_item(record: EworksItemRecord) -> bool:
    if not record.item_type or not record.item_type.item_type:
        return False
    return record.item_type.item_type.strip().lower() == "products"


def map_item_to_product_fields(record: EworksItemRecord) -> dict[str, Any]:
    category = record.item_category
    item_type = record.item_type
    category_name = None
    if category and category.item_category:
        category_name = truncate_text(str(category.item_category), PRODUCT_FIELD_MAX_LENGTHS["category"])

    type_name = None
    if item_type and item_type.item_type:
        type_name = truncate_text(str(item_type.item_type), PRODUCT_FIELD_MAX_LENGTHS["type_"])

    tax_rate_id = None
    if record.tax_rate_id is not None:
        tax_rate_id = truncate_text(str(record.tax_rate_id), PRODUCT_FIELD_MAX_LENGTHS["tax_rate_id"])

    product_name = truncate_text((record.item_name or "").strip(), PRODUCT_FIELD_MAX_LENGTHS["product_name"])
    product_code_raw = (record.item_code or "").strip()
    product_code = truncate_text(product_code_raw, PRODUCT_FIELD_MAX_LENGTHS["product_code"]) if product_code_raw else None

    return {
        "eworks_item_id": record.id,
        "product_name": product_name,
        "product_code": product_code,
        "scope_of_work": (record.item_description or "").strip() or None,
        "cost_price": parse_decimal(record.cost_price),
        "selling_price": parse_decimal(record.price),
        "margin": parse_decimal(record.item_margin),
        "tax_rate_id": tax_rate_id,
        "track_stock_level": parse_bool(record.track_stock_level),
        "current_stock_level": parse_stock_level(record.current_stock_level),
        "category": category_name,
        "category_id": category.id if category else None,
        "type_": type_name,
        "type_id": item_type.id if item_type else None,
        "eworks_created_on": parse_eworks_datetime(record.created_on),
        "eworks_last_updated_on": parse_eworks_datetime(record.last_updated_on),
        "raw_payload": build_safe_raw_payload(record),
    }


def prepare_product_sync_fields(record: EworksItemRecord) -> tuple[dict[str, Any] | None, str | None]:
    """Validate and normalize one eWorks item for local product upsert."""
    if not record.id:
        return None, "missing eworks item id"

    if not (record.item_name or "").strip():
        return None, "missing item_name"

    try:
        fields = map_item_to_product_fields(record)
        if not fields.get("product_name"):
            return None, "missing item_name"
        fields = normalize_product_field_lengths(fields)
        fields["raw_payload"] = build_safe_raw_payload(record)
        return fields, None
    except Exception as exc:
        return None, sanitize_sync_error(str(exc))
