"""Unit tests for eWorks Item API parsing and resilient product sync."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.product import Product
from app.schemas.eworks_item_api import (
    EworksItemRecord,
    build_safe_raw_payload,
    is_products_item,
    map_item_to_product_fields,
    parse_bool,
    parse_decimal,
    prepare_product_sync_fields,
    sanitize_sync_error,
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


@pytest.fixture()
def product_db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Product.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_parse_decimal_and_bool():
    assert parse_decimal(".0000") == Decimal("0")
    assert parse_decimal("100.00") == Decimal("100.00")
    assert parse_decimal(None) == Decimal("0")
    assert parse_decimal("not-a-number") == Decimal("0")
    assert parse_bool("0") is False
    assert parse_bool("1") is True


def test_is_products_item_filters_non_products():
    assert is_products_item(EworksItemRecord.model_validate(SAMPLE_ITEM)) is True
    assert is_products_item(EworksItemRecord.model_validate(SERVICE_ITEM)) is False
    assert is_products_item(EworksItemRecord.model_validate({**SAMPLE_ITEM, "item_type": None})) is False


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
    assert isinstance(fields["raw_payload"], dict)


def test_map_item_truncates_long_strings():
    long_name = "X" * 600
    record = EworksItemRecord.model_validate({**SAMPLE_ITEM, "item_name": long_name, "item_code": "C" * 150})
    fields = map_item_to_product_fields(record)
    assert len(fields["product_name"]) == 500
    assert len(fields["product_code"]) == 100


def test_prepare_product_sync_fields_rejects_missing_item_name():
    record = EworksItemRecord.model_validate({**SAMPLE_ITEM, "item_name": "   "})
    fields, error = prepare_product_sync_fields(record)
    assert fields is None
    assert error == "missing item_name"


def test_sanitize_sync_error_redacts_secrets():
    assert sanitize_sync_error("api_key=super-secret-value") == "invalid item data"
    assert sanitize_sync_error("value too long for type character varying(100)") != "invalid item data"


def test_build_safe_raw_payload_is_json_serializable():
    record = EworksItemRecord.model_validate(
        {
            **SAMPLE_ITEM,
            "custom_field": datetime(2024, 1, 1, tzinfo=timezone.utc),
        }
    )
    payload = build_safe_raw_payload(record)
    assert payload is not None
    assert payload["id"] == 1403


@patch("app.services.eworks_product_sync_service.fetch_all_eworks_items")
def test_sync_products_upserts_without_duplicates(mock_fetch):
    mock_fetch.return_value = [
        EworksItemRecord.model_validate(SAMPLE_ITEM),
        EworksItemRecord.model_validate(SERVICE_ITEM),
    ]

    db = MagicMock()
    existing = MagicMock()
    db.query.return_value.filter.return_value.one_or_none.side_effect = [None]

    summary = sync_products_from_eworks(db)

    assert summary.fetched == 2
    assert summary.skipped == 1
    assert summary.created == 1
    assert summary.updated == 0
    assert summary.failed == 0
    db.add.assert_called_once()


@patch("app.services.eworks_product_sync_service.fetch_all_eworks_items")
def test_one_bad_product_does_not_fail_whole_sync(mock_fetch, product_db_session):
    bad_item = EworksItemRecord.model_validate({**SAMPLE_ITEM, "id": 1404, "item_name": ""})
    good_item = EworksItemRecord.model_validate({**SAMPLE_ITEM, "id": 1405, "item_name": "Good Product"})
    mock_fetch.return_value = [bad_item, good_item]

    summary = sync_products_from_eworks(product_db_session)
    product_db_session.commit()

    assert summary.created == 1
    assert summary.failed == 1
    assert summary.errors[0].error == "missing item_name"
    assert summary.errors[0].eworks_item_id == "1404"
    products = product_db_session.scalars(select(Product)).all()
    assert len(products) == 1
    assert products[0].product_name == "Good Product"


@patch("app.services.eworks_product_sync_service.fetch_all_eworks_items")
def test_invalid_price_defaults_safely(mock_fetch, product_db_session):
    record = EworksItemRecord.model_validate({**SAMPLE_ITEM, "price": "not-a-price", "cost_price": "bad"})
    mock_fetch.return_value = [record]

    summary = sync_products_from_eworks(product_db_session)
    product_db_session.commit()

    assert summary.created == 1
    assert summary.failed == 0
    product = product_db_session.scalar(select(Product))
    assert product.selling_price == Decimal("0")
    assert product.cost_price == Decimal("0")


@patch("app.services.eworks_product_sync_service.fetch_all_eworks_items")
def test_duplicate_eworks_item_id_in_batch_is_reported(mock_fetch):
    first = EworksItemRecord.model_validate(SAMPLE_ITEM)
    duplicate = EworksItemRecord.model_validate({**SAMPLE_ITEM, "item_name": "Duplicate Name"})
    mock_fetch.return_value = [first, duplicate]

    db = MagicMock()
    db.query.return_value.filter.return_value.one_or_none.return_value = None
    db.begin_nested.return_value.__enter__ = MagicMock(return_value=None)
    db.begin_nested.return_value.__exit__ = MagicMock(return_value=False)

    summary = sync_products_from_eworks(db)

    assert summary.created == 1
    assert summary.failed == 1
    assert summary.errors[0].error == "duplicate eworks_item_id in sync batch"


@patch("app.services.eworks_product_sync_service.fetch_all_eworks_items")
def test_sync_errors_do_not_contain_secrets(mock_fetch):
    record = EworksItemRecord.model_validate({**SAMPLE_ITEM, "item_name": ""})
    mock_fetch.return_value = [record]

    db = MagicMock()
    summary = sync_products_from_eworks(db)

    assert summary.failed == 1
    assert "api_key" not in summary.errors[0].error.lower()
    assert "secret" not in summary.errors[0].error.lower()
