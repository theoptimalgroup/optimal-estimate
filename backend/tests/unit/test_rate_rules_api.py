"""Unit tests for admin rate rules API."""

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
from app.models.support import AuditLog


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
    for model in (User, AuditLog, Client, Trade, RateRule, CalculationSession):
        model.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    client = Client(name="Acme Ltd", default_vat_rate=Decimal("20"))
    trade = Trade(name="Electrical")
    session.add_all([client, trade])
    session.flush()

    active_rule = RateRule(
        client_id=client.id,
        trade_id=trade.id,
        version="v1",
        hourly_rate=Decimal("75"),
        half_day_rate=Decimal("280"),
        day_rate=Decimal("520"),
        active_from=date(2024, 1, 1),
        is_active=True,
        formula_source="simplified",
        xlsx_client_name="Acme XLSX",
        xlsx_trade_name="Electrical XLSX",
    )
    inactive_rule = RateRule(
        client_id=client.id,
        trade_id=trade.id,
        version="v0",
        hourly_rate=Decimal("60"),
        active_from=date(2023, 1, 1),
        active_to=date(2023, 12, 31),
        is_active=False,
        formula_source="xlsx",
    )
    session.add_all([active_rule, inactive_rule])
    session.commit()

    yield session, client, trade, active_rule, inactive_rule
    session.close()


@pytest.fixture()
def rate_rules_client(db_session):
    session, *_ = db_session

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@patch("app.auth.dependencies.settings")
def test_admin_can_list_rate_rules(mock_settings, rate_rules_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    _, _, _, active_rule, inactive_rule = db_session

    response = rate_rules_client.get("/api/v1/rate-rules")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["meta"]["total"] == 2
    ids = {item["id"] for item in body["data"]}
    assert str(active_rule.id) in ids
    assert str(inactive_rule.id) in ids
    first = body["data"][0]
    assert first["client_name"] == "Acme Ltd"
    assert first["trade_name"] == "Electrical"


@patch("app.auth.dependencies.settings")
def test_admin_can_filter_active_rate_rules(mock_settings, rate_rules_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    _, _, _, active_rule, _ = db_session

    response = rate_rules_client.get("/api/v1/rate-rules", params={"active": True})

    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] == 1
    assert body["data"][0]["id"] == str(active_rule.id)
    assert body["data"][0]["is_active"] is True


@patch("app.auth.dependencies.settings")
def test_admin_can_get_rate_rule_detail(mock_settings, rate_rules_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    _, _, _, active_rule, _ = db_session

    response = rate_rules_client.get(f"/api/v1/rate-rules/{active_rule.id}")

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["id"] == str(active_rule.id)
    assert body["client_name"] == "Acme Ltd"
    assert body["trade_name"] == "Electrical"
    assert body["usage"]["lookup_priority"] == "exact_client_trade"
    assert body["xlsx_client_name"] == "Acme XLSX"


@patch("app.auth.dependencies.settings")
def test_admin_can_patch_rate_rule_status(mock_settings, rate_rules_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    _, _, _, active_rule, _ = db_session

    response = rate_rules_client.patch(
        f"/api/v1/rate-rules/{active_rule.id}/status",
        json={"is_active": False},
    )

    assert response.status_code == 200
    assert response.json()["data"]["is_active"] is False

    list_response = rate_rules_client.get("/api/v1/rate-rules", params={"active": False})
    assert list_response.json()["meta"]["total"] == 2


@pytest.mark.parametrize("role", ["manager", "estimator", "engineer", "client"])
@patch("app.auth.dependencies.settings")
def test_non_admin_roles_blocked(mock_settings, rate_rules_client, role):
    _patch_dev_user(mock_settings, role=role)

    response = rate_rules_client.get("/api/v1/rate-rules")

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"


@patch("app.auth.dependencies.settings")
def test_unauthenticated_blocked_when_dev_auth_disabled(mock_settings, rate_rules_client):
    mock_settings.dev_auth_enabled = False

    response = rate_rules_client.get("/api/v1/rate-rules")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


@patch("app.auth.dependencies.settings")
def test_get_unknown_rate_rule_returns_404(mock_settings, rate_rules_client):
    _patch_dev_user(mock_settings, role="admin")

    response = rate_rules_client.get(f"/api/v1/rate-rules/{uuid4()}")

    assert response.status_code == 404
