"""Tests for Excel-parity subcontractor quote calculation."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.engines.approval_engine import build_calculation_breakdown
from app.engines.rules_engine import MatchedRule
from app.engines.xlsx_quote_calculator import (
    XlsxCalculationConfig,
    build_internal_notes_subcontractor,
    calculate_subcontractor_quote,
)
from app.schemas.calculation import LabourInput, MaterialInput
from tests.unit.test_xlsx_regression import make_lambert_carpenter_xlsx_rule


def _private_customer_config() -> XlsxCalculationConfig:
    return XlsxCalculationConfig(client_name="Private Customer")


class TestSubcontractorWorkbookExample:
    def test_scaffolder_danny_arnold_six_days(self):
        result = calculate_subcontractor_quote(
            subcontractor_name="Danny Arnold Scaffolding",
            trade="Scaffolder",
            units_type="Days",
            people_count=3,
            duration=Decimal("6"),
            labour_cost=Decimal("1500"),
            materials=Decimal("3500"),
            parking=Decimal("0"),
            congestion=Decimal("0"),
            client_fee_pct=Decimal("0"),
            client_name="Private Customer",
            config=_private_customer_config(),
        )
        assert result.selected_overhead_pct == Decimal("0.15")
        assert result.overhead_gbp == Decimal("346.15")
        assert result.labour_charge == Decimal("2310")
        assert result.materials_charge == Decimal("4375")
        assert result.cost_labour == Decimal("1846.15")
        assert result.cost_materials == Decimal("3500")
        assert result.profit_gbp == Decimal("1338.85")
        assert result.profit_pct == Decimal("20.03")

    def test_workbook_example_notes_rounding(self):
        result = calculate_subcontractor_quote(
            subcontractor_name="Danny Arnold Scaffolding",
            trade="Scaffolder",
            units_type="Days",
            people_count=3,
            duration=Decimal("6"),
            labour_cost=Decimal("1500"),
            materials=Decimal("3500"),
            client_name="Private Customer",
            config=_private_customer_config(),
        )
        notes = build_internal_notes_subcontractor(
            client_name="Private Customer",
            trade="Scaffolder",
            subcontractor_name="Danny Arnold Scaffolding",
            people_count=3,
            units_type="Days",
            duration=Decimal("6"),
            result=result,
            parking=Decimal("0"),
            congestion=Decimal("0"),
            materials_amount=Decimal("3500"),
        )
        assert "SUBBY CALCULATOR with O/H @ 15%" in notes
        assert "SUBCONTRACTOR:  Danny Arnold Scaffolding" in notes
        assert "SUBCONTRACTOR CHARGE TO US:  £5000  /  Breakdown ⬇️" in notes
        assert "TOTAL COST TO OPTIMAL:  £5346" in notes
        assert "TOTAL CHARGE TO CLIENT:  £6685" in notes
        assert "PROFIT ON JOB:  £1339 / 20%" in notes

    def test_breakdown_engine_subcontractor_path(self):
        rule = make_lambert_carpenter_xlsx_rule(
            xlsx_client_name="Private Customer",
            xlsx_trade_name="Scaffolder",
        )
        matched = MatchedRule(rule=rule, match_type="exact_client_trade")
        breakdown = build_calculation_breakdown(
            labour_items=[
                LabourInput(
                    labour_type="subcontractor",
                    number_of_engineers=3,
                    days_on_site=Decimal("6"),
                    subcontractor_name="Danny Arnold Scaffolding",
                    subcontractor_labour_cost=Decimal("1500"),
                )
            ],
            material_items=[
                MaterialInput(
                    material_name="Scaffolding materials",
                    quantity=Decimal("1"),
                    unit_cost=Decimal("3500"),
                )
            ],
            charges=None,
            matched_rule=matched,
            formula_version="1.0.0",
            calculation_client_name="Private Customer",
        )
        assert breakdown.labour_charge_to_client == Decimal("2310")
        assert breakdown.materials_parking_cc_charge == Decimal("4375")
        assert breakdown.cost_to_optimal_labour == Decimal("1846.15")
        assert breakdown.cost_to_optimal_materials == Decimal("3500")
        assert breakdown.profit_gbp == Decimal("1338.85")
        assert breakdown.profit_pct == Decimal("20.03")
        assert "SUBBY CALCULATOR with O/H @ 15%" in (breakdown.internal_notes or "")


class TestSubcontractorOverheadRates:
    def _base_kwargs(self) -> dict:
        return {
            "labour_cost": Decimal("1500"),
            "materials": Decimal("0"),
            "client_name": "Private Customer",
            "config": _private_customer_config(),
        }

    def test_hours_uses_30_percent_overhead(self):
        kwargs = self._base_kwargs()
        result = calculate_subcontractor_quote(
            units_type="Hours",
            people_count=1,
            duration=Decimal("8"),
            **kwargs,
        )
        assert result.selected_overhead_pct == Decimal("0.30")
        assert result.overhead_gbp == Decimal("692.31")

    def test_days_one_to_two_uses_20_percent_overhead(self):
        kwargs = self._base_kwargs()
        result = calculate_subcontractor_quote(
            units_type="Days",
            people_count=1,
            duration=Decimal("2"),
            **kwargs,
        )
        assert result.selected_overhead_pct == Decimal("0.20")
        assert result.overhead_gbp == Decimal("461.54")

    def test_days_three_or_more_uses_15_percent_overhead(self):
        kwargs = self._base_kwargs()
        result = calculate_subcontractor_quote(
            units_type="Days",
            people_count=1,
            duration=Decimal("3"),
            **kwargs,
        )
        assert result.selected_overhead_pct == Decimal("0.15")
        assert result.overhead_gbp == Decimal("346.15")


class TestSubcontractorClientAdjustments:
    def test_nhs_applies_overhead_uplift(self):
        base = calculate_subcontractor_quote(
            units_type="Days",
            people_count=1,
            duration=Decimal("6"),
            labour_cost=Decimal("1500"),
            client_name="Private Customer",
            config=_private_customer_config(),
        )
        nhs = calculate_subcontractor_quote(
            units_type="Days",
            people_count=1,
            duration=Decimal("6"),
            labour_cost=Decimal("1500"),
            client_name="NHS",
            config=XlsxCalculationConfig(client_name="NHS"),
        )
        assert nhs.overhead_gbp == Decimal("398.08")
        assert nhs.overhead_gbp > base.overhead_gbp

    def test_oliver_jaques_applies_charge_uplift(self):
        base = calculate_subcontractor_quote(
            units_type="Days",
            people_count=1,
            duration=Decimal("6"),
            labour_cost=Decimal("1500"),
            materials=Decimal("3500"),
            client_name="Private Customer",
            config=_private_customer_config(),
        )
        oj = calculate_subcontractor_quote(
            units_type="Days",
            people_count=1,
            duration=Decimal("6"),
            labour_cost=Decimal("1500"),
            materials=Decimal("3500"),
            client_name="Oliver Jaques",
            config=XlsxCalculationConfig(client_name="Oliver Jaques"),
        )
        assert oj.labour_charge > base.labour_charge
        assert oj.materials_charge > base.materials_charge
        assert oj.labour_charge == Decimal("2540")
        assert oj.materials_charge == Decimal("4815")


class TestSubcontractorValidation:
    def test_zero_duration_raises(self):
        with pytest.raises(ValueError, match="duration must be greater than zero"):
            calculate_subcontractor_quote(
                units_type="Days",
                people_count=1,
                duration=Decimal("0"),
                labour_cost=Decimal("1500"),
            )

    def test_negative_duration_raises(self):
        with pytest.raises(ValueError, match="duration must be greater than zero"):
            calculate_subcontractor_quote(
                units_type="Hours",
                people_count=1,
                duration=Decimal("-1"),
                labour_cost=Decimal("1500"),
            )
