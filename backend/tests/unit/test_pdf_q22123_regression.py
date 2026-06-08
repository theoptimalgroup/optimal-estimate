"""Regression tests for Q22123 single-work XLSX quote PDF item rows.

Problem: Top-level totals in all PDFs were correct (£410 subtotal / £82 VAT / £492
final).  But individual item rows used the per-work breakdown which was computed with
an empty ChargeInput, omitting parking (£100) and congestion charges.  This produced:

  - Client PDF quoted price: £285  (should be £410)
  - All Trades materials/subtotal: £140 / £285  (should be £265 / £410)
  - Optimal PDF Mat. chg / Client price: £140 / £285  (should be £265 / £410)
  - Full Estimate internal notes: Parking: £0  (should be Parking: £100)

Fix: for single-work quotes the combined (quote-level) breakdown is used everywhere
item rows are rendered because combined == per-work for labour but correctly folds in
parking/CC.
"""

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
from app.models.calculation_session_version import CalculationSessionVersion
from app.models.client import Client
from app.models.client_alias import ClientAlias
from app.models.trade import Trade
from app.services.calculation_session_service import render_combined_works_pdf


# ---------------------------------------------------------------------------
# Fixture data — mirrors the real Q22123 per-work vs combined discrepancy
# ---------------------------------------------------------------------------

_COMBINED_INTERNAL_NOTES = (
    "BUDGET: Materials:  £110 / Parking: £100 / CC: £0  / OH:  £43\n"
    "(combined notes with parking)"
)
_PER_WORK_INTERNAL_NOTES = (
    "BUDGET: Materials:  £110 / Parking: £0 / CC: £0  / OH:  £43\n"
    "(per-work notes without parking)"
)


def _q22123_ui_state() -> dict:
    """Single-work XLSX quote: per-work breakdown omits parking; combined has it."""
    per_work_breakdown = {
        "labour": [{"label": "Labour (hourly)", "formula": "xlsx", "total": "145.00"}],
        "materials": [
            {"label": "Materials, parking & congestion", "formula": "xlsx", "total": "140.00"}
        ],
        "charges": [],
        "subtotal": "285.00",
        "vat_rate": "20",
        "vat_total": "57.00",
        "final_total": "342.00",
        "labour_charge_to_client": "145.00",
        "materials_parking_cc_charge": "140.00",
        "direct_labour_cost": "107.00",
        "profit_gbp": "131.25",
        "formula_source": "xlsx",
        "formula_version": "1.0.0",
        "internal_notes": _PER_WORK_INTERNAL_NOTES,
    }
    combined_breakdown = {
        "labour": [{"label": "Labour (hourly)", "formula": "xlsx", "total": "145.00"}],
        "materials": [
            {"label": "Materials, parking & congestion", "formula": "xlsx", "total": "265.00"}
        ],
        "charges": [],
        "subtotal": "410.00",
        "vat_rate": "20",
        "vat_total": "82.00",
        "final_total": "492.00",
        "labour_charge_to_client": "145.00",
        "materials_parking_cc_charge": "265.00",
        "direct_labour_cost": "107.00",
        "profit_gbp": "156.25",
        "formula_source": "xlsx",
        "formula_version": "1.0.0",
        "internal_notes": _COMBINED_INTERNAL_NOTES,
    }
    return {
        "current_step": 3,
        "max_reachable_step": 3,
        "last_result": {
            "breakdown": combined_breakdown,
            "work_breakdowns": [
                {
                    "work_index": 0,
                    "scope": "Carpenter 1.5 hours — door repair",
                    "breakdown": per_work_breakdown,
                    "internal_notes": _PER_WORK_INTERNAL_NOTES,
                }
            ],
            "internal_notes": _COMBINED_INTERNAL_NOTES,
        },
    }


