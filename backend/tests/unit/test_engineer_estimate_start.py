"""Unit tests for engineer start/resume estimate from appointment assignments."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.types import AuthenticatedUser
from app.core.security import UserRole, get_password_hash
from app.db.session import get_db
from app.main import app
from app.models.calculation_session import CalculationSession
from app.models.client import Client
from app.models.client_alias import ClientAlias
from app.models.eworks_sync import EworksJob, EworksJobAppointment, EworksQuote, EworksQuoteAppointment
from app.models.quote_assignment import EworksQuoteAssignment
from app.models.rate_rule import RateRule
from app.models.support import AuditLog
from app.models.trade import Trade
from app.models.user import User
from app.services.engineer_assigned_estimates_service import list_assigned_estimates_for_engineer
from app.services.eworks_job_appointment_service import sync_job_appointments
from app.services.quote_assignment_service import start_assignment_estimate


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
        Client.__table__,
        ClientAlias.__table__,
        Trade.__table__,
        RateRule.__table__,
        CalculationSession.__table__,
        EworksQuote.__table__,
        EworksJob.__table__,
        EworksJobAppointment.__table__,
        EworksQuoteAppointment.__table__,
        EworksQuoteAssignment.__table__,
    ]:
        table.create(engine, checkfirst=True)

    Session = sessionmaker(bind=engine)
    session = Session()
    now = datetime.now(timezone.utc)
    vitor_id = uuid4()
    other_id = uuid4()
    vitor = User(
        id=vitor_id,
        email="vitor.santo@theoptimalgroup.co.uk",
        full_name="Vitor Espirito Santo",
        password_hash=get_password_hash("eng12345"),
        role=UserRole.ENGINEER.value,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    other = User(
        id=other_id,
        email="other.engineer@theoptimalgroup.co.uk",
        full_name="Other Engineer",
        password_hash=get_password_hash("eng22345"),
        role=UserRole.ENGINEER.value,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    trade = Trade(id=uuid4(), name="Carpenter", is_active=True, created_at=now, updated_at=now)
    rule = RateRule(
        client_id=None,
        trade_id=trade.id,
        formula_source="xlsx",
        version="trade-default-carpenter",
        hourly_rate=Decimal("95"),
        day_rate=Decimal("239.40"),
        direct_hourly_cost=Decimal("30"),
        direct_daily_cost=Decimal("239.40"),
        client_fee_pct=Decimal("0.15"),
        hourly_overhead_pct=Decimal("0.30"),
        daily_overhead_pct=Decimal("0.20"),
        daily_overhead_long_job_pct=Decimal("0.15"),
        labourer_hourly_cost=Decimal("18.75"),
        labourer_daily_cost=Decimal("150"),
        material_charge_denominator=Decimal("0.20"),
        parking_charge_denominator=Decimal("0.20"),
        congestion_charge_denominator=Decimal("0.20"),
        mround_increment=Decimal("5"),
        oj_uplift_pct=Decimal("10"),
        nhs_overhead_uplift_pct=Decimal("15"),
        eaf_flat_fee=Decimal("1"),
        xlsx_client_name="Trade default",
        xlsx_trade_name="Carpenter",
        material_markup_type="percentage",
        material_markup_value=Decimal("20"),
        vat_rate=Decimal("20"),
        active_from=date(2024, 1, 1),
        is_active=True,
    )
    session.add_all([vitor, other, trade, rule])
    session.commit()
    session.trade = trade  # type: ignore[attr-defined]
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


def _patch_dev_user(mock_settings, *, email: str, role: str = "engineer", name: str = "Engineer"):
    mock_settings.auth_provider = "dev"
    mock_settings.dev_auth_enabled = True
    mock_settings.dev_user_id = "dev-engineer-1"
    mock_settings.dev_user_email = email
    mock_settings.dev_user_name = name
    mock_settings.dev_user_role = role
    mock_settings.dev_user_is_active = True
    mock_settings.dev_auth_auto_create_user = False


def _engineer_user(db_session, *, email: str = "vitor.santo@theoptimalgroup.co.uk") -> AuthenticatedUser:
    user = db_session.query(User).filter(User.email == email).one()
    return AuthenticatedUser(
        id=str(user.id),
        email=user.email,
        name=user.full_name,
        role=UserRole.ENGINEER,
        is_active=True,
        auth_provider="dev",
    )


def _appointment_payload(*, appointment_id: int, user_email: str, user_name: str) -> dict:
    return {
        "appointments": [
            {
                "id": appointment_id,
                "status_text": "Accepted",
                "start_date": "2026-06-10T10:00:00.000Z",
                "end_date": "2026-06-10T11:30:00.000Z",
                "appointment_type": "1 Hour Job",
                "appointment_user": {
                    "full_name": user_name,
                    "email_address": user_email,
                },
            }
        ]
    }


def _seed_vitor_quote_job(
    db_session,
    *,
    eworks_quote_id: int = 29306,
    quote_ref: str = "Q22143",
    eworks_job_id: int = 34005,
    job_ref: str = "JOB-34005",
    appointment_id: int = 66054,
) -> tuple[EworksQuote, EworksJob]:
    quote = EworksQuote(
        eworks_quote_id=eworks_quote_id,
        quote_ref=quote_ref,
        customer_name="Test Customer",
        raw_payload={"site_address": "1 Test Street"},
    )
    job = EworksJob(
        eworks_job_id=eworks_job_id,
        job_ref=job_ref,
        eworks_quote_id=eworks_quote_id,
        customer_name="Test Customer",
        address="1 Test Street",
        raw_detail_payload=_appointment_payload(
            appointment_id=appointment_id,
            user_name="Vitor Espirito Santo",
            user_email="vitor.santo@theoptimalgroup.co.uk",
        ),
    )
    db_session.add_all([quote, job])
    db_session.flush()
    sync_job_appointments(db_session, job, raw_payload=job.raw_detail_payload)
    db_session.commit()
    db_session.refresh(quote)
    db_session.refresh(job)
    return quote, job


def test_vitor_q22143_appointment_can_start_estimate(db_session):
    _seed_vitor_quote_job(db_session)
    user = _engineer_user(db_session)

    items = list_assigned_estimates_for_engineer(db_session, user)

    assert len(items) == 1
    assert items[0]["quote_ref"] == "Q22143"
    assert items[0]["can_start_estimate"] is True
    assert items[0]["has_calculation_session"] is False


def test_appointment_start_creates_estimate_session(db_session):
    _seed_vitor_quote_job(db_session)
    user = _engineer_user(db_session)
    items = list_assigned_estimates_for_engineer(db_session, user)
    synthetic_id = items[0]["id"]
    assert synthetic_id < 0

    result = start_assignment_estimate(db_session, synthetic_id, user)

    assert result["created"] is True
    session = db_session.get(CalculationSession, UUID(result["session_id"]))
    assert session is not None
    assert session.payload_snapshot["appointment_id"] == 66054
    assert session.payload_snapshot["eworks_quote_id"] == 29306
    assert session.payload_snapshot["engineer_email"] == user.email
    assert session.submitted_by_name == "Vitor Espirito Santo"
    assert session.submitted_by_email == "vitor.santo@theoptimalgroup.co.uk"
    assert session.payload_snapshot["submitter_name"] == "Vitor Espirito Santo"
    assert session.payload_snapshot["submitter_email"] == "vitor.santo@theoptimalgroup.co.uk"
    assert session.payload_snapshot["assignment_source"] == "eworks_appointment"
    assert session.payload_snapshot["assignment_type"] == "engineer"


def test_second_start_resumes_existing_session(db_session):
    _seed_vitor_quote_job(db_session)
    user = _engineer_user(db_session)
    synthetic_id = list_assigned_estimates_for_engineer(db_session, user)[0]["id"]

    first = start_assignment_estimate(db_session, synthetic_id, user)
    second = start_assignment_estimate(db_session, synthetic_id, user)

    assert first["session_id"] == second["session_id"]
    assert second["created"] is False
    session = db_session.get(CalculationSession, UUID(first["session_id"]))
    assert session is not None
    assert session.submitted_by_name == "Vitor Espirito Santo"
    assert session.submitted_by_email == "vitor.santo@theoptimalgroup.co.uk"


def test_different_engineer_cannot_start_vitor_appointment(db_session):
    _seed_vitor_quote_job(db_session)
    other = _engineer_user(db_session, email="other.engineer@theoptimalgroup.co.uk")
    synthetic_id = -66054

    with pytest.raises(HTTPException) as exc_info:
        start_assignment_estimate(db_session, synthetic_id, other)
    assert exc_info.value.status_code == 403


def test_manual_assignment_start_still_works(db_session):
    quote = EworksQuote(eworks_quote_id=29399, quote_ref="Q-MANUAL-START", customer_name="Manual Customer")
    db_session.add(quote)
    db_session.flush()
    engineer = db_session.query(User).filter(User.email == "vitor.santo@theoptimalgroup.co.uk").one()
    assignment = EworksQuoteAssignment(
        synced_quote_id=quote.id,
        eworks_quote_id=quote.eworks_quote_id,
        quote_ref=quote.quote_ref,
        assigned_user_id=engineer.id,
        assigned_user_email=engineer.email,
        assigned_user_name=engineer.full_name,
        assignment_type="engineer",
        assignee_kind="registered",
        status="assigned",
    )
    db_session.add(assignment)
    db_session.commit()
    user = _engineer_user(db_session)

    result = start_assignment_estimate(db_session, assignment.id, user)

    assert result["created"] is True
    db_session.refresh(assignment)
    assert assignment.calculation_session_id is not None


@patch("app.auth.dependencies.settings")
def test_api_start_estimate_for_appointment_assignment(mock_settings, api_client, db_session):
    _seed_vitor_quote_job(db_session)
    _patch_dev_user(mock_settings, email="vitor.santo@theoptimalgroup.co.uk", name="Vitor Espirito Santo")
    items = list_assigned_estimates_for_engineer(db_session, _engineer_user(db_session))
    synthetic_id = items[0]["id"]

    resp = api_client.post(f"/api/v1/quote-assignments/{synthetic_id}/start-estimate")

    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["session_id"]
    assert data["resume_url"].startswith("/eworks/calculate?")
    assert data["quote_ref"] == "Q22143"


@patch("app.auth.dependencies.settings")
def test_api_other_engineer_blocked_from_vitor_appointment(mock_settings, api_client, db_session):
    _seed_vitor_quote_job(db_session)
    _patch_dev_user(mock_settings, email="other.engineer@theoptimalgroup.co.uk", name="Other Engineer")

    resp = api_client.post("/api/v1/quote-assignments/-66054/start-estimate")

    assert resp.status_code == 403


def test_assigned_estimate_shows_session_after_start(db_session):
    _seed_vitor_quote_job(db_session)
    user = _engineer_user(db_session)
    synthetic_id = list_assigned_estimates_for_engineer(db_session, user)[0]["id"]
    start_assignment_estimate(db_session, synthetic_id, user)

    items = list_assigned_estimates_for_engineer(db_session, user)

    assert items[0]["has_calculation_session"] is True
    assert items[0]["can_start_estimate"] is True
    assert items[0]["status"] == "in_progress"
