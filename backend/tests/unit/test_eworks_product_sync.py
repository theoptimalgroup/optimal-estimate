"""Unit tests for eWorks Item API parsing and product sync."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.eworks_item_api import (
    EworksItemApiResponse,
    EworksItemRecord,
    is_products_item,
    map_item_to_product_fields,
    parse_bool,
    parse_decimal,
)
from app.services.eworks_product_sync_service import sync_products_from_eworks

SAMPLE_ITEM = {
    "id": 1403,
    "item_name": "Plant Room",
    "item_code": "PR-0011",
    "item_description": "Inspect plant room equipment",
    "cost_price": ".0000",
    "price": "100.00",
    "item_margin": "0.0",
    "tax_rate_id": "3",
    "track_stock_level": "0",
    "current_stock_level": "0",
    "item_type": {"id": 1, "item_type": "Products"},
    "item_category": {"id": 1, "item_category": "General"},
    "created_on": "2024-11-28T16:10:25.000000Z",
    "last_updated_on": "2024-11-28T16:10:25.000000Z",
}

SERVICE_ITEM = {
    **SAMPLE_ITEM,
    "id": 999,
    "item_name": "Labour",
    "item_type": {"id": 2, "item_type": "Services"},
}


def test_parse_decimal_and_bool():
    assert parse_decimal(".0000") == Decimal("0")
    assert parse_decimal("100.00") == Decimal("100.00")
    assert parse_decimal(None) == Decimal("0")
    assert parse_bool("0") is False
    assert parse_bool("1") is True


def test_is_products_item_filters_non_products():
    assert is_products_item(EworksItemRecord.model_validate(SAMPLE_ITEM)) is True
    assert is_products_item(EworksItemRecord.model_validate(SERVICE_ITEM)) is False


def test_map_item_to_product_fields():
    record = EworksItemRecord.model_validate({**SAMPLE_ITEM, "item_description": ""})
    fields = map_item_to_product_fields(record)
    assert fields["eworks_item_id"] == 1403
    assert fields["product_name"] == "Plant Room"
    assert fields["product_code"] == "PR-0011"
    assert fields["scope_of_work"] is None
    assert fields["cost_price"] == Decimal("0")
    assert fields["selling_price"] == Decimal("100.00")
    assert fields["margin"] == Decimal("0")
    assert fields["track_stock_level"] is False
    assert fields["category"] == "General"
    assert fields["type_"] == "Products"


@patch("app.services.eworks_product_sync_service.fetch_all_eworks_items")
def test_sync_products_upserts_without_duplicates(mock_fetch):
    mock_fetch.return_value = [
        EworksItemRecord.model_validate(SAMPLE_ITEM),
        EworksItemRecord.model_validate(SERVICE_ITEM),
    ]

    db = MagicMock()
    existing = MagicMock()
    db.query.return_value.filter.return_value.one_or_none.side_effect = [None, existing, existing]

    summary = sync_products_from_eworks(db)

    assert summary.total_fetched == 2
    assert summary.skipped == 1
    assert summary.inserted == 1
    assert summary.updated == 0
    db.add.assert_called_once()
    db.flush.assert_called_once()
