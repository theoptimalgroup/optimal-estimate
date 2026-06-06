"""Unit tests for manual calculation session creation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import UserRole, get_password_hash
from app.db.session import get_db
from app.main import app
from app.models.calculation_session import CalculationSession
from app.models.client import Client
from app.models.client_alias import ClientAlias
from app.models.rate_rule import RateRule
from app.models.support import AuditLog
from app.models.trade import Trade
from app.models.user import User


def _patch_dev_user(mock_settings, *, role: str):
    email_map = {
        "admin": "admin@optimal.example",
        "manager": "manager@optimal.example",
        "estimator": "estimator@optimal.example",
        "engineer": "engineer@optimal.example",
        "client": "client@optimal.example",
    }
    mock_settings.auth_provider = "dev"
    mock_settings.dev_auth_enabled = True
    mock_settings.dev_user_id = f"dev-{role}-1"
    mock_settings.dev_user_email = email_map[role]
    mock_settings.dev_user_name = f"{role.title()} User"
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
    for table in [
        User.__table__,
        AuditLog.__table__,
        Client.__table__,
        ClientAlias.__table__,
        Trade.__table__,
        RateRule.__table__,
        CalculationSession.__table__,
    ]:
        table.create(engine)

    Session = sessionmaker(bind=engine)
    session = Session()
    now = datetime.now(timezone.utc)

    users = [
        User(
            id=uuid.uuid4(),
            email="admin@optimal.example",
            full_name="Admin",
            password_hash=get_password_hash("admin12345"),
            role=UserRole.ADMIN.value,
            is_active=True,
            created_at=now,
            updated_at=now,
        ),
        User(
            id=uuid.uuid4(),
            email="manager@optimal.example",
            full_name="Manager",
            password_hash=get_password_hash("manager12345"),
            role=UserRole.MANAGER.value,
            is_active=True,
            created_at=now,
            updated_at=now,
        ),
        User(
            id=uuid.uuid4(),
            email="estimator@optimal.example",
            full_name="Estimator",
            password_hash=get_password_hash("est12345"),
            role=UserRole.ESTIMATOR.value,
            is_active=True,
            created_at=now,
            updated_at=now,
        ),
        User(
            id=uuid.uuid4(),
            email="engineer@optimal.example",
            full_name="Engineer",
            password_hash=get_password_hash("eng12345"),
            role=UserRole.ENGINEER.value,
            is_active=True,
            created_at=now,
            updated_at=now,
        ),
        User(
            id=uuid.uuid4(),
            email="client@optimal.example",
            full_name="Client",
            password_hash=get_password_hash("client12345"),
            role=UserRole.CLIENT.value,
            is_active=True,
            created_at=now,
            updated_at=now,
        ),
    ]
    session.add_all(users)
    trade = Trade(id=uuid.uuid4(), name="Carpenter", is_active=True, created_at=now, updated_at=now)
    session.add(trade)
    session.commit()

    yield session
    session.close()


@pytest.fixture()
def api_client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.parametrize("role", ["admin", "manager", "estimator"])
@patch("app.auth.dependencies.settings")
def test_staff_can_create_manual_session(mock_settings, api_client, db_session, role):
    _patch_dev_user(mock_settings, role=role)
    response = api_client.post("/api/v1/calculation-session/manual", json={})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["session_id"]
    assert data["session_token"]
    assert data["resume_url"].startswith("/eworks/calculate?session_id=")
    assert "token=" in data["resume_url"]
    assert "password_hash" not in response.text

    session = db_session.scalar(select(CalculationSession))
    assert session is not None
    assert session.source == "manual"
    assert session.step1_snapshot["client_name"] == "Manual Estimate"

    audit = db_session.query(AuditLog).filter(AuditLog.action == "manual_estimate_created").one()
    assert audit.entity_type == "calculation_session"
    assert audit.new_value is not None
    assert "session_token" not in (audit.new_value or {})


@pytest.mark.parametrize("role", ["engineer", "client"])
@patch("app.auth.dependencies.settings")
def test_engineer_and_client_blocked(mock_settings, api_client, role):
    _patch_dev_user(mock_settings, role=role)
    response = api_client.post("/api/v1/calculation-session/manual", json={})
    assert response.status_code == 403


@patch("app.auth.dependencies.settings")
def test_manual_session_accepts_optional_fields(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    response = api_client.post(
        "/api/v1/calculation-session/manual",
        json={
            "quote_ref": "Q-CUSTOM",
            "job_ref": "J-100",
            "client_name": "Acme Ltd",
            "trade_name": "Carpenter",
        },
    )
    assert response.status_code == 200
    session = db_session.scalar(select(CalculationSession))
    assert session.step1_snapshot["quote_number"] == "Q-CUSTOM"
    assert session.step1_snapshot["job_number"] == "J-100"
    assert session.step1_snapshot["client_name"] == "Acme Ltd"
    assert session.step1_snapshot["trade_name"] == "Carpenter"
