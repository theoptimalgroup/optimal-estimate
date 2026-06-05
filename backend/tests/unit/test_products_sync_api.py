"""Unit tests for eWorks product sync API auth and audit."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.main import app
from app.models.product import Product
from app.models.support import AuditLog
from app.models.user import User
from app.schemas.product import ProductSyncSummary


@pytest.fixture()
def sync_db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in [User.__table__, Product.__table__, AuditLog.__table__]:
        table.create(engine)

    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture()
def sync_api_client(sync_db_session):
    def override_get_db():
        try:
            yield sync_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def _patch_dev_user(mock_settings, *, role: str, enabled: bool = True):
    mock_settings.auth_provider = "dev"
    mock_settings.dev_auth_enabled = enabled
    mock_settings.dev_user_id = "dev-user-1"
    mock_settings.dev_user_email = "staff@optimal.example"
    mock_settings.dev_user_name = "Staff User"
    mock_settings.dev_user_role = role
    mock_settings.dev_user_is_active = True
    mock_settings.dev_auth_auto_create_user = False
    mock_settings.dashboard_password = "test-dashboard-pass"


def _mock_summary(**overrides):
    defaults = {
        "fetched": 10,
        "created": 3,
        "updated": 5,
        "skipped": 2,
        "failed": 0,
        "errors": [],
    }
    defaults.update(overrides)
    return ProductSyncSummary(**defaults)


@patch("app.api.v1.integrations.eworks.sync_products_from_eworks")
@patch("app.auth.dependencies.settings")
def test_admin_can_trigger_product_sync(mock_settings, mock_sync, sync_api_client):
    _patch_dev_user(mock_settings, role="admin")
    mock_sync.return_value = _mock_summary()

    response = sync_api_client.post("/api/v1/integrations/eworks/products/sync")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    summary = body["data"]["summary"]
    assert summary["fetched"] == 10
    assert summary["created"] == 3
    assert summary["updated"] == 5
    assert summary["skipped"] == 2
    assert summary["failed"] == 0
    assert summary["errors"] == []
    assert summary["total_fetched"] == 10
    assert summary["inserted"] == 3
    assert "api_key" not in response.text.lower()
    mock_sync.assert_called_once()


@pytest.mark.parametrize("role", ["manager", "estimator", "engineer", "client"])
@patch("app.api.v1.integrations.eworks.sync_products_from_eworks")
@patch("app.auth.dependencies.settings")
def test_non_admin_roles_blocked_from_product_sync(mock_settings, mock_sync, sync_api_client, role):
    _patch_dev_user(mock_settings, role=role)
    response = sync_api_client.post("/api/v1/integrations/eworks/products/sync")
    assert response.status_code == 403
    mock_sync.assert_not_called()


@patch("app.api.v1.integrations.eworks.sync_products_from_eworks")
@patch("app.auth.dependencies.settings")
def test_dashboard_password_fallback_still_works(mock_settings, mock_sync, sync_api_client):
    mock_settings.dev_auth_enabled = False
    mock_settings.dashboard_password = "test-dashboard-pass"
    mock_sync.return_value = _mock_summary(created=1, updated=0)

    response = sync_api_client.post(
        "/api/v1/integrations/eworks/products/sync",
        headers={"X-Dashboard-Password": "test-dashboard-pass"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["summary"]["created"] == 1
    mock_sync.assert_called_once()


@patch("app.api.v1.integrations.eworks.sync_products_from_eworks")
@patch("app.auth.dependencies.settings")
def test_product_sync_creates_audit_log(mock_settings, mock_sync, sync_api_client, sync_db_session):
    _patch_dev_user(mock_settings, role="admin")
    mock_sync.return_value = _mock_summary(fetched=12, created=4, updated=6, failed=0)

    response = sync_api_client.post("/api/v1/integrations/eworks/products/sync")
    assert response.status_code == 200

    logs = sync_db_session.scalars(
        select(AuditLog).where(AuditLog.action == "eworks_products_sync_completed")
    ).all()
    assert len(logs) == 1
    log = logs[0]
    assert log.entity_type == "product"
    metadata = (log.new_value or {}).get("_metadata") or {}
    assert metadata["fetched"] == 12
    assert metadata["created"] == 4
    assert metadata["updated"] == 6
    assert metadata["failed"] == 0
    assert "api_key" not in str(metadata).lower()


@patch("app.api.v1.integrations.eworks.sync_products_from_eworks")
@patch("app.auth.dependencies.settings")
def test_password_sync_audit_uses_dashboard_actor(mock_settings, mock_sync, sync_api_client, sync_db_session):
    mock_settings.dev_auth_enabled = False
    mock_settings.dashboard_password = "test-dashboard-pass"
    mock_sync.return_value = _mock_summary()

    response = sync_api_client.post(
        "/api/v1/integrations/eworks/products/sync",
        headers={"X-Dashboard-Password": "test-dashboard-pass"},
    )
    assert response.status_code == 200

    log = sync_db_session.scalars(
        select(AuditLog).where(AuditLog.action == "eworks_products_sync_completed")
    ).one()
    metadata = (log.new_value or {}).get("_metadata") or {}
    assert metadata["auth_method"] == "dashboard_password"
    assert metadata["actor_email"] == "dashboard-password"
