"""Unit tests for manager/admin reports API."""

from __future__ import annotations

from datetime import datetime, timezone
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
from app.models.support import AuditLog
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


def _step1_snapshot(*, quote_number: str, client_name: str, trade_name: str) -> dict:
    return {
        "quote_number": quote_number,
        "job_number": "JOB-001",
        "client_name": client_name,
        "trade_name": trade_name,
        "property_address": "1 Test Street",
    }


def _ui_state_with_total(final_total: str, *, internal_notes: str | None = None) -> dict:
    return {
        "current_step": 3,
        "max_reachable_step": 3,
        "last_result": {
            "breakdown": {"final_total": final_total},
            "work_breakdowns": [{"work_index": 0, "breakdown": {"final_total": final_total}}],
            "internal_notes": internal_notes,
        },
    }


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for model in (User, Client, Trade, CalculationSession, AuditLog):
        model.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    client = Client(name="Atkinson McLeod", default_vat_rate=Decimal("20"))
    trade = Trade(name="Painter")
    session.add_all([client, trade])
    session.flush()

    submitted_at = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    session.add_all(
        [
            CalculationSession(
                id=uuid4(),
                session_token="token-submitted-1",
                source="test",
                payload_snapshot={},
                step1_snapshot=_step1_snapshot(
                    quote_number="Q-1001",
                    client_name="Atkinson McLeod",
                    trade_name="Painter",
                ),
                ui_state=_ui_state_with_total("1200.00", internal_notes="Site note"),
                client_id=client.id,
                trade_id=trade.id,
                expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
                status="submitted",
                submitted_at=submitted_at,
            ),
            CalculationSession(
                id=uuid4(),
                session_token="token-submitted-2",
                source="test",
                payload_snapshot={},
                step1_snapshot=_step1_snapshot(
                    quote_number="Q-1002",
                    client_name="Atkinson McLeod",
                    trade_name="Painter",
                ),
                ui_state=_ui_state_with_total("800.00"),
                client_id=client.id,
                trade_id=trade.id,
                expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
                status="submitted",
                submitted_at=datetime(2026, 6, 2, 9, 0, tzinfo=timezone.utc),
            ),
            CalculationSession(
                id=uuid4(),
                session_token="token-progress",
                source="test",
                payload_snapshot={},
                step1_snapshot=_step1_snapshot(
                    quote_number="Q-DRAFT",
                    client_name="Atkinson McLeod",
                    trade_name="Painter",
                ),
                ui_state=_ui_state_with_total("500.00"),
                client_id=client.id,
                trade_id=trade.id,
                expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
                status="in_progress",
            ),
        ]
    )
    session.add(
        AuditLog(
            id=uuid4(),
            user_id=None,
            action="quote_reopened",
            entity_type="calculation_session",
            entity_id=uuid4(),
            old_value=None,
            new_value={"session_token": "secret-token", "password_hash": "secret"},
            created_at=datetime(2026, 6, 1, 15, 0, tzinfo=timezone.utc),
        )
    )
    session.commit()

    yield session
    session.close()


@pytest.fixture()
def reports_client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@patch("app.auth.dependencies.settings")
def test_manager_can_access_report_summary(mock_settings, reports_client):
    _patch_dev_user(mock_settings, role="manager")
    response = reports_client.get("/api/v1/reports/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["kpis"]["submitted_quotes"] == 2
    assert float(body["data"]["kpis"]["total_value"]) == 2000.0


@patch("app.auth.dependencies.settings")
def test_admin_can_access_report_summary(mock_settings, reports_client):
    _patch_dev_user(mock_settings, role="admin")
    response = reports_client.get("/api/v1/reports/summary")
    assert response.status_code == 200
    assert response.json()["data"]["kpis"]["submitted_quotes"] == 2


@pytest.mark.parametrize("role", ["estimator", "engineer", "client"])
@patch("app.auth.dependencies.settings")
def test_non_manager_roles_blocked(mock_settings, reports_client, role):
    _patch_dev_user(mock_settings, role=role)
    response = reports_client.get("/api/v1/reports/summary")
    assert response.status_code == 403


@patch("app.auth.dependencies.settings")
def test_unauthenticated_blocked(mock_settings, reports_client):
    mock_settings.dev_auth_enabled = False
    response = reports_client.get("/api/v1/reports/summary")
    assert response.status_code == 401


@patch("app.auth.dependencies.settings")
def test_summary_handles_no_data(mock_settings, reports_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    db_session.query(CalculationSession).delete()
    db_session.commit()

    response = reports_client.get("/api/v1/reports/summary")
    assert response.status_code == 200
    kpis = response.json()["data"]["kpis"]
    assert kpis["submitted_quotes"] == 0
    assert float(kpis["total_value"]) == 0.0
    assert float(kpis["average_quote_value"]) == 0.0


@patch("app.auth.dependencies.settings")
def test_summary_kpis_and_breakdowns(mock_settings, reports_client):
    _patch_dev_user(mock_settings, role="manager")
    response = reports_client.get("/api/v1/reports/summary")
    data = response.json()["data"]

    assert data["kpis"]["with_internal_notes_count"] == 1
    assert data["kpis"]["reopened_count"] == 1
    assert len(data["by_client"]) == 1
    assert data["by_client"][0]["client_name"] == "Atkinson McLeod"
    assert data["by_client"][0]["count"] == 2
    assert len(data["by_trade"]) == 1
    assert len(data["recent_quotes"]) == 2


@patch("app.auth.dependencies.settings")
def test_summary_date_filter(mock_settings, reports_client):
    _patch_dev_user(mock_settings, role="manager")
    response = reports_client.get("/api/v1/reports/summary?date_from=2026-06-02T00:00:00Z")
    data = response.json()["data"]
    assert data["kpis"]["submitted_quotes"] == 1
    assert float(data["kpis"]["total_value"]) == 800.0


@patch("app.auth.dependencies.settings")
def test_no_sensitive_fields_in_response(mock_settings, reports_client):
    _patch_dev_user(mock_settings, role="manager")
    response = reports_client.get("/api/v1/reports/summary")
    text = response.text.lower()
    assert "session_token" not in text
    assert "password_hash" not in text
    assert "dashboard_password" not in text
    assert "api_key" not in text
    assert "formula denominator" not in text


@patch("app.auth.dependencies.settings")
def test_list_report_quotes(mock_settings, reports_client):
    _patch_dev_user(mock_settings, role="manager")
    response = reports_client.get("/api/v1/reports/quotes?limit=10&offset=0")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["meta"]["total"] == 2
    assert len(body["data"]) == 2
    assert "session_token" not in response.text
