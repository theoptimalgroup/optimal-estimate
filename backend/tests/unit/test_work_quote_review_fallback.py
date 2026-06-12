"""Tests for Quote Review display fallbacks when per-work calculation snapshots are missing."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.calculation_session import CalculationSession
from app.models.client import Client
from app.models.client_alias import ClientAlias
from app.models.rate_rule import RateRule
from app.models.trade import Trade
from app.schemas.eworks_link import Step1Snapshot, Step2Snapshot, WorkBlockSnapshot
from app.services.calculation_session_service import _build_dashboard_quote_item_from_session
from app.services.work_quote_review_fallback_service import (
    UNAVAILABLE_INTERNAL_NOTES,
    build_standard_preview_work_breakdown,
    resolve_work_quote_review_display,
    stored_work_internal_notes,
)


def _step1() -> dict:
    return {
        "quote_number": "Q-100",
        "job_number": "J-100",
        "client_name": "Test Client",
        "trade_name": "Decorator",
        "property_address": "1 Test Street",
    }


def _work_one() -> WorkBlockSnapshot:
    return WorkBlockSnapshot(
        scope="- Paint walls.",
        product_name="Decoration - 2 Bedroom Flat",
        product_code="D--0001",
        skill_required="Electrician",
        engineers_required=True,
        engineers_needed=1,
        engineer_time_unit="hours",
        engineer_time_value=Decimal("2"),
        markup_value=Decimal("20"),
        materials_to_order=[
            {
                "links": [{"link": "asdfa", "quantity": 10, "cost": 10}],
                "delivery_charge": 10,
            }
        ],
        shelf_materials_rows=[{"link": "1sdvas", "quantity": 10, "cost": 10}],
    )


def _work_two() -> WorkBlockSnapshot:
    return WorkBlockSnapshot(
        scope="- Strip wallpaper.",
        product_name="Bedroom 3 and 4",
        product_code="B3-0003",
        skill_required="Painter & Decorator",
        engineers_required=True,
        engineers_needed=1,
        engineer_time_unit="hours",
        engineer_time_value=Decimal("2.5"),
        markup_value=Decimal("20"),
    )


def _step2_two_works() -> dict:
    return Step2Snapshot(
        works=[_work_one(), _work_two()],
        parking_required=True,
        parking_type="fixed",
        parking_fixed_amount=Decimal("126"),
        parking_vehicles=1,
        congestion_required=True,
        congestion_amount=Decimal("28.80"),
    ).model_dump(mode="json")


def _make_xlsx_rule(*, trade_id, client_id=None, trade_name: str) -> RateRule:
    return RateRule(
        client_id=client_id,
        trade_id=trade_id,
        formula_source="xlsx",
        version=f"xlsx-{trade_name.lower().replace(' ', '-')}",
        hourly_rate=Decimal("95"),
        day_rate=Decimal("239.40"),
        direct_hourly_cost=Decimal("30"),
        direct_daily_cost=Decimal("239.40"),
        client_fee_pct=Decimal("0.12"),
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
        xlsx_client_name="Portico",
        xlsx_trade_name=trade_name,
        material_markup_type="percentage",
        material_markup_value=Decimal("20"),
        vat_rate=Decimal("20"),
        active_from=date(2024, 1, 1),
        is_active=True,
    )


@pytest.fixture()
def preview_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for model in (Client, ClientAlias, Trade, RateRule, CalculationSession):
        model.__table__.create(engine)
    db = sessionmaker(bind= engine)()
    client = Client(name="Test", is_active=True)
    decorator = Trade(name="Decorator", is_active=True)
    electrician = Trade(name="Electrician", is_active=True)
    painter = Trade(name="Painter & Decorator", is_active=True)
    db.add_all([client, decorator, electrician, painter])
    db.flush()
    db.add_all(
        [
            _make_xlsx_rule(trade_id=decorator.id, client_id=client.id, trade_name="Decorator"),
            _make_xlsx_rule(trade_id=electrician.id, client_id=client.id, trade_name="Electrician"),
            _make_xlsx_rule(trade_id=painter.id, client_id=client.id, trade_name="Painter & Decorator"),
        ]
    )
    db.commit()
    yield db
    db.close()


def _session_with_works(db, *, ui_state=None) -> CalculationSession:
    client = db.scalars(select(Client)).first()
    trade = db.scalars(select(Trade).where(Trade.name == "Decorator")).first()
    session = CalculationSession(
        id=uuid4(),
        session_token="fallback-token",
        source="test",
        payload_snapshot={},
        step1_snapshot=_step1(),
        step2_snapshot=_step2_two_works(),
        ui_state=ui_state or {
            "last_result": {
                "breakdown": {"final_total": "1000.00"},
                "work_breakdowns": [],
            }
        },
        client_id=client.id,
        trade_id=trade.id,
        expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
        status="submitted",
        submitted_at=datetime(2026, 6, 12, tzinfo=timezone.utc),
        locked=True,
    )
    db.add(session)
    db.commit()
    return session


def test_stored_internal_notes_take_priority():
    work_result = {
        "work_index": 0,
        "internal_notes": "Stored per-work notes",
        "breakdown": {"internal_notes": "Breakdown notes"},
    }
    assert stored_work_internal_notes(work_result) == "Stored per-work notes"


def test_standard_preview_notes_include_xlsx_sections(preview_db):
    session = _session_with_works(preview_db)
    step1 = Step1Snapshot.model_validate(session.step1_snapshot)
    step2 = Step2Snapshot.model_validate(session.step2_snapshot)
    block = step2.works[0]

    breakdown = build_standard_preview_work_breakdown(
        preview_db,
        session=session,
        step1=step1,
        step2=step2,
        block=block,
        work_index=0,
        allocation=None,
    )
    assert breakdown is not None
    notes = breakdown.internal_notes or ""
    assert "HOURLY QUOTE HELPER USED" in notes
    assert "BUDGET:" in notes
    assert "TOTAL COST TO OPTIMAL:" in notes
    assert "TOTAL CHARGE TO CLIENT:" in notes
    assert "PROFIT ON JOB:" in notes
    assert "EXTERNAL DELIVERY:" in notes
    assert "Labour Only:" in notes
    assert "Labour & Materials:" in notes


def test_standard_preview_includes_parking_and_cc_in_budget(preview_db):
    session = _session_with_works(preview_db)
    step1 = Step1Snapshot.model_validate(session.step1_snapshot)
    step2 = Step2Snapshot.model_validate(session.step2_snapshot)
    from app.services.parking_charge_service import allocate_parking_cc_to_work_blocks

    allocation = allocate_parking_cc_to_work_blocks(step2, step2.works[0:1])[0]
    breakdown = build_standard_preview_work_breakdown(
        preview_db,
        session=session,
        step1=step1,
        step2=step2,
        block=step2.works[0],
        work_index=0,
        allocation=allocation,
    )
    notes = breakdown.internal_notes or ""
    assert "Parking:" in notes
    assert "CC:" in notes
    assert "BUDGET:" in notes
    assert "31.50" in notes


def test_multi_work_generates_standard_preview_notes_per_work(preview_db):
    session = _session_with_works(preview_db)
    step1 = Step1Snapshot.model_validate(session.step1_snapshot)
    step2 = Step2Snapshot.model_validate(session.step2_snapshot)
    from app.services.parking_charge_service import allocate_parking_cc_to_work_blocks

    allocations = allocate_parking_cc_to_work_blocks(step2, step2.works)
    for index, block in enumerate(step2.works):
        breakdown = build_standard_preview_work_breakdown(
            preview_db,
            session=session,
            step1=step1,
            step2=step2,
            block=block,
            work_index=index,
            allocation=allocations[index],
        )
        notes = breakdown.internal_notes or ""
        assert "HOURLY QUOTE HELPER USED" in notes
        assert block.skill_required in notes


def test_multi_work_different_trades_each_get_cc_in_internal_notes(preview_db):
    session = _session_with_works(preview_db)
    step1 = Step1Snapshot.model_validate(session.step1_snapshot)
    step2 = Step2Snapshot.model_validate(session.step2_snapshot)
    from app.services.parking_charge_service import allocate_parking_cc_to_work_blocks

    allocations = allocate_parking_cc_to_work_blocks(step2, step2.works)
    assert allocations[0].cc_total == Decimal("28.80")
    assert allocations[1].cc_total == Decimal("28.80")

    breakdown = build_standard_preview_work_breakdown(
        preview_db,
        session=session,
        step1=step1,
        step2=step2,
        block=step2.works[1],
        work_index=1,
        allocation=allocations[1],
    )
    notes = breakdown.internal_notes or ""
    assert "CC:" in notes
    assert "28.80" in notes
    assert "CC: £0" not in notes


def test_resolve_work_quote_review_display_uses_stored_notes_when_present(preview_db):
    step1 = Step1Snapshot.model_validate(_step1())
    step2 = Step2Snapshot.model_validate(_step2_two_works())
    session = _session_with_works(preview_db)
    work_result = {"internal_notes": "Stored notes only"}

    notes, labour, materials = resolve_work_quote_review_display(
        preview_db,
        session,
        step1,
        step2,
        step2.works[0],
        work_index=0,
        work_result=work_result,
        allocation=None,
        labour_subtotal=Decimal("250"),
        materials_subtotal=Decimal("100"),
    )

    assert notes == "Stored notes only"
    assert labour == Decimal("250")
    assert materials == Decimal("100")


def test_preview_fallback_does_not_mutate_ui_state(preview_db):
    session = _session_with_works(preview_db)
    before = dict(session.ui_state or {})

    _build_dashboard_quote_item_from_session(preview_db, session)

    assert session.ui_state == before


def test_quote_review_with_missing_work_breakdowns_shows_standard_internal_notes(preview_db):
    session = _session_with_works(preview_db)
    quote = _build_dashboard_quote_item_from_session(preview_db, session)
    assert len(quote.works) == 2

    work_one = quote.works[0]
    work_two = quote.works[1]

    assert work_one.internal_notes is not None
    assert work_one.internal_notes != UNAVAILABLE_INTERNAL_NOTES
    assert "HOURLY QUOTE HELPER USED" in work_one.internal_notes
    assert "BUDGET:" in work_one.internal_notes
    assert "Parking:" in work_one.internal_notes
    assert work_two.internal_notes is not None
    assert "HOURLY QUOTE HELPER USED" in work_two.internal_notes
    assert work_one.labour_subtotal is not None
    assert work_one.materials_subtotal is not None


def test_unavailable_message_when_preview_fails(preview_db):
    session = _session_with_works(preview_db)
    step1 = Step1Snapshot.model_validate(session.step1_snapshot)
    step2 = Step2Snapshot.model_validate(session.step2_snapshot)

    with patch(
        "app.services.work_quote_review_fallback_service.build_standard_preview_work_breakdown",
        return_value=None,
    ):
        notes, labour, materials = resolve_work_quote_review_display(
            preview_db,
            session,
            step1,
            step2,
            step2.works[0],
            work_index=0,
            work_result={},
            allocation=None,
            labour_subtotal=None,
            materials_subtotal=None,
        )

    assert notes == UNAVAILABLE_INTERNAL_NOTES
    assert labour is None
    assert materials is None


def test_client_views_do_not_use_dashboard_fallback():
    from app.services import client_quote_service

    source = open(client_quote_service.__file__).read()
    assert "work_quote_review_fallback_service" not in source
