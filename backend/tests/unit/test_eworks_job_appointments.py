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
from app.models.eworks_sync import EworksJob, EworksJobAppointment, EworksQuote, EworksQuoteAppointment
from app.models.user import User
from app.services.engineer_assigned_jobs_service import list_assigned_jobs_for_engineer
from app.services.eworks_job_appointment_service import (
    extract_job_appointments_from_raw,
    is_cancelled_appointment_status,
    parse_is_sales_appointment,
    resolve_is_sales_appointment,
    select_active_appointment,
    sync_job_appointments,
)
from app.services.eworks_job_detail_sync_service import backfill_job_appointments_from_details
from app.services.eworks_quote_appointment_service import backfill_quote_sales_appointments_from_eworks


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
        EworksQuoteAppointment.__table__,
    ]:
        table.create(engine, checkfirst=True)

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


def _real_eworks_payload(*, is_sales: str = "1") -> dict:
    return {
        "appointments": [
            {
                "id": 9901,
                "appointment_user": {"email_address": "rohit@example.com", "user_name": "Rohit"},
                "appointment_time": "2026-06-10 11:00",
                "total_time": "60",
                "is_sales_appointment": is_sales,
                "status": "Scheduled",
                "mobile": "07123456789",
                "telephone": "02071234567",
            }
        ]
    }


def test_extract_real_shaped_eworks_start_date_when_appointment_time_zero():
    rows = extract_job_appointments_from_raw(
        {
            "appointments": [
                {
                    "id": 65951,
                    "appointment_user": {
                        "email_address": "alex@theoptimalgroup.co.uk",
                        "user_name": "a.alves@btconnect.com",
                        "full_name": "0. Alex Alves",
                    },
                    "appointment_time": "0",
                    "start_date": "2026-06-12T08:00:00.000Z",
                    "end_date": "2026-06-12T13:00:00.000Z",
                    "status": "1",
                    "status_text": "Awaiting",
                    "total_time": "300",
                }
            ]
        }
    )
    assert len(rows) == 1
    assert rows[0]["user_name"] == "Alex Alves"
    assert rows[0]["user_email"] == "alex@theoptimalgroup.co.uk"
    assert rows[0]["start_at"] == "2026-06-12T08:00:00.000Z"
    assert rows[0]["end_at"] == "2026-06-12T13:00:00.000Z"
    assert rows[0]["status"] == "Awaiting"
    assert rows[0]["duration_minutes"] == 300


def test_extract_real_shaped_eworks_appointment_user():
    rows = extract_job_appointments_from_raw(_real_eworks_payload())
    assert len(rows) == 1
    assert rows[0]["user_name"] == "Rohit"
    assert rows[0]["user_email"] == "rohit@example.com"
    assert rows[0]["start_at"] == "2026-06-10 11:00"
    assert rows[0]["duration_minutes"] == 60
    assert rows[0]["user_mobile"] == "07123456789"
    assert rows[0]["user_telephone"] == "02071234567"


def test_is_sales_appointment_parsing():
    assert parse_is_sales_appointment("1") is True
    assert parse_is_sales_appointment(1) is True
    assert parse_is_sales_appointment("true") is True
    assert parse_is_sales_appointment("") is False
    assert parse_is_sales_appointment(None) is False
    assert parse_is_sales_appointment("0") is False


def test_real_shaped_payload_sync_creates_row(db_session):
    job = EworksJob(
        eworks_job_id=5100,
        job_ref="JOB-5100",
        customer_name="ACME Ltd",
        raw_detail_payload=_real_eworks_payload(is_sales=""),
    )
    db_session.add(job)
    db_session.flush()
    sync_job_appointments(db_session, job, raw_payload=job.raw_detail_payload)
    db_session.commit()

    rows = (
        db_session.query(EworksJobAppointment)
        .filter(EworksJobAppointment.eworks_job_id == 5100)
        .all()
    )
    assert len(rows) == 1
    assert rows[0].is_sales_appointment is False
    assert rows[0].user_email == "rohit@example.com"


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
def test_name_only_match_does_not_assign_job(mock_settings, api_client, db_session):
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
    assert len(resp.json()["data"]) == 0


@patch("app.auth.dependencies.settings")
def test_email_match_assigns_job_case_insensitive(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="engineer", email="rohit@example.com", name="Rohit")
    _seed_job(
        db_session,
        eworks_job_id=5008,
        raw_payload=_scheduled_payload(email="ROHIT@EXAMPLE.COM", name="Rohit"),
    )

    resp = api_client.get("/api/v1/engineer/jobs/assigned")
    assert resp.status_code == 200
    items = resp.json()["data"]
    assert len(items) == 1
    assert items[0]["job_ref"] == "JOB-5008"
    assert items[0]["appointment_user_email"] == "ROHIT@EXAMPLE.COM"


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


