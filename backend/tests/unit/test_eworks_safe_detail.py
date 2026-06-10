"""Unit tests for quote safe detail sales appointment merging."""

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
from app.services.eworks_job_appointment_service import (
    merge_quote_sales_appointments,
    serialize_linked_job_appointments_for_quote,
    sync_job_appointments,
)
from app.services.eworks_linked_job_sync_service import (
    clear_linked_job_auto_sync_attempts,
    sync_linked_jobs_for_quote,
)
from app.services.eworks_safe_detail_service import build_quote_safe_detail


@pytest.fixture(autouse=True)
def _clear_auto_sync_attempts():
    clear_linked_job_auto_sync_attempts()
    yield
    clear_linked_job_auto_sync_attempts()


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


def _q22147_job_34012_payload() -> dict:
    return {
        "appointments": [
            {
                "id": 66022,
                "job_id": "36026",
                "start_date": "2026-06-10T10:00:00.000Z",
                "end_date": "2026-06-10T11:30:00.000Z",
                "status": "3",
                "status_text": "Accepted",
                "appointment_type": "1 Hour Job",
                "appointment_user": {
                    "id": 13,
                    "full_name": "0. Vitor Espirito Santo",
                    "email_address": "vitor.santo@theoptimalgroup.co.uk",
                },
                "is_sales_appointment": None,
            }
        ]
    }


def _seed_q22147_with_linked_job(db_session) -> tuple[EworksQuote, EworksJob]:
    quote = EworksQuote(
        eworks_quote_id=29259,
        quote_ref="Q22147",
        customer_name="Thanuja Marasinghe",
    )
    job = EworksJob(
        eworks_job_id=36026,
        job_ref="JOB-34012",
        eworks_quote_id=29259,
        customer_name="Thanuja Marasinghe",
        raw_detail_payload=_q22147_job_34012_payload(),
        total_appointments=1,
    )
    db_session.add_all([quote, job])
    db_session.flush()
    sync_job_appointments(db_session, job, raw_payload=job.raw_detail_payload)
    db_session.commit()
    db_session.refresh(quote)
    db_session.refresh(job)
    return quote, job


def test_quote_safe_detail_includes_linked_job_appointment(db_session):
    quote, job = _seed_q22147_with_linked_job(db_session)

    detail = build_quote_safe_detail(db_session, quote, auto_sync_linked_jobs=False)

    assert len(detail["sales_appointments"]) == 1
    appointment = detail["sales_appointments"][0]
    assert appointment["source"] == "job"
    assert appointment["job_ref"] == job.job_ref
    assert appointment["eworks_job_id"] == job.eworks_job_id
    assert appointment["user_name"] == "Vitor Espirito Santo"
    assert appointment["user_email"] == "vitor.santo@theoptimalgroup.co.uk"
    assert appointment["status"] == "Accepted"
    assert appointment["start_at"] == "2026-06-10T10:00:00.000Z"
    assert appointment["end_at"] == "2026-06-10T11:30:00.000Z"
    assert appointment["is_sales_appointment"] is True


def test_serialize_linked_job_appointments_marks_source_job(db_session):
    quote, job = _seed_q22147_with_linked_job(db_session)

    rows = serialize_linked_job_appointments_for_quote(db_session, quote)

    assert len(rows) == 1
    assert rows[0]["source"] == "job"
    assert rows[0]["job_ref"] == job.job_ref


def test_merge_deduplicates_quote_and_job_appointment_by_id(db_session):
    quote = EworksQuote(eworks_quote_id=29259, quote_ref="Q22147", customer_name="Customer")
    job = EworksJob(
        eworks_job_id=36026,
        job_ref="JOB-34012",
        eworks_quote_id=29259,
        customer_name="Customer",
        raw_detail_payload=_q22147_job_34012_payload(),
    )
    db_session.add_all([quote, job])
    db_session.flush()
    db_session.add(
        EworksQuoteAppointment(
            eworks_quote_id=29259,
            dedupe_key="id:66022",
            appointment_id=66022,
            user_name="Vitor Espirito Santo",
            user_email="vitor.santo@theoptimalgroup.co.uk",
            status="Accepted",
            is_sales_appointment=True,
            start_at="2026-06-10T10:00:00.000Z",
            end_at="2026-06-10T11:30:00.000Z",
        )
    )
    sync_job_appointments(db_session, job, raw_payload=job.raw_detail_payload)
    db_session.commit()

    detail = build_quote_safe_detail(db_session, quote, auto_sync_linked_jobs=False)

    assert len(detail["sales_appointments"]) == 1
    assert detail["sales_appointments"][0]["source"] == "quote"


