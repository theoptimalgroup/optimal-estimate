"""Unit tests for dashboard dual-auth (role-based dev auth + password fallback)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import DashboardAccess, require_dashboard_access
from app.core.security import UserRole
from app.db.session import get_db
from app.main import app
from app.models.user import User
from app.schemas.eworks_link import DashboardQuotesResponse


@pytest.fixture()
def dashboard_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    User.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture()
def dashboard_client(dashboard_db):
    def override_get_db():
        try:
            yield dashboard_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def _patch_dev_user(mock_settings, *, role: str, enabled: bool = True):
    mock_settings.dev_auth_enabled = enabled
    mock_settings.dev_user_id = "dev-user-1"
    mock_settings.dev_user_email = "staff@optimal.example"
    mock_settings.dev_user_name = "Staff User"
    mock_settings.dev_user_role = role
    mock_settings.dev_user_is_active = True
    mock_settings.dev_auth_auto_create_user = False
    mock_settings.dashboard_password = "test-dashboard-pass"


def _build_dashboard_access_test_app(db_session) -> FastAPI:
    test_app = FastAPI()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    test_app.dependency_overrides[get_db] = override_get_db

    @test_app.get("/check")
    def check(_access: DashboardAccess = Depends(require_dashboard_access)):
        return {"method": _access.method, "role": _access.user.role.value if _access.user else None}

    return test_app


@patch("app.auth.dependencies.settings")
def test_valid_dashboard_password_still_works(mock_settings, dashboard_client):
    mock_settings.dev_auth_enabled = False
    mock_settings.dashboard_password = "test-dashboard-pass"

    with patch("app.api.v1.dashboard.list_submitted_quotes") as mock_list:
        mock_list.return_value = DashboardQuotesResponse(quotes=[])
        response = dashboard_client.get(
            "/api/v1/dashboard/quotes",
            headers={"X-Dashboard-Password": "test-dashboard-pass"},
        )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["data"]["quotes"] == []


@pytest.mark.parametrize("role", ["admin", "manager", "estimator"])
@patch("app.auth.dependencies.settings")
def test_staff_role_can_access_dashboard_without_password(mock_settings, dashboard_client, role):
    _patch_dev_user(mock_settings, role=role)

    with patch("app.api.v1.dashboard.list_submitted_quotes") as mock_list:
        mock_list.return_value = DashboardQuotesResponse(quotes=[])
        response = dashboard_client.get("/api/v1/dashboard/quotes")

    assert response.status_code == 200
    assert response.json()["data"]["quotes"] == []


@pytest.mark.parametrize("role", ["engineer", "client"])
@patch("app.auth.dependencies.settings")
def test_blocked_role_denied_without_password(mock_settings, dashboard_client, role):
    _patch_dev_user(mock_settings, role=role)

    with patch("app.api.v1.dashboard.list_submitted_quotes"):
        response = dashboard_client.get("/api/v1/dashboard/quotes")

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"


@patch("app.auth.dependencies.settings")
def test_invalid_password_and_no_dev_auth_returns_401(mock_settings, dashboard_client):
    mock_settings.dev_auth_enabled = False
    mock_settings.dashboard_password = "test-dashboard-pass"

    response = dashboard_client.get("/api/v1/dashboard/quotes")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid dashboard password"


@patch("app.auth.dependencies.settings")
def test_wrong_password_with_blocked_role_returns_403(mock_settings, dashboard_client):
    _patch_dev_user(mock_settings, role="engineer")

    response = dashboard_client.get(
        "/api/v1/dashboard/quotes",
        headers={"X-Dashboard-Password": "wrong-pass"},
    )

    assert response.status_code == 403


@patch("app.auth.dependencies.settings")
def test_require_dashboard_access_password_path(mock_settings, dashboard_db):
    mock_settings.dev_auth_enabled = False
    mock_settings.dashboard_password = "secret"

    with TestClient(_build_dashboard_access_test_app(dashboard_db)) as client:
        response = client.get("/check", headers={"X-Dashboard-Password": "secret"})

    assert response.status_code == 200
    assert response.json() == {"method": "password", "role": None}


@patch("app.auth.dependencies.settings")
def test_require_dashboard_access_user_path(mock_settings, dashboard_db):
    _patch_dev_user(mock_settings, role="manager")

    with TestClient(_build_dashboard_access_test_app(dashboard_db)) as client:
        response = client.get("/check")

    assert response.status_code == 200
    assert response.json() == {"method": "user", "role": "manager"}
