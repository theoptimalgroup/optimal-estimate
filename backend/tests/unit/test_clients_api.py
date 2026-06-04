"""Unit tests for admin clients API."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import UserRole, get_password_hash
from app.db.session import get_db
from app.main import app
from app.models.calculation_session import CalculationSession
from app.models.client import Client
from app.models.client_alias import ClientAlias
from app.models.rate_rule import RateRule
from app.models.trade import Trade
from app.models.user import User


def _patch_dev_user(mock_settings, *, role: str, email: str = "staff@optimal.example", enabled: bool = True):
    mock_settings.dev_auth_enabled = enabled
    mock_settings.dev_user_id = "dev-user-1"
    mock_settings.dev_user_email = email
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
    for model in (User, Client, ClientAlias, Trade, RateRule, CalculationSession):
        model.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    client = Client(name="Atkinson McLeod", billing_email="billing@example.com", default_vat_rate=Decimal("20"))
    inactive = Client(name="Legacy Client", is_active=False, default_vat_rate=Decimal("20"))
    session.add_all([client, inactive])
    session.flush()
    session.add(ClientAlias(client_id=client.id, alias_name="Atkinson"))
    trade = Trade(name="Plumber")
    session.add(trade)
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
    session.add(
        CalculationSession(
            id=uuid4(),
            session_token="token-1",
            source="test",
            payload_snapshot={},
            step1_snapshot={},
            client_id=client.id,
            trade_id=trade.id,
            expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
            status="in_progress",
        )
    )
    session.commit()

    yield session, client, inactive
    session.close()


@pytest.fixture()
def clients_client(db_session):
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


@patch("app.auth.dependencies.settings")
def test_admin_can_list_clients(mock_settings, clients_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    response = clients_client.get("/api/v1/clients")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["meta"]["total"] == 2
    assert body["data"][0]["rate_rules_count"] >= 0


@patch("app.auth.dependencies.settings")
def test_admin_can_filter_clients_by_search_and_active(mock_settings, clients_client):
    _patch_dev_user(mock_settings, role="admin")
    response = clients_client.get("/api/v1/clients?search=Atkinson&active=true")
    assert response.status_code == 200
    names = [item["name"] for item in response.json()["data"]]
    assert names == ["Atkinson McLeod"]


@patch("app.auth.dependencies.settings")
def test_admin_can_get_client_detail(mock_settings, clients_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    _, client, _ = db_session
    response = clients_client.get(f"/api/v1/clients/{client.id}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "Atkinson McLeod"
    assert data["aliases"] == ["Atkinson"]
    assert data["rate_rules_count"] == 1
    assert data["calculation_sessions_count"] == 1


@patch("app.auth.dependencies.settings")
def test_admin_can_update_client_safe_fields(mock_settings, clients_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    _, client, _ = db_session
    response = clients_client.patch(
        f"/api/v1/clients/{client.id}",
        json={"name": "Atkinson McLeod Updated", "is_active": False},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "Atkinson McLeod Updated"
    assert data["is_active"] is False


@pytest.mark.parametrize("role", ["manager", "estimator", "engineer", "client"])
@patch("app.auth.dependencies.settings")
def test_non_admin_cannot_update_clients(mock_settings, clients_client, db_session, role):
    _patch_dev_user(mock_settings, role=role)
    _, client, _ = db_session
    list_response = clients_client.get("/api/v1/clients")
    assert list_response.status_code == 403
    update_response = clients_client.patch(f"/api/v1/clients/{client.id}", json={"name": "Blocked"})
    assert update_response.status_code == 403


@patch("app.auth.dependencies.settings")
def test_unauthenticated_blocked_from_clients(mock_settings, clients_client, db_session):
    mock_settings.dev_auth_enabled = False
    _, client, _ = db_session
    response = clients_client.get("/api/v1/clients")
    assert response.status_code == 401
