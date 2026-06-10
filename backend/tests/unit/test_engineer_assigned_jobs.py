"""Unit tests for engineer assigned jobs routing."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.types import AuthenticatedUser
from app.core.security import UserRole, get_password_hash
from app.models.eworks_sync import EworksJob, EworksJobAppointment, EworksQuote
from app.models.user import User
from app.services.engineer_assigned_jobs_service import list_assigned_jobs_for_engineer
from app.services.eworks_job_appointment_service import sync_job_appointments
from app.utils.html_text import html_to_plain_text

EWORKS_ACCESS_HTML = (
    "<span style=\"font-size: 12px;\"><strong>Access</strong>"
    "<br><li>Side gate</li></span>"
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
        EworksQuote.__table__,
        EworksJob.__table__,
        EworksJobAppointment.__table__,
    ]:
        table.create(engine, checkfirst=True)

    Session = sessionmaker(bind=engine)
    session = Session()
    now = datetime.now(timezone.utc)
    vitor_id = uuid4()
    abc_id = uuid4()
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
    abc = User(
        id=abc_id,
        email="abc@example.com",
        full_name="User Abc",
        password_hash=get_password_hash("eng22345"),
        role=UserRole.ENGINEER.value,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    session.add_all([vitor, abc])
    session.commit()
    yield session
    session.close()


def _appointment_payload(
    *,
    appointment_id: int,
    user_name: str,
    user_email: str,
) -> dict:
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


def _seed_job(
    db_session,
    *,
    eworks_job_id: int,
    job_ref: str,
    user_email: str,
    user_name: str,
    appointment_id: int,
    eworks_quote_id: int | None = None,
    quote_ref: str | None = None,
    description: str | None = None,
) -> EworksJob:
    if eworks_quote_id is not None:
        db_session.add(
            EworksQuote(
                eworks_quote_id=eworks_quote_id,
                quote_ref=quote_ref,
                customer_name="Customer",
                status="1",
            )
        )
        db_session.flush()
    job = EworksJob(
        eworks_job_id=eworks_job_id,
        job_ref=job_ref,
        eworks_quote_id=eworks_quote_id,
        customer_name="Customer",
        address="1 Job Street",
        description=description,
        raw_detail_payload=_appointment_payload(
            appointment_id=appointment_id,
            user_name=user_name,
            user_email=user_email,
        ),
    )
    db_session.add(job)
    db_session.flush()
    sync_job_appointments(db_session, job, raw_payload=job.raw_detail_payload)
    db_session.commit()
    db_session.refresh(job)
    return job


def _user(email: str, db_session) -> AuthenticatedUser:
    row = db_session.query(User).filter(User.email == email).one()
    return AuthenticatedUser(
        id=str(row.id),
        email=row.email,
        name=row.full_name,
        role=UserRole.ENGINEER,
        is_active=True,
        auth_provider="dev",
    )


def test_quote_linked_job_ref_appointment_not_in_assigned_jobs(db_session):
    _seed_job(
        db_session,
        eworks_job_id=34005,
        job_ref="JOB-34005",
        eworks_quote_id=29301,
        quote_ref="Q22143",
        appointment_id=66050,
        user_email="vitor.santo@theoptimalgroup.co.uk",
        user_name="Vitor Espirito Santo",
    )
    user = _user("vitor.santo@theoptimalgroup.co.uk", db_session)

    items = list_assigned_jobs_for_engineer(db_session, user)

    assert items == []


def test_true_job_without_quote_ref_appears_in_assigned_jobs(db_session):
    job = _seed_job(
        db_session,
        eworks_job_id=35001,
        job_ref="JOB-35001",
        appointment_id=66060,
        user_email="abc@example.com",
        user_name="User Abc",
    )
    user = _user("abc@example.com", db_session)

    items = list_assigned_jobs_for_engineer(db_session, user)

    assert len(items) == 1
    assert items[0]["job_ref"] == job.job_ref
    assert items[0]["quote_ref"] is None
    assert items[0]["source"] == "eworks_appointment"


def test_vitor_assigned_jobs_excludes_q22143_and_q22132(db_session):
    _seed_job(
        db_session,
        eworks_job_id=34005,
        job_ref="JOB-34005",
        eworks_quote_id=29306,
        quote_ref="Q22143",
        appointment_id=66054,
        user_email="vitor.santo@theoptimalgroup.co.uk",
        user_name="Vitor Espirito Santo",
    )
    _seed_job(
        db_session,
        eworks_job_id=34008,
        job_ref="JOB-34008",
        eworks_quote_id=29307,
        quote_ref="Q22132",
        appointment_id=66055,
        user_email="vitor.santo@theoptimalgroup.co.uk",
        user_name="Vitor Espirito Santo",
    )
    user = _user("vitor.santo@theoptimalgroup.co.uk", db_session)

    items = list_assigned_jobs_for_engineer(db_session, user)
    quote_refs = {item.get("quote_ref") for item in items}
    job_refs = {item.get("job_ref") for item in items}

    assert "Q22143" not in quote_refs
    assert "Q22132" not in quote_refs
    assert "JOB-34005" not in job_refs
    assert "JOB-34008" not in job_refs


def test_description_html_is_sanitized_in_assigned_jobs(db_session):
    _seed_job(
        db_session,
        eworks_job_id=35002,
        job_ref="JOB-35002",
        appointment_id=66061,
        user_email="abc@example.com",
        user_name="User Abc",
        description=EWORKS_ACCESS_HTML,
    )
    user = _user("abc@example.com", db_session)

    items = list_assigned_jobs_for_engineer(db_session, user)

    description = items[0]["description"]
    assert "<span" not in (description or "").lower()
    assert "Access" in description
    assert description == html_to_plain_text(EWORKS_ACCESS_HTML)
