"""XLSX rate-rule fallback when exact client + trade rule is missing."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.engines.approval_engine import build_calculation_breakdown
from app.engines.rules_engine import (
    DEFAULT_XLSX_CLIENT_NAME,
    find_active_xlsx_rule,
    has_exact_client_trade_xlsx_rule,
    resolve_calculation_rule,
)
from app.models.client import Client
from app.models.rate_rule import RateRule
from app.models.trade import Trade
from app.schemas.calculation import ChargeInput, LabourInput, MaterialInput
from app.services.calculation_service import preview_calculation
from app.schemas.calculation import CalculationPreviewRequest
from tests.unit.test_xlsx_regression import make_lambert_carpenter_xlsx_rule


def _carpenter_trade(db_session) -> Trade:
    trade = Trade(id=uuid4(), name="Carpenter")
    db_session.add(trade)
    db_session.flush()
    return trade


def _default_carpenter_rule(trade_id, *, client_id=None, client_name="Trade default", fee=Decimal("0")) -> RateRule:
    return make_lambert_carpenter_xlsx_rule(
        client_id=client_id,
        trade_id=trade_id,
        client_fee_pct=fee,
        xlsx_client_name=client_name,
        xlsx_trade_name="Carpenter",
        version="fallback-test",
    )


@pytest.fixture()
def fallback_db():
    engine = create_engine("sqlite:///:memory:")
    for model in (Client, Trade, RateRule):
        model.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    expert = Client(id=uuid4(), name="Expert Letts Ltd", default_vat_rate=Decimal("20"))
    default_client = Client(id=uuid4(), name=DEFAULT_XLSX_CLIENT_NAME, default_vat_rate=Decimal("20"))
    lambert = Client(id=uuid4(), name="Lambert Chartered Surveyors", default_vat_rate=Decimal("20"))
    trade = _carpenter_trade(session)

    exact_rule = make_lambert_carpenter_xlsx_rule(
        client_id=lambert.id,
        trade_id=trade.id,
        xlsx_client_name="Lambert Chartered Surveyors",
        version="exact-test",
    )
    default_named_rule = _default_carpenter_rule(
        trade.id,
        client_id=default_client.id,
        client_name=DEFAULT_XLSX_CLIENT_NAME,
        fee=Decimal("0"),
    )
    global_trade_rule = _default_carpenter_rule(trade.id, client_id=None, client_name="Trade default", fee=Decimal("0"))

    session.add_all([expert, default_client, lambert, exact_rule, default_named_rule, global_trade_rule])
    session.commit()
    yield session, expert, default_client, lambert, trade
    session.close()


def _example_preview(client_id, trade_id):
    return CalculationPreviewRequest(
        client_id=client_id,
        trade_id=trade_id,
        labour_items=[
            LabourInput(
                labour_type="hourly",
                number_of_engineers=1,
                hours_on_site=Decimal("1.5"),
            )
        ],
        material_items=[
            MaterialInput(
                material_name="Materials",
                quantity=Decimal("1"),
                unit_cost=Decimal("110"),
                delivery_cost=Decimal("0"),
                markup_type="percentage",
                markup_value=Decimal("20"),
                client_visible=True,
            )
        ],
        charges=ChargeInput(
            parking_required=True,
            parking_type="fixed",
            parking_fixed_amount=Decimal("100"),
            congestion_required=True,
            congestion_amount=Decimal("18"),
        ),
        calculation_client_name="Expert Letts Ltd",
    )


class TestXlsxRuleFallbackLookup:
    def test_exact_client_trade_uses_exact_xlsx_rule(self, fallback_db):
        db, expert, _default_client, lambert, trade = fallback_db
        matched = find_active_xlsx_rule(db, lambert.id, trade.id, date.today())
        assert matched is not None
        assert matched.match_type == "exact_client_trade"
        assert matched.rule.xlsx_client_name == "Lambert Chartered Surveyors"

    def test_missing_client_uses_default_named_client_rule(self, fallback_db):
        db, expert, default_client, _lambert, trade = fallback_db
        matched = find_active_xlsx_rule(db, expert.id, trade.id, date.today())
        assert matched is not None
        assert matched.match_type == "default_named_client_trade"
        assert matched.rule.client_id == default_client.id

    def test_missing_default_client_uses_global_trade_rule(self, fallback_db):
        db, expert, default_client, _lambert, trade = fallback_db
        db.query(RateRule).filter(RateRule.client_id == default_client.id).delete()
        db.commit()

        matched = find_active_xlsx_rule(db, expert.id, trade.id, date.today())
        assert matched is not None
        assert matched.match_type == "global_trade"
        assert matched.rule.client_id is None

    def test_no_xlsx_rules_falls_back_to_simplified(self, fallback_db):
        db, expert, _default_client, _lambert, trade = fallback_db
        db.query(RateRule).filter(RateRule.formula_source == "xlsx").delete()
        simplified = RateRule(
            client_id=expert.id,
            trade_id=trade.id,
            version="simplified-1",
            formula_source="simplified",
            hourly_rate=Decimal("75"),
            half_day_rate=Decimal("280"),
            day_rate=Decimal("520"),
            material_markup_type="percentage",
            material_markup_value=Decimal("20"),
            vat_rate=Decimal("20"),
            active_from=date(2024, 1, 1),
            is_active=True,
        )
        db.add(simplified)
        db.commit()

        matched = resolve_calculation_rule(db, expert.id, trade.id, date.today())
        assert matched is not None
        assert matched.rule.formula_source == "simplified"


class TestXlsxClientFallbackCalculation:
    def test_missing_client_materials_parking_cc_is_285(self, fallback_db):
        db, expert, _default_client, _lambert, trade = fallback_db
        breakdown = preview_calculation(db, _example_preview(expert.id, trade.id))
        assert breakdown.formula_source == "xlsx"
        assert breakdown.materials_parking_cc_charge == Decimal("285")
        assert breakdown.client_fee_pct == Decimal("0")

    def test_exact_client_still_uses_exact_rule(self, fallback_db):
        db, _expert, _default_client, lambert, trade = fallback_db
        breakdown = preview_calculation(
            db,
            CalculationPreviewRequest(
                client_id=lambert.id,
                trade_id=trade.id,
                labour_items=[LabourInput(labour_type="hourly", number_of_engineers=1, hours_on_site=Decimal("2"))],
                material_items=[],
                charges=None,
            ),
        )
        assert breakdown.formula_source == "xlsx"
        assert has_exact_client_trade_xlsx_rule(db, lambert.id, trade.id)

    def test_fallback_warning_and_internal_notes(self, fallback_db):
        db, expert, _default_client, _lambert, trade = fallback_db
        breakdown = preview_calculation(db, _example_preview(expert.id, trade.id))
        assert any("Exact client rate rule not found" in warning for warning in breakdown.warnings)
        assert "Used default XLSX Carpenter rule." in breakdown.warnings[0]
        notes = breakdown.internal_notes or ""
        assert "Client not available or Expert Letts Ltd Comms @ 0%" in notes
        assert "XLSX/default rule used (Carpenter)" in notes

    def test_missing_client_display_name_does_not_change_totals(self, fallback_db):
        db, expert, _default_client, _lambert, trade = fallback_db
        with_name = preview_calculation(db, _example_preview(expert.id, trade.id))
        without_name = preview_calculation(
            db,
            CalculationPreviewRequest(
                client_id=expert.id,
                trade_id=trade.id,
                labour_items=_example_preview(expert.id, trade.id).labour_items,
                material_items=_example_preview(expert.id, trade.id).material_items,
                charges=_example_preview(expert.id, trade.id).charges,
            ),
        )
        assert without_name.materials_parking_cc_charge == with_name.materials_parking_cc_charge
        assert without_name.labour_charge_to_client == with_name.labour_charge_to_client

    def test_no_xlsx_trade_rule_uses_simplified(self, fallback_db):
        db, expert, _default_client, _lambert, trade = fallback_db
        db.query(RateRule).filter(RateRule.formula_source == "xlsx").delete()
        db.commit()

        matched = resolve_calculation_rule(db, expert.id, trade.id, date.today())
        breakdown = build_calculation_breakdown(
            labour_items=[LabourInput(labour_type="hourly", number_of_engineers=1, hours_on_site=Decimal("1.5"))],
            material_items=_example_preview(expert.id, trade.id).material_items,
            charges=_example_preview(expert.id, trade.id).charges,
            matched_rule=matched,
            formula_version="1.0.0",
        )
        assert breakdown.formula_source == "simplified"
        assert breakdown.materials_parking_cc_charge is None
        assert breakdown.materials[0].total == Decimal("132")


class TestClientViewHidesFallbackWarnings:
    def test_warnings_not_in_client_view(self, fallback_db):
        from app.models.calculation_session import CalculationSession
        from app.schemas.eworks_link import Step1Snapshot, Step2Snapshot
        from app.services.calculation_view_service import build_client_view_from_session

        db, expert, _default_client, _lambert, trade = fallback_db
        breakdown = preview_calculation(db, _example_preview(expert.id, trade.id))
        session = CalculationSession(
            session_token="token",
            source="eworks",
            payload_snapshot={},
            step1_snapshot=Step1Snapshot(
                quote_number="Q1",
                job_number="J1",
                client_name="Expert Letts Ltd",
                trade_name="Carpenter",
                property_address="1 Test Street",
            ).model_dump(mode="json"),
            client_id=expert.id,
            trade_id=trade.id,
            expires_at=date.today(),
        )
        client_view = build_client_view_from_session(
            session,
            breakdown,
            Step1Snapshot.model_validate(session.step1_snapshot),
            Step2Snapshot.model_validate({"works": [{"scope": "Test"}]}),
        )
        assert "warnings" not in client_view["calculation"]
        assert "internal_notes" not in client_view["calculation"]
