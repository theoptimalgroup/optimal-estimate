"""Unit tests for admin trades API and public trade reads."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.main import app
from app.models.calculation_session import CalculationSession
from app.models.client import Client
from app.models.rate_rule import RateRule
from app.models.trade import Trade
from app.models.user import User


def _patch_dev_user(mock_settings, *, role: str, enabled: bool = True):
    mock_settings.dev_auth_enabled = enabled
    mock_settings.dev_user_id = "dev-user-1"
    mock_settings.dev_user_email = "staff@optimal.example"
    mock_settings.dev_user_name = "Staff User"
    mock_settings.dev_user_role = role
    mock_settings.dev_user_is_active = True
    mock_settings.dev_auth_auto_create_user = False


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for model in (User, Client, Trade, RateRule, CalculationSession):
        model.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    client = Client(name="Acme", default_vat_rate=Decimal("20"))
    trade = Trade(name="Plumber", description="Plumbing works", is_active=True)
    inactive = Trade(name="Legacy Trade", is_active=False)
    session.add_all([client, trade, inactive])
    session.flush()

    session.add(
        RateRule(
            client_id=client.id,
            trade_id=trade.id,
            version="v1",
            hourly_rate=Decimal("75"),
            active_from=date(2024, 1, 1),
            is_active=True,
            formula_source="simplified",
        )
    )
    session.commit()

    yield session, trade, inactive
    session.close()


@pytest.fixture()
def trades_client(db_session):
    session, *_ = db_session

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_public_trades_list_still_works(trades_client):
    response = trades_client.get("/api/v1/trades?page=1&page_size=20&is_active=true")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["meta"]["page"] == 1
    assert len(body["data"]) == 1
    assert body["data"][0]["name"] == "Plumber"
    assert "rate_rules_count" not in body["data"][0]


@patch("app.auth.dependencies.settings")
def test_admin_can_list_trades_with_counts(mock_settings, trades_client):
    _patch_dev_user(mock_settings, role="admin")
    response = trades_client.get("/api/v1/trades?limit=25&offset=0")
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] == 2
    plumber = next(item for item in body["data"] if item["name"] == "Plumber")
    assert plumber["rate_rules_count"] == 1
    assert plumber["products_count"] == 0


@patch("app.auth.dependencies.settings")
def test_admin_can_get_trade_detail_enriched(mock_settings, trades_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    _, trade, _ = db_session
    response = trades_client.get(f"/api/v1/trades/{trade.id}?enriched=true")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["description"] == "Plumbing works"
    assert data["rate_rules_count"] == 1


def test_public_trade_detail_still_works(trades_client, db_session):
    _, trade, _ = db_session
    response = trades_client.get(f"/api/v1/trades/{trade.id}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "Plumber"
    assert "rate_rules_count" not in data


@patch("app.auth.dependencies.settings")
def test_admin_can_update_trade_safe_fields(mock_settings, trades_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    _, trade, _ = db_session
    response = trades_client.patch(
        f"/api/v1/trades/{trade.id}",
        json={"description": "Updated plumbing scope", "is_active": False},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["description"] == "Updated plumbing scope"
    assert data["is_active"] is False


@pytest.mark.parametrize("role", ["manager", "estimator", "engineer", "client"])
@patch("app.auth.dependencies.settings")
def test_non_admin_cannot_update_trades(mock_settings, trades_client, db_session, role):
    _patch_dev_user(mock_settings, role=role)
    _, trade, _ = db_session
    response = trades_client.patch(f"/api/v1/trades/{trade.id}", json={"description": "Blocked"})
    assert response.status_code == 403


@patch("app.auth.dependencies.settings")
def test_unauthenticated_blocked_from_trade_update(mock_settings, trades_client, db_session):
    mock_settings.dev_auth_enabled = False
    _, trade, _ = db_session
    response = trades_client.patch(f"/api/v1/trades/{trade.id}", json={"description": "Blocked"})
    assert response.status_code == 401
