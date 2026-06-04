"""Unit tests for admin audit logs API and redaction."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import UserRole, get_password_hash
from app.db.session import get_db
from app.main import app
from app.models.support import AuditLog
from app.models.user import User
from app.services.audit_log_service import create_audit_log, redact_sensitive_fields


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
    for model in (User, AuditLog):
        model.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    now = datetime.now(timezone.utc)
    admin = User(
        id=uuid4(),
        email="admin@optimal.example",
        full_name="Admin User",
        password_hash=get_password_hash("admin12345"),
        role=UserRole.ADMIN.value,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    session.add(admin)
    session.flush()

    create_audit_log(
        session,
        actor_user_id=admin.id,
        actor_email=admin.email,
        action="user_updated",
        entity_type="user",
        entity_id=admin.id,
        before={"role": "manager", "password_hash": "secret"},
        after={"role": "admin"},
    )
    session.commit()

    yield session, admin
    session.close()


@pytest.fixture()
def audit_client(db_session):
    session, _ = db_session

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_redact_sensitive_fields():
    payload = {
        "email": "user@example.com",
        "password_hash": "secret",
        "session_token": "abc123",
        "nested": {"api_key": "key-value"},
    }
    redacted = redact_sensitive_fields(payload)
    assert redacted["email"] == "user@example.com"
    assert redacted["password_hash"] == "***REDACTED***"
    assert redacted["session_token"] == "***REDACTED***"
    assert redacted["nested"]["api_key"] == "***REDACTED***"


@patch("app.auth.dependencies.settings")
def test_admin_can_list_audit_logs(mock_settings, audit_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    response = audit_client.get("/api/v1/audit-logs")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["meta"]["total"] >= 1
    assert "password_hash" not in response.text


@patch("app.auth.dependencies.settings")
def test_admin_can_filter_audit_logs_by_action(mock_settings, audit_client):
    _patch_dev_user(mock_settings, role="admin")
    response = audit_client.get("/api/v1/audit-logs?action=user_updated")
    assert response.status_code == 200
    assert all(item["action"] == "user_updated" for item in response.json()["data"])


@patch("app.auth.dependencies.settings")
def test_admin_can_get_audit_log_detail(mock_settings, audit_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    session, admin = db_session
    log_id = session.scalar(select(AuditLog.id).limit(1))
    response = audit_client.get(f"/api/v1/audit-logs/{log_id}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["action"] == "user_updated"
    assert data["before_snapshot"]["password_hash"] == "***REDACTED***"
    assert "secret" not in response.text


@pytest.mark.parametrize("role", ["manager", "estimator", "engineer", "client"])
@patch("app.auth.dependencies.settings")
def test_non_admin_cannot_list_audit_logs(mock_settings, audit_client, role):
    _patch_dev_user(mock_settings, role=role)
    response = audit_client.get("/api/v1/audit-logs")
    assert response.status_code == 403


@patch("app.auth.dependencies.settings")
def test_unauthenticated_blocked_from_audit_logs(mock_settings, audit_client):
    mock_settings.dev_auth_enabled = False
    response = audit_client.get("/api/v1/audit-logs")
    assert response.status_code == 401


@patch("app.auth.dependencies.settings")
def test_user_update_creates_audit_log(mock_settings, audit_client, db_session):
    _patch_dev_user(mock_settings, role="admin", email="admin@optimal.example")
    session, admin = db_session
    manager = User(
        id=uuid4(),
        email="manager@optimal.example",
        full_name="Manager User",
        password_hash=get_password_hash("manager12345"),
        role=UserRole.MANAGER.value,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(manager)
    session.commit()

    response = audit_client.patch(
        f"/api/v1/users/{manager.id}",
        json={"role": "estimator"},
    )
    assert response.status_code == 200

    logs = session.scalars(select(AuditLog).where(AuditLog.action == "user_updated", AuditLog.entity_id == manager.id)).all()
    assert len(logs) >= 1
    assert logs[-1].old_value is not None
    assert "password_hash" not in (logs[-1].old_value or {})
