"""PDF internal notes — generated calculation notes in internal/full PDFs only."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.calculation_session import CalculationSession
from app.models.client import Client
from app.models.client_alias import ClientAlias
from app.models.trade import Trade
from app.services.calculation_session_pdf_service import render_session_quote_pdf
from app.services.client_quote_service import render_public_client_quote_pdf
from app.services.manager_quote_pdf_service import render_manager_quote_pdf
from app.services.pdf_calculation_context_service import (
    build_combined_internal_notes_for_pdf,
    build_work_internal_calculation_note,
)
from app.schemas.calculation import CalculationBreakdown
from app.schemas.eworks_link import Step1Snapshot, Step2Snapshot, WorkBlockSnapshot, WorkBreakdownResult


GENERATED_INTERNAL_NOTE = """PRODUCT:
IMPORTANT INFO:
ACME Ltd Comms @ 20%
HOURLY QUOTE HELPER USED
BUDGET:
Materials: £110 / Parking: £100 / CC: £18 / OH: £43
TOTAL COST TO OPTIMAL:
Labour etc: £44 / Materials etc: £228
TOTAL CHARGE TO CLIENT:
Labour: £145 / Materials etc: £285
PROFIT ON JOB:
£158 / 37%"""

MANUAL_INTERNAL_NOTE = "Manual site access note from estimator."


def _visible_html(content: bytes, media_type: str) -> str:
    if media_type == "application/pdf":
        return ""
    html = content.decode("utf-8")
    return re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)


def _step1(*, quote_number: str = "Q-NOTES") -> dict:
    return {
        "quote_number": quote_number,
        "job_number": "JOB-NOTES",
        "client_name": "ACME Ltd",
        "trade_name": "Carpenter",
        "property_address": "1 Test Street",
        "engineer_name": "Alex Engineer",
    }


def _generated_breakdown(*, internal_notes: str | None = GENERATED_INTERNAL_NOTE) -> dict:
    return {
        "labour": [{"label": "Labour", "formula": "x", "total": "145.00"}],
        "materials": [{"label": "Materials", "formula": "x", "total": "285.00"}],
        "charges": [],
        "subtotal": "430.00",
        "vat_rate": "20",
        "vat_total": "86.00",
        "final_total": "516.00",
        "labour_charge_to_client": "145.00",
        "materials_parking_cc_charge": "285.00",
        "direct_labour_cost": "44.00",
        "profit_gbp": "158.00",
        "profit_pct": "37",
        "formula_version": "1.0.0",
        "internal_notes": internal_notes,
    }


def _single_work_step2(*, other_notes: str | None = None) -> dict:
    work = {
        "scope": "Supply and fit materials as scoped.",
        "skill_required": "Carpenter",
        "engineers_needed": 1,
        "engineer_time_value": 1.5,
    }
    if other_notes is not None:
        work["other_notes"] = other_notes
    return {"works": [work]}


def _ui_state(*, other_notes: str | None = None, include_generated: bool = True) -> dict:
    breakdown = _generated_breakdown(
        internal_notes=GENERATED_INTERNAL_NOTE if include_generated else None,
    )
    work_breakdown = {
        "work_index": 0,
        "scope": "Supply and fit materials as scoped.",
        "breakdown": dict(breakdown),
    }
    return {
        "current_step": 3,
        "max_reachable_step": 3,
        "last_result": {
            "breakdown": breakdown,
            "work_breakdowns": [work_breakdown],
            "internal_notes": GENERATED_INTERNAL_NOTE if include_generated else None,
        },
    }


@pytest.fixture()
def notes_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for model in (Client, ClientAlias, Trade, CalculationSession):
        model.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    client = Client(name="ACME Ltd", default_vat_rate=Decimal("20"))
    trade = Trade(name="Carpenter", is_active=True)
    db.add_all([client, trade])
    db.flush()

    session_id = uuid4()
    db.add(
        CalculationSession(
            id=session_id,
            session_token="token-notes",
            public_quote_token="public-token-notes",
            source="test",
            payload_snapshot={},
            step1_snapshot=_step1(),
            step2_snapshot=_single_work_step2(),
            ui_state=_ui_state(),
            client_id=client.id,
            trade_id=trade.id,
            expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
            status="submitted",
            submitted_at=datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc),
            locked=True,
        )
    )
    db.commit()
    return db, session_id


def test_build_work_internal_calculation_note_uses_breakdown_when_no_manual():
    step2 = Step2Snapshot.model_validate(_single_work_step2())
    breakdown = CalculationBreakdown.model_validate(_generated_breakdown())
    work_result = WorkBreakdownResult.model_validate(
        {
            "work_index": 0,
            "scope": step2.works[0].scope,
            "breakdown": breakdown.model_dump(mode="json"),
        }
    )

    note = build_work_internal_calculation_note(
        work_index=0,
        work_block=step2.works[0],
        work_result=work_result,
        quote_internal_notes=GENERATED_INTERNAL_NOTE,
        quote_breakdown=breakdown,
        work_count=1,
    )

    assert note is not None
    assert "TOTAL COST TO OPTIMAL" in note
    assert "PROFIT ON JOB" in note


def test_build_work_internal_calculation_note_includes_manual_and_generated():
    step2 = Step2Snapshot.model_validate(_single_work_step2(other_notes=MANUAL_INTERNAL_NOTE))
    breakdown = CalculationBreakdown.model_validate(_generated_breakdown())
    work_result = WorkBreakdownResult.model_validate(
        {
            "work_index": 0,
            "scope": step2.works[0].scope,
            "breakdown": breakdown.model_dump(mode="json"),
        }
    )

    note = build_work_internal_calculation_note(
        work_index=0,
        work_block=step2.works[0],
        work_result=work_result,
        quote_internal_notes=GENERATED_INTERNAL_NOTE,
        quote_breakdown=breakdown,
        work_count=1,
    )

    assert MANUAL_INTERNAL_NOTE in (note or "")
    assert "TOTAL COST TO OPTIMAL" in (note or "")
    assert note.index(MANUAL_INTERNAL_NOTE) < note.index("TOTAL COST TO OPTIMAL")


def test_internal_pdf_shows_generated_calculation_notes(notes_db):
    db, session_id = notes_db
    content, _, media_type = render_manager_quote_pdf(db, session_id=session_id, view="internal")
    html = _visible_html(content, media_type)
    if not html:
        pytest.skip("PDF renderer returned binary output")
    assert "TOTAL COST TO OPTIMAL" in html
    assert "PROFIT ON JOB" in html
    assert "Labour: £145" in html


def test_full_estimate_pdf_shows_generated_calculation_notes(notes_db):
    db, session_id = notes_db
    content, _, media_type = render_manager_quote_pdf(db, session_id=session_id, view="combined")
    html = _visible_html(content, media_type)
    if not html:
        pytest.skip("PDF renderer returned binary output")
    assert "TOTAL COST TO OPTIMAL" in html
    assert "PROFIT ON JOB" in html
    assert "Internal Notes" in html


def test_client_pdf_excludes_generated_calculation_notes(notes_db):
    db, session_id = notes_db
    content, _, media_type = render_manager_quote_pdf(db, session_id=session_id, view="client")
    html = _visible_html(content, media_type)
    if not html:
        pytest.skip("PDF renderer returned binary output")
    assert "TOTAL COST TO OPTIMAL" not in html
    assert "PROFIT ON JOB" not in html


def test_public_client_pdf_excludes_generated_calculation_notes(notes_db):
    db, _ = notes_db
    content, _, media_type = render_public_client_quote_pdf(db, "public-token-notes")
    html = _visible_html(content, media_type)
    if not html:
        pytest.skip("PDF renderer returned binary output")
    assert "TOTAL COST TO OPTIMAL" not in html
    assert "PROFIT ON JOB" not in html


def test_full_estimate_pdf_shows_manual_and_generated_notes(notes_db):
    db, session_id = notes_db
    session = db.get(CalculationSession, session_id)
    session.step2_snapshot = _single_work_step2(other_notes=MANUAL_INTERNAL_NOTE)
    db.commit()

    content, _, media_type = render_session_quote_pdf(
        db,
        session_id=session_id,
        session_token="token-notes",
        read_only=True,
    )
    html = _visible_html(content, media_type)
    if not html:
        pytest.skip("PDF renderer returned binary output")
    assert MANUAL_INTERNAL_NOTE in html
    assert "TOTAL COST TO OPTIMAL" in html


def test_combined_internal_notes_for_single_work(notes_db):
    db, session_id = notes_db
    session = db.get(CalculationSession, session_id)
    step2 = Step2Snapshot.model_validate(session.step2_snapshot)
    breakdown = CalculationBreakdown.model_validate(_generated_breakdown())
    work_result = WorkBreakdownResult.model_validate(session.ui_state["last_result"]["work_breakdowns"][0])

    note = build_combined_internal_notes_for_pdf(
        work_blocks=step2.works,
        work_breakdowns=[work_result],
        quote_internal_notes=GENERATED_INTERNAL_NOTE,
        quote_breakdown=breakdown,
    )

    assert note is not None
    assert "PROFIT ON JOB" in note
