"""PDF calculation consistency — all views must match submitted quote totals."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.calculation_session import CalculationSession
from app.models.calculation_session_version import CalculationSessionVersion
from app.models.client import Client
from app.models.client_alias import ClientAlias
from app.models.trade import Trade
from app.services.calculation_session_pdf_service import render_session_quote_pdf
from app.services.calculation_session_service import render_combined_works_pdf
from app.services.client_quote_service import get_public_client_quote
from app.services.manager_quote_pdf_service import render_manager_quote_pdf
from app.services.pdf_calculation_context_service import (
    build_pdf_calculation_context,
    quote_level_totals_for_works,
    resolve_session_calculation_result,
    session_blocks_recalculation,
)
from app.schemas.calculation import CalculationBreakdown, LineBreakdown
from app.schemas.eworks_link import WorkBreakdownResult


# Known fixture: works £420 + additional charges £40 = £460 ex-VAT; VAT £92; final £552
KNOWN_WORKS_SUBTOTAL = Decimal("420")
KNOWN_ADDITIONAL_CHARGES = Decimal("40")
KNOWN_SUBTOTAL = Decimal("460")
KNOWN_VAT = Decimal("92")
KNOWN_FINAL_TOTAL = Decimal("552")


def _step1(*, quote_number: str = "Q552") -> dict:
    return {
        "quote_number": quote_number,
        "job_number": "JOB-552",
        "client_name": "ACME Ltd",
        "trade_name": "Carpenter",
        "property_address": "1 Test Street",
        "engineer_name": "Alex Engineer",
    }


def _552_step2() -> dict:
    return {
        "works": [
            {"scope": "Work one scope", "product_code": "P-001"},
            {"scope": "Work two scope", "product_code": "P-002"},
        ],
        "congestion_required": True,
        "congestion_amount": "15.00",
        "travel_charge": "25.00",
    }


def _552_ui_state(*, final_total: str = "552.00") -> dict:
    work_breakdowns = [
        {
            "work_index": 0,
            "scope": "Work one scope",
            "breakdown": {
                "labour": [{"label": "Labour", "formula": "x", "total": "200.00"}],
                "materials": [{"label": "Materials", "formula": "x", "total": "100.00"}],
                "charges": [],
                "subtotal": "300.00",
                "vat_rate": "20",
                "vat_total": "60.00",
                "final_total": "360.00",
                "labour_charge_to_client": "200.00",
                "materials_parking_cc_charge": "100.00",
                "direct_labour_cost": "120.00",
                "profit_gbp": "80.00",
                "formula_version": "1.0.0",
            },
        },
        {
            "work_index": 1,
            "scope": "Work two scope",
            "breakdown": {
                "labour": [{"label": "Labour", "formula": "x", "total": "100.00"}],
                "materials": [{"label": "Materials", "formula": "x", "total": "20.00"}],
                "charges": [],
                "subtotal": "120.00",
                "vat_rate": "20",
                "vat_total": "24.00",
                "final_total": "144.00",
                "labour_charge_to_client": "100.00",
                "materials_parking_cc_charge": "20.00",
                "direct_labour_cost": "60.00",
                "profit_gbp": "40.00",
                "formula_version": "1.0.0",
            },
        },
    ]
    breakdown = {
        "labour": [{"label": "Labour", "formula": "x", "total": "300.00"}],
        "materials": [{"label": "Materials", "formula": "x", "total": "120.00"}],
        "charges": [
            {"label": "Congestion", "formula": "x", "total": "15.00"},
            {"label": "Travel", "formula": "x", "total": "25.00"},
        ],
        "subtotal": str(KNOWN_SUBTOTAL),
        "vat_rate": "20",
        "vat_total": str(KNOWN_VAT),
        "final_total": final_total,
        "labour_charge_to_client": "300.00",
        "materials_parking_cc_charge": "120.00",
        "profit_gbp": "120.00",
        "formula_version": "1.0.0",
    }
    return {
        "current_step": 3,
        "max_reachable_step": 3,
        "last_result": {
            "breakdown": breakdown,
            "work_breakdowns": work_breakdowns,
            "internal_notes": "Combined internal notes",
        },
    }


@pytest.fixture()
def calc_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for model in (Client, ClientAlias, Trade, CalculationSession, CalculationSessionVersion):
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
            session_token="token-552",
            public_quote_token="public-token-552",
            source="test",
            payload_snapshot={},
            step1_snapshot=_step1(),
            step2_snapshot=_552_step2(),
            ui_state=_552_ui_state(),
            client_id=client.id,
            trade_id=trade.id,
            expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
            status="submitted",
            submitted_at=datetime(2026, 6, 5, 12, 0, tzinfo=timezone.utc),
            locked=True,
        )
    )
    db.commit()
    return db, session_id


def _extract_grand_total(content: bytes, media_type: str) -> str | None:
    text = content.decode("utf-8") if media_type != "application/pdf" else ""
    if not text:
        return None
    visible = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    match = re.search(r"Quote Total[^£]*£([\d,]+\.\d{2})", visible, re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.search(r"Final total[^£]*£([\d,]+\.\d{2})", visible, re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.search(r'"final_total":\s*"£([\d,]+\.\d{2})"', visible)
    return match.group(1) if match else None


def _normalize_amount(value: str) -> Decimal:
    return Decimal(value.replace(",", ""))


@pytest.mark.parametrize(
    "view,render_fn",
    [
        ("client", lambda db, sid: render_manager_quote_pdf(db, session_id=sid, view="client")),
        ("internal", lambda db, sid: render_manager_quote_pdf(db, session_id=sid, view="internal")),
        ("combined", lambda db, sid: render_manager_quote_pdf(db, session_id=sid, view="combined")),
        ("all-trades", lambda db, sid: render_manager_quote_pdf(db, session_id=sid, view="all-trades")),
    ],
)
def test_all_manager_pdfs_match_submitted_total_552(calc_db, view, render_fn):
    db, session_id = calc_db
    content, _, media_type = render_fn(db, session_id)
    assert len(content) > 0
    grand = _extract_grand_total(content, media_type)
    if grand is not None:
        assert _normalize_amount(grand) == KNOWN_FINAL_TOTAL, view


@patch("app.services.calculation_session_service.calculate_session")
def test_submitted_session_never_recalculates(mock_calculate, calc_db):
    db, session_id = calc_db
    session = db.get(CalculationSession, session_id)
    assert session_blocks_recalculation(session)

    result, source = resolve_session_calculation_result(db, session, allow_recalculate=False)
    assert source == "cached"
    assert Decimal(str(result["breakdown"]["final_total"])) == KNOWN_FINAL_TOTAL
    mock_calculate.assert_not_called()

    render_manager_quote_pdf(db, session_id=session_id, view="client")
    render_manager_quote_pdf(db, session_id=session_id, view="internal")
    render_manager_quote_pdf(db, session_id=session_id, view="combined")
    mock_calculate.assert_not_called()


def test_client_and_internal_pdfs_use_quote_level_total_not_per_work_sum(calc_db):
    """Summing per-work final totals would yield £504; quote-level total is £552."""
    db, session_id = calc_db
    per_work_sum = Decimal("360") + Decimal("144")
    assert per_work_sum == Decimal("504")
    assert per_work_sum != KNOWN_FINAL_TOTAL

    for view_type in ("client", "optimal"):
        content, _, media_type = render_combined_works_pdf(
            db,
            session_id=session_id,
            work_indexes=[0, 1],
            view_type=view_type,
        )
        grand = _extract_grand_total(content, media_type)
        assert grand is not None
        assert _normalize_amount(grand) == KNOWN_FINAL_TOTAL, view_type


def test_additional_charges_counted_once_at_quote_level(calc_db):
    db, session_id = calc_db
    ctx = build_pdf_calculation_context(db, db.get(CalculationSession, session_id), allow_recalculate=False)
    charge_total = sum((line.total for line in ctx.breakdown.charges), Decimal("0"))
    assert charge_total == KNOWN_ADDITIONAL_CHARGES
    assert ctx.breakdown.subtotal == KNOWN_WORKS_SUBTOTAL + KNOWN_ADDITIONAL_CHARGES

    subtotal, vat, final = quote_level_totals_for_works(
        breakdown=ctx.breakdown,
        work_breakdowns=ctx.work_breakdowns,
        work_indexes=[0, 1],
        all_work_indexes={0, 1},
    )
    assert subtotal == KNOWN_SUBTOTAL
    assert vat == KNOWN_VAT
    assert final == KNOWN_FINAL_TOTAL


def test_public_client_quote_matches_submitted_total(calc_db):
    db, _ = calc_db
    quote = get_public_client_quote(db, "public-token-552")
    assert quote.summary.total == KNOWN_FINAL_TOTAL
    assert quote.summary.additional_charges == KNOWN_ADDITIONAL_CHARGES


def test_version_history_pdf_uses_stored_calculation_result(calc_db):
    db, session_id = calc_db
    session = db.get(CalculationSession, session_id)
    version_one_total = "400.00"
    db.add(
        CalculationSessionVersion(
            session_id=session_id,
            version_number=1,
            step1_snapshot=session.step1_snapshot,
            step2_snapshot=session.step2_snapshot,
            calculation_result=_552_ui_state(final_total=version_one_total)["last_result"],
            submitted_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
            status="superseded",
            is_current=False,
        )
    )
    db.commit()

    content, _, media_type = render_manager_quote_pdf(
        db,
        session_id=session_id,
        view="client",
        version_number=1,
    )
    grand = _extract_grand_total(content, media_type)
    assert grand is not None
    assert _normalize_amount(grand) == Decimal(version_one_total)

    current_content, _, current_media = render_manager_quote_pdf(
        db,
        session_id=session_id,
        view="client",
    )
    current_grand = _extract_grand_total(current_content, current_media)
    assert current_grand is not None
    assert _normalize_amount(current_grand) == KNOWN_FINAL_TOTAL


def test_selected_estimate_session_pdf_uses_that_session_totals(calc_db):
    """Two submitted sessions: PDF totals must follow the requested session_id."""
    db, session_a = calc_db
    client = db.query(Client).one()
    trade = db.query(Trade).one()

    session_b = uuid4()
    db.add(
        CalculationSession(
            id=session_b,
            session_token="token-other",
            source="test",
            payload_snapshot={},
            step1_snapshot=_step1(quote_number="Q552-B"),
            step2_snapshot=_552_step2(),
            ui_state=_552_ui_state(final_total="600.00"),
            client_id=client.id,
            trade_id=trade.id,
            expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
            status="submitted",
            submitted_at=datetime(2026, 6, 6, tzinfo=timezone.utc),
            locked=True,
        )
    )
    db.commit()

    content_a, _, media_a = render_manager_quote_pdf(db, session_id=session_a, view="client")
    content_b, _, media_b = render_manager_quote_pdf(db, session_id=session_b, view="client")

    grand_a = _extract_grand_total(content_a, media_a)
    grand_b = _extract_grand_total(content_b, media_b)
    assert grand_a is not None and grand_b is not None
    assert _normalize_amount(grand_a) == KNOWN_FINAL_TOTAL
    assert _normalize_amount(grand_b) == Decimal("600.00")


@patch("app.services.calculation_session_pdf_service.calculate_session")
def test_full_estimate_pdf_uses_cached_breakdown(mock_calculate, calc_db):
    db, session_id = calc_db
    content, _, media_type = render_session_quote_pdf(
        db,
        session_id=session_id,
        session_token="token-552",
        read_only=True,
    )
    assert len(content) > 0
    mock_calculate.assert_not_called()
    if media_type != "application/pdf":
        assert "552.00" in content.decode("utf-8")


def test_build_pdf_context_parses_work_breakdowns(calc_db):
    db, session_id = calc_db
    ctx = build_pdf_calculation_context(
        db,
        db.get(CalculationSession, session_id),
        allow_recalculate=False,
        view_type="test",
    )
    assert isinstance(ctx.breakdown, CalculationBreakdown)
    assert len(ctx.work_breakdowns) == 2
    assert all(isinstance(item, WorkBreakdownResult) for item in ctx.work_breakdowns)
    assert ctx.breakdown.final_total == KNOWN_FINAL_TOTAL
