"""Unit tests for products list API."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


def _product(**overrides):
    defaults = {
        "id": 1,
        "eworks_item_id": 1403,
        "product_name": "Plant Room",
        "product_code": "PR-0011",
        "scope_of_work": "Inspect plant room",
        "cost_price": Decimal("0"),
        "selling_price": Decimal("100"),
        "margin": Decimal("0"),
        "tax_rate_id": "3",
        "track_stock_level": False,
        "current_stock_level": Decimal("0"),
        "category": "General",
        "category_id": 1,
        "type_": "Products",
        "type_id": 1,
        "description": None,
        "is_active": True,
        "created_at": None,
        "updated_at": None,
        "eworks_created_on": None,
        "eworks_last_updated_on": None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


PRODUCTS = [
    _product(),
    _product(
        id=2,
        eworks_item_id=1404,
        product_name="Window Repair",
        product_code="WR-001",
        scope_of_work="",
    ),
]


@pytest.fixture()
def products_client():
    with TestClient(app) as client:
        yield client


@patch("app.api.v1.products.list_products")
def test_list_products_returns_expected_keys(mock_list, products_client):
    mock_list.return_value = (PRODUCTS, {"total": 2, "page": 1, "per_page": 25, "last_page": 1})
    response = products_client.get("/api/v1/products")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["meta"]["total"] == 2
    item = body["data"][0]
    for key in (
        "id",
        "eworks_item_id",
        "product_name",
        "product_code",
        "scope_of_work",
        "selling_price",
        "category",
        "type",
    ):
        assert key in item


@patch("app.api.v1.products.list_products")
def test_list_products_search(mock_list, products_client):
    mock_list.return_value = ([PRODUCTS[0]], {"total": 1, "page": 1, "per_page": 25, "last_page": 1})
    response = products_client.get("/api/v1/products?search=Plant")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["product_name"] == "Plant Room"
    mock_list.assert_called_once()


@patch("app.api.v1.products.list_products")
def test_list_products_has_scope_filter(mock_list, products_client):
    mock_list.return_value = ([PRODUCTS[0]], {"total": 1, "page": 1, "per_page": 25, "last_page": 1})
    response = products_client.get("/api/v1/products?has_scope_of_work=true")
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1

    mock_list.return_value = ([PRODUCTS[1]], {"total": 1, "page": 1, "per_page": 25, "last_page": 1})
    response = products_client.get("/api/v1/products?has_scope_of_work=false")
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1


@patch("app.api.v1.products.get_product")
def test_get_product_by_id(mock_get, products_client):
    mock_get.return_value = PRODUCTS[0]
    response = products_client.get("/api/v1/products/1")
    assert response.status_code == 200
    assert response.json()["data"]["product_name"] == "Plant Room"

    mock_get.return_value = None
    missing = products_client.get("/api/v1/products/999")
    assert missing.status_code == 404
