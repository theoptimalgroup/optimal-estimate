"""Unit tests for admin settings API."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
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
from app.models.rate_rule import RateRule
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


def _mock_app_settings():
    mock = MagicMock()
    mock.environment = "development"
    mock.is_development = True
    mock.api_v1_prefix = "/api/v1"
    mock.formula_version = "1.0.0"
    mock.template_version = "1.0.0"
    mock.dev_auth_enabled = True
    mock.dev_user_email = "admin@optimal.example"
    mock.dev_auth_auto_create_user = False
    mock.eworks_base_url = "https://eworks.example.com"
    mock.eworks_api_key = "eworks-secret-key-12345"
    mock.eworks_api_enabled = True
    mock.eworks_acceptance_sync_enabled = False
    mock.eworks_acceptance_sync_mode = "custom_field"
    mock.eworks_acceptance_custom_field_id = 45
    mock.eworks_acceptance_custom_field_key = "txtar_45"
    mock.auth_provider = "dev"
    mock.is_azure_auth = False
    mock.is_dev_auth = True
    mock.dashboard_password = "super-secret-dashboard-pass"
    mock.storage_backend = "local"
    mock.azure_storage_account_name = None
    mock.azure_storage_connection_string = None
    mock.azure_storage_use_managed_identity = False
    mock.database_url = "postgresql://estimate:estimate_dev@localhost:5432/estimate_tool"
    mock.secret_key = "jwt-secret-key-value"
    mock.cors_origin_list = ["http://localhost:3000"]
    return mock


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for model in (User, Client, Trade, RateRule, CalculationSession, AuditLog):
        model.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    now = datetime.now(timezone.utc)
    user = User(
        id=uuid4(),
        email="admin@optimal.example",
        full_name="Admin User",
        password_hash=get_password_hash("admin12345"),
        role=UserRole.ADMIN.value,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    client = Client(name="Atkinson McLeod", default_vat_rate=Decimal("20"))
    trade = Trade(name="Painter")
    session.add_all([user, client, trade])
    session.flush()

    session.add(
        AuditLog(
            id=uuid4(),
            user_id=user.id,
            action="user_updated",
            entity_type="user",
            entity_id=user.id,
            created_at=now,
        )
    )
    session.commit()

    yield session
    session.close()


@pytest.fixture()
def settings_client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@patch("app.api.v1.settings.settings", new_callable=_mock_app_settings)
@patch("app.auth.dependencies.settings")
def test_admin_can_access_settings(mock_auth_settings, mock_app_settings, settings_client):
    _patch_dev_user(mock_auth_settings, role="admin")
    response = settings_client.get("/api/v1/settings")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["app"]["environment"] == "development"
    assert body["data"]["auth"]["auth_provider"] == "dev"
    assert body["data"]["eworks"]["base_url_configured"] is True
    assert body["data"]["eworks"]["acceptance_sync"]["enabled"] is False
    assert body["data"]["eworks"]["acceptance_sync"]["custom_field_key"] == "txtar_45"
    assert body["data"]["dashboard"]["password_configured"] is True


@patch("app.api.v1.settings.settings", new_callable=_mock_app_settings)
@patch("app.auth.dependencies.settings")
@pytest.mark.parametrize("role", ["manager", "estimator", "engineer", "client"])
def test_non_admin_roles_blocked(mock_auth_settings, mock_app_settings, settings_client, role):
    _patch_dev_user(mock_auth_settings, role=role)
    response = settings_client.get("/api/v1/settings")
    assert response.status_code == 403


@patch("app.api.v1.settings.settings", new_callable=_mock_app_settings)
@patch("app.auth.dependencies.settings")
def test_unauthenticated_blocked(mock_auth_settings, mock_app_settings, settings_client):
    mock_auth_settings.dev_auth_enabled = False
    response = settings_client.get("/api/v1/settings")
    assert response.status_code == 401


@patch("app.api.v1.settings.settings", new_callable=_mock_app_settings)
@patch("app.auth.dependencies.settings")
def test_response_redacts_secrets(mock_auth_settings, mock_app_settings, settings_client):
    _patch_dev_user(mock_auth_settings, role="admin")
    response = settings_client.get("/api/v1/settings")
    text = response.text
    assert "super-secret-dashboard-pass" not in text
    assert "eworks-secret-key-12345" not in text
    assert "jwt-secret-key-value" not in text
    assert "postgresql://estimate:estimate_dev" not in text
    body = response.json()
    assert body["data"]["dashboard"]["password_value"] == "***REDACTED***"
    assert body["data"]["database"]["url"] == "***REDACTED***"


@patch("app.api.v1.settings.settings", new_callable=_mock_app_settings)
@patch("app.auth.dependencies.settings")
def test_configured_flags_are_booleans(mock_auth_settings, mock_app_settings, settings_client):
    _patch_dev_user(mock_auth_settings, role="admin")
    data = settings_client.get("/api/v1/settings").json()["data"]
    assert isinstance(data["eworks"]["base_url_configured"], bool)
    assert isinstance(data["eworks"]["api_key_configured"], bool)
    assert isinstance(data["eworks"]["license_key_configured"], bool)
    assert isinstance(data["dashboard"]["password_configured"], bool)
    assert isinstance(data["database"]["configured"], bool)
    assert isinstance(data["storage"]["azure_blob_configured"], bool)


@patch("app.auth.dependencies.settings")
def test_status_endpoint_returns_counts(mock_auth_settings, settings_client):
    _patch_dev_user(mock_auth_settings, role="admin")
    response = settings_client.get("/api/v1/settings/status")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["database_reachable"] is True
    counts = body["data"]["counts"]
    assert counts["users"] == 1
    assert counts["clients"] == 1
    assert counts["trades"] == 1
    assert counts["audit_logs"] == 1
    assert "latest_audit_log_at" in body["data"]


@patch("app.auth.dependencies.settings")
@pytest.mark.parametrize("role", ["manager", "estimator", "engineer", "client"])
def test_status_endpoint_blocked_for_non_admin(mock_auth_settings, settings_client, role):
    _patch_dev_user(mock_auth_settings, role=role)
    response = settings_client.get("/api/v1/settings/status")
    assert response.status_code == 403
