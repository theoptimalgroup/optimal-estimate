"""Unit tests for eWorks Job detail sync and appointment backfill."""

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
from app.models.calculation_session import CalculationSession
from app.models.eworks_sync import EworksJob, EworksJobAppointment, EworksQuote
from app.models.user import User
from app.services.eworks_job_detail_sync_service import (
    JobDetailFetchStats,
    apply_job_detail_payload,
    backfill_job_appointments_from_details,
    maybe_fetch_job_detail_after_list_upsert,
    should_fetch_job_detail,
)


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in [
        User.__table__,
        CalculationSession.__table__,
        EworksQuote.__table__,
        EworksJob.__table__,
        EworksJobAppointment.__table__,
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
    engineer = User(
        id=uuid.uuid4(),
        email="rohit@example.com",
        full_name="Rohit",
        password_hash=get_password_hash("eng12345"),
        role=UserRole.ENGINEER.value,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    session.add_all([admin, engineer])
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


def _patch_dev_user(mock_settings, *, role: str, email: str | None = None, name: str | None = None):
    email_map = {
        "admin": "admin@optimal.example",
        "engineer": "rohit@example.com",
    }
    mock_settings.auth_provider = "dev"
    mock_settings.dev_auth_enabled = True
    mock_settings.dev_user_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    mock_settings.dev_user_email = email or email_map.get(role, f"{role}@example.com")
    mock_settings.dev_user_name = name or role.title()
    mock_settings.dev_user_role = role
    mock_settings.dev_user_is_active = True
    mock_settings.dev_auth_auto_create_user = False


def _detail_payload(*, email: str = "rohit@example.com", name: str = "Rohit", status: str = "Scheduled") -> dict:
    return {
        "id": 7001,
        "job_ref": "JOB-7001",
        "total_appointments": 1,
        "completed_appointments": 0,
        "Appointments": [
            {
                "id": 9101,
                "user": {"name": name, "email": email},
                "appointment_type": "1 Hour Job",
                "status": status,
                "start_date": "2026-06-10",
                "start_time": "11:00",
                "end_date": "2026-06-10",
                "end_time": "12:00",
            }
        ],
    }


def _list_payload(*, total_appointments: int) -> dict:
    return {
        "id": 7001,
        "job_ref": "JOB-7001",
        "total_appointments": total_appointments,
    }


def _seed_job(db_session, *, eworks_job_id: int = 7001, total_appointments: int | None = None) -> EworksJob:
    job = EworksJob(
        eworks_job_id=eworks_job_id,
        job_ref=f"JOB-{eworks_job_id}",
        customer_name="ACME Ltd",
        total_appointments=total_appointments,
        raw_payload=_list_payload(total_appointments=total_appointments or 0),
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


def test_should_fetch_job_detail_when_total_appointments_positive(monkeypatch):
    monkeypatch.setattr(
        "app.services.eworks_job_detail_sync_service.settings.eworks_sync_job_details_enabled",
        True,
    )
    monkeypatch.setattr(
        "app.services.eworks_job_detail_sync_service.settings.eworks_sync_job_details_only_with_appointments",
        True,
    )
    assert should_fetch_job_detail(_list_payload(total_appointments=2)) is True


def test_should_fetch_job_detail_skips_when_total_appointments_zero(monkeypatch):
    monkeypatch.setattr(
        "app.services.eworks_job_detail_sync_service.settings.eworks_sync_job_details_enabled",
        True,
    )
    monkeypatch.setattr(
        "app.services.eworks_job_detail_sync_service.settings.eworks_sync_job_details_only_with_appointments",
        True,
    )
    assert should_fetch_job_detail(_list_payload(total_appointments=0)) is False


@patch("app.services.eworks_job_detail_sync_service.fetch_job_detail")
def test_maybe_fetch_job_detail_triggers_detail_fetch(mock_fetch, db_session, monkeypatch):
    monkeypatch.setattr(
        "app.services.eworks_job_detail_sync_service.settings.eworks_sync_job_details_enabled",
        True,
    )
    monkeypatch.setattr(
        "app.services.eworks_job_detail_sync_service.settings.eworks_sync_job_details_only_with_appointments",
        True,
    )
    mock_fetch.return_value = _detail_payload()
    job = _seed_job(db_session, total_appointments=1)
    stats = JobDetailFetchStats()

    maybe_fetch_job_detail_after_list_upsert(
        db_session,
        job,
        _list_payload(total_appointments=1),
        stats=stats,
    )

    mock_fetch.assert_called_once_with(7001)
    assert stats.attempted == 1
    assert stats.success == 1
    assert stats.failed == 0
    assert job.raw_detail_payload is not None
    assert "Appointments" in job.raw_detail_payload


@patch("app.services.eworks_job_detail_sync_service.fetch_job_detail")
def test_maybe_fetch_job_detail_skips_when_total_appointments_zero(mock_fetch, db_session, monkeypatch):
    monkeypatch.setattr(
        "app.services.eworks_job_detail_sync_service.settings.eworks_sync_job_details_enabled",
        True,
    )
    monkeypatch.setattr(
        "app.services.eworks_job_detail_sync_service.settings.eworks_sync_job_details_only_with_appointments",
        True,
    )
    job = _seed_job(db_session, total_appointments=0)
    stats = JobDetailFetchStats()

    maybe_fetch_job_detail_after_list_upsert(
        db_session,
        job,
        _list_payload(total_appointments=0),
        stats=stats,
    )

    mock_fetch.assert_not_called()
    assert stats.attempted == 0


def test_apply_job_detail_payload_creates_appointment_rows(db_session):
    job = _seed_job(db_session, total_appointments=1)
    created, updated = apply_job_detail_payload(db_session, job, _detail_payload())
    db_session.commit()

    rows = (
        db_session.query(EworksJobAppointment)
        .filter(EworksJobAppointment.eworks_job_id == job.eworks_job_id)
        .all()
    )
    assert created == 1
    assert updated == 0
    assert len(rows) == 1
    assert rows[0].appointment_id == 9101
    assert rows[0].user_email == "rohit@example.com"
    assert rows[0].status == "Scheduled"
    assert job.detail_synced_at is not None


@patch("app.services.eworks_job_detail_sync_service.fetch_job_detail")
def test_upsert_jobs_triggers_detail_fetch_when_total_appointments_positive(
    mock_fetch, db_session, monkeypatch
):
    monkeypatch.setattr("app.core.config.settings.eworks_sync_job_details_enabled", True)
    monkeypatch.setattr(
        "app.core.config.settings.eworks_sync_job_details_only_with_appointments",
        True,
    )
    mock_fetch.return_value = _detail_payload()

    from app.services.eworks_sync_service import _upsert_jobs

    summary = _upsert_jobs(
        db_session,
        [
            {
                "id": 7101,
                "job_ref": "J-7101",
                "total_appointments": 2,
            }
        ],
    )
    db_session.commit()

    assert summary.created == 1
    assert summary.failed == 0
    mock_fetch.assert_called_once_with(7101)
    row = db_session.query(EworksJob).filter(EworksJob.eworks_job_id == 7101).one()
    assert row.raw_detail_payload is not None
    assert (
        db_session.query(EworksJobAppointment)
        .filter(EworksJobAppointment.eworks_job_id == 7101)
        .count()
        == 1
    )


@patch("app.services.eworks_job_detail_sync_service.fetch_job_detail")
def test_upsert_jobs_skips_detail_fetch_when_total_appointments_zero(
    mock_fetch, db_session, monkeypatch
):
    monkeypatch.setattr("app.core.config.settings.eworks_sync_job_details_enabled", True)
    monkeypatch.setattr(
        "app.core.config.settings.eworks_sync_job_details_only_with_appointments",
        True,
    )

    from app.services.eworks_sync_service import _upsert_jobs

    summary = _upsert_jobs(
        db_session,
        [
            {
                "id": 7102,
                "job_ref": "J-7102",
                "total_appointments": 0,
            }
        ],
    )
    db_session.commit()

    assert summary.created == 1
    mock_fetch.assert_not_called()


@patch("app.services.eworks_job_detail_sync_service.fetch_job_detail")
def test_upsert_jobs_detail_fetch_failure_does_not_fail_batch(mock_fetch, db_session, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.eworks_sync_job_details_enabled", True)
    monkeypatch.setattr(
        "app.core.config.settings.eworks_sync_job_details_only_with_appointments",
        True,
    )
    mock_fetch.side_effect = RuntimeError("detail API unavailable")

    from app.services.eworks_sync_service import _upsert_jobs

    summary = _upsert_jobs(
        db_session,
        [
            {
                "id": 7103,
                "job_ref": "J-7103",
                "total_appointments": 1,
            },
            {
                "id": 7104,
                "job_ref": "J-7104",
                "total_appointments": 0,
            },
        ],
    )
    db_session.commit()

    assert summary.created == 2
    assert summary.failed == 0
    assert db_session.query(EworksJob).filter(EworksJob.eworks_job_id == 7103).one().job_ref == "J-7103"
    assert db_session.query(EworksJob).filter(EworksJob.eworks_job_id == 7104).one().job_ref == "J-7104"


@patch("app.auth.dependencies.settings")
def test_detail_sync_active_appointment_appears_in_engineer_assigned_jobs(
    mock_settings, api_client, db_session
):
    _patch_dev_user(mock_settings, role="engineer", email="rohit@example.com", name="Rohit")
    job = _seed_job(db_session, total_appointments=1)
    apply_job_detail_payload(db_session, job, _detail_payload())
    db_session.commit()

    resp = api_client.get("/api/v1/engineer/jobs/assigned")
    assert resp.status_code == 200
    items = resp.json()["data"]
    assert len(items) == 1
    assert items[0]["job_ref"] == "JOB-7001"
    assert items[0]["appointment_user_name"] == "Rohit"
    assert items[0]["appointment_status"] == "Scheduled"


@patch("app.auth.dependencies.settings")
def test_detail_sync_cancelled_appointment_stored_but_not_in_assigned_jobs(
    mock_settings, api_client, db_session
):
    _patch_dev_user(mock_settings, role="engineer", email="rohit@example.com", name="Rohit")
    job = _seed_job(db_session, total_appointments=1)
    apply_job_detail_payload(db_session, job, _detail_payload(status="Cancelled"))
    db_session.commit()

    rows = (
        db_session.query(EworksJobAppointment)
        .filter(EworksJobAppointment.eworks_job_id == job.eworks_job_id)
        .all()
    )
    assert len(rows) == 1
    assert rows[0].status == "Cancelled"

    resp = api_client.get("/api/v1/engineer/jobs/assigned")
    assert resp.status_code == 200
    assert resp.json()["data"] == []


@patch("app.services.eworks_job_detail_sync_service.fetch_job_detail")
@patch("app.auth.dependencies.settings")
def test_backfill_endpoint_returns_summary_fields(mock_settings, mock_fetch, api_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr("app.core.config.settings.eworks_api_enabled", True)
    try:
        _seed_job(db_session, eworks_job_id=7201, total_appointments=1)
        _seed_job(db_session, eworks_job_id=7202, total_appointments=0)
        mock_fetch.return_value = _detail_payload()

        resp = api_client.post("/api/v1/eworks-sync/jobs/backfill-appointments?limit=5")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["jobs_scanned"] == 2
        assert data["jobs_with_total_appointments"] == 1
        assert data["detail_fetches_attempted"] == 1
        assert data["detail_fetches_success"] == 1
        assert data["detail_fetches_failed"] == 0
        assert data["appointments_created"] == 1
        assert data["appointments_updated"] == 0
    finally:
        monkeypatch.undo()


@patch("app.services.eworks_job_detail_sync_service.fetch_job_detail")
def test_backfill_service_counts_failures(mock_fetch, db_session):
    _seed_job(db_session, eworks_job_id=7301, total_appointments=1)
    mock_fetch.side_effect = RuntimeError("detail API unavailable")

    summary = backfill_job_appointments_from_details(db_session, limit=1)

    assert summary.jobs_scanned == 1
    assert summary.jobs_with_total_appointments == 1
    assert summary.detail_fetches_attempted == 1
    assert summary.detail_fetches_success == 0
    assert summary.detail_fetches_failed == 1
