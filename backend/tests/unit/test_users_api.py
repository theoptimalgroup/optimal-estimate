"""Unit tests for admin users API."""

from __future__ import annotations

from datetime import datetime, timezone
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
from app.models.user import User
from app.models.support import AuditLog


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
    User.__table__.create(engine)
    AuditLog.__table__.create(engine)
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
    manager = User(
        id=uuid4(),
        email="manager@optimal.example",
        full_name="Manager User",
        password_hash=get_password_hash("manager12345"),
        role=UserRole.MANAGER.value,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    inactive = User(
        id=uuid4(),
        email="inactive@optimal.example",
        full_name="Inactive User",
        password_hash=get_password_hash("inactive12345"),
        role=UserRole.ESTIMATOR.value,
        is_active=False,
        created_at=now,
        updated_at=now,
    )
    session.add_all([admin, manager, inactive])
    session.commit()

    yield session, admin, manager, inactive
    session.close()


@pytest.fixture()
def users_client(db_session):
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
def test_admin_can_list_users(mock_settings, users_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    response = users_client.get("/api/v1/users")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["meta"]["total"] == 3
    assert "password_hash" not in response.text


@patch("app.auth.dependencies.settings")
def test_admin_can_filter_users_by_role(mock_settings, users_client):
    _patch_dev_user(mock_settings, role="admin")
    response = users_client.get("/api/v1/users?role=manager")
    assert response.status_code == 200
    emails = [item["email"] for item in response.json()["data"]]
    assert emails == ["manager@optimal.example"]


@patch("app.auth.dependencies.settings")
def test_admin_can_get_user_detail(mock_settings, users_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    _, admin, _, _ = db_session
    response = users_client.get(f"/api/v1/users/{admin.id}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["email"] == "admin@optimal.example"
    assert data["name"] == "Admin User"
    assert data["role"] == "admin"
    assert data["auth_provider"] == "local"
    assert "password_hash" not in data


@patch("app.services.user_service.settings")
@patch("app.auth.dependencies.settings")
def test_admin_can_create_user(mock_auth_settings, mock_user_settings, users_client, db_session):
    _patch_dev_user(mock_auth_settings, role="admin")
    mock_user_settings.auth_provider = "azure"
    session, *_ = db_session

    response = users_client.post(
        "/api/v1/users",
        json={
            "email": "new.user@optimal.example",
            "name": "New User",
            "role": "estimator",
            "is_active": True,
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["email"] == "new.user@optimal.example"
    assert data["name"] == "New User"
    assert data["role"] == "estimator"
    assert data["is_active"] is True
    assert data["auth_provider"] == "azure"
    assert "password_hash" not in data
    assert "password_hash" not in response.text

    audit = session.query(AuditLog).filter(AuditLog.action == "user_created").one()
    assert audit.entity_type == "user"
    assert audit.new_value is not None
    assert "password_hash" not in (audit.new_value or {})


@patch("app.auth.dependencies.settings")
def test_create_user_duplicate_email_blocked(mock_settings, users_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    _, admin, _, _ = db_session

    response = users_client.post(
        "/api/v1/users",
        json={
            "email": admin.email.upper(),
            "name": "Duplicate User",
            "role": "manager",
        },
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


@patch("app.auth.dependencies.settings")
def test_create_user_invalid_role_returns_422(mock_settings, users_client):
    _patch_dev_user(mock_settings, role="admin")
    response = users_client.post(
        "/api/v1/users",
        json={
            "email": "bad.role@optimal.example",
            "name": "Bad Role User",
            "role": "superadmin",
        },
    )
    assert response.status_code == 422


@pytest.mark.parametrize("role", ["manager", "engineer"])
@patch("app.auth.dependencies.settings")
def test_non_admin_cannot_create_user(mock_settings, users_client, role):
    _patch_dev_user(mock_settings, role=role)
    response = users_client.post(
        "/api/v1/users",
        json={
            "email": "blocked@optimal.example",
            "name": "Blocked User",
            "role": "client",
        },
    )
    assert response.status_code == 403


@patch("app.auth.dependencies.settings")
def test_admin_can_update_role(mock_settings, users_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    _, _, manager, _ = db_session
    response = users_client.patch(
        f"/api/v1/users/{manager.id}",
        json={"role": "estimator"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["role"] == "estimator"


@patch("app.auth.dependencies.settings")
def test_admin_can_deactivate_and_reactivate_user(mock_settings, users_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    _, _, manager, _ = db_session

    deactivate = users_client.patch(f"/api/v1/users/{manager.id}", json={"is_active": False})
    assert deactivate.status_code == 200
    assert deactivate.json()["data"]["is_active"] is False

    reactivate = users_client.patch(f"/api/v1/users/{manager.id}", json={"is_active": True})
    assert reactivate.status_code == 200
    assert reactivate.json()["data"]["is_active"] is True


@patch("app.auth.dependencies.settings")
def test_admin_cannot_deactivate_self_when_emails_match(mock_settings, users_client, db_session):
    _patch_dev_user(mock_settings, role="admin", email="admin@optimal.example")
    _, admin, _, _ = db_session
    response = users_client.patch(f"/api/v1/users/{admin.id}", json={"is_active": False})
    assert response.status_code == 400
    assert "cannot deactivate your own account" in response.json()["detail"].lower()


@pytest.mark.parametrize("role", ["manager", "estimator", "engineer", "client"])
@patch("app.auth.dependencies.settings")
def test_non_admin_cannot_list_or_update_users(mock_settings, users_client, db_session, role):
    _patch_dev_user(mock_settings, role=role)
    _, admin, manager, _ = db_session

    list_response = users_client.get("/api/v1/users")
    assert list_response.status_code == 403

    create_response = users_client.post(
        "/api/v1/users",
        json={
            "email": "blocked@optimal.example",
            "name": "Blocked User",
            "role": "client",
        },
    )
    assert create_response.status_code == 403

    update_response = users_client.patch(
        f"/api/v1/users/{manager.id}",
        json={"role": "client"},
    )
    assert update_response.status_code == 403


@patch("app.auth.dependencies.settings")
def test_unauthenticated_blocked(mock_settings, users_client, db_session):
    mock_settings.dev_auth_enabled = False
    _, _, manager, _ = db_session
    response = users_client.get("/api/v1/users")
    assert response.status_code == 401


@patch("app.auth.dependencies.settings")
def test_invalid_role_update_returns_422(mock_settings, users_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    _, _, manager, _ = db_session
    response = users_client.patch(
        f"/api/v1/users/{manager.id}",
        json={"role": "superadmin"},
    )
    assert response.status_code == 422
