"""Unit tests for eWorks appointment-derived assignment and engineer name resolution."""

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
from app.models.eworks_sync import EworksCustomer, EworksJob, EworksJobAppointment, EworksQuote, EworksQuoteAppointment, EworksCustomFieldDefinition
from app.models.quote_assignment import EworksQuoteAssignment
from app.models.support import AuditLog
from app.models.user import User
from app.schemas.eworks_link import EworksLinkPayload, Step1Snapshot
from app.services.engineer_assigned_estimates_service import list_assigned_estimates_for_engineer
from app.services.engineer_assigned_jobs_service import list_assigned_jobs_for_engineer
from app.services.eworks_job_appointment_service import (
    apply_appointment_engineer_name_to_step1,
    get_active_job_appointment_assignee,
    sync_job_appointments,
)
from app.services.eworks_safe_detail_service import build_quote_safe_detail
from app.services.quote_assignment_service import (
    build_unified_assignments_for_quote,
    create_assignment,
    list_assignments_for_quote,
    override_assignment,
)


@pytest.fixture(autouse=True)
def _skip_custom_field_definition_sync(monkeypatch):
    monkeypatch.setattr(
        "app.services.eworks_safe_detail_service.ensure_custom_field_definitions",
        lambda db, *, force=False: False,
    )


