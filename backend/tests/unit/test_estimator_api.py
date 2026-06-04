"""Unit tests for estimator API."""

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
from app.models.client_alias import ClientAlias
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


def _ui_state_with_total(final_total: str) -> dict:
    return {
        "current_step": 3,
        "max_reachable_step": 3,
        "last_result": {
            "breakdown": {"final_total": final_total},
            "work_breakdowns": [{"work_index": 0, "breakdown": {"final_total": final_total}}],
        },
    }


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for model in (User, Client, ClientAlias, Trade, CalculationSession, AuditLog):
        model.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    client = Client(name="Atkinson McLeod", default_vat_rate=Decimal("20"))
    trade = Trade(name="Painter")
    session.add_all([client, trade])
    session.flush()
    session.add(ClientAlias(client_id=client.id, alias_name="Atkinson"))

    in_progress_id = uuid4()
    submitted_id = uuid4()
    reopened_id = uuid4()

    session.add_all(
        [
            CalculationSession(
                id=in_progress_id,
                session_token="token-draft",
                source="test",
                payload_snapshot={},
                step1_snapshot=_step1_snapshot(quote_number="Q-DRAFT", client_name="Atkinson McLeod", trade_name="Painter"),
                step2_snapshot={"works": [{"scope": "Paint hallway"}]},
                ui_state=_ui_state_with_total("500.00"),
                client_id=client.id,
                trade_id=trade.id,
                expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
                status="in_progress",
            ),
            CalculationSession(
                id=submitted_id,
                session_token="token-submitted",
                source="test",
                payload_snapshot={},
                step1_snapshot=_step1_snapshot(quote_number="Q-SUBMITTED", client_name="Atkinson McLeod", trade_name="Painter"),
                step2_snapshot={"works": [{"scope": "Paint kitchen"}]},
                ui_state=_ui_state_with_total("1200.00"),
                client_id=client.id,
                trade_id=trade.id,
                expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
                status="submitted",
                submitted_at=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
            ),
            CalculationSession(
                id=reopened_id,
                session_token="token-reopened",
                source="test",
                payload_snapshot={},
                step1_snapshot=_step1_snapshot(quote_number="Q-REOPENED", client_name="Atkinson McLeod", trade_name="Painter"),
                step2_snapshot={"works": []},
                ui_state={"current_step": 1, "max_reachable_step": 1, "last_result": None},
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
            entity_id=reopened_id,
            old_value=None,
            new_value={"session_token": "secret-token"},
            created_at=datetime(2026, 6, 2, 10, 0, tzinfo=timezone.utc),
        )
    )
    session.commit()

    yield session
    session.close()


@pytest.fixture()
def estimator_client(db_session):
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
def test_estimator_can_access_dashboard(mock_settings, estimator_client):
    _patch_dev_user(mock_settings, role="estimator")
    response = estimator_client.get("/api/v1/estimator/dashboard")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["kpis"]["draft_count"] == 1
    assert data["kpis"]["submitted_count"] == 1
    assert data["kpis"]["reopened_count"] == 1


@patch("app.auth.dependencies.settings")
def test_admin_can_access_estimator_quotes(mock_settings, estimator_client):
    _patch_dev_user(mock_settings, role="admin")
    response = estimator_client.get("/api/v1/estimator/quotes")
    assert response.status_code == 200
    assert response.json()["meta"]["total"] == 3


@patch("app.auth.dependencies.settings")
@pytest.mark.parametrize("role", ["manager", "engineer", "client"])
def test_non_estimator_roles_blocked(mock_settings, estimator_client, role):
    _patch_dev_user(mock_settings, role=role)
    response = estimator_client.get("/api/v1/estimator/dashboard")
    assert response.status_code == 403


@patch("app.auth.dependencies.settings")
def test_unauthenticated_blocked(mock_settings, estimator_client):
    mock_settings.dev_auth_enabled = False
    response = estimator_client.get("/api/v1/estimator/quotes")
    assert response.status_code == 401


@patch("app.auth.dependencies.settings")
def test_empty_data_returns_valid_response(mock_settings, estimator_client, db_session):
    _patch_dev_user(mock_settings, role="estimator")
    db_session.query(CalculationSession).delete()
    db_session.commit()
    response = estimator_client.get("/api/v1/estimator/dashboard")
    assert response.status_code == 200
    kpis = response.json()["data"]["kpis"]
    assert kpis["draft_count"] == 0
    assert kpis["submitted_count"] == 0


@patch("app.auth.dependencies.settings")
def test_sample_sessions_kpi_totals(mock_settings, estimator_client):
    _patch_dev_user(mock_settings, role="estimator")
    data = estimator_client.get("/api/v1/estimator/dashboard").json()["data"]
    assert float(data["kpis"]["total_submitted_value"]) == 1200.0
    assert len(data["recent_quotes"]) == 3


@patch("app.auth.dependencies.settings")
def test_response_does_not_contain_sensitive_fields(mock_settings, estimator_client):
    _patch_dev_user(mock_settings, role="estimator")
    response = estimator_client.get("/api/v1/estimator/quotes")
    text = response.text.lower()
    assert "session_token" not in text
    assert "token-draft" not in text
    assert "formula" not in text
    assert "denominator" not in text
    assert "profit" not in text
    assert "margin" not in text
    assert "password_hash" not in text


@patch("app.auth.dependencies.settings")
def test_resume_returns_token_only_on_explicit_endpoint(mock_settings, estimator_client, db_session):
    _patch_dev_user(mock_settings, role="estimator")
    session_id = db_session.query(CalculationSession).filter(CalculationSession.status == "in_progress").first().id
    response = estimator_client.post(f"/api/v1/estimator/quotes/{session_id}/resume")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["session_token"] == "token-draft"


@patch("app.auth.dependencies.settings")
def test_approvals_returns_submitted_only(mock_settings, estimator_client):
    _patch_dev_user(mock_settings, role="estimator")
    response = estimator_client.get("/api/v1/estimator/approvals")
    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 1
    assert items[0]["quote_ref"] == "Q-SUBMITTED"


@patch("app.auth.dependencies.settings")
def test_estimator_clients_list(mock_settings, estimator_client):
    _patch_dev_user(mock_settings, role="estimator")
    response = estimator_client.get("/api/v1/estimator/clients")
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1
    assert "billing_email" not in response.text
