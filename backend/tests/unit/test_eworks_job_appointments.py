"""Unit tests for eWorks job appointment extraction and engineer assigned jobs."""

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
from app.models.calculation_session import CalculationSession
from app.models.eworks_sync import EworksJob, EworksJobAppointment, EworksQuote
from app.models.user import User
from app.services.engineer_assigned_jobs_service import list_assigned_jobs_for_engineer
from app.services.eworks_job_appointment_service import (
    extract_job_appointments_from_raw,
    is_cancelled_appointment_status,
    select_active_appointment,
    sync_job_appointments,
)


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in [User.__table__, CalculationSession.__table__, EworksQuote.__table__, EworksJob.__table__]:
        table.create(engine, checkfirst=True)
    EworksJobAppointment.__table__.create(engine, checkfirst=True)

    Session = sessionmaker(bind=engine)
    session = Session()
    now = datetime.now(timezone.utc)
    engineer_id = uuid4()
    other_id = uuid4()
    manager_id = uuid4()
    engineer = User(
        id=engineer_id,
        email="rohit@example.com",
        full_name="Rohit",
        password_hash=get_password_hash("eng12345"),
        role=UserRole.ENGINEER.value,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    other = User(
        id=other_id,
        email="other@example.com",
        full_name="Other Engineer",
        password_hash=get_password_hash("eng22345"),
        role=UserRole.ENGINEER.value,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    manager = User(
        id=manager_id,
        email="manager@example.com",
        full_name="Manager User",
        password_hash=get_password_hash("mgr12345"),
        role=UserRole.MANAGER.value,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    session.add_all([engineer, other, manager])
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


def _patch_dev_user(mock_settings, *, role: str, email: str = "rohit@example.com", name: str = "Rohit"):
    mock_settings.auth_provider = "dev"
    mock_settings.dev_auth_enabled = True
    mock_settings.dev_user_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    mock_settings.dev_user_email = email
    mock_settings.dev_user_name = name
    mock_settings.dev_user_role = role
    mock_settings.dev_user_is_active = True
    mock_settings.dev_auth_auto_create_user = False


def _scheduled_payload(*, email: str = "rohit@example.com", name: str = "Rohit") -> dict:
    return {
        "appointments": [
            {
                "id": 9001,
                "user": {"name": name, "email": email},
                "appointment_type": "1 Hour Job",
                "status": "Scheduled",
                "start_date": "2026-06-10",
                "start_time": "11:00",
                "end_date": "2026-06-10",
                "end_time": "12:00",
            }
        ]
    }


def _seed_job(db_session, *, eworks_job_id: int, raw_payload: dict, **kwargs) -> EworksJob:
    job = EworksJob(
        eworks_job_id=eworks_job_id,
        job_ref=kwargs.get("job_ref", f"JOB-{eworks_job_id}"),
        customer_name=kwargs.get("customer_name", "ACME Ltd"),
        address=kwargs.get("address", "1 Test Street"),
        status_name=kwargs.get("status_name", "Open"),
        raw_payload=raw_payload,
    )
    db_session.add(job)
    db_session.flush()
    sync_job_appointments(db_session, job, raw_payload=raw_payload)
    db_session.commit()
    db_session.refresh(job)
    return job


def test_extract_job_appointments_from_raw_user_name():
    rows = extract_job_appointments_from_raw(_scheduled_payload())
    assert len(rows) == 1
    assert rows[0]["user_name"] == "Rohit"
    assert rows[0]["user_email"] == "rohit@example.com"
    assert rows[0]["appointment_type"] == "1 Hour Job"


def test_cancelled_appointment_status_is_detected():
    assert is_cancelled_appointment_status("Cancelled")
    assert is_cancelled_appointment_status("Cancelled by customer")
    assert not is_cancelled_appointment_status("Scheduled")


def test_select_active_appointment_ignores_cancelled():
    rows = extract_job_appointments_from_raw(
        {
            "appointments": [
                {
                    "id": 1,
                    "user": {"name": "Alex Alves", "email": "alex@example.com"},
                    "appointment_type": "1 Hour Job",
                    "status": "Cancelled",
                    "start_date": "2020-11-24",
                    "start_time": "11:00",
                    "end_date": "2020-11-24",
                    "end_time": "12:00",
                },
                {
                    "id": 2,
                    "user": {"name": "Rohit", "email": "rohit@example.com"},
                    "appointment_type": "1 Hour Job",
                    "status": "Scheduled",
                    "start_date": "2026-06-10",
                    "start_time": "11:00",
                    "end_date": "2026-06-10",
                    "end_time": "12:00",
                },
            ]
        }
    )
    active = select_active_appointment(rows)
    assert active is not None
    assert active["user_email"] == "rohit@example.com"


@patch("app.auth.dependencies.settings")
def test_non_cancelled_appointment_creates_assigned_job_for_matching_engineer(
    mock_settings, api_client, db_session
):
    _patch_dev_user(mock_settings, role="engineer")
    _seed_job(db_session, eworks_job_id=5001, raw_payload=_scheduled_payload())

    resp = api_client.get("/api/v1/engineer/jobs/assigned")
    assert resp.status_code == 200
    items = resp.json()["data"]
    assert len(items) == 1
    assert items[0]["job_ref"] == "JOB-5001"
    assert items[0]["appointment_user_name"] == "Rohit"
    assert items[0]["appointment_status"] == "Scheduled"


@patch("app.auth.dependencies.settings")
def test_cancelled_appointment_is_ignored_for_active_assigned_jobs(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="engineer")
    _seed_job(
        db_session,
        eworks_job_id=5002,
        raw_payload={
            "appointments": [
                {
                    "id": 9100,
                    "user": {"name": "Rohit", "email": "rohit@example.com"},
                    "appointment_type": "1 Hour Job",
                    "status": "Cancelled",
                    "start_date": "2020-11-24",
                    "start_time": "11:00",
                    "end_date": "2020-11-24",
                    "end_time": "12:00",
                }
            ]
        },
    )

    resp = api_client.get("/api/v1/engineer/jobs/assigned")
    assert resp.status_code == 200
    assert resp.json()["data"] == []


@patch("app.auth.dependencies.settings")
def test_matching_by_email_works(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="engineer", email="rohit@example.com", name="Different Name")
    _seed_job(db_session, eworks_job_id=5003, raw_payload=_scheduled_payload(name="Rohit"))

    resp = api_client.get("/api/v1/engineer/jobs/assigned")
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1


@patch("app.auth.dependencies.settings")
def test_fallback_matching_by_name_works(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="engineer", email="rohit@example.com", name="Rohit")
    _seed_job(
        db_session,
        eworks_job_id=5004,
        raw_payload={
            "appointments": [
                {
                    "id": 9200,
                    "user": {"name": "Rohit"},
                    "appointment_type": "1 Hour Job",
                    "status": "Scheduled",
                    "start_date": "2026-06-10",
                    "start_time": "11:00",
                    "end_date": "2026-06-10",
                    "end_time": "12:00",
                }
            ]
        },
    )

    resp = api_client.get("/api/v1/engineer/jobs/assigned")
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1


@patch("app.auth.dependencies.settings")
def test_engineer_cannot_see_other_engineers_assigned_jobs(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="engineer")
    _seed_job(
        db_session,
        eworks_job_id=5005,
        raw_payload=_scheduled_payload(email="other@example.com", name="Other Engineer"),
    )

    resp = api_client.get("/api/v1/engineer/jobs/assigned")
    assert resp.status_code == 200
    assert resp.json()["data"] == []


@patch("app.auth.dependencies.settings")
def test_assigned_jobs_response_excludes_raw_payload(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="engineer")
    payload = _scheduled_payload()
    payload["secret_token"] = "hidden"
    _seed_job(db_session, eworks_job_id=5006, raw_payload=payload)

    resp = api_client.get("/api/v1/engineer/jobs/assigned")
    body = resp.text
    assert resp.status_code == 200
    assert "raw_payload" not in body
    assert "secret_token" not in body


@patch("app.auth.dependencies.settings")
def test_job_safe_detail_includes_appointments_section(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager", email="manager@example.com", name="Manager User")
    job = _seed_job(db_session, eworks_job_id=5007, raw_payload=_scheduled_payload())

    resp = api_client.get(f"/api/v1/eworks-sync/jobs/{job.id}/safe")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "appointments" in data
    assert len(data["appointments"]) == 1
    assert data["appointments"][0]["user_name"] == "Rohit"
    assert "raw_payload" not in resp.text