@pytest.fixture()
def manager_user(db_session):
    from app.auth.types import AuthenticatedUser

    return AuthenticatedUser(
        id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        email="manager@example.com",
        name="Manager User",
        role=UserRole.MANAGER,
        is_active=True,
        auth_provider="dev",
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
        EworksCustomer.__table__,
        EworksQuote.__table__,
        EworksCustomFieldDefinition.__table__,
        EworksJob.__table__,
        EworksJobAppointment.__table__,
        EworksQuoteAppointment.__table__,
        EworksQuoteAssignment.__table__,
        AuditLog.__table__,
    ]:
        table.create(engine, checkfirst=True)

    Session = sessionmaker(bind=engine)
    session = Session()
    now = datetime.now(timezone.utc)
    user_abc_id = uuid4()
    user_xyz_id = uuid4()
    user_abc = User(
        id=user_abc_id,
        email="abc@example.com",
        full_name="User Abc",
        password_hash=get_password_hash("eng12345"),
        role=UserRole.ENGINEER.value,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    user_xyz = User(
        id=user_xyz_id,
        email="xyz@example.com",
        full_name="User Xyz",
        password_hash=get_password_hash("eng22345"),
        role=UserRole.ENGINEER.value,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    session.add_all([user_abc, user_xyz])
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


def _appointment_payload(
    *,
    appointment_id: int,
    user_name: str,
    user_email: str,
    status_text: str = "Awaiting",
    start_date: str = "2026-06-09T14:30:00.000Z",
    end_date: str = "2026-06-09T15:45:00.000Z",
) -> dict:
    return {
        "appointments": [
            {
                "id": appointment_id,
                "status_text": status_text,
                "start_date": start_date,
                "end_date": end_date,
                "appointment_type": "1 Hour Job",
                "appointment_user": {
                    "full_name": user_name,
                    "email_address": user_email,
                },
            }
        ]
    }


def _seed_quote_with_job(
    db_session,
    *,
    eworks_quote_id: int,
    quote_ref: str,
    eworks_job_id: int,
    job_ref: str,
    user_name: str,
    user_email: str,
    status_text: str = "Awaiting",
    appointment_id: int | None = None,
    quote_status: str = "1",
) -> tuple[EworksQuote, EworksJob]:
    appt_id = appointment_id if appointment_id is not None else eworks_job_id * 2
    quote = EworksQuote(
        eworks_quote_id=eworks_quote_id,
        quote_ref=quote_ref,
        customer_name="Customer",
        status=quote_status,
    )
    job = EworksJob(
        eworks_job_id=eworks_job_id,
        job_ref=job_ref,
        eworks_quote_id=eworks_quote_id,
        customer_name="Customer",
        raw_detail_payload=_appointment_payload(
            appointment_id=appt_id,
            user_name=user_name,
            user_email=user_email,
            status_text=status_text,
        ),
    )
    db_session.add_all([quote, job])
    db_session.flush()
    sync_job_appointments(db_session, job, raw_payload=job.raw_detail_payload)
    db_session.commit()
    db_session.refresh(quote)
    db_session.refresh(job)
    return quote, job


def _seed_q22105_job_33957(db_session) -> tuple[EworksQuote, EworksJob]:
    """Integration fixture only — not used in production code."""
    return _seed_quote_with_job(
        db_session,
        eworks_quote_id=29209,
        quote_ref="Q22105",
        eworks_job_id=33957,
        job_ref="JOB-33957",
        user_name="0. Alex Alves",
        user_email="alex@theoptimalgroup.co.uk",
        appointment_id=65931,
    )


def test_quote_a_returns_appointment_assignee_abc(db_session):
    quote, _job = _seed_quote_with_job(
        db_session,
        eworks_quote_id=10001,
        quote_ref="Q-A",
        eworks_job_id=20001,
        job_ref="JOB-A",
        user_name="User Abc",
        user_email="abc@example.com",
    )

    assignee = get_active_job_appointment_assignee(
        db_session,
        quote_ref=quote.quote_ref,
        eworks_quote_id=quote.eworks_quote_id,
    )

    assert assignee is not None
    assert assignee["user_name"] == "User Abc"
    assert assignee["user_email"] == "abc@example.com"
    assert assignee["source"] == "eworks_appointment"
    assert assignee["job_ref"] == "JOB-A"


def test_quote_b_returns_appointment_assignee_xyz(db_session):
    quote, _job = _seed_quote_with_job(
        db_session,
        eworks_quote_id=10002,
        quote_ref="Q-B",
        eworks_job_id=20002,
        job_ref="JOB-B",
        user_name="User Xyz",
        user_email="xyz@example.com",
    )

    assignee = get_active_job_appointment_assignee(
        db_session,
        quote_ref=quote.quote_ref,
        eworks_quote_id=quote.eworks_quote_id,
    )

    assert assignee is not None
    assert assignee["user_name"] == "User Xyz"
    assert assignee["user_email"] == "xyz@example.com"
    assert assignee["job_ref"] == "JOB-B"


def test_no_linked_job_returns_null(db_session):
    quote = EworksQuote(eworks_quote_id=10003, quote_ref="Q-NO-JOB", customer_name="Customer")
    db_session.add(quote)
    db_session.commit()

    assignee = get_active_job_appointment_assignee(
        db_session,
        quote_ref=quote.quote_ref,
        eworks_quote_id=quote.eworks_quote_id,
    )

    assert assignee is None


def test_only_cancelled_appointments_returns_null(db_session):
    quote, _job = _seed_quote_with_job(
        db_session,
        eworks_quote_id=10004,
        quote_ref="Q-CANCELLED",
        eworks_job_id=20004,
        job_ref="JOB-CANCELLED",
        user_name="User Abc",
        user_email="abc@example.com",
        status_text="Cancelled",
    )

    assignee = get_active_job_appointment_assignee(
        db_session,
        eworks_quote_id=quote.eworks_quote_id,
    )

    assert assignee is None


def test_registered_user_email_matching(db_session):
    _seed_quote_with_job(
        db_session,
        eworks_quote_id=10005,
        quote_ref="Q-REG",
        eworks_job_id=20005,
        job_ref="JOB-REG",
        user_name="User Abc",
        user_email="abc@example.com",
    )

    assignee = get_active_job_appointment_assignee(db_session, quote_ref="Q-REG")

    assert assignee is not None
    assert assignee["assignee_kind"] == "registered"
    assert assignee["registered_user_id"] is not None


def test_missing_user_is_external(db_session):
    quote, _job = _seed_quote_with_job(
        db_session,
        eworks_quote_id=10006,
        quote_ref="Q-EXT",
        eworks_job_id=20006,
        job_ref="JOB-EXT",
        user_name="Unknown Engineer",
        user_email="unknown@example.com",
    )

    assignee = get_active_job_appointment_assignee(db_session, eworks_quote_id=quote.eworks_quote_id)

    assert assignee is not None
    assert assignee["assignee_kind"] == "external"
    assert assignee["registered_user_id"] is None


def test_active_appointment_plus_active_manual_both_available(db_session):
    quote, _job = _seed_quote_with_job(
        db_session,
        eworks_quote_id=10007,
        quote_ref="Q-BOTH",
        eworks_job_id=20007,
        job_ref="JOB-BOTH",
        user_name="User Abc",
        user_email="abc@example.com",
    )
    manual = EworksQuoteAssignment(
        synced_quote_id=quote.id,
        eworks_quote_id=quote.eworks_quote_id,
        quote_ref=quote.quote_ref,
        assigned_user_email="other@example.com",
        assigned_user_name="Other Engineer",
        assignment_type="engineer",
        assignee_kind="external",
        status="assigned",
    )
    db_session.add(manual)
    db_session.commit()

    items = list_assignments_for_quote(db_session, quote.id)
    detail = build_quote_safe_detail(db_session, quote)

    assert len(items) == 1
    assert items[0]["source"] == "manual"
    assert items[0]["is_derived"] is False
    assert detail["appointment_assignee"]["name"] == "User Abc"
    assert detail["appointment_assignee"]["email"] == "abc@example.com"


def test_active_appointment_plus_cancelled_manual_still_returns_assignee(db_session):
    quote, _job = _seed_quote_with_job(
        db_session,
        eworks_quote_id=10008,
        quote_ref="Q-CANC-MAN",
        eworks_job_id=20008,
        job_ref="JOB-CANC-MAN",
        user_name="User Xyz",
        user_email="xyz@example.com",
    )
    db_session.add(
        EworksQuoteAssignment(
            synced_quote_id=quote.id,
            eworks_quote_id=quote.eworks_quote_id,
            quote_ref=quote.quote_ref,
            assigned_user_email="estimator@example.com",
            assigned_user_name="Estimator User",
            assignment_type="estimator",
            assignee_kind="registered",
            status="cancelled",
        )
    )
    db_session.commit()

    items = list_assignments_for_quote(db_session, quote.id)
    detail = build_quote_safe_detail(db_session, quote)

    assert len(items) == 1
    assert items[0]["status"] == "cancelled"
    assert detail["appointment_assignee"]["name"] == "User Xyz"


def test_manual_assignments_list_excludes_derived_rows(db_session):
    quote, _job = _seed_quote_with_job(
        db_session,
        eworks_quote_id=10009,
        quote_ref="Q-NO-DERIVED",
        eworks_job_id=20009,
        job_ref="JOB-NO-DERIVED",
        user_name="User Abc",
        user_email="abc@example.com",
    )

    items = list_assignments_for_quote(db_session, quote.id)

    assert items == []


def test_quote_safe_detail_includes_appointment_assignee(db_session):
    quote, _job = _seed_quote_with_job(
        db_session,
        eworks_quote_id=10010,
        quote_ref="Q-DETAIL",
        eworks_job_id=20010,
        job_ref="JOB-DETAIL",
        user_name="User Abc",
        user_email="abc@example.com",
    )

    detail = build_quote_safe_detail(db_session, quote)

    assert detail["appointment_assignee"]["name"] == "User Abc"
    assert detail["appointment_assignee"]["email"] == "abc@example.com"
    assert detail["appointment_assignee"]["source"] == "eworks_appointment"


def test_engineer_name_from_appointment_when_empty(db_session):
    quote, job = _seed_quote_with_job(
        db_session,
        eworks_quote_id=10011,
        quote_ref="Q-ENG",
        eworks_job_id=20011,
        job_ref="JOB-ENG",
        user_name="User Abc",
        user_email="abc@example.com",
    )
    step1 = Step1Snapshot(
        quote_number=quote.quote_ref,
        job_number=job.job_ref,
        client_name="Customer",
        trade_name="Carpenter",
        property_address="1 Test Street",
    )

    updated = apply_appointment_engineer_name_to_step1(
        db_session,
        step1,
        quote_ref=quote.quote_ref,
        eworks_quote_id=quote.eworks_quote_id,
    )

    assert updated.engineer_name == "User Abc"
    assert updated.engineer_name_source == "eworks_appointment"


def test_does_not_overwrite_manual_engineer_name(db_session):
    quote, job = _seed_quote_with_job(
        db_session,
        eworks_quote_id=10012,
        quote_ref="Q-KEEP",
        eworks_job_id=20012,
        job_ref="JOB-KEEP",
        user_name="User Abc",
        user_email="abc@example.com",
    )
    step1 = Step1Snapshot(
        quote_number=quote.quote_ref,
        job_number=job.job_ref,
        engineer_name="Manual Engineer",
        client_name="Customer",
        trade_name="Carpenter",
        property_address="1 Test Street",
    )

    updated = apply_appointment_engineer_name_to_step1(
        db_session,
        step1,
        quote_ref=quote.quote_ref,
        eworks_quote_id=quote.eworks_quote_id,
    )

    assert updated.engineer_name == "Manual Engineer"
    assert updated.engineer_name_source is None


def test_job_ref_lookup_resolves_assignee(db_session):
    _quote, job = _seed_quote_with_job(
        db_session,
        eworks_quote_id=10013,
        quote_ref="Q-JOB-LOOKUP",
        eworks_job_id=20013,
        job_ref="JOB-LOOKUP",
        user_name="User Xyz",
        user_email="xyz@example.com",
    )

    assignee = get_active_job_appointment_assignee(db_session, job_ref=job.job_ref)

    assert assignee is not None
    assert assignee["user_email"] == "xyz@example.com"


def test_q22105_integration_fixture(db_session):
    """Real-world integration fixture; production code must stay generic."""
    alex_id = uuid4()
    now = datetime.now(timezone.utc)
    db_session.add(
        User(
            id=alex_id,
            email="alex@theoptimalgroup.co.uk",
            full_name="Alex Alves",
            password_hash=get_password_hash("eng12345"),
            role=UserRole.ENGINEER.value,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.commit()

    quote, job = _seed_q22105_job_33957(db_session)

    assignee = get_active_job_appointment_assignee(
        db_session,
        quote_ref=quote.quote_ref,
        eworks_quote_id=quote.eworks_quote_id,
    )

    assert assignee is not None
    assert assignee["user_name"] == "Alex Alves"
    assert assignee["user_email"] == "alex@theoptimalgroup.co.uk"
    assert assignee["job_ref"] == job.job_ref

    detail = build_quote_safe_detail(db_session, quote)
    assert detail["appointment_assignee"]["name"] == "Alex Alves"
    assert len(detail["sales_appointments"]) == 1
    assert detail["sales_appointments"][0]["source"] == "job"
    assert detail["sales_appointments"][0]["job_ref"] == job.job_ref


def test_q22105_lookup_by_quote_id(db_session):
    quote, _job = _seed_q22105_job_33957(db_session)

    assignee = get_active_job_appointment_assignee(db_session, quote_id=quote.id)

    assert assignee is not None
    assert assignee["user_name"] == "Alex Alves"


def test_q22105_lookup_by_quote_ref(db_session):
    _seed_q22105_job_33957(db_session)

    assignee = get_active_job_appointment_assignee(db_session, quote_ref="Q22105")

    assert assignee is not None
    assert assignee["user_name"] == "Alex Alves"


def test_q22105_lookup_by_eworks_quote_id(db_session):
    _seed_q22105_job_33957(db_session)

    assignee = get_active_job_appointment_assignee(db_session, eworks_quote_id=29209)

    assert assignee is not None
    assert assignee["user_name"] == "Alex Alves"


def test_q22105_lookup_by_job_ref(db_session):
    _seed_q22105_job_33957(db_session)

    assignee = get_active_job_appointment_assignee(db_session, job_ref="JOB-33957")

    assert assignee is not None
    assert assignee["user_name"] == "Alex Alves"


def test_q22105_job_ref_fallback_when_eworks_job_id_mismatch(db_session):
    """Production jobs can have eworks_job_id != numeric suffix in job_ref."""
    quote = EworksQuote(
        eworks_quote_id=29209,
        quote_ref="Q22105",
        customer_name="Customer",
    )
    job = EworksJob(
        eworks_job_id=35971,
        job_ref="JOB-33957",
        eworks_quote_id=29209,
        customer_name="Customer",
    )
    db_session.add_all([quote, job])
    db_session.flush()
    db_session.add(
        EworksJobAppointment(
            eworks_job_id=33957,
            job_ref="JOB-33957",
            dedupe_key="id:65931",
            appointment_id=65931,
            user_name="Alex Alves",
            user_email="alex@theoptimalgroup.co.uk",
            status="Awaiting",
            start_at="2026-06-12T08:00:00.000Z",
            end_at="2026-06-12T13:00:00.000Z",
        )
    )
    db_session.commit()

    assignee = get_active_job_appointment_assignee(db_session, quote_id=quote.id)

    assert assignee is not None
    assert assignee["user_name"] == "Alex Alves"
    assert assignee["job_ref"] == "JOB-33957"


@patch("app.auth.dependencies.settings")
def test_safe_quote_detail_api_includes_appointment_assignee(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    quote, _job = _seed_q22105_job_33957(db_session)

    resp = api_client.get(f"/api/v1/eworks-sync/quotes/{quote.id}/safe")

    assert resp.status_code == 200
    detail = resp.json()["data"]
    assert detail["appointment_assignee"] is not None
    assert detail["appointment_assignee"]["name"] == "Alex Alves"
    assert detail["appointment_assignee"]["email"] == "alex@theoptimalgroup.co.uk"


def test_external_assignee_in_quote_safe_detail(db_session):
    quote, _job = _seed_quote_with_job(
        db_session,
        eworks_quote_id=10015,
        quote_ref="Q-EXT-DETAIL",
        eworks_job_id=20015,
        job_ref="JOB-EXT-DETAIL",
        user_name="Unknown Engineer",
        user_email="unknown@example.com",
    )

    detail = build_quote_safe_detail(db_session, quote)

    assert detail["appointment_assignee"]["name"] == "Unknown Engineer"
    assert detail["appointment_assignee"]["email"] == "unknown@example.com"
    assert detail["appointment_assignee"]["assignee_kind"] == "external"
    assert detail["appointment_assignee"]["registered_user_id"] is None


def test_external_engineer_name_from_appointment(db_session):
    quote, job = _seed_quote_with_job(
        db_session,
        eworks_quote_id=10016,
        quote_ref="Q-EXT-ENG",
        eworks_job_id=20016,
        job_ref="JOB-EXT-ENG",
        user_name="Unknown Engineer",
        user_email="unknown@example.com",
    )
    step1 = Step1Snapshot(
        quote_number=quote.quote_ref,
        job_number=job.job_ref,
        client_name="Customer",
        trade_name="Carpenter",
        property_address="1 Test Street",
    )

    updated = apply_appointment_engineer_name_to_step1(
        db_session,
        step1,
        quote_ref=quote.quote_ref,
        eworks_quote_id=quote.eworks_quote_id,
    )

    assert updated.engineer_name == "Unknown Engineer"
    assert updated.engineer_name_source == "eworks_appointment"


def test_registered_user_email_matching_is_case_insensitive(db_session):
    _seed_quote_with_job(
        db_session,
        eworks_quote_id=10017,
        quote_ref="Q-REG-CASE",
        eworks_job_id=20017,
        job_ref="JOB-REG-CASE",
        user_name="User Abc",
        user_email="ABC@EXAMPLE.COM",
    )

    assignee = get_active_job_appointment_assignee(db_session, quote_ref="Q-REG-CASE")

    assert assignee is not None
    assert assignee["assignee_kind"] == "registered"
    assert assignee["registered_user_id"] is not None


def test_external_assignee_not_in_engineer_assigned_jobs_for_other_user(db_session):
    _seed_quote_with_job(
        db_session,
        eworks_quote_id=10018,
        quote_ref="Q-EXT-JOBS",
        eworks_job_id=20018,
        job_ref="JOB-EXT-JOBS",
        user_name="Unknown Engineer",
        user_email="unknown@example.com",
    )
    engineer = db_session.query(User).filter(User.email == "abc@example.com").one()
    from app.auth.types import AuthenticatedUser

    user = AuthenticatedUser(
        id=str(engineer.id),
        email=engineer.email,
        name=engineer.full_name,
        role=UserRole.ENGINEER,
        is_active=True,
        auth_provider="dev",
    )

    items = list_assigned_jobs_for_engineer(db_session, user)

    assert all(item["appointment_user_email"] != "unknown@example.com" for item in items)
    assert not any(item["job_ref"] == "JOB-EXT-JOBS" for item in items)


def test_quote_linked_appointment_in_assigned_estimates_not_assigned_jobs(db_session):
    quote, job = _seed_quote_with_job(
        db_session,
        eworks_quote_id=10014,
        quote_ref="Q-ASSIGNED-JOBS",
        eworks_job_id=20014,
        job_ref="JOB-ASSIGNED-JOBS",
        user_name="User Abc",
        user_email="abc@example.com",
    )
    engineer = db_session.query(User).filter(User.email == "abc@example.com").one()
    from app.auth.types import AuthenticatedUser

    user = AuthenticatedUser(
        id=str(engineer.id),
        email=engineer.email,
        name=engineer.full_name,
        role=UserRole.ENGINEER,
        is_active=True,
        auth_provider="dev",
    )

    job_items = list_assigned_jobs_for_engineer(db_session, user)
    estimate_items = list_assigned_estimates_for_engineer(db_session, user)

    assert job_items == []
    assert len(estimate_items) == 1
    assert estimate_items[0]["job_ref"] == job.job_ref
    assert estimate_items[0]["quote_ref"] == quote.quote_ref
    assert estimate_items[0]["source"] == "eworks_appointment"
    assert estimate_items[0]["can_start_estimate"] is True
    assert estimate_items[0]["appointment_id"] is not None


def test_safe_detail_assignments_includes_eworks_appointment(db_session):
    quote, _job = _seed_quote_with_job(
        db_session,
        eworks_quote_id=10020,
        quote_ref="Q-ASSIGN-LIST",
        eworks_job_id=20020,
        job_ref="JOB-ASSIGN-LIST",
        user_name="User Abc",
        user_email="abc@example.com",
    )

    detail = build_quote_safe_detail(db_session, quote)

    assert len(detail["assignments"]) == 1
    assert detail["assignments"][0]["source"] == "eworks_appointment"
    assert detail["assignments"][0]["is_read_only"] is True
    assert detail["assignments"][0]["assigned_user_name"] == "User Abc"
    assert detail["appointment_assignee"]["name"] == "User Abc"


def test_adding_manual_engineer_keeps_eworks_appointment(db_session, manager_user):
    quote, _job = _seed_quote_with_job(
        db_session,
        eworks_quote_id=10021,
        quote_ref="Q-ADD-ENG",
        eworks_job_id=20021,
        job_ref="JOB-ADD-ENG",
        user_name="User Abc",
        user_email="abc@example.com",
    )

    create_assignment(
        db_session,
        quote_id=quote.id,
        payload={
            "assignment_type": "engineer",
            "assignee_kind": "external",
            "assigned_user_email": "other@example.com",
            "assigned_user_name": "Other Engineer",
        },
        current_user=manager_user,
    )

    unified = build_unified_assignments_for_quote(db_session, quote.id)
    manual = list_assignments_for_quote(db_session, quote.id)

    assert len(manual) == 1
    assert len(unified) == 2
    assert unified[0]["source"] == "eworks_appointment"
    assert unified[1]["source"] == "manual"
    assert unified[1]["assigned_user_email"] == "other@example.com"


def test_adding_manual_estimator_keeps_existing_engineer(db_session, manager_user):
    quote, _job = _seed_quote_with_job(
        db_session,
        eworks_quote_id=10022,
        quote_ref="Q-ADD-EST",
        eworks_job_id=20022,
        job_ref="JOB-ADD-EST",
        user_name="User Abc",
        user_email="abc@example.com",
    )
    create_assignment(
        db_session,
        quote_id=quote.id,
        payload={
            "assignment_type": "engineer",
            "assignee_kind": "external",
            "assigned_user_email": "manual-eng@example.com",
            "assigned_user_name": "Manual Engineer",
        },
        current_user=manager_user,
    )

    create_assignment(
        db_session,
        quote_id=quote.id,
        payload={
            "assignment_type": "estimator",
            "assignee_kind": "external",
            "assigned_user_email": "estimator@example.com",
            "assigned_user_name": "Manual Estimator",
        },
        current_user=manager_user,
    )

    unified = build_unified_assignments_for_quote(db_session, quote.id)

    assert len(unified) == 3
    assert unified[0]["source"] == "eworks_appointment"
    assert any(item["assignment_type"] == "estimator" and item["source"] == "manual" for item in unified)
    assert any(
        item["assignment_type"] == "engineer"
        and item["source"] == "manual"
        and item["assigned_user_email"] == "manual-eng@example.com"
        for item in unified
    )


def test_multiple_manual_assignees_can_exist(db_session, manager_user):
    quote = EworksQuote(eworks_quote_id=10023, quote_ref="Q-MULTI", customer_name="Customer")
    db_session.add(quote)
    db_session.commit()

    create_assignment(
        db_session,
        quote_id=quote.id,
        payload={
            "assignment_type": "estimator",
            "assignee_kind": "external",
            "assigned_user_email": "est1@example.com",
            "assigned_user_name": "Estimator One",
        },
        current_user=manager_user,
    )
    create_assignment(
        db_session,
        quote_id=quote.id,
        payload={
            "assignment_type": "engineer",
            "assignee_kind": "external",
            "assigned_user_email": "eng1@example.com",
            "assigned_user_name": "Engineer One",
        },
        current_user=manager_user,
    )

    manual = list_assignments_for_quote(db_session, quote.id)

    assert len(manual) == 2


def test_duplicate_email_type_updates_existing_manual(db_session, manager_user):
    quote = EworksQuote(eworks_quote_id=10024, quote_ref="Q-DEDUP", customer_name="Customer")
    db_session.add(quote)
    db_session.commit()

    first = create_assignment(
        db_session,
        quote_id=quote.id,
        payload={
            "assignment_type": "engineer",
            "assignee_kind": "external",
            "assigned_user_email": "dup@example.com",
            "assigned_user_name": "Engineer One",
            "notes": "First note",
        },
        current_user=manager_user,
    )
    second = create_assignment(
        db_session,
        quote_id=quote.id,
        payload={
            "assignment_type": "engineer",
            "assignee_kind": "external",
            "assigned_user_email": "dup@example.com",
            "assigned_user_name": "Engineer One",
            "notes": "Updated note",
        },
        current_user=manager_user,
    )

    manual = list_assignments_for_quote(db_session, quote.id)

    assert len(manual) == 1
    assert first["id"] == second["id"]
    assert manual[0]["notes"] == "Updated note"


def test_override_endpoint_replaces_manual_only(db_session, manager_user):
    quote, _job = _seed_quote_with_job(
        db_session,
        eworks_quote_id=10025,
        quote_ref="Q-OVERRIDE",
        eworks_job_id=20025,
        job_ref="JOB-OVERRIDE",
        user_name="User Abc",
        user_email="abc@example.com",
    )
    create_assignment(
        db_session,
        quote_id=quote.id,
        payload={
            "assignment_type": "engineer",
            "assignee_kind": "external",
            "assigned_user_email": "old@example.com",
            "assigned_user_name": "Old Engineer",
        },
        current_user=manager_user,
    )

    override_assignment(
        db_session,
        quote_id=quote.id,
        payload={
            "assignment_type": "engineer",
            "assignee_kind": "external",
            "assigned_user_email": "new@example.com",
            "assigned_user_name": "New Engineer",
        },
        current_user=manager_user,
    )

    manual = list_assignments_for_quote(db_session, quote.id)
    unified = build_unified_assignments_for_quote(db_session, quote.id)

    assert len(manual) == 2
    cancelled = [item for item in manual if item["status"] == "cancelled"]
    active = [item for item in manual if item["status"] != "cancelled"]
    assert len(cancelled) == 1
    assert len(active) == 1
    assert active[0]["assigned_user_email"] == "new@example.com"
    assert unified[0]["source"] == "eworks_appointment"
    assert unified[0]["assigned_user_email"] == "abc@example.com"


@patch("app.auth.dependencies.settings")
def test_safe_detail_api_returns_assignments_list(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    quote, _job = _seed_quote_with_job(
        db_session,
        eworks_quote_id=10026,
        quote_ref="Q-SAFE-LIST",
        eworks_job_id=20026,
        job_ref="JOB-SAFE-LIST",
        user_name="User Abc",
        user_email="abc@example.com",
    )

    resp = api_client.get(f"/api/v1/eworks-sync/quotes/{quote.id}/safe")

    assert resp.status_code == 200
    detail = resp.json()["data"]
    assert len(detail["assignments"]) == 1
    assert detail["assignments"][0]["source"] == "eworks_appointment"
    assert detail["appointment_assignee"]["email"] == "abc@example.com"


@patch("app.auth.dependencies.settings")
def test_create_assignment_api_does_not_remove_appointment(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    quote, _job = _seed_quote_with_job(
        db_session,
        eworks_quote_id=10027,
        quote_ref="Q-API-ADD",
        eworks_job_id=20027,
        job_ref="JOB-API-ADD",
        user_name="User Abc",
        user_email="abc@example.com",
    )

    create_resp = api_client.post(
        f"/api/v1/eworks-sync/quotes/{quote.id}/assignments",
        json={
            "assignment_type": "engineer",
            "assignee_kind": "external",
            "assigned_user_email": "manual@example.com",
            "assigned_user_name": "Manual Engineer",
        },
    )
    safe_resp = api_client.get(f"/api/v1/eworks-sync/quotes/{quote.id}/safe")

    assert create_resp.status_code == 200
    detail = safe_resp.json()["data"]
    assert len(detail["assignments"]) == 2
    assert detail["assignments"][0]["source"] == "eworks_appointment"
    assert detail["appointment_assignee"]["email"] == "abc@example.com"


@patch("app.auth.dependencies.settings")
def test_override_assignment_api(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    quote, _job = _seed_quote_with_job(
        db_session,
        eworks_quote_id=10028,
        quote_ref="Q-API-OVERRIDE",
        eworks_job_id=20028,
        job_ref="JOB-API-OVERRIDE",
        user_name="User Abc",
        user_email="abc@example.com",
    )
    api_client.post(
        f"/api/v1/eworks-sync/quotes/{quote.id}/assignments",
        json={
            "assignment_type": "engineer",
            "assignee_kind": "external",
            "assigned_user_email": "old@example.com",
            "assigned_user_name": "Old Engineer",
        },
    )

    override_resp = api_client.post(
        f"/api/v1/eworks-sync/quotes/{quote.id}/assignments/override",
        json={
            "assignment_type": "engineer",
            "assignee_kind": "external",
            "assigned_user_email": "new@example.com",
            "assigned_user_name": "New Engineer",
        },
    )
    list_resp = api_client.get(f"/api/v1/eworks-sync/quotes/{quote.id}/assignments")

    assert override_resp.status_code == 200
    assert override_resp.json()["data"]["assigned_user_email"] == "new@example.com"
    active_manual = [item for item in list_resp.json()["data"]["items"] if item["status"] != "cancelled"]
    assert len(active_manual) == 1
    assert active_manual[0]["assigned_user_email"] == "new@example.com"
