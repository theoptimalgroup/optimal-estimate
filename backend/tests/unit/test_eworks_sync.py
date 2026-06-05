"""Unit tests for eWorks Quote/Job sync — Phase 22."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import UserRole, get_password_hash
from app.db.session import get_db
from app.main import app
from app.models.eworks_sync import EworksJob, EworksQuote, EworksSyncRun
from app.models.support import AuditLog
from app.models.user import User


# ---------------------------------------------------------------------------
# Fixtures: in-memory SQLite DB wired to FastAPI
# ---------------------------------------------------------------------------


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
        EworksQuote.__table__,
        EworksJob.__table__,
        EworksSyncRun.__table__,
    ]:
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
    engineer = User(
        id=uuid.uuid4(),
        email="engineer@optimal.example",
        full_name="Engineer",
        password_hash=get_password_hash("eng12345"),
        role=UserRole.ENGINEER.value,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    session.add_all([admin, manager, engineer])
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
        "engineer": "engineer@optimal.example",
    }
    mock_settings.auth_provider = "dev"
    mock_settings.dev_auth_enabled = True
    mock_settings.dev_user_id = f"dev-{role}-1"
    mock_settings.dev_user_email = email_map[role]
    mock_settings.dev_user_name = f"{role.title()} User"
    mock_settings.dev_user_role = role
    mock_settings.dev_user_is_active = True
    mock_settings.dev_auth_auto_create_user = False


# ---------------------------------------------------------------------------
# Tests: role-based access control
# ---------------------------------------------------------------------------


@patch("app.api.v1.eworks_sync.sync_quotes_from_eworks")
@patch("app.auth.dependencies.settings")
def test_admin_can_trigger_quotes_sync(mock_settings, mock_sync, api_client):
    _patch_dev_user(mock_settings, role="admin")
    run_id = uuid.uuid4()
    mock_sync.return_value = (
        MagicMock(fetched=5, created=2, updated=3, failed=0, model_dump=lambda: {
            "fetched": 5, "created": 2, "updated": 3, "failed": 0
        }),
        MagicMock(id=run_id),
    )
    resp = api_client.post("/api/v1/eworks-sync/quotes", json={})
    assert resp.status_code == 200


@patch("app.api.v1.eworks_sync.sync_jobs_from_eworks")
@patch("app.auth.dependencies.settings")
def test_admin_can_trigger_jobs_sync(mock_settings, mock_sync, api_client):
    _patch_dev_user(mock_settings, role="admin")
    run_id = uuid.uuid4()
    mock_sync.return_value = (
        MagicMock(fetched=10, created=5, updated=5, failed=0, model_dump=lambda: {
            "fetched": 10, "created": 5, "updated": 5, "failed": 0
        }),
        MagicMock(id=run_id),
    )
    resp = api_client.post("/api/v1/eworks-sync/jobs", json={})
    assert resp.status_code == 200


@patch("app.auth.dependencies.settings")
def test_manager_cannot_trigger_quotes_sync(mock_settings, api_client):
    _patch_dev_user(mock_settings, role="manager")
    resp = api_client.post("/api/v1/eworks-sync/quotes", json={})
    assert resp.status_code == 403


@patch("app.auth.dependencies.settings")
def test_engineer_cannot_trigger_jobs_sync(mock_settings, api_client):
    _patch_dev_user(mock_settings, role="engineer")
    resp = api_client.post("/api/v1/eworks-sync/jobs", json={})
    assert resp.status_code == 403


@patch("app.auth.dependencies.settings")
def test_manager_cannot_trigger_all_sync(mock_settings, api_client):
    _patch_dev_user(mock_settings, role="manager")
    resp = api_client.post("/api/v1/eworks-sync/all", json={})
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Tests: sync service upsert logic
# ---------------------------------------------------------------------------


def test_upsert_quotes_creates_new_record(db_session):
    from app.services.eworks_sync_service import _upsert_quotes

    raw = [
        {
            "id": 100,
            "quote_ref": "Q-100",
            "customer": {"id": 1, "customer_name": "ACME Ltd"},
            "quote_status": {"id": "2", "quote_status": "Pending"},
            "quote_date": "2026-01-01",
            "total": "1500.00",
        }
    ]
    summary = _upsert_quotes(db_session, raw)
    assert summary.created == 1
    assert summary.updated == 0
    assert summary.failed == 0
    db_session.commit()
    row = db_session.query(EworksQuote).filter(EworksQuote.eworks_quote_id == 100).one()
    assert row.quote_ref == "Q-100"
    assert row.customer_name == "ACME Ltd"


def test_upsert_quotes_updates_existing_record(db_session):
    from app.services.eworks_sync_service import _upsert_quotes

    db_session.add(EworksQuote(eworks_quote_id=200, quote_ref="Q-200"))
    db_session.commit()

    raw = [{"id": 200, "quote_ref": "Q-200-UPDATED", "total": "2000.00"}]
    summary = _upsert_quotes(db_session, raw)
    assert summary.created == 0
    assert summary.updated == 1
    db_session.commit()
    row = db_session.query(EworksQuote).filter(EworksQuote.eworks_quote_id == 200).one()
    assert row.quote_ref == "Q-200-UPDATED"


def test_upsert_jobs_creates_new_record(db_session):
    from app.services.eworks_sync_service import _upsert_jobs

    raw = [
        {
            "id": 55,
            "job_ref": "J-55",
            "customer": {"id": 1, "customer_name": "Corp X"},
            "quote_id": 100,
            "job_date": "2026-02-01",
        }
    ]
    summary = _upsert_jobs(db_session, raw)
    assert summary.created == 1
    assert summary.failed == 0
    db_session.commit()
    row = db_session.query(EworksJob).filter(EworksJob.eworks_job_id == 55).one()
    assert row.job_ref == "J-55"
    assert row.eworks_quote_id == 100


def test_upsert_skips_record_missing_id(db_session):
    from app.services.eworks_sync_service import _upsert_quotes

    raw = [{"quote_ref": "NO-ID"}]  # no "id" field
    summary = _upsert_quotes(db_session, raw)
    assert summary.failed == 1
    assert summary.created == 0


def test_individual_record_failure_does_not_stop_whole_batch(db_session):
    from app.services.eworks_sync_service import _upsert_quotes

    raw = [
        {"id": 300, "quote_ref": "Q-300"},
        {"quote_ref": "MISSING-ID"},  # will fail
        {"id": 301, "quote_ref": "Q-301"},
    ]
    summary = _upsert_quotes(db_session, raw)
    assert summary.created == 2
    assert summary.failed == 1


def test_pagination_stops_at_last_page():
    """Verify _fetch_all fetches all pages and stops at last_page."""
    responses = [
        {
            "status": 1,
            "collection": {
                "meta": {"total": 2, "last_page": 2, "current_page": 1, "per_page": 1},
                "data": [{"id": 1}],
            },
        },
        {
            "status": 1,
            "collection": {
                "meta": {"total": 2, "last_page": 2, "current_page": 2, "per_page": 1},
                "data": [{"id": 2}],
            },
        },
    ]
    call_count = 0

    def fake_get(url, **kwargs):
        nonlocal call_count
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = responses[call_count]
        call_count += 1
        return resp

    with (
        patch("app.services.eworks_quotes_jobs_api_service.settings") as mock_settings,
        patch("httpx.Client") as mock_client_cls,
    ):
        mock_settings.eworks_api_enabled = True
        mock_settings.eworks_base_url = "http://eworks.local"
        mock_settings.eworks_api_key = "key"
        mock_settings.eworks_api_timeout_seconds = 5

        mock_client_instance = MagicMock()
        mock_client_instance.get.side_effect = fake_get
        mock_client_cls.return_value.__enter__ = lambda s: mock_client_instance
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        from app.services.eworks_quotes_jobs_api_service import fetch_all_quotes
        records = fetch_all_quotes()

    assert len(records) == 2
    assert call_count == 2


# ---------------------------------------------------------------------------
# Tests: status endpoint
# ---------------------------------------------------------------------------


@patch("app.auth.dependencies.settings")
def test_status_endpoint_returns_counts(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    db_session.add(EworksQuote(eworks_quote_id=1, quote_ref="Q-1"))
    db_session.add(EworksJob(eworks_job_id=1, job_ref="J-1"))
    db_session.commit()

    resp = api_client.get("/api/v1/eworks-sync/status")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["quotes_count"] >= 1
    assert data["jobs_count"] >= 1
    assert "eworks_api_enabled" in data


@patch("app.auth.dependencies.settings")
def test_status_endpoint_not_accessible_to_manager(mock_settings, api_client):
    _patch_dev_user(mock_settings, role="manager")
    resp = api_client.get("/api/v1/eworks-sync/status")
    assert resp.status_code == 403


@patch("app.auth.dependencies.settings")
def test_status_endpoint_not_accessible_to_engineer(mock_settings, api_client):
    _patch_dev_user(mock_settings, role="engineer")
    resp = api_client.get("/api/v1/eworks-sync/status")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Tests: list endpoints (admin/manager/estimator)
# ---------------------------------------------------------------------------


@patch("app.auth.dependencies.settings")
def test_admin_can_list_local_quotes(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    db_session.add(EworksQuote(eworks_quote_id=10, quote_ref="Q-10", customer_name="Acme"))
    db_session.commit()
    resp = api_client.get("/api/v1/eworks-sync/quotes")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 1
    # raw_payload must not be in list response
    for item in data["items"]:
        assert "raw_payload" not in item


@patch("app.auth.dependencies.settings")
def test_admin_can_list_local_jobs(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    db_session.add(EworksJob(eworks_job_id=10, job_ref="J-10", customer_name="Acme"))
    db_session.commit()
    resp = api_client.get("/api/v1/eworks-sync/jobs")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 1


@patch("app.auth.dependencies.settings")
def test_engineer_cannot_list_quotes(mock_settings, api_client):
    _patch_dev_user(mock_settings, role="engineer")
    resp = api_client.get("/api/v1/eworks-sync/quotes")
    assert resp.status_code == 403


@patch("app.auth.dependencies.settings")
def test_engineer_cannot_list_jobs(mock_settings, api_client):
    _patch_dev_user(mock_settings, role="engineer")
    resp = api_client.get("/api/v1/eworks-sync/jobs")
    assert resp.status_code == 403


@patch("app.auth.dependencies.settings")
def test_admin_can_get_quote_detail(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    db_session.add(
        EworksQuote(
            eworks_quote_id=999,
            quote_ref="Q-999",
            raw_payload={"id": 999, "some_field": "value"},
        )
    )
    db_session.commit()
    q = db_session.query(EworksQuote).filter(EworksQuote.eworks_quote_id == 999).one()
    resp = api_client.get(f"/api/v1/eworks-sync/quotes/{q.id}")
    assert resp.status_code == 200
    detail = resp.json()["data"]
    # admin can see raw_payload
    assert "raw_payload" in detail
    # but no API key in response
    assert "api_key" not in resp.text
    assert "eworks_api_key" not in resp.text


# ---------------------------------------------------------------------------
# Tests: no secrets in responses
# ---------------------------------------------------------------------------


@patch("app.auth.dependencies.settings")
def test_no_secrets_in_status_response(mock_settings, api_client):
    _patch_dev_user(mock_settings, role="admin")
    resp = api_client.get("/api/v1/eworks-sync/status")
    assert resp.status_code == 200
    body = resp.text
    assert "api_key" not in body
    assert "EWORKS_API_KEY" not in body
    assert "eworks_api_key" not in body


# ---------------------------------------------------------------------------
# Tests: JSON column works with SQLite
# ---------------------------------------------------------------------------


def test_json_payload_stored_and_retrieved(db_session):
    payload = {"id": 42, "items": [1, 2, 3], "nested": {"a": "b"}}
    db_session.add(EworksQuote(eworks_quote_id=42, raw_payload=payload))
    db_session.commit()
    row = db_session.query(EworksQuote).filter(EworksQuote.eworks_quote_id == 42).one()
    assert row.raw_payload == payload


def test_json_job_payload_stored_and_retrieved(db_session):
    payload = {"id": 77, "status": "completed"}
    db_session.add(EworksJob(eworks_job_id=77, raw_payload=payload))
    db_session.commit()
    row = db_session.query(EworksJob).filter(EworksJob.eworks_job_id == 77).one()
    assert row.raw_payload == payload