def _job_33957_payload() -> dict:
    return {
        "appointments": [
            {
                "id": 65931,
                "notes": "",
                "job_id": "35971",
                "status": "1",
                "user_id": "289",
                "end_date": "2026-06-09T15:45:00.000Z",
                "start_date": "2026-06-09T14:30:00.000Z",
                "total_time": "75",
                "status_text": "Awaiting",
                "appointment_time": "0",
                "appointment_type": "1 Hour Job",
                "appointment_user": {
                    "id": 14,
                    "mobile": "+44-7775 655 243",
                    "full_name": "0. Alex Alves",
                    "telephone": "",
                    "user_name": "a.alves@btconnect.com",
                    "email_address": "alex@theoptimalgroup.co.uk",
                },
                "is_sales_appointment": None,
            }
        ]
    }


def test_job_33957_shaped_payload_extracts_appointment_fields():
    rows = extract_job_appointments_from_raw(_job_33957_payload())
    assert len(rows) == 1
    assert rows[0]["user_name"] == "Alex Alves"
    assert rows[0]["user_email"] == "alex@theoptimalgroup.co.uk"
    assert rows[0]["status"] == "Awaiting"
    assert rows[0]["appointment_type"] == "1 Hour Job"
    assert rows[0]["start_at"] == "2026-06-09T14:30:00.000Z"
    assert rows[0]["end_at"] == "2026-06-09T15:45:00.000Z"
    assert rows[0]["is_sales_appointment"] is False


def test_resolve_is_sales_appointment_requires_flag_or_source():
    assert resolve_is_sales_appointment({"is_sales_appointment": "1"}) is True
    assert resolve_is_sales_appointment({"tab": "Sales Appointments"}) is True
    assert resolve_is_sales_appointment({"appointment_type": "Sales Visit"}) is True
    assert resolve_is_sales_appointment({"is_sales_appointment": None}) is False
    assert resolve_is_sales_appointment({"is_sales_appointment": None}, infer_unmarked_as_sales=True) is True
    assert resolve_is_sales_appointment({}, from_sales_list=True) is True


def test_job_detail_payload_infers_sales_when_flag_null():
    rows = extract_job_appointments_from_raw(_job_33957_payload(), infer_unmarked_as_sales=True)
    assert len(rows) == 1
    assert rows[0]["is_sales_appointment"] is True


def test_job_ref_single_mode_backfill_processes_one_job(db_session):
    job_a = EworksJob(
        eworks_job_id=33957,
        job_ref="JOB-33957",
        customer_name="Customer A",
        raw_detail_payload=_job_33957_payload(),
        total_appointments=1,
    )
    job_b = EworksJob(
        eworks_job_id=33958,
        job_ref="JOB-33958",
        customer_name="Customer B",
        raw_detail_payload=_job_33957_payload(),
        total_appointments=1,
    )
    db_session.add_all([job_a, job_b])
    db_session.commit()

    summary = backfill_job_appointments_from_details(db_session, job_ref="JOB-33957")

    assert summary.jobs_scanned == 1
    assert summary.appointments_found == 1
    rows = (
        db_session.query(EworksJobAppointment)
        .filter(EworksJobAppointment.eworks_job_id == 33957)
        .all()
    )
    assert len(rows) == 1
    assert rows[0].user_name == "Alex Alves"
    assert (
        db_session.query(EworksJobAppointment)
        .filter(EworksJobAppointment.eworks_job_id == 33958)
        .count()
        == 0
    )


def test_quote_backfill_returns_zero_for_job_only_appointment_data(db_session, monkeypatch):
    quote = EworksQuote(
        eworks_quote_id=29209,
        quote_ref="Q22105",
        customer_name="Customer",
    )
    db_session.add(quote)
    db_session.commit()

    monkeypatch.setattr("app.core.config.settings.eworks_sync_sales_appointments_enabled", True)

    def _fake_fetch(_eworks_quote_id: int):
        return _job_33957_payload(), 0

    monkeypatch.setattr(
        "app.services.eworks_quote_appointment_service.fetch_quote_detail",
        _fake_fetch,
    )

    summary = backfill_quote_sales_appointments_from_eworks(
        db_session,
        quote_ref="Q22105",
    )

    assert summary.quotes_scanned == 1
    assert summary.appointments_found == 0
    assert summary.sales_appointments_found == 0


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
