"""Unit tests for engineer assigned estimates routing."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.types import AuthenticatedUser
from app.core.security import UserRole, get_password_hash
from app.models.calculation_session import CalculationSession
from app.models.eworks_sync import EworksJob, EworksJobAppointment, EworksQuote, EworksQuoteAppointment
from app.models.quote_assignment import EworksQuoteAssignment
from app.models.support import AuditLog
from app.models.user import User
from app.services.engineer_assigned_estimates_service import list_assigned_estimates_for_engineer
from app.services.eworks_job_appointment_service import sync_job_appointments
from app.services.quote_assignment_service import list_assignments_for_user
from app.utils.html_text import html_to_plain_text

EWORKS_ACCESS_HTML = (
    "&lt;span style=&quot;font-size: 12px;&quot;&gt;&lt;strong&gt;Access&lt;/strong&gt;"
    "&lt;br&gt;&lt;li&gt;Side gate&lt;/li&gt;&lt;/span&gt;"
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
    session.add(vitor)
    session.commit()
    yield session
    session.close()


def _engineer_user(db_session) -> AuthenticatedUser:
    user = db_session.query(User).filter(User.email == "vitor.santo@theoptimalgroup.co.uk").one()
    return AuthenticatedUser(
        id=str(user.id),
        email=user.email,
        name=user.full_name,
        role=UserRole.ENGINEER,
        is_active=True,
        auth_provider="dev",
    )


def _appointment_payload(
    *,
    appointment_id: int,
    user_name: str,
    user_email: str,
    start_date: str = "2026-06-10T10:00:00.000Z",
    end_date: str = "2026-06-10T11:30:00.000Z",
) -> dict:
    return {
        "appointments": [
            {
                "id": appointment_id,
                "status_text": "Accepted",
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


def _seed_quote_linked_job(
    db_session,
    *,
    eworks_quote_id: int,
    quote_ref: str,
    eworks_job_id: int,
    job_ref: str,
    appointment_id: int,
    description: str | None = None,
    status: str = "1",
) -> tuple[EworksQuote, EworksJob]:
    quote = EworksQuote(
        eworks_quote_id=eworks_quote_id,
        quote_ref=quote_ref,
        customer_name="Test Customer",
        description=description,
        status=status,
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


def test_job_ref_and_quote_ref_appointment_appears_in_assigned_estimates(db_session):
    quote, job = _seed_quote_linked_job(
        db_session,
        eworks_quote_id=29301,
        quote_ref="Q22143",
        eworks_job_id=34005,
        job_ref="JOB-34005",
        appointment_id=66050,
    )
    user = _engineer_user(db_session)

    items = list_assigned_estimates_for_engineer(db_session, user)

    assert len(items) == 1
    assert items[0]["quote_ref"] == quote.quote_ref
    assert items[0]["job_ref"] == job.job_ref
    assert items[0]["source"] == "eworks_appointment"
    assert items[0]["assigned_user_email"] == user.email
    assert items[0]["can_start_estimate"] is True
    assert items[0]["customer_name"] == quote.customer_name
    assert items[0]["site_address"] == "1 Test Street"
    assert items[0]["eworks_job_id"] == job.eworks_job_id


def test_linked_job_appointment_for_draft_quote_appears_in_assigned_estimates(db_session):
    quote, _job = _seed_quote_linked_job(
        db_session,
        eworks_quote_id=29302,
        quote_ref="Q22132",
        eworks_job_id=34006,
        job_ref="JOB-34006",
        appointment_id=66051,
    )
    user = _engineer_user(db_session)

    items = list_assigned_estimates_for_engineer(db_session, user)

    assert any(item["quote_ref"] == quote.quote_ref for item in items)


def test_quote_level_appointment_appears_in_assigned_estimates(db_session):
    quote = EworksQuote(
        eworks_quote_id=29303,
        quote_ref="Q-QUOTE-ONLY",
        customer_name="Quote Customer",
        status="1",
        raw_payload={"site_address": "2 Quote Street"},
    )
    db_session.add(quote)
    db_session.flush()
    db_session.add(
        EworksQuoteAppointment(
            eworks_quote_id=quote.eworks_quote_id,
            dedupe_key="id:66052",
            appointment_id=66052,
            user_name="Vitor Espirito Santo",
            user_email="vitor.santo@theoptimalgroup.co.uk",
            status="Awaiting",
            is_sales_appointment=True,
            start_at="2026-06-11T09:00:00.000Z",
            end_at="2026-06-11T10:00:00.000Z",
        )
    )
    db_session.commit()
    user = _engineer_user(db_session)

    items = list_assigned_estimates_for_engineer(db_session, user)

    assert len(items) == 1
    assert items[0]["quote_ref"] == "Q-QUOTE-ONLY"
    assert items[0]["appointment_id"] == 66052


def test_manual_engineer_assignment_appears_in_assigned_estimates(db_session):
    quote = EworksQuote(
        eworks_quote_id=29304,
        quote_ref="Q-MANUAL",
        customer_name="Manual Customer",
        status="1",
    )
    db_session.add(quote)
    db_session.flush()
    engineer = db_session.query(User).filter(User.email == "vitor.santo@theoptimalgroup.co.uk").one()
    db_session.add(
        EworksQuoteAssignment(
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
    )
    db_session.commit()
    user = _engineer_user(db_session)

    items = list_assigned_estimates_for_engineer(db_session, user)

    assert len(items) == 1
    assert items[0]["source"] == "manual"
    assert items[0]["quote_ref"] == "Q-MANUAL"


def test_description_html_is_sanitized_in_assigned_estimates(db_session):
    _seed_quote_linked_job(
        db_session,
        eworks_quote_id=29305,
        quote_ref="Q-HTML",
        eworks_job_id=34007,
        job_ref="JOB-34007",
        appointment_id=66053,
        description=EWORKS_ACCESS_HTML,
    )
    user = _engineer_user(db_session)

    items = list_assigned_estimates_for_engineer(db_session, user)

    description = items[0]["quote_summary"]["description"]
    assert "<span" not in (description or "").lower()
    assert "Access" in description
    assert "Side gate" in description
    assert description == html_to_plain_text(EWORKS_ACCESS_HTML)


def test_vitor_assigned_estimates_includes_q22143_and_q22132_when_draft(db_session):
    _seed_quote_linked_job(
        db_session,
        eworks_quote_id=29306,
        quote_ref="Q22143",
        eworks_job_id=34005,
        job_ref="JOB-34005",
        appointment_id=66054,
        status="1",
    )
    _seed_quote_linked_job(
        db_session,
        eworks_quote_id=29307,
        quote_ref="Q22132",
        eworks_job_id=34008,
        job_ref="JOB-34008",
        appointment_id=66055,
        status="1",
    )
    user = _engineer_user(db_session)

    items = list_assignments_for_user(db_session, user)
    quote_refs = {item["quote_ref"] for item in items}

    assert "Q22143" in quote_refs
    assert "Q22132" in quote_refs


def test_vitor_assigned_estimates_excludes_q22143_and_q22132_when_not_draft(db_session):
    _seed_quote_linked_job(
        db_session,
        eworks_quote_id=29306,
        quote_ref="Q22143",
        eworks_job_id=34005,
        job_ref="JOB-34005",
        appointment_id=66054,
        status="4",
    )
    _seed_quote_linked_job(
        db_session,
        eworks_quote_id=29307,
        quote_ref="Q22132",
        eworks_job_id=34008,
        job_ref="JOB-34008",
        appointment_id=66055,
        status="4",
    )
    user = _engineer_user(db_session)

    items = list_assignments_for_user(db_session, user)
    quote_refs = {item["quote_ref"] for item in items}

    assert "Q22143" not in quote_refs
    assert "Q22132" not in quote_refs


@pytest.mark.parametrize("status", ["2", "4", "6", "7"])
def test_processed_rejected_accepted_converted_quote_linked_appointment_excluded(
    db_session, status: str
):
    _seed_quote_linked_job(
        db_session,
        eworks_quote_id=29400 + int(status),
        quote_ref=f"Q-NON-DRAFT-{status}",
        eworks_job_id=34100 + int(status),
        job_ref=f"JOB-NON-DRAFT-{status}",
        appointment_id=66100 + int(status),
        status=status,
    )
    user = _engineer_user(db_session)

    items = list_assigned_estimates_for_engineer(db_session, user)

    assert items == []


def test_manual_assignment_on_non_draft_hidden(db_session):
    quote = EworksQuote(
        eworks_quote_id=29310,
        quote_ref="Q-MANUAL-NON-DRAFT",
        customer_name="Manual Customer",
        status="4",
    )
    db_session.add(quote)
    db_session.flush()
    engineer = db_session.query(User).filter(User.email == "vitor.santo@theoptimalgroup.co.uk").one()
    db_session.add(
        EworksQuoteAssignment(
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
    )
    db_session.commit()
    user = _engineer_user(db_session)

    items = list_assigned_estimates_for_engineer(db_session, user)

    assert items == []


def test_quote_level_appointment_on_non_draft_hidden(db_session):
    quote = EworksQuote(
        eworks_quote_id=29311,
        quote_ref="Q-QUOTE-NON-DRAFT",
        customer_name="Quote Customer",
        status="4",
    )
    db_session.add(quote)
    db_session.flush()
    db_session.add(
        EworksQuoteAppointment(
            eworks_quote_id=quote.eworks_quote_id,
            dedupe_key="id:66060",
            appointment_id=66060,
            user_name="Vitor Espirito Santo",
            user_email="vitor.santo@theoptimalgroup.co.uk",
            status="Awaiting",
            is_sales_appointment=True,
            start_at="2026-06-11T09:00:00.000Z",
            end_at="2026-06-11T10:00:00.000Z",
        )
    )
    db_session.commit()
    user = _engineer_user(db_session)

    items = list_assigned_estimates_for_engineer(db_session, user)

    assert items == []