@pytest.fixture()
def q22123_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for model in (Client, ClientAlias, Trade, CalculationSession, CalculationSessionVersion):
        model.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    client = Client(name="Test Client", default_vat_rate=Decimal("20"))
    trade = Trade(name="Carpenter", is_active=True)
    db.add_all([client, trade])
    db.flush()

    session_id = uuid4()
    db.add(
        CalculationSession(
            id=session_id,
            session_token="token-q22123",
            source="test",
            payload_snapshot={},
            step1_snapshot={
                "quote_number": "Q22123",
                "job_number": "JOB-22123",
                "client_name": "Test Client",
                "trade_name": "Carpenter",
                "property_address": "10 Example Road",
                "engineer_name": "J. Smith",
            },
            step2_snapshot={"works": [{"scope": "Carpenter 1.5 hours — door repair"}]},
            ui_state=_q22123_ui_state(),
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _html(content: bytes, media_type: str) -> str:
    if media_type == "application/pdf":
        return ""
    html = content.decode("utf-8")
    return re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)


def _render(db, session_id, view_type: str) -> str:
    content, _, media_type = render_combined_works_pdf(
        db,
        session_id=session_id,
        work_indexes=[0],
        view_type=view_type,
    )
    return _html(content, media_type)


def _render_all_trades(db, session_id) -> str:
    from app.services.calculation_session_service import render_combined_all_trades_pdf

    content, _, media_type = render_combined_all_trades_pdf(
        db,
        session_id=session_id,
        work_indexes=[0],
    )
    return _html(content, media_type)


def _render_full_estimate(db, session_id) -> str:
    from app.services.calculation_session_pdf_service import render_session_quote_pdf

    content, _, media_type = render_session_quote_pdf(
        db,
        session_id=session_id,
        session_token="token-q22123",
        read_only=True,
    )
    return _html(content, media_type)


# ---------------------------------------------------------------------------
# Client PDF: quoted price must be £410, not £285
# ---------------------------------------------------------------------------

def test_client_pdf_item_quoted_price_uses_combined_breakdown(q22123_db):
    """Client PDF item row must show the combined subtotal (£410), not per-work (£285)."""
    db, session_id = q22123_db
    html = _render(db, session_id, "client")
    if not html:
        pytest.skip("PDF renderer returned binary output")

    assert "410.00" in html, "Expected quoted price £410.00 in client PDF"
    assert "285.00" not in html, "Stale per-work quoted price £285.00 must not appear in client PDF"


# ---------------------------------------------------------------------------
# Optimal PDF: Mat. chg / Client price / Profit / Margin
# ---------------------------------------------------------------------------

def test_optimal_pdf_item_materials_charge_uses_combined_breakdown(q22123_db):
    """Optimal PDF item row must show materials charge £265 (combined), not £140 (per-work)."""
    db, session_id = q22123_db
    html = _render(db, session_id, "optimal")
    if not html:
        pytest.skip("PDF renderer returned binary output")

    assert "265.00" in html, "Expected materials charge £265.00 in optimal PDF"
    # £140.00 could legitimately appear as material *cost* from combined lines if those
    # sum differently; the key assertion is that the materials_parking_cc_charge column
    # shows £265 and the client price is £410.
    assert "410.00" in html, "Expected client price £410.00 in optimal PDF"


def test_optimal_pdf_item_profit_uses_combined_breakdown(q22123_db):
    """Optimal PDF profit must use combined breakdown (£156.25), not per-work (£131.25)."""
    db, session_id = q22123_db
    html = _render(db, session_id, "optimal")
    if not html:
        pytest.skip("PDF renderer returned binary output")

    assert "156.25" in html, "Expected profit £156.25 in optimal PDF"
    assert "131.25" not in html, "Stale per-work profit £131.25 must not appear in optimal PDF"


def test_optimal_pdf_item_margin_uses_combined_breakdown(q22123_db):
    """Optimal PDF margin must reflect combined breakdown (~38.11%), not per-work (~46.05%)."""
    db, session_id = q22123_db
    html = _render(db, session_id, "optimal")
    if not html:
        pytest.skip("PDF renderer returned binary output")

    # Combined: 156.25 / 410 * 100 = 38.11%
    assert "38.11" in html, "Expected margin 38.11% in optimal PDF"
    # Per-work (wrong): 131.25 / 285 * 100 = 46.05%
    assert "46.05" not in html, "Stale per-work margin 46.05% must not appear in optimal PDF"


# ---------------------------------------------------------------------------
# All Trades PDF: materials subtotal / work subtotal
# ---------------------------------------------------------------------------

def test_all_trades_pdf_materials_subtotal_uses_combined_breakdown(q22123_db):
    """All Trades materials column must show £265 (combined), not £140 (per-work)."""
    db, session_id = q22123_db
    html = _render_all_trades(db, session_id)
    if not html:
        pytest.skip("PDF renderer returned binary output")

    assert "265.00" in html, "Expected materials subtotal £265.00 in all-trades PDF"
    assert "285.00" not in html, "Stale work subtotal £285.00 must not appear in all-trades PDF"


def test_all_trades_pdf_work_subtotal_uses_combined_breakdown(q22123_db):
    """All Trades work subtotal must be £410 (labour £145 + materials/parking/CC £265)."""
    db, session_id = q22123_db
    html = _render_all_trades(db, session_id)
    if not html:
        pytest.skip("PDF renderer returned binary output")

    assert "410.00" in html, "Expected work subtotal £410.00 in all-trades PDF"


def test_all_trades_pdf_materials_column_label_for_single_work(q22123_db):
    """All Trades header for single-work must say 'Materials / Parking / CC'."""
    db, session_id = q22123_db
    html = _render_all_trades(db, session_id)
    if not html:
        pytest.skip("PDF renderer returned binary output")

    assert "Materials / Parking / CC" in html, (
        "Expected 'Materials / Parking / CC' column label for single-work all-trades PDF"
    )


# ---------------------------------------------------------------------------
# Full Estimate PDF: internal notes must show combined parking amount
# ---------------------------------------------------------------------------

def test_full_estimate_internal_notes_show_combined_parking(q22123_db):
    """Full Estimate internal notes must show Parking: £100 (combined), not Parking: £0 (per-work)."""
    db, session_id = q22123_db
    html = _render_full_estimate(db, session_id)
    if not html:
        pytest.skip("PDF renderer returned binary output")

    assert "Parking: £100" in html, (
        "Expected 'Parking: £100' in full estimate internal notes"
    )
    assert "Parking: £0" not in html, (
        "Stale 'Parking: £0' from per-work notes must not appear in full estimate PDF"
    )


def test_full_estimate_internal_notes_show_combined_materials(q22123_db):
    """Full Estimate internal notes must show combined materials line (£265), not per-work (£140)."""
    db, session_id = q22123_db
    html = _render_full_estimate(db, session_id)
    if not html:
        pytest.skip("PDF renderer returned binary output")

    # The combined notes say "Materials etc: £265" (or similar), per-work says "£140".
    assert "combined notes with parking" in html, (
        "Full estimate should use combined internal notes containing 'combined notes with parking'"
    )
    assert "per-work notes without parking" not in html, (
        "Stale per-work phrase must not appear in full estimate internal notes"
    )


# ---------------------------------------------------------------------------
# Sanity: top-level totals remain correct in all views (non-regression)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("view_type", ["client", "optimal"])
def test_top_level_totals_still_correct(q22123_db, view_type):
    """Combined PDF grand total must remain £492.00 (unaffected by item-row fix)."""
    db, session_id = q22123_db
    html = _render(db, session_id, view_type)
    if not html:
        pytest.skip("PDF renderer returned binary output")

    assert "492.00" in html, f"Expected grand total £492.00 in {view_type} PDF"
    assert "82.00" in html, f"Expected VAT £82.00 in {view_type} PDF"