def test_merge_quote_sales_appointments_dedupes_by_appointment_id():
    quote_rows = [
        {
            "appointment_id": 66022,
            "user_name": "Vitor Espirito Santo",
            "start_at": "2026-06-10T10:00:00.000Z",
            "end_at": "2026-06-10T11:30:00.000Z",
        }
    ]
    job_rows = [
        {
            "appointment_id": 66022,
            "user_name": "Vitor Espirito Santo",
            "start_at": "2026-06-10T10:00:00.000Z",
            "end_at": "2026-06-10T11:30:00.000Z",
            "source": "job",
            "job_ref": "JOB-34012",
            "eworks_job_id": 36026,
        }
    ]

    merged = merge_quote_sales_appointments(quote_rows, job_rows)

    assert len(merged) == 1
    assert merged[0]["source"] == "quote"


@patch("app.auth.dependencies.settings")
def test_safe_quote_detail_api_includes_job_linked_appointment(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    quote, job = _seed_q22147_with_linked_job(db_session)

    resp = api_client.get(f"/api/v1/eworks-sync/quotes/{quote.id}/safe")

    assert resp.status_code == 200
    appointments = resp.json()["data"]["sales_appointments"]
    assert len(appointments) == 1
    assert appointments[0]["source"] == "job"
    assert appointments[0]["job_ref"] == job.job_ref
    assert appointments[0]["user_name"] == "Vitor Espirito Santo"


@patch("app.core.config.settings.eworks_api_enabled", True)
@patch("app.services.eworks_linked_job_sync_service.fetch_jobs_for_quote")
@patch("app.services.eworks_job_detail_sync_service.fetch_job_detail")
def test_sync_linked_for_quote_fetches_job_and_appointments(
    mock_fetch_job_detail,
    mock_fetch_jobs_for_quote,
    db_session,
):
    quote = EworksQuote(
        eworks_quote_id=29259,
        quote_ref="Q22147",
        customer_name="Thanuja Marasinghe",
    )
    db_session.add(quote)
    db_session.commit()

    list_payload = {
        "id": 36026,
        "job_ref": "JOB-34012",
        "quote_id": 29259,
        "total_appointments": "1",
    }
    detail_payload = _q22147_job_34012_payload()
    detail_payload.update(list_payload)
    mock_fetch_jobs_for_quote.return_value = [list_payload]
    mock_fetch_job_detail.return_value = (detail_payload, 0)

    summary = sync_linked_jobs_for_quote(db_session, quote_ref="Q22147")

    assert summary.jobs_found_in_eworks == 1
    assert summary.jobs_upserted == 1
    assert summary.detail_fetches_success == 1
    assert summary.appointments_found == 1

    job = db_session.query(EworksJob).filter(EworksJob.eworks_job_id == 36026).one()
    assert job.job_ref == "JOB-34012"
    assert job.eworks_quote_id == 29259

    detail = build_quote_safe_detail(db_session, quote)
    assert len(detail["sales_appointments"]) == 1
    assert detail["sales_appointments"][0]["user_name"] == "Vitor Espirito Santo"


@patch("app.core.config.settings.eworks_api_enabled", True)
@patch("app.auth.dependencies.settings")
@patch("app.services.eworks_linked_job_sync_service.sync_linked_jobs_for_quote")
def test_sync_linked_for_quote_endpoint(mock_sync, mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    from app.services.eworks_linked_job_sync_service import LinkedJobSyncSummary

    mock_sync.return_value = LinkedJobSyncSummary(
        quote_ref="Q22147",
        eworks_quote_id=29259,
        jobs_found_in_eworks=1,
        jobs_upserted=1,
        detail_fetches_success=1,
        appointments_found=1,
        appointments_created=1,
    )

    resp = api_client.post(
        "/api/v1/eworks-sync/jobs/sync-linked-for-quote",
        params={"quote_ref": "Q22147"},
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["quote_ref"] == "Q22147"
    assert data["appointments_found"] == 1


def test_safe_detail_resolves_status_id_to_label(db_session):
    quote = EworksQuote(
        eworks_quote_id=29280,
        quote_ref="Q22163",
        status="1",
    )
    db_session.add(quote)
    db_session.commit()

    detail = build_quote_safe_detail(db_session, quote, auto_sync_linked_jobs=False)

    assert detail["identity"]["status"] == "1"
    assert detail["identity"]["status_name"] == "Draft"


@patch("app.core.config.settings.eworks_api_enabled", True)
@patch("app.services.eworks_safe_detail_service.maybe_auto_sync_linked_jobs_for_quote")
def test_safe_detail_triggers_auto_sync_when_no_local_job_appointments(mock_auto_sync, db_session):
    quote = EworksQuote(
        eworks_quote_id=29259,
        quote_ref="Q22147",
        customer_name="Thanuja Marasinghe",
        status="1",
    )
    db_session.add(quote)
    db_session.commit()

    build_quote_safe_detail(db_session, quote)

    mock_auto_sync.assert_called_once_with(db_session, quote, opened_directly=True)


@patch("app.core.config.settings.eworks_api_enabled", True)
@patch("app.services.eworks_linked_job_sync_service.fetch_jobs_for_quote")
@patch("app.services.eworks_job_detail_sync_service.fetch_job_detail")
def test_safe_detail_auto_sync_returns_job_appointment(
    mock_fetch_job_detail,
    mock_fetch_jobs_for_quote,
    db_session,
):
    quote = EworksQuote(
        eworks_quote_id=29259,
        quote_ref="Q22147",
        customer_name="Thanuja Marasinghe",
        status="1",
    )
    db_session.add(quote)
    db_session.commit()

    list_payload = {
        "id": 36026,
        "job_ref": "JOB-34012",
        "quote_id": 29259,
        "total_appointments": "1",
    }
    detail_payload = _q22147_job_34012_payload()
    detail_payload.update(list_payload)
    mock_fetch_jobs_for_quote.return_value = [list_payload]
    mock_fetch_job_detail.return_value = (detail_payload, 0)

    detail = build_quote_safe_detail(db_session, quote)

    assert len(detail["sales_appointments"]) == 1
    assert detail["sales_appointments"][0]["source"] == "job"
    assert detail["sales_appointments"][0]["job_ref"] == "JOB-34012"
    assert detail["sales_appointments"][0]["user_name"] == "Vitor Espirito Santo"


@patch("app.core.config.settings.eworks_api_enabled", True)
@patch("app.services.eworks_linked_job_sync_service.sync_linked_jobs_for_quote")
def test_safe_detail_survives_auto_sync_failure(mock_sync, db_session):
    quote = EworksQuote(
        eworks_quote_id=29259,
        quote_ref="Q22147",
        customer_name="Thanuja Marasinghe",
        status="1",
    )
    db_session.add(quote)
    db_session.commit()
    mock_sync.side_effect = RuntimeError("eWorks unavailable")

    detail = build_quote_safe_detail(db_session, quote)

    assert detail["identity"]["quote_ref"] == "Q22147"
    assert detail["sales_appointments"] == []


@patch("app.core.config.settings.eworks_api_enabled", True)
@patch("app.services.eworks_linked_job_sync_service.sync_linked_jobs_for_quote")
def test_recent_auto_sync_attempt_is_not_retried(mock_sync, db_session):
    from app.services.eworks_linked_job_sync_service import LinkedJobSyncSummary, _record_auto_sync_attempt

    quote = EworksQuote(
        eworks_quote_id=29259,
        quote_ref="Q22147",
        customer_name="Thanuja Marasinghe",
        status="1",
    )
    db_session.add(quote)
    db_session.commit()
    _record_auto_sync_attempt(29259)

    build_quote_safe_detail(db_session, quote)

    mock_sync.assert_not_called()


@patch("app.core.config.settings.eworks_api_enabled", True)
@patch("app.services.eworks_linked_job_sync_service.fetch_jobs_for_quote")
@patch("app.services.eworks_job_detail_sync_service.fetch_job_detail")
@patch("app.auth.dependencies.settings")
def test_safe_detail_api_q22147_style_returns_vitor_after_auto_sync(
    mock_settings,
    mock_fetch_job_detail,
    mock_fetch_jobs_for_quote,
    api_client,
    db_session,
):
    _patch_dev_user(mock_settings, role="manager")
    quote = EworksQuote(
        eworks_quote_id=29259,
        quote_ref="Q22147",
        customer_name="Thanuja Marasinghe",
        status="1",
    )
    db_session.add(quote)
    db_session.commit()

    list_payload = {
        "id": 36026,
        "job_ref": "JOB-34012",
        "quote_id": 29259,
        "total_appointments": "1",
    }
    detail_payload = _q22147_job_34012_payload()
    detail_payload.update(list_payload)
    mock_fetch_jobs_for_quote.return_value = [list_payload]
    mock_fetch_job_detail.return_value = (detail_payload, 0)

    resp = api_client.get(f"/api/v1/eworks-sync/quotes/{quote.id}/safe")

    assert resp.status_code == 200
    appointments = resp.json()["data"]["sales_appointments"]
    assert len(appointments) == 1
    assert appointments[0]["user_name"] == "Vitor Espirito Santo"
    assert appointments[0]["job_ref"] == "JOB-34012"
    assert appointments[0]["status"] == "Accepted"
