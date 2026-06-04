from __future__ import annotations

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
    return {
        "eworks_item_id": record.id,
        "product_name": (record.item_name or "").strip() or f"Item {record.id}",
        "product_code": (record.item_code or "").strip() or None,
        "scope_of_work": (record.item_description or "").strip() or None,
        "cost_price": parse_decimal(record.cost_price),
        "selling_price": parse_decimal(record.price),
        "margin": parse_decimal(record.item_margin),
        "tax_rate_id": str(record.tax_rate_id).strip() if record.tax_rate_id is not None else None,
        "track_stock_level": parse_bool(record.track_stock_level),
        "current_stock_level": parse_stock_level(record.current_stock_level),
        "category": (category.item_category if category else None) or None,
        "category_id": category.id if category else None,
        "type_": (item_type.item_type if item_type else None) or None,
        "type_id": item_type.id if item_type else None,
        "eworks_created_on": parse_eworks_datetime(record.created_on),
        "eworks_last_updated_on": parse_eworks_datetime(record.last_updated_on),
        "raw_payload": record.model_dump(mode="json"),
    }
