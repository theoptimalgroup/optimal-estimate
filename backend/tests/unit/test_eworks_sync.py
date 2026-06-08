"""Unit tests for eWorks Quote/Job sync — Phase 22."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import UserRole, get_password_hash
from app.db.session import get_db
from app.main import app
from app.models.calculation_session import CalculationSession
from app.models.eworks_sync import EworksAttachment, EworksCustomer, EworksJob, EworksJobAppointment, EworksQuote, EworksSyncLock, EworksSyncRun
from app.models.product import Product
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
        EworksJobAppointment.__table__,
        EworksCustomer.__table__,
        EworksAttachment.__table__,
        EworksSyncRun.__table__,
        EworksSyncLock.__table__,
        CalculationSession.__table__,
        Product.__table__,
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


@patch("app.api.v1.eworks_sync.schedule_eworks_sync")
@patch("app.auth.dependencies.settings")
def test_admin_can_trigger_quotes_sync(mock_settings, mock_schedule, api_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    run = EworksSyncRun(
        id=uuid.uuid4(),
        sync_type="quotes",
        status="running",
    )
    mock_schedule.return_value = run
    resp = api_client.post("/api/v1/eworks-sync/quotes", json={})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "running"
    assert data["run_id"] == str(run.id)


@patch("app.api.v1.eworks_sync.schedule_eworks_sync")
@patch("app.auth.dependencies.settings")
def test_admin_can_trigger_jobs_sync(mock_settings, mock_schedule, api_client):
    _patch_dev_user(mock_settings, role="admin")
    run = EworksSyncRun(id=uuid.uuid4(), sync_type="jobs", status="running")
    mock_schedule.return_value = run
    resp = api_client.post("/api/v1/eworks-sync/jobs", json={})
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "running"


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


def test_resolve_sync_filters_defaults_to_last_seven_days():
    from datetime import date, timedelta

    from app.services.eworks_sync_service import SYNC_DEFAULT_DAYS, resolve_sync_filters

    filters = resolve_sync_filters({}, full=False)
    today = date.today()
    expected_from = (today - timedelta(days=SYNC_DEFAULT_DAYS)).isoformat()
    assert filters["date_from"] == expected_from
    assert filters["date_to"] == today.isoformat()


def test_resolve_sync_filters_full_sync_skips_date_window():
    from app.services.eworks_sync_service import resolve_sync_filters

    filters = resolve_sync_filters({}, full=True)
    assert "date_from" not in filters
    assert "date_to" not in filters


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


def test_upsert_jobs_syncs_appointments_from_raw_payload(db_session):
    from app.models.eworks_sync import EworksJobAppointment
    from app.services.eworks_sync_service import _upsert_jobs

    raw = [
        {
            "id": 56,
            "job_ref": "J-56",
            "appointments": [
                {
                    "id": 8801,
                    "user": {"name": "Alex Alves", "email": "alex@example.com"},
                    "appointment_type": "1 Hour Job",
                    "status": "Scheduled",
                    "start_date": "2026-06-10",
                    "start_time": "11:00",
                    "end_date": "2026-06-10",
                    "end_time": "12:00",
                }
            ],
        }
    ]
    summary = _upsert_jobs(db_session, raw)
    assert summary.created == 1
    db_session.commit()
    row = db_session.query(EworksJob).filter(EworksJob.eworks_job_id == 56).one()
    assert row.assigned_user_name == "Alex Alves"
    assert row.assigned_user_email == "alex@example.com"
    appointments = (
        db_session.query(EworksJobAppointment)
        .filter(EworksJobAppointment.eworks_job_id == 56)
        .all()
    )
    assert len(appointments) == 1
    assert appointments[0].status == "Scheduled"


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
    db_session.add(
        Product(
            eworks_item_id=1403,
            product_name="Plant Room",
            product_code="PR-0011",
            category="Plumber",
            type_="Products",
            is_active=True,
        )
    )
    db_session.commit()

    resp = api_client.get("/api/v1/eworks-sync/status")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["quotes_count"] >= 1
    assert data["jobs_count"] >= 1
    assert data["products_count"] >= 1
    assert "customers_count" in data
    assert "products_count" in data
    assert "last_customers_sync" in data
    assert "last_products_sync" in data
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
def test_manager_can_list_local_quotes(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    db_session.add(EworksQuote(eworks_quote_id=11, quote_ref="Q-11", customer_name="Beta Corp"))
    db_session.commit()
    resp = api_client.get("/api/v1/eworks-sync/quotes")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 1
    for item in data["items"]:
        assert "raw_payload" not in item


@patch("app.auth.dependencies.settings")
def test_quote_list_uses_raw_payload_customer_fallback(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    db_session.add(
        EworksQuote(
            eworks_quote_id=801,
            quote_ref="Q-801",
            raw_payload={
                "customer": {"full_name": "Payload Customer Ltd"},
                "session_token": "must-not-leak",
            },
        )
    )
    db_session.commit()
    resp = api_client.get("/api/v1/eworks-sync/quotes?search=Q-801")
    assert resp.status_code == 200
    item = resp.json()["data"]["items"][0]
    assert item["customer_name"] == "Payload Customer Ltd"
    assert item["display_customer_name"] == "Payload Customer Ltd"
    assert "raw_payload" not in item
    assert "session_token" not in resp.text


@patch("app.auth.dependencies.settings")
def test_quote_list_uses_raw_payload_status_fallback(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    db_session.add(
        EworksQuote(
            eworks_quote_id=802,
            quote_ref="Q-802",
            raw_payload={"Status_Name": "Awaiting Approval"},
        )
    )
    db_session.commit()
    resp = api_client.get("/api/v1/eworks-sync/quotes?search=Q-802")
    item = resp.json()["data"]["items"][0]
    assert item["status_name"] == "Awaiting Approval"
    assert item["display_status"] == "Awaiting Approval"


@patch("app.auth.dependencies.settings")
def test_quote_list_maps_status_id_one_to_new_quote(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    db_session.add(
        EworksQuote(
            eworks_quote_id=803,
            quote_ref="Q-803",
            status="1",
            raw_payload={"status": "1"},
        )
    )
    db_session.commit()
    resp = api_client.get("/api/v1/eworks-sync/quotes?search=Q-803")
    item = resp.json()["data"]["items"][0]
    assert item["status_name"] == "New Quote"
    assert item["display_status"] == "New Quote"


@patch("app.auth.dependencies.settings")
def test_quote_list_uses_raw_payload_tags_fallback(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    db_session.add(
        EworksQuote(
            eworks_quote_id=804,
            quote_ref="Q-804",
            raw_payload={"tag_names": ["electrical", "urgent"]},
        )
    )
    db_session.commit()
    resp = api_client.get("/api/v1/eworks-sync/quotes?search=Q-804")
    item = resp.json()["data"]["items"][0]
    assert item["tags"] == ["electrical", "urgent"]
    assert item["display_tags"] == ["electrical", "urgent"]


@patch("app.auth.dependencies.settings")
def test_quote_list_uses_raw_payload_total_fallback(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    db_session.add(
        EworksQuote(
            eworks_quote_id=805,
            quote_ref="Q-805",
            raw_payload={"grand_total": 2500.5},
        )
    )
    db_session.commit()
    resp = api_client.get("/api/v1/eworks-sync/quotes?search=Q-805")
    item = resp.json()["data"]["items"][0]
    assert item["total"] == 2500.5
    assert item["display_total"] == 2500.5


@patch("app.auth.dependencies.settings")
def test_quote_list_uses_raw_payload_quote_date_fallback(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    db_session.add(
        EworksQuote(
            eworks_quote_id=806,
            quote_ref="Q-806",
            raw_payload={"Quote_Date": "2026-03-15"},
        )
    )
    db_session.commit()
    resp = api_client.get("/api/v1/eworks-sync/quotes?search=Q-806")
    item = resp.json()["data"]["items"][0]
    assert item["quote_date"] == "2026-03-15"
    assert item["display_quote_date"] == "2026-03-15"


@patch("app.auth.dependencies.settings")
def test_manager_can_list_local_jobs(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    db_session.add(EworksJob(eworks_job_id=11, job_ref="J-11", customer_name="Beta Corp"))
    db_session.commit()
    resp = api_client.get("/api/v1/eworks-sync/jobs")
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] >= 1


@patch("app.auth.dependencies.settings")
def test_manager_can_get_quote_safe_detail(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    db_session.add(
        EworksQuote(
            eworks_quote_id=501,
            quote_ref="Q-501",
            customer_name="Safe Co",
            customer_notes="Please call before visit",
            raw_payload={"id": 501, "secret": "hidden"},
        )
    )
    db_session.commit()
    q = db_session.query(EworksQuote).filter(EworksQuote.eworks_quote_id == 501).one()
    resp = api_client.get(f"/api/v1/eworks-sync/quotes/{q.id}/safe")
    assert resp.status_code == 200
    detail = resp.json()["data"]
    assert detail["identity"]["quote_ref"] == "Q-501"
    assert detail["quote_details"]["customer_notes"] == "Please call before visit"
    assert "raw_payload" not in detail
    assert "secret" not in resp.text


@patch("app.auth.dependencies.settings")
def test_manager_can_get_job_safe_detail(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    db_session.add(
        EworksJob(
            eworks_job_id=601,
            job_ref="J-601",
            notes="Site access via rear gate",
            raw_payload={"id": 601, "api_key": "must-not-leak"},
        )
    )
    db_session.commit()
    j = db_session.query(EworksJob).filter(EworksJob.eworks_job_id == 601).one()
    resp = api_client.get(f"/api/v1/eworks-sync/jobs/{j.id}/safe")
    assert resp.status_code == 200
    detail = resp.json()["data"]
    assert detail["identity"]["job_ref"] == "J-601"
    assert detail["job_details"]["notes"] == "Site access via rear gate"
    assert "raw_payload" not in detail
    assert "api_key" not in resp.text


@patch("app.auth.dependencies.settings")
def test_manager_cannot_get_quote_raw_detail(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    db_session.add(EworksQuote(eworks_quote_id=502, quote_ref="Q-502", raw_payload={"id": 502}))
    db_session.commit()
    q = db_session.query(EworksQuote).filter(EworksQuote.eworks_quote_id == 502).one()
    resp = api_client.get(f"/api/v1/eworks-sync/quotes/{q.id}")
    assert resp.status_code == 403


@patch("app.auth.dependencies.settings")
def test_manager_cannot_get_job_raw_detail(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    db_session.add(EworksJob(eworks_job_id=602, job_ref="J-602", raw_payload={"id": 602}))
    db_session.commit()
    j = db_session.query(EworksJob).filter(EworksJob.eworks_job_id == 602).one()
    resp = api_client.get(f"/api/v1/eworks-sync/jobs/{j.id}")
    assert resp.status_code == 403


@patch("app.auth.dependencies.settings")
def test_quote_search_filters_by_ref_customer_status(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    db_session.add_all(
        [
            EworksQuote(
                eworks_quote_id=701,
                quote_ref="FIND-ME",
                customer_name="Target Customer",
                status="3",
                status_name="Approved",
            ),
            EworksQuote(
                eworks_quote_id=702,
                quote_ref="OTHER",
                customer_name="Someone Else",
                status="1",
                status_name="Draft",
            ),
        ]
    )
    db_session.commit()

    by_ref = api_client.get("/api/v1/eworks-sync/quotes", params={"search": "FIND-ME"})
    assert by_ref.status_code == 200
    assert by_ref.json()["data"]["total"] == 1

    by_customer = api_client.get("/api/v1/eworks-sync/quotes", params={"customer_name": "Target"})
    assert by_customer.status_code == 200
    assert by_customer.json()["data"]["total"] == 1

    by_status = api_client.get("/api/v1/eworks-sync/quotes", params={"status": "Approved"})
    assert by_status.status_code == 200
    assert by_status.json()["data"]["total"] == 1


@patch("app.auth.dependencies.settings")
def test_job_search_filters_by_ref_customer_status(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    db_session.add_all(
        [
            EworksJob(
                eworks_job_id=801,
                job_ref="JOB-FIND",
                customer_name="Target Customer",
                status="2",
                status_name="In Progress",
            ),
            EworksJob(
                eworks_job_id=802,
                job_ref="JOB-OTHER",
                customer_name="Someone Else",
                status="9",
                status_name="Complete",
            ),
        ]
    )
    db_session.commit()

    by_ref = api_client.get("/api/v1/eworks-sync/jobs", params={"search": "JOB-FIND"})
    assert by_ref.status_code == 200
    assert by_ref.json()["data"]["total"] == 1

    by_customer = api_client.get("/api/v1/eworks-sync/jobs", params={"customer_name": "Target"})
    assert by_customer.status_code == 200
    assert by_customer.json()["data"]["total"] == 1

    by_status = api_client.get("/api/v1/eworks-sync/jobs", params={"status": "Progress"})
    assert by_status.status_code == 200
    assert by_status.json()["data"]["total"] == 1


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
def test_admin_can_get_sync_run_detail(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    run = EworksSyncRun(
        id=uuid.uuid4(),
        sync_type="quotes",
        status="success",
        fetched_count=10,
        created_count=5,
        updated_count=5,
        failed_count=0,
        metadata_={"summary": {"fetched": 10, "created": 5, "updated": 5, "failed": 0}},
    )
    db_session.add(run)
    db_session.commit()

    resp = api_client.get(f"/api/v1/eworks-sync/runs/{run.id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "success"
    assert data["metadata"]["summary"]["fetched"] == 10


@patch("app.auth.dependencies.settings")
def test_cannot_start_second_sync_while_running(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    db_session.add(
        EworksSyncRun(
            id=uuid.uuid4(),
            sync_type="quotes",
            status="running",
            started_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()

    resp = api_client.post("/api/v1/eworks-sync/jobs", json={})
    assert resp.status_code == 409


@patch("app.auth.dependencies.settings")
def test_status_includes_active_sync(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    run_id = uuid.uuid4()
    db_session.add(
        EworksSyncRun(
            id=run_id,
            sync_type="all",
            status="running",
            started_at=datetime.now(timezone.utc),
            metadata_={"phase": "quotes"},
        )
    )
    db_session.commit()

    resp = api_client.get("/api/v1/eworks-sync/status")
    assert resp.status_code == 200
    active = resp.json()["data"]["active_sync"]
    assert active["run_id"] == str(run_id)
    assert active["sync_type"] == "all"
    assert active["phase"] == "quotes"


def test_sync_all_uses_single_run(db_session):
    from app.services.eworks_sync_service import sync_all_eworks

    with (
        patch("app.services.eworks_sync_service.fetch_all_customers", return_value=[]),
        patch("app.services.eworks_sync_service.fetch_all_quotes", return_value=[{"id": 1, "quote_ref": "Q-1"}]),
        patch("app.services.eworks_sync_service.fetch_all_jobs", return_value=[{"id": 2, "job_ref": "J-2"}]),
    ):
        result = sync_all_eworks(db_session)

    assert result.customers.fetched == 0
    assert result.quotes.fetched == 1
    assert result.jobs.fetched == 1
    runs = db_session.query(EworksSyncRun).all()
    assert len(runs) == 1
    assert runs[0].sync_type == "all"
    assert runs[0].status == "success"


def test_update_sync_run_progress_persists_counts(db_session):
    from app.services.eworks_sync_run_state import update_sync_run_progress

    run = EworksSyncRun(id=uuid.uuid4(), sync_type="quotes", status="running")
    db_session.add(run)
    db_session.commit()

    update_sync_run_progress(
        db_session,
        run,
        phase="upserting",
        fetched=250,
        created=0,
        updated=250,
        failed=0,
    )

    db_session.refresh(run)
    assert run.fetched_count == 250
    assert run.updated_count == 250
    assert run.metadata_["phase"] == "upserting"


def test_recover_stale_sync_runs_on_startup(db_session):
    from app.services.eworks_sync_run_state import (
        STALE_SYNC_TIMEOUT_MESSAGE,
        clear_stale_running_sync_locks,
        is_running_lock_stale,
    )

    stale_started = datetime.now(timezone.utc) - timedelta(minutes=45)
    run = EworksSyncRun(
        id=uuid.uuid4(),
        sync_type="quotes",
        status="running",
        started_at=stale_started,
    )
    db_session.add(run)
    db_session.commit()

    assert is_running_lock_stale(run) is True
    cleared = clear_stale_running_sync_locks(db_session)
    assert cleared == 1
    db_session.refresh(run)
    assert run.status == "failed"
    assert run.finished_at is not None
    assert run.error_message == STALE_SYNC_TIMEOUT_MESSAGE


def test_clear_stale_running_lock_preserves_recent_run(db_session):
    from app.services.eworks_sync_run_state import clear_stale_running_sync_locks

    run = EworksSyncRun(
        id=uuid.uuid4(),
        sync_type="quotes",
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(run)
    db_session.commit()

    cleared = clear_stale_running_sync_locks(db_session)
    assert cleared == 0
    db_session.refresh(run)
    assert run.status == "running"
    assert run.finished_at is None


@patch("app.services.eworks_sync_runner.threading.Thread")
@patch("app.auth.dependencies.settings")
def test_stale_running_lock_cleared_before_new_sync(mock_settings, mock_thread, api_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    mock_thread.return_value.start = lambda: None

    stale_started = datetime.now(timezone.utc) - timedelta(minutes=45)
    db_session.add(
        EworksSyncRun(
            id=uuid.uuid4(),
            sync_type="quotes",
            status="running",
            started_at=stale_started,
        )
    )
    db_session.commit()

    resp = api_client.post("/api/v1/eworks-sync/jobs", json={})

    assert resp.status_code == 200
    stale = db_session.query(EworksSyncRun).filter(EworksSyncRun.sync_type == "quotes").one()
    assert stale.status == "failed"
    assert stale.finished_at is not None
    assert stale.error_message == "Marked failed automatically after stale sync timeout"


@patch("app.auth.dependencies.settings")
def test_admin_can_cancel_running_sync(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    run_id = uuid.uuid4()
    db_session.add(EworksSyncRun(id=run_id, sync_type="quotes", status="running"))
    db_session.commit()

    resp = api_client.post(f"/api/v1/eworks-sync/runs/{run_id}/cancel")
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "failed"


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


# ---------------------------------------------------------------------------
# Tests: status and tag extraction
# ---------------------------------------------------------------------------


def test_quote_sync_extracts_status_and_status_name():
    from app.services.eworks_sync_service import _extract_quote_fields

    fields = _extract_quote_fields(
        {
            "id": 100,
            "quote_ref": "Q-100",
            "quote_status": {"id": 3, "quote_status": "Approved"},
        }
    )
    assert fields["status"] == "3"
    assert fields["status_name"] == "Approved"


def test_job_sync_extracts_status_and_status_name():
    from app.services.eworks_sync_service import _extract_job_fields

    fields = _extract_job_fields(
        {
            "id": 200,
            "job_ref": "J-200",
            "job_status": {"id": 2, "job_status": "In Progress"},
        }
    )
    assert fields["status"] == "2"
    assert fields["status_name"] == "In Progress"


def test_quote_sync_extracts_tags_from_multiple_formats():
    from app.services.eworks_sync_service import _extract_quote_fields

    fields = _extract_quote_fields(
        {
            "id": 101,
            "tags": ["urgent", "vip"],
            "labels": "Electrical, Rewire",
            "custom_fields": [
                {"name": "Project Tags", "value": [{"label": "Commercial"}]},
            ],
        }
    )
    assert fields["tags"] == ["urgent", "vip", "Electrical", "Rewire", "Commercial"]
    assert fields["raw_payload"]["tags"] == ["urgent", "vip"]


def test_extract_customer_name_from_raw_customer_name():
    from app.services.eworks_sync_service import extract_customer_name_from_raw

    assert extract_customer_name_from_raw({"customer_name": "Top Level Co"}) == "Top Level Co"


def test_extract_customer_name_from_raw_customer_full_name():
    from app.services.eworks_sync_service import extract_customer_name_from_raw

    assert (
        extract_customer_name_from_raw({"customer": {"id": 9, "full_name": "Nested Full Name Ltd"}})
        == "Nested Full Name Ltd"
    )


def test_extract_customer_name_from_raw_customer_customer_name():
    from app.services.eworks_sync_service import extract_customer_name_from_raw

    assert (
        extract_customer_name_from_raw({"customer": {"customer_name": "Nested Customer Ltd"}})
        == "Nested Customer Ltd"
    )


def test_extract_customer_name_from_raw_client_name():
    from app.services.eworks_sync_service import extract_customer_name_from_raw

    assert (
        extract_customer_name_from_raw(
            {
                "customer_id": 12,
                "client_name": "Lambert Chartered Surveyors",
                "site": {"address_1": "10 High Street", "city": "London"},
            }
        )
        == "Lambert Chartered Surveyors"
    )


def test_extract_customer_name_from_raw_site_client_name():
    from app.services.eworks_sync_service import extract_customer_name_from_raw

    assert (
        extract_customer_name_from_raw(
            {
                "customer_id": 15,
                "site": {"client_name": "Site Client Ltd", "address_1": "1 Nile Street"},
            }
        )
        == "Site Client Ltd"
    )


def test_extract_customer_name_null_when_only_customer_id():
    from app.services.eworks_sync_service import extract_customer_name_from_raw

    assert extract_customer_name_from_raw({"customer_id": 99, "customer": {"id": 99}}) is None


def test_quote_sync_extracts_customer_name_from_raw_payload():
    from app.services.eworks_sync_service import _extract_quote_fields

    fields = _extract_quote_fields(
        {
            "id": 22104,
            "quote_ref": "Q22104",
            "client_name": "Linked Co",
            "customer": {"id": 44},
            "site": {"address_1": "The Factory", "city": "London"},
        }
    )
    assert fields["customer_name"] == "Linked Co"
    assert fields["customer_id"] == 44


Q22114_STYLE_PAYLOAD = {
    "id": "29218",
    "quote_ref": "Q22114",
    "customer_id": "20",
    "customer_contact_id": "506",
    "customer_site_id": "0",
    "customer_ref": "IS22497543",
    "site": {
        "city": "London",
        "postcode": "W6 8NX",
        "company_name": "",
        "full_name": "",
    },
    "billing": {
        "full_name": "Patrycja Gimenez",
        "email_address": "p.gimenez@portico.com",
    },
    "delivery": {"company_name": ""},
}


def test_extract_customer_id_from_top_level_when_no_nested_customer():
    from app.services.eworks_sync_service import extract_customer_id_from_raw

    assert extract_customer_id_from_raw(Q22114_STYLE_PAYLOAD) == 20
    assert extract_customer_id_from_raw({"customer": {}, "customer_id": "20"}) == 20


def test_extract_quote_fields_q22114_style_payload():
    from app.services.eworks_sync_service import _extract_quote_fields

    fields = _extract_quote_fields(Q22114_STYLE_PAYLOAD)
    assert fields["eworks_quote_id"] == 29218
    assert fields["quote_ref"] == "Q22114"
    assert fields["customer_id"] == 20
    assert fields["customer_contact_id"] == 506
    assert fields["customer_site_id"] is None
    assert fields["customer_name"] is None


def test_q22114_customer_name_enriched_from_synced_customers(db_session):
    from app.models.eworks_sync import EworksCustomer, EworksQuote
    from app.services.eworks_sync_service import (
        _extract_quote_fields,
        backfill_existing_quotes_customer_fields,
        enrich_customer_name_on_fields,
    )

    db_session.add(
        EworksCustomer(
            eworks_customer_id=20,
            customer_name="Portico Grace Conlon",
            raw_payload={"id": 20},
        )
    )
    db_session.add(
        EworksQuote(
            eworks_quote_id=29218,
            quote_ref="Q22114",
            customer_id=None,
            customer_name=None,
            raw_payload=Q22114_STYLE_PAYLOAD,
        )
    )
    db_session.commit()

    updated = backfill_existing_quotes_customer_fields(db_session)
    db_session.commit()

    quote = db_session.query(EworksQuote).filter(EworksQuote.quote_ref == "Q22114").one()
    assert updated == 1
    assert quote.customer_id == 20
    assert quote.customer_name == "Portico Grace Conlon"
    assert quote.customer_contact_id == 506
    assert quote.customer_site_id is None

    fields = _extract_quote_fields(Q22114_STYLE_PAYLOAD)
    enrich_customer_name_on_fields(db_session, fields)
    assert fields["customer_name"] == "Portico Grace Conlon"


def test_log_unresolved_quote_customer_logs_payload_keys(caplog):
    import logging

    from app.services.eworks_sync_service import log_unresolved_quote_customer

    with caplog.at_level(logging.DEBUG):
        log_unresolved_quote_customer(
            {"id": 1, "quote_ref": "Q-UNRES", "site": {"address": "1 Main St"}},
            {"quote_ref": "Q-UNRES", "eworks_quote_id": 1, "customer_id": None, "customer_name": None},
        )

    assert "Q-UNRES" in caplog.text
    assert "payload_keys" in caplog.text
    assert "raw_payload" not in caplog.text.lower() or "payload_keys" in caplog.text


@patch("app.auth.dependencies.settings")
def test_manager_list_shows_display_customer_from_raw_payload_fallback(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    db_session.add(
        EworksQuote(
            eworks_quote_id=807,
            quote_ref="Q-807",
            raw_payload={
                "client_name": "Payload Client Ltd",
                "customer": {"id": 3},
                "site": {"address_1": "1 Main St"},
            },
        )
    )
    db_session.commit()
    resp = api_client.get("/api/v1/eworks-sync/quotes?search=Q-807")
    item = resp.json()["data"]["items"][0]
    assert item["display_customer_name"] == "Payload Client Ltd"
    assert item["customer_name"] == "Payload Client Ltd"
    assert "raw_payload" not in item


@patch("app.auth.dependencies.settings")
def test_manager_quote_safe_detail_uses_raw_payload_customer_fallback(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    db_session.add(
        EworksQuote(
            eworks_quote_id=808,
            quote_ref="Q-808",
            raw_payload={
                "customer": {"full_name": "Detail Fallback Ltd"},
                "site": {"address_1": "2 High Street"},
            },
        )
    )
    db_session.commit()
    q = db_session.query(EworksQuote).filter(EworksQuote.eworks_quote_id == 808).one()
    resp = api_client.get(f"/api/v1/eworks-sync/quotes/{q.id}/safe")
    assert resp.status_code == 200
    assert resp.json()["data"]["customer"]["customer_name"] == "Detail Fallback Ltd"
    assert "raw_payload" not in resp.json()["data"]


def test_job_sync_extracts_tags():
    from app.services.eworks_sync_service import _extract_job_fields

    fields = _extract_job_fields(
        {
            "id": 201,
            "tag": "maintenance, after-hours",
            "categories": [{"name": "Priority"}],
        }
    )
    assert fields["tags"] == ["maintenance", "after-hours", "Priority"]


def test_normalize_tags_returns_empty_list_when_missing():
    from app.services.eworks_sync_service import _normalize_tags

    assert _normalize_tags(None) == []
    assert _normalize_tags("") == []
    assert _normalize_tags([]) == []


@patch("app.auth.dependencies.settings")
def test_tag_filter_works_for_quotes(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    db_session.add_all(
        [
            EworksQuote(eworks_quote_id=901, quote_ref="Q-901", tags=["urgent", "vip"]),
            EworksQuote(eworks_quote_id=902, quote_ref="Q-902", tags=["standard"]),
        ]
    )
    db_session.commit()

    resp = api_client.get("/api/v1/eworks-sync/quotes", params={"tag": "urgent"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["quote_ref"] == "Q-901"
    assert data["items"][0]["tags"] == ["urgent", "vip"]


@patch("app.auth.dependencies.settings")
def test_tag_filter_matches_comma_separated_ready_to_send_tags(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    db_session.add_all(
        [
            EworksQuote(
                eworks_quote_id=905,
                quote_ref="Q-905",
                tags="Quote Ready to Send (Quotes),To Send With Invoice (QUOTES),URGENT,",
            ),
            EworksQuote(eworks_quote_id=906, quote_ref="Q-906", tags=["URGENT"]),
        ]
    )
    db_session.commit()

    resp = api_client.get(
        "/api/v1/eworks-sync/quotes",
        params={"tag": "Quotes Ready to send (Quotes)"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["quote_ref"] == "Q-905"
    assert "Quote Ready to Send (Quotes)" in data["items"][0]["tags"]


@patch("app.auth.dependencies.settings")
def test_tag_filter_works_for_jobs(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    db_session.add_all(
        [
            EworksJob(eworks_job_id=901, job_ref="J-901", tags=["urgent"]),
            EworksJob(eworks_job_id=902, job_ref="J-902", tags=["maintenance"]),
        ]
    )
    db_session.commit()

    resp = api_client.get("/api/v1/eworks-sync/jobs", params={"tag": "maintenance"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["job_ref"] == "J-902"
    assert data["items"][0]["tags"] == ["maintenance"]


@patch("app.auth.dependencies.settings")
def test_manager_list_includes_tags_but_not_raw_payload(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    db_session.add(
        EworksQuote(
            eworks_quote_id=903,
            quote_ref="Q-903",
            tags=["urgent"],
            raw_payload={"id": 903, "tags": ["urgent"], "secret": "hidden"},
        )
    )
    db_session.commit()

    resp = api_client.get("/api/v1/eworks-sync/quotes")
    assert resp.status_code == 200
    item = resp.json()["data"]["items"][0]
    assert item["tags"] == ["urgent"]
    assert "raw_payload" not in item
    assert "secret" not in resp.text


# ---------------------------------------------------------------------------
# Tests: grouped safe detail extraction
# ---------------------------------------------------------------------------


@patch("app.auth.dependencies.settings")
def test_safe_quote_detail_extracts_grouped_fields(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    db_session.add(
        EworksQuote(
            eworks_quote_id=1001,
            quote_ref="Q-1001",
            customer_name="Acme",
            status="2",
            status_name="Pending",
            quote_date="2026-01-15",
            expiry_date="2026-04-15",
            subtotal=1000,
            vat=200,
            total=1200,
            tags=["urgent"],
            raw_payload={
                "id": 1001,
                "preferred_date": "2026-01-20",
                "preferred_time": "09:00",
                "currency": "GBP",
                "quote_items": [
                    {
                        "name": "Panel install",
                        "description": "Main board",
                        "quantity": 1,
                        "unit_price": 1000,
                        "total": 1000,
                    }
                ],
                "custom_fields": [
                    {"label": "Access Code", "field_key": "access_code", "value": "1234"},
                    {"label": "API Key", "field_key": "api_key", "value": "secret-value"},
                ],
            },
        )
    )
    db_session.commit()
    q = db_session.query(EworksQuote).filter(EworksQuote.eworks_quote_id == 1001).one()
    resp = api_client.get(f"/api/v1/eworks-sync/quotes/{q.id}/safe")
    assert resp.status_code == 200
    detail = resp.json()["data"]

    assert detail["identity"]["quote_ref"] == "Q-1001"
    assert detail["customer"]["customer_name"] == "Acme"
    assert detail["quote_details"]["preferred_date"] == "2026-01-20"
    assert detail["financials"]["total"] == 1200.0
    assert detail["tags"] == ["urgent"]
    assert len(detail["items"]) == 1
    assert detail["items"][0]["name"] == "Panel install"
    assert any(field["field_key"] == "access_code" for field in detail["custom_fields"])
    assert all(field["value"] != "secret-value" for field in detail["custom_fields"] if field["field_key"] == "api_key")
    assert "raw_payload" not in detail


@patch("app.auth.dependencies.settings")
def test_safe_quote_detail_redacts_sensitive_custom_fields(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    db_session.add(
        EworksQuote(
            eworks_quote_id=1002,
            quote_ref="Q-1002",
            raw_payload={
                "custom_fields": {"session_token": "abc123", "notes": "Safe note"},
            },
        )
    )
    db_session.commit()
    q = db_session.query(EworksQuote).filter(EworksQuote.eworks_quote_id == 1002).one()
    resp = api_client.get(f"/api/v1/eworks-sync/quotes/{q.id}/safe")
    detail = resp.json()["data"]
    token_field = next(field for field in detail["custom_fields"] if field["field_key"] == "session_token")
    assert token_field["value"] == "***REDACTED***"
    assert "abc123" not in resp.text


@patch("app.auth.dependencies.settings")
def test_engineer_blocked_from_quote_safe_detail(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="engineer")
    db_session.add(EworksQuote(eworks_quote_id=1003, quote_ref="Q-1003"))
    db_session.commit()
    q = db_session.query(EworksQuote).filter(EworksQuote.eworks_quote_id == 1003).one()
    resp = api_client.get(f"/api/v1/eworks-sync/quotes/{q.id}/safe")
    assert resp.status_code == 403


@patch("app.auth.dependencies.settings")
def test_safe_quote_detail_links_estimate_session(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    session_id = uuid.uuid4()
    db_session.add(
        EworksQuote(eworks_quote_id=22104, quote_ref="Q22104", customer_name="Linked Co")
    )
    db_session.add(
        CalculationSession(
            id=session_id,
            session_token="mock-session-token-should-not-leak",
            source="eworks",
            payload_snapshot={"quote_number": "Q22104"},
            step1_snapshot={"quote_number": "Q22104", "client_name": "Linked Co"},
            expires_at=datetime.now(timezone.utc),
            status="submitted",
        )
    )
    db_session.commit()
    q = db_session.query(EworksQuote).filter(EworksQuote.eworks_quote_id == 22104).one()
    resp = api_client.get(f"/api/v1/eworks-sync/quotes/{q.id}/safe")
    detail = resp.json()["data"]
    assert detail["linked_estimate"]["has_estimate_session"] is True
    assert detail["linked_estimate"]["session_id"] == str(session_id)
    assert "mock-session-token-should-not-leak" not in resp.text


def test_build_quote_safe_detail_handles_missing_raw_payload(db_session):
    from app.services.eworks_safe_detail_service import build_quote_safe_detail

    quote = EworksQuote(eworks_quote_id=55, quote_ref="Q-55", customer_name="Minimal")
    db_session.add(quote)
    db_session.commit()
    detail = build_quote_safe_detail(db_session, quote)
    assert detail["identity"]["quote_ref"] == "Q-55"
    assert detail["items"] == []
    assert detail["custom_fields"] == []


# ---------------------------------------------------------------------------
# Tests: attachment metadata sync (Phase 24)
# ---------------------------------------------------------------------------


def test_extract_attachment_metadata_from_quote_raw_payload(db_session):
    from app.services.eworks_attachment_sync_service import sync_parent_attachments

    quote = EworksQuote(
        eworks_quote_id=5001,
        quote_ref="Q-5001",
        raw_payload={
            "id": 5001,
            "attachments": [
                {
                    "id": 11,
                    "filename": "scope.pdf",
                    "mime_type": "application/pdf",
                    "size_bytes": 2048,
                    "uploaded_by": "Alice",
                    "created_on": "2026-01-01",
                    "download_url": "https://eworks.example/files/11?api_key=secret-key",
                }
            ],
        },
    )
    db_session.add(quote)
    db_session.commit()

    with patch("app.services.eworks_attachment_sync_service.settings") as mock_settings:
        mock_settings.eworks_sync_attachments_enabled = True
        count = sync_parent_attachments(
            db_session,
            parent_type="quote",
            parent_eworks_id=5001,
            parent_local_id=quote.id,
            raw_payload=quote.raw_payload,
        )

    assert count == 1
    attachment = db_session.query(EworksAttachment).one()
    assert attachment.filename == "scope.pdf"
    assert attachment.mime_type == "application/pdf"
    assert attachment.size_bytes == 2048
    assert attachment.uploaded_by == "Alice"
    assert attachment.parent_type == "quote"
    assert attachment.parent_eworks_id == 5001
    assert attachment.parent_local_id == quote.id
    assert attachment.download_endpoint is not None
    assert attachment.local_storage_path is None
    assert attachment.downloaded_at is None


def test_extract_attachment_metadata_from_job_raw_payload(db_session):
    from app.services.eworks_attachment_sync_service import sync_parent_attachments

    job = EworksJob(
        eworks_job_id=6001,
        job_ref="J-6001",
        raw_payload={
            "id": 6001,
            "job_attachments": [
                {
                    "attachment_id": "ja-1",
                    "file_name": "site-photo.jpg",
                    "content_type": "image/jpeg",
                    "size": 4096,
                    "uploaded_by": {"name": "Bob"},
                    "uploaded_at": "2026-02-02",
                }
            ],
        },
    )
    db_session.add(job)
    db_session.commit()

    with patch("app.services.eworks_attachment_sync_service.settings") as mock_settings:
        mock_settings.eworks_sync_attachments_enabled = True
        count = sync_parent_attachments(
            db_session,
            parent_type="job",
            parent_eworks_id=6001,
            parent_local_id=job.id,
            raw_payload=job.raw_payload,
        )

    assert count == 1
    attachment = db_session.query(EworksAttachment).one()
    assert attachment.filename == "site-photo.jpg"
    assert attachment.mime_type == "image/jpeg"
    assert attachment.parent_type == "job"
    assert attachment.uploaded_by == "Bob"


def test_attachment_sync_disabled_does_not_create_rows(db_session):
    from app.services.eworks_attachment_sync_service import sync_parent_attachments

    with patch("app.services.eworks_attachment_sync_service.settings") as mock_settings:
        mock_settings.eworks_sync_attachments_enabled = False
        count = sync_parent_attachments(
            db_session,
            parent_type="quote",
            parent_eworks_id=7001,
            parent_local_id=1,
            raw_payload={"attachments": [{"id": 1, "filename": "ignored.pdf"}]},
        )

    assert count == 0
    assert db_session.query(EworksAttachment).count() == 0


@patch("app.auth.dependencies.settings")
def test_manager_can_list_safe_quote_attachments(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    quote = EworksQuote(eworks_quote_id=8001, quote_ref="Q-8001")
    db_session.add(quote)
    db_session.flush()
    db_session.add(
        EworksAttachment(
            eworks_attachment_id="att-1",
            parent_type="quote",
            parent_eworks_id=8001,
            parent_local_id=quote.id,
            filename="invoice.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            description="January invoice",
            uploaded_by="Carol",
            created_on="2026-03-01",
            download_endpoint="https://eworks.example/download?token=secret-token",
            raw_payload={"id": "att-1", "token": "secret-token"},
        )
    )
    db_session.commit()

    resp = api_client.get(f"/api/v1/eworks-sync/quotes/{quote.id}/attachments")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 1
    item = data["items"][0]
    assert item["filename"] == "invoice.pdf"
    assert item["mime_type"] == "application/pdf"
    assert item["size_bytes"] == 1024
    assert item["uploaded_by"] == "Carol"
    assert "raw_payload" not in item
    assert "download_endpoint" not in item
    assert "secret-token" not in resp.text


@patch("app.auth.dependencies.settings")
def test_manager_cannot_view_attachment_admin_detail(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    quote = EworksQuote(eworks_quote_id=8002, quote_ref="Q-8002")
    db_session.add(quote)
    db_session.flush()
    attachment = EworksAttachment(
        eworks_attachment_id="att-2",
        parent_type="quote",
        parent_eworks_id=8002,
        parent_local_id=quote.id,
        filename="private.pdf",
        raw_payload={"secret": "admin-only"},
    )
    db_session.add(attachment)
    db_session.commit()

    resp = api_client.get(f"/api/v1/eworks-sync/attachments/{attachment.id}")
    assert resp.status_code == 403


@patch("app.auth.dependencies.settings")
def test_admin_can_view_attachment_raw_payload(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    quote = EworksQuote(eworks_quote_id=8003, quote_ref="Q-8003")
    db_session.add(quote)
    db_session.flush()
    attachment = EworksAttachment(
        eworks_attachment_id="att-3",
        parent_type="quote",
        parent_eworks_id=8003,
        parent_local_id=quote.id,
        filename="spec.pdf",
        raw_payload={"id": "att-3", "notes": "admin visible"},
    )
    db_session.add(attachment)
    db_session.commit()

    resp = api_client.get(f"/api/v1/eworks-sync/attachments/{attachment.id}")
    assert resp.status_code == 200
    detail = resp.json()["data"]
    assert detail["raw_payload"]["notes"] == "admin visible"
    assert detail["download_endpoint"] is None


@patch("app.auth.dependencies.settings")
@patch("app.core.config.settings")
def test_attachment_download_disabled_by_default(mock_cfg_settings, mock_auth_settings, api_client, db_session):
    _patch_dev_user(mock_auth_settings, role="manager")
    mock_cfg_settings.eworks_sync_attachment_files_enabled = False
    attachment = EworksAttachment(
        eworks_attachment_id="att-4",
        parent_type="job",
        parent_eworks_id=9001,
        parent_local_id=1,
        filename="plan.dwg",
    )
    db_session.add(attachment)
    db_session.commit()

    resp = api_client.get(f"/api/v1/eworks-sync/attachments/{attachment.id}/download")
    assert resp.status_code == 503
    assert "disabled" in resp.json()["detail"].lower()

