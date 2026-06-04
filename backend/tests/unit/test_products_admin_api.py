"""Unit tests for admin product write API."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.main import app
from app.models.user import User


def _patch_dev_user(mock_settings, *, role: str, enabled: bool = True):
    mock_settings.dev_auth_enabled = enabled
    mock_settings.dev_user_id = "dev-user-1"
    mock_settings.dev_user_email = "staff@optimal.example"
    mock_settings.dev_user_name = "Staff User"
    mock_settings.dev_user_role = role
    mock_settings.dev_user_is_active = True
    mock_settings.dev_auth_auto_create_user = False


def _product(**overrides):
    now = datetime.now(timezone.utc)
    defaults = {
        "id": 1,
        "eworks_item_id": 1001,
        "product_name": "Boiler Service",
        "product_code": "BS-001",
        "scope_of_work": "Inspect and service boiler",
        "description": "Annual boiler service",
        "category": "Plumber",
        "is_active": True,
        "cost_price": Decimal("0"),
        "selling_price": Decimal("150"),
        "margin": Decimal("0"),
        "tax_rate_id": None,
        "track_stock_level": False,
        "current_stock_level": Decimal("0"),
        "category_id": None,
        "type_": "Products",
        "type_id": None,
        "eworks_created_on": None,
        "eworks_last_updated_on": None,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


PRODUCTS = [
    _product(),
    _product(id=2, eworks_item_id=1002, product_name="Legacy Item", is_active=False, scope_of_work=""),
]


@pytest.fixture()
def products_admin_client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    User.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    session.close()


@patch("app.api.v1.products.list_products")
@patch("app.auth.dependencies.settings")
def test_admin_can_list_products(mock_settings, mock_list, products_admin_client):
    _patch_dev_user(mock_settings, role="admin")
    mock_list.return_value = (PRODUCTS, {"total": 2, "page": 1, "per_page": 25, "last_page": 1})
    response = products_admin_client.get("/api/v1/products")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["meta"]["total"] == 2
    assert body["data"][0]["is_active"] is True


@patch("app.api.v1.products.list_products")
@patch("app.auth.dependencies.settings")
def test_admin_can_filter_active_products(mock_settings, mock_list, products_admin_client):
    _patch_dev_user(mock_settings, role="admin")
    mock_list.return_value = ([PRODUCTS[0]], {"total": 1, "page": 1, "per_page": 25, "last_page": 1})
    response = products_admin_client.get("/api/v1/products?active=true")
    assert response.status_code == 200
    mock_list.assert_called_once()
    assert mock_list.call_args.kwargs["active"] is True


@patch("app.api.v1.products.list_products")
@patch("app.auth.dependencies.settings")
def test_admin_can_filter_by_category_search(mock_settings, mock_list, products_admin_client):
    _patch_dev_user(mock_settings, role="admin")
    mock_list.return_value = ([PRODUCTS[0]], {"total": 1, "page": 1, "per_page": 25, "last_page": 1})
    response = products_admin_client.get("/api/v1/products?category=Plumb")
    assert response.status_code == 200
    mock_list.assert_called_once()
    assert mock_list.call_args.kwargs["category"] == "Plumb"


@patch("app.api.v1.products.get_product")
@patch("app.auth.dependencies.settings")
def test_admin_can_get_product_detail(mock_settings, mock_get, products_admin_client):
    _patch_dev_user(mock_settings, role="admin")
    mock_get.return_value = PRODUCTS[0]
    response = products_admin_client.get("/api/v1/products/1")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["product_name"] == "Boiler Service"
    assert data["scope_of_work"] == "Inspect and service boiler"


@patch("app.api.v1.products.update_product")
@patch("app.auth.dependencies.settings")
def test_admin_can_update_scope_of_work(mock_settings, mock_update, products_admin_client):
    _patch_dev_user(mock_settings, role="admin")
    updated = _product(scope_of_work="Updated scope text")
    mock_update.return_value = updated
    response = products_admin_client.patch(
        "/api/v1/products/1",
        json={"scope_of_work": "Updated scope text"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["scope_of_work"] == "Updated scope text"


@pytest.mark.parametrize("role", ["manager", "estimator", "engineer", "client"])
@patch("app.api.v1.products.update_product")
@patch("app.auth.dependencies.settings")
def test_non_admin_cannot_update_products(mock_settings, mock_update, products_admin_client, role):
    _patch_dev_user(mock_settings, role=role)
    response = products_admin_client.patch(
        "/api/v1/products/1",
        json={"scope_of_work": "Blocked update"},
    )
    assert response.status_code == 403
    mock_update.assert_not_called()


@patch("app.api.v1.products.update_product")
@patch("app.auth.dependencies.settings")
def test_unauthenticated_blocked_from_admin_write(mock_settings, mock_update, products_admin_client):
    mock_settings.dev_auth_enabled = False
    response = products_admin_client.patch(
        "/api/v1/products/1",
        json={"scope_of_work": "Blocked update"},
    )
    assert response.status_code == 401
    mock_update.assert_not_called()


@patch("app.api.v1.products.update_product")
@patch("app.auth.dependencies.settings")
def test_admin_update_requires_product_name(mock_settings, mock_update, products_admin_client):
    _patch_dev_user(mock_settings, role="admin")
    mock_update.side_effect = ValueError("Product name is required")
    response = products_admin_client.patch(
        "/api/v1/products/1",
        json={"product_name": "   "},
    )
    assert response.status_code == 400
