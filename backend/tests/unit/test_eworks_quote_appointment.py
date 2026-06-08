"""Unit tests for eWorks quote sales appointment backfill."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.exceptions import AppError
from app.core.security import UserRole, get_password_hash
from app.db.session import get_db
from app.main import app
from app.models.eworks_sync import EworksQuote, EworksQuoteAppointment, EworksSyncLock
from app.models.user import User
from app.services.eworks_quote_appointment_service import (
    backfill_quote_sales_appointments_from_eworks,
)
from app.services.eworks_sync_lock_service import try_acquire_sync_lock


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
        EworksQuoteAppointment.__table__,
        EworksSyncLock.__table__,
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


def _sales_detail_payload(*, quote_id: int = 29227, quote_ref: str = "Q22123") -> dict:
    return {
        "id": quote_id,
        "quote_ref": quote_ref,
        "sales_appointments": [
            {
                "id": 501,
                "user": {"name": "Alice", "email": "alice@example.com"},
                "appointment_type": "Sales Visit",
                "status": "Scheduled",
                "is_sales_appointment": "1",
                "start_date": "2026-06-10",
                "start_time": "09:00",
                "end_date": "2026-06-10",
                "end_time": "10:00",
            }
        ],
    }


def _seed_quote(
    db_session,
    *,
    eworks_quote_id: int,
    quote_ref: str,
    synced_at: datetime | None = None,
) -> EworksQuote:
    quote = EworksQuote(
        eworks_quote_id=eworks_quote_id,
        quote_ref=quote_ref,
        raw_payload={"id": eworks_quote_id, "quote_ref": quote_ref},
        synced_at=synced_at or datetime.now(timezone.utc),
    )
    db_session.add(quote)
    db_session.commit()
    db_session.refresh(quote)
    return quote


@patch("app.services.eworks_quote_appointment_service.fetch_quote_detail")
@patch("app.auth.dependencies.settings")
def test_backfill_endpoint_default_limit_is_50(mock_settings, mock_fetch, api_client, db_session, monkeypatch):
    _patch_dev_user(mock_settings)
    monkeypatch.setattr("app.core.config.settings.eworks_api_enabled", True)
    monkeypatch.setattr("app.core.config.settings.eworks_sync_sales_appointments_enabled", True)

    for idx in range(55):
        _seed_quote(db_session, eworks_quote_id=30000 + idx, quote_ref=f"Q{30000 + idx}")
    mock_fetch.return_value = (_sales_detail_payload(), 0)

    resp = api_client.post("/api/v1/eworks-sync/quotes/backfill-sales-appointments")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["quotes_scanned"] == 50
    assert data["has_more"] is True
    assert data["next_offset"] == 50


@patch("app.services.eworks_quote_appointment_service.fetch_quote_detail")
@patch("app.auth.dependencies.settings")
def test_backfill_quote_ref_processes_one_quote(mock_settings, mock_fetch, api_client, db_session, monkeypatch):
    _patch_dev_user(mock_settings)
    monkeypatch.setattr("app.core.config.settings.eworks_api_enabled", True)
    monkeypatch.setattr("app.core.config.settings.eworks_sync_sales_appointments_enabled", True)

    _seed_quote(db_session, eworks_quote_id=29227, quote_ref="Q22123")
    _seed_quote(db_session, eworks_quote_id=29228, quote_ref="Q22124")
    mock_fetch.return_value = (_sales_detail_payload(), 0)

    resp = api_client.post("/api/v1/eworks-sync/quotes/backfill-sales-appointments?quote_ref=Q22123")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["quotes_scanned"] == 1
    assert data["sales_appointments_found"] == 1
    assert mock_fetch.call_count == 1
    assert mock_fetch.call_args.args[0] == 29227


@patch("app.services.eworks_quote_appointment_service.time.monotonic")
@patch("app.services.eworks_quote_appointment_service.fetch_quote_detail")
def test_backfill_timeout_stops_early(mock_fetch, mock_monotonic, db_session, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.eworks_sync_sales_appointments_enabled", True)

    for idx in range(5):
        _seed_quote(db_session, eworks_quote_id=31000 + idx, quote_ref=f"Q{31000 + idx}")
    mock_fetch.return_value = (_sales_detail_payload(), 0)

    call_count = {"n": 0}

    def fake_monotonic() -> float:
        call_count["n"] += 1
        return 0.0 if call_count["n"] <= 3 else 100.0

    mock_monotonic.side_effect = fake_monotonic

    summary = backfill_quote_sales_appointments_from_eworks(
        db_session,
        limit=5,
        timeout_seconds=60,
    )

    assert summary.stopped_reason == "timeout"
    assert summary.quotes_scanned < 5
    assert summary.has_more is True


@patch("app.services.eworks_quote_appointment_service.fetch_quote_detail")
@patch("app.auth.dependencies.settings")
def test_backfill_429_increments_rate_limited_count(mock_settings, mock_fetch, api_client, db_session, monkeypatch):
    _patch_dev_user(mock_settings)
    monkeypatch.setattr("app.core.config.settings.eworks_api_enabled", True)
    monkeypatch.setattr("app.core.config.settings.eworks_sync_sales_appointments_enabled", True)

    _seed_quote(db_session, eworks_quote_id=29227, quote_ref="Q22123")
    mock_fetch.side_effect = [
        (_sales_detail_payload(), 2),
        AppError("EWORKS_RATE_LIMITED", "rate limited", 429),
    ]
    _seed_quote(db_session, eworks_quote_id=29228, quote_ref="Q22124")

    resp = api_client.post("/api/v1/eworks-sync/quotes/backfill-sales-appointments?limit=2")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["rate_limited_count"] >= 2
    assert data["failed"] == 1


@patch("app.services.eworks_quotes_jobs_api_service.fetch_quote_attachments")
@patch("app.services.eworks_quote_appointment_service.fetch_quote_detail")
@patch("app.auth.dependencies.settings")
def test_backfill_does_not_call_attachments(
    mock_settings, mock_fetch, mock_attachments, api_client, db_session, monkeypatch
):
    _patch_dev_user(mock_settings)
    monkeypatch.setattr("app.core.config.settings.eworks_api_enabled", True)
    monkeypatch.setattr("app.core.config.settings.eworks_sync_sales_appointments_enabled", True)

    _seed_quote(db_session, eworks_quote_id=29227, quote_ref="Q22123")
    mock_fetch.return_value = (_sales_detail_payload(), 0)

    resp = api_client.post("/api/v1/eworks-sync/quotes/backfill-sales-appointments?quote_ref=Q22123")
    assert resp.status_code == 200
    mock_attachments.assert_not_called()


@patch("app.services.eworks_quote_appointment_service.fetch_quote_detail")
@patch("app.auth.dependencies.settings")
def test_backfill_lock_prevents_concurrent_run(mock_settings, mock_fetch, api_client, db_session, monkeypatch):
    _patch_dev_user(mock_settings)
    monkeypatch.setattr("app.core.config.settings.eworks_api_enabled", True)
    monkeypatch.setattr("app.core.config.settings.eworks_sync_sales_appointments_enabled", True)

    assert try_acquire_sync_lock(db_session, "quote_sales_appointments", locked_by="other-worker") is not None

    resp = api_client.post("/api/v1/eworks-sync/quotes/backfill-sales-appointments?quote_ref=Q22123")
    assert resp.status_code == 409
    assert "already running" in resp.json()["detail"].lower()
    mock_fetch.assert_not_called()


@patch("app.services.eworks_quote_appointment_service.fetch_quote_detail")
@patch("app.auth.dependencies.settings")
def test_backfill_response_includes_pagination_fields(mock_settings, mock_fetch, api_client, db_session, monkeypatch):
    _patch_dev_user(mock_settings)
    monkeypatch.setattr("app.core.config.settings.eworks_api_enabled", True)
    monkeypatch.setattr("app.core.config.settings.eworks_sync_sales_appointments_enabled", True)

    _seed_quote(db_session, eworks_quote_id=29227, quote_ref="Q22123")
    mock_fetch.return_value = (_sales_detail_payload(), 0)

    resp = api_client.post("/api/v1/eworks-sync/quotes/backfill-sales-appointments?limit=50&offset=0")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "next_offset" in data
    assert "has_more" in data
    assert data["next_offset"] == 1
    assert data["has_more"] is False


@patch("app.services.eworks_quote_appointment_service.fetch_quote_detail")
def test_backfill_service_creates_rows(mock_fetch, db_session, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.eworks_sync_sales_appointments_enabled", True)
    _seed_quote(db_session, eworks_quote_id=29227, quote_ref="Q22123")
    mock_fetch.return_value = (_sales_detail_payload(), 0)

    summary = backfill_quote_sales_appointments_from_eworks(
        db_session,
        quote_ref="Q22123",
        limit=1,
    )

    assert summary.quotes_scanned == 1
    assert summary.sales_appointments_found == 1
    assert summary.appointments_created == 1
    assert db_session.query(EworksQuoteAppointment).count() == 1
