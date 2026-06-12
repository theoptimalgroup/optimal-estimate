"""PDF estimator identity — Estimated By / WHO QUOTED resolution."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.types import AuthenticatedUser
from app.core.security import UserRole
from app.models.calculation_session import CalculationSession
from app.models.client import Client
from app.models.client_alias import ClientAlias
from app.models.quote_assignment import EworksQuoteAssignment
from app.models.trade import Trade
from app.models.user import User
from app.schemas.calculation import CalculationBreakdown
from app.schemas.eworks_link import Step1Snapshot, Step2Snapshot, WorkBlockSnapshot
from app.services.calculation_session_service import render_combined_works_pdf
from app.services.eworks_pdf_context_service import build_eworks_estimate_pdf_context
from app.services.eworks_questionnaire_service import build_internal_notes_context
from app.services.pdf_calculation_context_service import build_work_internal_calculation_note
from app.services.pdf_estimator_identity_service import (
    patch_who_quoted_in_internal_notes,
    resolve_estimated_by_for_pdf,
)


def _step1(**overrides) -> Step1Snapshot:
    base = {
        "quote_number": "Q-EST",
        "job_number": "JOB-EST",
        "engineer_name": "eWorks Appointment Engineer",
        "client_name": "ACME Ltd",
        "trade_name": "Carpenter",
        "property_address": "1 Test Street",
    }
    base.update(overrides)
    return Step1Snapshot(**base)


def _step2() -> Step2Snapshot:
    return Step2Snapshot(
        works=[
            WorkBlockSnapshot(
                scope="Test scope",
                skill_required="Carpenter",
                best_engineer="Site Best Engineer",
                engineers_needed=1,
                engineer_time_value=1,
            )
        ]
    )


def _breakdown() -> CalculationBreakdown:
    return CalculationBreakdown(
        labour=[],
        materials=[],
        charges=[],
        subtotal=Decimal("100"),
        vat_rate=Decimal("20"),
        vat_total=Decimal("20"),
        final_total=Decimal("120"),
        formula_version="test",
        internal_notes="LINK/S & QUANTITY:\nWHO QUOTED: eWorks Appointment Engineer\nBEST ENGINEER: Site Best Engineer",
    )


@pytest.fixture()
def estimator_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for model in (User, Client, ClientAlias, Trade, CalculationSession, EworksQuoteAssignment):
        model.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    client = Client(name="ACME Ltd", default_vat_rate=Decimal("20"))
    trade = Trade(name="Carpenter", is_active=True)
    estimator = User(
        email="estimator@example.com",
        full_name="App Estimator",
        password_hash="hash",
        role="estimator",
        is_active=True,
    )
    assignee = User(
        email="assigned@example.com",
        full_name="Assigned Estimator",
        password_hash="hash",
        role="estimator",
        is_active=True,
    )
    db.add_all([client, trade, estimator, assignee])
    db.flush()

    session_id = uuid4()
    db.add(
        CalculationSession(
            id=session_id,
            session_token="token-est",
            source="test",
            payload_snapshot={},
            step1_snapshot=_step1().model_dump(mode="json"),
            step2_snapshot=_step2().model_dump(mode="json"),
            ui_state={
                "last_result": {
                    "breakdown": _breakdown().model_dump(mode="json"),
                    "work_breakdowns": [
                        {
                            "work_index": 0,
                            "scope": "Test scope",
                            "breakdown": _breakdown().model_dump(mode="json"),
                        }
                    ],
                }
            },
            client_id=client.id,
            trade_id=trade.id,
            expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
            status="submitted",
            submitted_at=datetime(2026, 6, 6, tzinfo=timezone.utc),
            locked=True,
        )
    )
    db.commit()
    return db, session_id, estimator, assignee


def test_pdf_uses_submitted_by_name_when_present(estimator_db):
    db, session_id, _, _ = estimator_db
    session = db.get(CalculationSession, session_id)
    session.submitted_by_name = "Submitted Estimator"
    db.commit()

    step1 = Step1Snapshot.model_validate(session.step1_snapshot)
    resolved = resolve_estimated_by_for_pdf(db, session, step1)
    assert resolved == "Submitted Estimator"


def test_pdf_does_not_use_step1_engineer_name_when_submitter_exists(estimator_db):
    db, session_id, _, _ = estimator_db
    session = db.get(CalculationSession, session_id)
    session.submitted_by_name = "Submitted Estimator"
    db.commit()

    step1 = Step1Snapshot.model_validate(session.step1_snapshot)
    assert step1.engineer_name == "eWorks Appointment Engineer"
    assert resolve_estimated_by_for_pdf(db, session, step1) != step1.engineer_name


def test_pdf_uses_assigned_estimator_when_submitter_missing(estimator_db):
    db, session_id, _, assignee = estimator_db
    session = db.get(CalculationSession, session_id)
    db.add(
        EworksQuoteAssignment(
            synced_quote_id=1,
            eworks_quote_id=1,
            quote_ref="Q-EST",
            assignment_type="estimator",
            assignee_kind="registered",
            assigned_user_id=assignee.id,
            assigned_user_email=assignee.email,
            assigned_user_name=assignee.full_name,
            status="assigned",
            calculation_session_id=session_id,
        )
    )
    db.commit()

    step1 = Step1Snapshot.model_validate(session.step1_snapshot)
    assert resolve_estimated_by_for_pdf(db, session, step1) == "Assigned Estimator"


def test_pdf_uses_current_user_when_no_submitter_or_assignment(estimator_db):
    db, session_id, estimator, _ = estimator_db
    session = db.get(CalculationSession, session_id)
    step1 = Step1Snapshot.model_validate(session.step1_snapshot)
    current_user = AuthenticatedUser(
        id=str(estimator.id),
        email=estimator.email,
        name=estimator.full_name,
        role=UserRole.ESTIMATOR,
        is_active=True,
        auth_provider="local",
    )
    assert resolve_estimated_by_for_pdf(db, session, step1, current_user=current_user) == "App Estimator"


def test_step1_engineer_name_is_only_fallback(estimator_db):
    db, session_id, _, _ = estimator_db
    session = db.get(CalculationSession, session_id)
    step1 = Step1Snapshot.model_validate(session.step1_snapshot)
    assert resolve_estimated_by_for_pdf(db, session, step1) == "eWorks Appointment Engineer"


def test_who_quoted_in_internal_notes_uses_estimator_identity():
    step1 = _step1()
    block = _step2().works[0]
    context = build_internal_notes_context(step1, block, who_quoted="Submitted Estimator")
    assert context.who_quoted == "Submitted Estimator"
    assert context.best_engineer == "Site Best Engineer"


def test_best_engineer_unchanged_in_internal_notes():
    step1 = _step1()
    block = _step2().works[0]
    context = build_internal_notes_context(step1, block, who_quoted="Submitted Estimator")
    assert context.best_engineer == "Site Best Engineer"


def test_patch_who_quoted_replaces_cached_line():
    notes = "WHO QUOTED: eWorks Appointment Engineer\nBEST ENGINEER: Site Best Engineer"
    patched = patch_who_quoted_in_internal_notes(notes, "Submitted Estimator")
    assert "WHO QUOTED: Submitted Estimator" in patched
    assert "eWorks Appointment Engineer" not in patched
    assert "BEST ENGINEER: Site Best Engineer" in patched


def test_build_eworks_pdf_context_uses_estimated_by_label():
    step1 = _step1()
    step2 = _step2()
    breakdown = _breakdown()
    context = build_eworks_estimate_pdf_context(
        step1=step1,
        step2=step2,
        breakdown=breakdown,
        client_view={"calculation": breakdown.model_dump(mode="json")},
        estimated_by_name="Submitted Estimator",
        show_internal_notes=False,
    )
    assert context["estimation_fields"][0]["label"] == "Estimated By"
    assert context["estimation_fields"][0]["value"] == "Submitted Estimator"
    assert "eWorks Appointment Engineer" not in context["header_line"]


def test_client_and_optimal_pdf_use_same_estimated_by(estimator_db):
    db, session_id, _, _ = estimator_db
    session = db.get(CalculationSession, session_id)
    session.submitted_by_name = "Submitted Estimator"
    db.commit()

    client_content, _, _ = render_combined_works_pdf(
        db,
        session_id=session_id,
        work_indexes=[0],
        view_type="client",
    )
    optimal_content, _, _ = render_combined_works_pdf(
        db,
        session_id=session_id,
        work_indexes=[0],
        view_type="optimal",
    )
    assert b"Submitted Estimator" in client_content
    assert b"Submitted Estimator" in optimal_content


def test_pdf_internal_notes_who_quoted_matches_estimator(estimator_db):
    db, session_id, _, _ = estimator_db
    session = db.get(CalculationSession, session_id)
    session.submitted_by_name = "Submitted Estimator"
    db.commit()

    step2 = Step2Snapshot.model_validate(session.step2_snapshot)
    breakdown = _breakdown()
    note = build_work_internal_calculation_note(
        work_index=0,
        work_block=step2.works[0],
        work_result=None,
        quote_internal_notes=breakdown.internal_notes,
        quote_breakdown=breakdown,
        work_count=1,
        who_quoted="Submitted Estimator",
    )
    assert note is not None
    assert "WHO QUOTED: Submitted Estimator" in note
    assert "BEST ENGINEER: Site Best Engineer" in note
