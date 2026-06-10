"""Tests for dashboard quote detail refresh and reconcile."""

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
from app.models.eworks_sync import (
    EworksCustomer,
    EworksJob,
    EworksQuote,
    EworksSyncLock,
    EworksSyncRun,
)
from app.models.product import Product
from app.models.user import User


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in [
        User.__table__,
        EworksQuote.__table__,
        EworksJob.__table__,
        EworksCustomer.__table__,
        EworksSyncRun.__table__,
        EworksSyncLock.__table__,
        Product.__table__,
    ]:
        table.create(engine, checkfirst=True)

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
    session.add(admin)
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


def _patch_dev_user(mock_settings, *, role: str = "admin"):
    mock_settings.auth_provider = "dev"
    mock_settings.dev_auth_enabled = True
    mock_settings.dev_user_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    mock_settings.dev_user_email = "admin@optimal.example"
    mock_settings.dev_user_name = "Admin"
    mock_settings.dev_user_role = role
    mock_settings.dev_user_is_active = True
    mock_settings.dev_auth_auto_create_user = False


def _seed_draft_quote(db_session, *, eworks_quote_id: int, quote_ref: str) -> EworksQuote:
    quote = EworksQuote(
        eworks_quote_id=eworks_quote_id,
        quote_ref=quote_ref,
        customer_name="Acme",
        status="Draft",
        quote_date=datetime.now(timezone.utc).date().isoformat(),
        synced_at=datetime.now(timezone.utc),
    )
    db_session.add(quote)
    db_session.commit()
    db_session.refresh(quote)
    return quote


@patch("app.services.eworks_quote_detail_sync_service.fetch_quote_detail")
@patch("app.auth.dependencies.settings")
def test_dashboard_refresh_endpoint_runs_immediately(
    mock_settings, mock_fetch, api_client, db_session, monkeypatch
):
    _patch_dev_user(mock_settings, role="admin")
    monkeypatch.setattr("app.core.config.settings.eworks_api_enabled", True)

    _seed_draft_quote(db_session, eworks_quote_id=501, quote_ref="Q501")
    mock_fetch.return_value = (
        {
            "id": 501,
            "quote_ref": "Q501",
            "quote_status": "Draft",
            "customer_name": "Acme",
        },
        0,
    )

    with patch(
        "app.services.eworks_quote_detail_sync_service.select_dashboard_candidate_quotes"
    ) as mock_select:
        quote = db_session.query(EworksQuote).filter(EworksQuote.eworks_quote_id == 501).one()
        mock_select.return_value = [quote]
        resp = api_client.post("/api/v1/eworks-sync/quotes/dashboard-refresh")

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["quotes_selected"] == 1
    assert data["details_fetched"] == 1
    assert data["quotes_updated"] == 1
    assert data["stopped_reason"] == "completed"
    mock_fetch.assert_called_once_with(501)


@patch("app.auth.dependencies.settings")
def test_status_reports_external_worker_active(mock_settings, api_client, monkeypatch):
    _patch_dev_user(mock_settings, role="admin")
    monkeypatch.setattr("app.core.config.settings.eworks_background_worker_deployed", True)
    monkeypatch.setattr("app.core.config.settings.eworks_background_sync_enabled", False)
    monkeypatch.setattr("app.core.config.settings.run_background_worker", False)

    resp = api_client.get("/api/v1/eworks-sync/status")
    assert resp.status_code == 200
    bg = resp.json()["data"]["background_sync"]
    assert bg["enabled"] is True
    assert bg["worker_enabled"] is True
    assert bg["scheduler_active"] is True
    assert bg["background_worker_deployed"] is True
    assert bg["dashboard_quote_refresh_enabled"] is True
    assert bg["quote_detail_reconcile_enabled"] is True
