"""Unit tests for quote review submitter identity on appointment-derived submissions."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.types import AuthenticatedUser
from app.core.security import UserRole, get_password_hash
from app.db.session import get_db
from app.main import app
from app.models.calculation_session import CalculationSession
from app.models.calculation_session_version import CalculationSessionVersion
from app.models.client import Client
from app.models.client_alias import ClientAlias
from app.models.eworks_sync import EworksJob, EworksJobAppointment, EworksQuote, EworksQuoteAppointment
from app.models.quote_assignment import EworksQuoteAssignment
from app.models.rate_rule import RateRule
from app.models.selected_estimate_decision import SelectedEstimateDecision
from app.models.support import AuditLog
from app.models.trade import Trade
from app.models.user import User
from app.services.eworks_job_appointment_service import sync_job_appointments
from app.services.quote_assignment_service import (
    resolve_session_submitter_identity,
    start_assignment_estimate,
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
        AuditLog.__table__,
        Client.__table__,
        ClientAlias.__table__,
        Trade.__table__,
        RateRule.__table__,
        CalculationSession.__table__,
        CalculationSessionVersion.__table__,
        EworksQuote.__table__,
        EworksJob.__table__,
        EworksJobAppointment.__table__,
        EworksQuoteAppointment.__table__,
        EworksQuoteAssignment.__table__,
        SelectedEstimateDecision.__table__,
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
    client = Client(id=uuid4(), name="Test Customer", default_vat_rate=Decimal("20"), created_at=now, updated_at=now)
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
        active_from=datetime(2024, 1, 1).date(),
        is_active=True,
    )
    session.add_all([vitor, other, trade, client, rule])
    session.commit()
    session.trade = trade  # type: ignore[attr-defined]
    session.client = client  # type: ignore[attr-defined]
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


def _patch_dev_user(mock_settings, *, role: str = "manager", email: str = "manager@example.com", name: str = "Manager"):
    mock_settings.auth_provider = "dev"
    mock_settings.dev_auth_enabled = True
    mock_settings.dev_user_id = "dev-manager-1"
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


def _step1(*, quote_number: str, external_job_id: str | None = None) -> dict:
    return {
        "quote_number": quote_number,
        "job_number": external_job_id or "JOB-001",
        "external_job_id": external_job_id,
        "client_name": "Test Customer",
        "trade_name": "Carpenter",
        "property_address": "1 Test Street",
    }


def _ui_state(final_total: str) -> dict:
    return {
        "current_step": 3,
        "max_reachable_step": 3,
        "last_result": {
            "breakdown": {"final_total": final_total},
            "work_breakdowns": [{"work_index": 0, "breakdown": {"final_total": final_total}}],
        },
    }


def _submit_appointment_session(db_session, user: AuthenticatedUser) -> CalculationSession:
    _seed_vitor_quote_job(db_session)
    result = start_assignment_estimate(db_session, -66054, user)
    session = db_session.get(CalculationSession, UUID(result["session_id"]))
    assert session is not None
    session.status = "submitted"
    session.submitted_at = datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)
    session.locked = True
    db_session.commit()
    db_session.refresh(session)
    return session


def test_vitor_q22143_submission_shows_in_quote_review(db_session, api_client):
    user = _engineer_user(db_session)
    _submit_appointment_session(db_session, user)

    with patch("app.auth.dependencies.settings") as mock_settings:
        _patch_dev_user(mock_settings)
        response = api_client.get("/api/v1/dashboard/quote-groups/detail", params={"quote_ref": "Q22143"})

    assert response.status_code == 200
    group = response.json()["data"]["group"]
    rows = group["assignment_submissions"]
    assert len(rows) == 1
    row = rows[0]
    assert row["assignee_name"] == "Vitor Espirito Santo"
    assert row["submitted_by_name"] == "Vitor Espirito Santo"
    assert row["submitted_by_email"] == "vitor.santo@theoptimalgroup.co.uk"
    assert row["assignment_type"] == "engineer"
    assert row["assignment_source"] == "eworks_appointment"
    assert group["sessions"][0]["submitted_by_name"] == "Vitor Espirito Santo"


def test_appointment_session_missing_submitter_uses_appointment_fallback(db_session):
    quote, _job = _seed_vitor_quote_job(db_session)
    client = db_session.client  # type: ignore[attr-defined]
    trade = db_session.trade  # type: ignore[attr-defined]
    session = CalculationSession(
        session_token="fallback-token",
        source="assignment",
        payload_snapshot={
            "eworks_quote_id": quote.eworks_quote_id,
            "appointment_id": 66054,
            "source": "eworks_appointment",
        },
        step1_snapshot=_step1(quote_number="Q22143", external_job_id="34005"),
        step2_snapshot={"works": [{"scope": "Fallback scope"}]},
        ui_state=_ui_state("120.00"),
        client_id=client.id,
        trade_id=trade.id,
        expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
        status="submitted",
        submitted_at=datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc),
    )
    db_session.add(session)
    db_session.commit()

    identity = resolve_session_submitter_identity(db_session, session)

    assert identity["submitted_by_name"] == "Vitor Espirito Santo"
    assert identity["submitted_by_email"] == "vitor.santo@theoptimalgroup.co.uk"
    assert identity["assignment_source"] == "eworks_appointment"
    assert identity["submitted_by_role"] == "engineer"


def test_manual_assignment_submission_still_shows_assignee(db_session, api_client):
    quote = EworksQuote(eworks_quote_id=29400, quote_ref="Q-MANUAL-REVIEW", customer_name="Manual Customer")
    db_session.add(quote)
    db_session.flush()
    engineer = db_session.query(User).filter(User.email == "vitor.santo@theoptimalgroup.co.uk").one()
    client = db_session.client  # type: ignore[attr-defined]
    trade = db_session.trade  # type: ignore[attr-defined]
    calc_session = CalculationSession(
        session_token="manual-token",
        source="assignment",
        payload_snapshot={"eworks_quote_id": quote.eworks_quote_id},
        step1_snapshot=_step1(quote_number="Q-MANUAL-REVIEW"),
        step2_snapshot={"works": [{"scope": "Manual scope"}]},
        ui_state=_ui_state("99.00"),
        client_id=client.id,
        trade_id=trade.id,
        expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
        status="submitted",
        submitted_at=datetime(2026, 6, 10, 13, 0, tzinfo=timezone.utc),
        submitted_by_name="Vitor Espirito Santo",
        submitted_by_email="vitor.santo@theoptimalgroup.co.uk",
    )
    db_session.add(calc_session)
    db_session.flush()
    assignment = EworksQuoteAssignment(
        synced_quote_id=quote.id,
        eworks_quote_id=quote.eworks_quote_id,
        quote_ref=quote.quote_ref,
        assigned_user_id=engineer.id,
        assigned_user_email=engineer.email,
        assigned_user_name=engineer.full_name,
        assignment_type="engineer",
        assignee_kind="registered",
        status="submitted",
        calculation_session_id=calc_session.id,
    )
    db_session.add(assignment)
    db_session.flush()
    calc_session.payload_snapshot = {
        "eworks_quote_id": quote.eworks_quote_id,
        "assignment_id": assignment.id,
    }
    db_session.commit()

    with patch("app.auth.dependencies.settings") as mock_settings:
        _patch_dev_user(mock_settings)
        response = api_client.get("/api/v1/dashboard/quote-groups/detail", params={"quote_ref": "Q-MANUAL-REVIEW"})

    row = response.json()["data"]["group"]["assignment_submissions"][0]
    assert row["assignee_name"] == "Vitor Espirito Santo"
    assert row["submitted_by_name"] == "Vitor Espirito Santo"
    assert row["assignment_type"] == "engineer"
    assert row.get("assignment_source") in {None, "manual"}


def test_unknown_only_when_no_identity_anywhere(db_session, api_client):
    client = db_session.client  # type: ignore[attr-defined]
    trade = db_session.trade  # type: ignore[attr-defined]
    session = CalculationSession(
        session_token="unknown-token",
        source="test",
        payload_snapshot={"eworks_quote_id": 99999},
        step1_snapshot=_step1(quote_number="Q-UNKNOWN"),
        step2_snapshot={"works": [{"scope": "Anonymous scope"}]},
        ui_state=_ui_state("10.00"),
        client_id=client.id,
        trade_id=trade.id,
        expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
        status="submitted",
        submitted_at=datetime(2026, 6, 10, 14, 0, tzinfo=timezone.utc),
    )
    db_session.add(session)
    db_session.commit()

    identity = resolve_session_submitter_identity(db_session, session)
    assert identity["submitted_by_name"] == "Unknown submitter"

    with patch("app.auth.dependencies.settings") as mock_settings:
        _patch_dev_user(mock_settings)
        response = api_client.get("/api/v1/dashboard/quote-groups/detail", params={"quote_ref": "Q-UNKNOWN"})

    row = response.json()["data"]["group"]["assignment_submissions"][0]
    assert row["assignee_name"] == "Unknown"
    assert row["submitted_by_name"] == "Unknown submitter"
