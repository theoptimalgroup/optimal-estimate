"""Regression tests derived from docs/1.7 MASTER HELPER.xlsx QUOTE CALCULATOR."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.engines.approval_engine import build_calculation_breakdown
from app.engines.rules_engine import MatchedRule
from app.engines.xlsx_quote_calculator import (
    XlsxTradeRates,
    build_internal_notes_hourly,
    calculate_daily_quote,
    calculate_hourly_quote,
)
from app.models.rate_rule import RateRule
from app.schemas.calculation import ChargeInput, InternalNotesContext, LabourInput, MaterialInput


LAMBERT_FEE = Decimal("0")
CARPENTER = XlsxTradeRates.from_row("Carpenter", Decimal("95"))


def make_lambert_carpenter_xlsx_rule(**overrides) -> RateRule:
    defaults = dict(
        formula_source="xlsx",
        version="xlsx-test",
        hourly_rate=Decimal("95"),
        day_rate=Decimal("239.40"),
        direct_hourly_cost=Decimal("30"),
        direct_daily_cost=Decimal("239.40"),
        client_fee_pct=Decimal("0"),
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
        xlsx_client_name="Lambert Chartered Surveyors",
        xlsx_trade_name="Carpenter",
        material_markup_type="percentage",
        material_markup_value=Decimal("20"),
        vat_rate=Decimal("20"),
        active_from=date(2024, 1, 1),
        is_active=True,
    )
    defaults.update(overrides)
    return RateRule(**defaults)


class TestXlsxReferenceCalculator:
    def test_lambert_carpenter_hourly(self):
        result = calculate_hourly_quote(
            trade=CARPENTER,
            engineers=1,
            hours=Decimal("2"),
            client_fee_pct=LAMBERT_FEE,
        )
        assert result.labour_charge == Decimal("190")
        assert result.materials_charge == Decimal("0")
        assert result.overhead_gbp == Decimal("57")
        assert result.cost_labour == Decimal("58")
        assert result.profit_gbp == Decimal("132")
        assert result.profit_pct == Decimal("69.47")

    def test_lambert_carpenter_daily(self):
        result = calculate_daily_quote(
            trade=CARPENTER,
            engineers=1,
            days=Decimal("1"),
            client_fee_pct=LAMBERT_FEE,
        )
        assert result.labour_charge == Decimal("400")
        assert result.overhead_gbp == Decimal("79.80")
        assert result.cost_labour == Decimal("319.20")
        assert result.profit_gbp == Decimal("80.80")
        assert result.profit_pct == Decimal("20.20")

    def test_lambert_carpenter_daily_long_job(self):
        result = calculate_daily_quote(
            trade=CARPENTER,
            engineers=1,
            days=Decimal("5"),
            client_fee_pct=LAMBERT_FEE,
        )
        assert result.labour_charge == Decimal("1840")
        assert result.overhead_gbp == Decimal("276.23")
        assert result.cost_labour == Decimal("1473.23")
        assert result.profit_gbp == Decimal("366.77")
        assert result.profit_pct == Decimal("19.93")


@pytest.fixture()
def carpenter_rule():
    rule = make_lambert_carpenter_xlsx_rule()
    return MatchedRule(rule=rule, match_type="test")


class TestAppEngineXlsxParity:
    def test_hourly_matches_xlsx(self, carpenter_rule):
        breakdown = build_calculation_breakdown(
            labour_items=[LabourInput(labour_type="hourly", number_of_engineers=1, hours_on_site=Decimal("2"))],
            material_items=[],
            charges=None,
            matched_rule=carpenter_rule,
            formula_version="1.0.0",
        )
        xlsx = calculate_hourly_quote(trade=CARPENTER, engineers=1, hours=Decimal("2"))
        assert breakdown.labour_charge_to_client == xlsx.labour_charge
        assert breakdown.profit_gbp == xlsx.profit_gbp
        assert breakdown.overhead_cost == xlsx.overhead_gbp

    def test_daily_matches_xlsx(self, carpenter_rule):
        breakdown = build_calculation_breakdown(
            labour_items=[LabourInput(labour_type="day", number_of_engineers=1, days_on_site=Decimal("1"))],
            material_items=[],
            charges=None,
            matched_rule=carpenter_rule,
            formula_version="1.0.0",
        )
        xlsx = calculate_daily_quote(trade=CARPENTER, engineers=1, days=Decimal("1"))
        assert breakdown.labour_charge_to_client == xlsx.labour_charge
        assert breakdown.profit_gbp == xlsx.profit_gbp

    def test_materials_parking_cc(self, carpenter_rule):
        breakdown = build_calculation_breakdown(
            labour_items=[LabourInput(labour_type="hourly", number_of_engineers=1, hours_on_site=Decimal("2"))],
            material_items=[
                MaterialInput(
                    material_name="Part",
                    quantity=Decimal("1"),
                    unit_cost=Decimal("50"),
                    delivery_cost=Decimal("0"),
                    markup_type="percentage",
                    markup_value=Decimal("20"),
                    client_visible=True,
                )
            ],
            charges=ChargeInput(
                parking_required=True,
                parking_type="hourly",
                parking_rate_per_hour=Decimal("5"),
                parking_hours=Decimal("2"),
            ),
            matched_rule=carpenter_rule,
            formula_version="1.0.0",
        )
        assert breakdown.materials_parking_cc_charge == Decimal("75")

    def test_overhead_matches_xlsx(self, carpenter_rule):
        breakdown = build_calculation_breakdown(
            labour_items=[LabourInput(labour_type="hourly", number_of_engineers=1, hours_on_site=Decimal("2"))],
            material_items=[],
            charges=None,
            matched_rule=carpenter_rule,
            formula_version="1.0.0",
        )
        xlsx = calculate_hourly_quote(trade=CARPENTER, engineers=1, hours=Decimal("2"))
        assert breakdown.overhead_cost == xlsx.overhead_gbp
        assert xlsx.cost_labour == Decimal("58")

    def test_mround_nearest_five(self, carpenter_rule):
        breakdown = build_calculation_breakdown(
            labour_items=[LabourInput(labour_type="day", number_of_engineers=1, days_on_site=Decimal("1"))],
            material_items=[],
            charges=None,
            matched_rule=carpenter_rule,
            formula_version="1.0.0",
        )
        assert breakdown.labour_charge_to_client % Decimal("5") == Decimal("0")

    def test_profit_fields(self, carpenter_rule):
        breakdown = build_calculation_breakdown(
            labour_items=[LabourInput(labour_type="hourly", number_of_engineers=1, hours_on_site=Decimal("2"))],
            material_items=[],
            charges=None,
            matched_rule=carpenter_rule,
            formula_version="1.0.0",
        )
        assert breakdown.profit_gbp == Decimal("132")
        assert breakdown.profit_pct == Decimal("69.47")


class TestXlsxInternalNotesTemplate:
    def test_hourly_internal_notes_include_full_xlsx_sections(self):
        result = calculate_hourly_quote(
            trade=CARPENTER,
            engineers=1,
            hours=Decimal("1.5"),
            client_fee_pct=LAMBERT_FEE,
            parking=Decimal("0"),
            congestion=Decimal("18"),
            materials=Decimal("190"),
        )
        notes = build_internal_notes_hourly(
            client_name="Lambert Chartered Surveyors",
            client_fee_pct=LAMBERT_FEE,
            trade="Carpenter",
            engineers=1,
            hours=Decimal("1.5"),
            result=result,
            parking=Decimal("0"),
            congestion=Decimal("18"),
            materials_amount=Decimal("190"),
            notes_context=InternalNotesContext(who_quoted="Alex Alves"),
            trade_rates=CARPENTER,
        )
        assert notes.startswith("Enter this information into internal notes:")
        assert "PRODUCT:" in notes
        assert "IMPORTANT INFO:" in notes
        assert "LINK/S & QUANTITY:" in notes
        assert "WHO QUOTED: Alex Alves" in notes
        assert "WHO QUOTED:\tAlex Alves" not in notes
        assert "BEST ENGINEER:" in notes
        assert "EXTERNAL DELIVERY:" in notes
        assert "BUDGET: Materials:  £190 / Parking: £0 / CC: £18  / OH:  £43" in notes
        assert "TOTAL COST TO OPTIMAL:  Labour etc:  £44  /  Materials etc:  £208" in notes
        assert "TOTAL CHARGE TO CLIENT:  Labour:  £145  / Materials etc:  £260" in notes
        assert "Labour Only:  £60 @ £40p/h = Profit: £94 / 23%" in notes
        assert "Labour & Materials:  £250 = Profit: £94 / 23%" in notes
        assert "PROFIT ON JOB:  £153 / 38%" in notes
