"""Unit tests for admin dashboard — reuses manager classification, admin-only access."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import UserRole, get_password_hash
from app.db.session import get_db
from app.main import app
from app.models.eworks_sync import EworksQuote
from app.models.user import User
from app.schemas.settings import SettingsCountsRead, SettingsStatusRead
from app.services.manager_dashboard_service import AWAITING_SUPPLIER_TAG, READY_TO_SEND_TAG


@pytest.fixture(autouse=True)
def mock_admin_settings_services():
    with patch("app.api.v1.admin.get_settings_status") as mock_status, patch(
        "app.api.v1.admin.get_safe_settings"
    ) as mock_safe:
        mock_status.return_value = SettingsStatusRead(
            database_reachable=True,
            counts=SettingsCountsRead(
                users=2,
                clients=0,
                trades=0,
                products=3,
                rate_rules=0,
                submitted_sessions=0,
                audit_logs=5,
            ),
        )
        mock_safe.return_value = type(
            "SafeSettings",
            (),
            {"eworks": type("EworksSettings", (), {"api_enabled": True})()},
        )()
        yield mock_status, mock_safe


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in [User.__table__, EworksQuote.__table__]:
        table.create(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    now = datetime.now(timezone.utc)
    admin = User(
        id=uuid.uuid4(),
        email="admin@optimal.example",
        full_name="Admin",
        password_hash=get_password_hash("admin12345"),
        role=UserRole.ADMIN.value,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    manager = User(
        id=uuid.uuid4(),
        email="manager@optimal.example",
        full_name="Manager",
        password_hash=get_password_hash("manager12345"),
        role=UserRole.MANAGER.value,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    session.add_all([admin, manager])
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


def _patch_dev_user(mock_settings, *, role: str):
    email_map = {
        "admin": "admin@optimal.example",
        "manager": "manager@optimal.example",
    }
    mock_settings.auth_provider = "dev"
    mock_settings.dev_auth_enabled = True
    mock_settings.dev_user_id = f"dev-{role}-1"
    mock_settings.dev_user_email = email_map[role]
    mock_settings.dev_user_name = f"{role.title()} User"
    mock_settings.dev_user_role = role
    mock_settings.dev_user_is_active = True
    mock_settings.dev_auth_auto_create_user = False


def _seed_dashboard_quotes(db_session):
    synced = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    db_session.add_all(
        [
            EworksQuote(
                eworks_quote_id=101,
                quote_ref="Q-NEW",
                customer_name="New Co",
                status="1",
                status_name="New",
                quote_date="2026-06-01",
                total=100.0,
                synced_at=synced,
                raw_payload={"secret": "hidden"},
            ),
            EworksQuote(
                eworks_quote_id=102,
                quote_ref="Q-AWAIT",
                customer_name="Await Co",
                status="2",
                tags=[AWAITING_SUPPLIER_TAG],
                quote_date="2026-06-02",
                total=200.0,
                synced_at=synced,
            ),
            EworksQuote(
                eworks_quote_id=103,
                quote_ref="Q-READY",
                customer_name="Ready Co",
                status="2",
                tags=[READY_TO_SEND_TAG],
                quote_date="2026-06-03",
                total=300.0,
                synced_at=synced,
            ),
        ]
    )
    db_session.commit()


@patch("app.auth.dependencies.settings")
def test_admin_can_fetch_admin_dashboard(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    _seed_dashboard_quotes(db_session)

    resp = api_client.get("/api/v1/admin/dashboard")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["categories"]["new_quotes"]["count"] == 1
    assert data["categories"]["awaiting_supplier"]["count"] == 1
    assert data["categories"]["ready_to_send"]["count"] == 1
    assert "admin_stats" in data
    assert "users" in data["admin_stats"]
    assert "eworks_api_enabled" in data["admin_stats"]


@patch("app.auth.dependencies.settings")
def test_manager_cannot_fetch_admin_dashboard(mock_settings, api_client):
    _patch_dev_user(mock_settings, role="manager")
    resp = api_client.get("/api/v1/admin/dashboard")
    assert resp.status_code == 403


@patch("app.auth.dependencies.settings")
def test_admin_dashboard_classification_matches_manager(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    _seed_dashboard_quotes(db_session)

    admin_resp = api_client.get("/api/v1/admin/dashboard")
    assert admin_resp.status_code == 200

    _patch_dev_user(mock_settings, role="manager")
    manager_resp = api_client.get("/api/v1/manager/dashboard")
    assert manager_resp.status_code == 200

    admin_data = admin_resp.json()["data"]
    manager_data = manager_resp.json()["data"]

    for bucket in ("new_quotes", "awaiting_supplier", "ready_to_send"):
        assert admin_data["categories"][bucket]["count"] == manager_data["categories"][bucket]["count"]
        admin_refs = {q["quote_ref"] for q in admin_data["categories"][bucket]["quotes"]}
        manager_refs = {q["quote_ref"] for q in manager_data["categories"][bucket]["quotes"]}
        assert admin_refs == manager_refs


@patch("app.auth.dependencies.settings")
def test_admin_dashboard_does_not_return_raw_payload(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    _seed_dashboard_quotes(db_session)

    resp = api_client.get("/api/v1/admin/dashboard")
    assert resp.status_code == 200
    body_text = resp.text
    assert "raw_payload" not in body_text
    assert "secret" not in body_text

    data = resp.json()["data"]
    for category in data["categories"].values():
        for item in category["quotes"]:
            assert "raw_payload" not in item
