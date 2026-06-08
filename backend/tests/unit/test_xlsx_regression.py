"""Regression tests derived from docs/1.7 MASTER HELPER.xlsx QUOTE CALCULATOR."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.engines.approval_engine import build_calculation_breakdown
from app.engines.rules_engine import MatchedRule
from app.engines.xlsx_quote_calculator import (
    XlsxCalculationConfig,
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


class TestXlsxMaterialsParkingCcExample:
    """Regression for QUOTE CALCULATOR E31 / K35: materials+parking+CC charge to client."""

    @staticmethod
    def _example_breakdown(carpenter_rule, **overrides):
        defaults = dict(
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
            matched_rule=carpenter_rule,
            formula_version="1.0.0",
        )
        defaults.update(overrides)
        return build_calculation_breakdown(**defaults)

    def test_exact_example_materials_parking_cc_charge_285(self, carpenter_rule):
        """228 / (1 - 0 - 0.20) = 285; MROUND(..., 5) = £285."""
        breakdown = self._example_breakdown(carpenter_rule)
        assert breakdown.materials_parking_cc_charge == Decimal("285")
        assert breakdown.labour_charge_to_client == Decimal("145")

    def test_exact_example_internal_notes_budget_and_charge_lines(self, carpenter_rule):
        breakdown = self._example_breakdown(carpenter_rule)
        notes = breakdown.internal_notes
        assert "BUDGET: Materials:  £110 / Parking: £100 / CC: £18" in notes
        assert "TOTAL CHARGE TO CLIENT:  Labour:  £145  / Materials etc:  £285" in notes
        assert "TOTAL COST TO OPTIMAL:" in notes
        assert "EXTERNAL DELIVERY:" in notes

    def test_exact_example_calculator_parity(self):
        result = calculate_hourly_quote(
            trade=CARPENTER,
            engineers=1,
            hours=Decimal("1.5"),
            client_fee_pct=LAMBERT_FEE,
            parking=Decimal("100"),
            congestion=Decimal("18"),
            materials=Decimal("110"),
        )
        assert result.materials_charge == Decimal("285")

    def test_client_fee_15_percent_increases_materials_denominator(self, carpenter_rule):
        rule = make_lambert_carpenter_xlsx_rule(client_fee_pct=Decimal("0.15"))
        matched = MatchedRule(rule=rule, match_type="test")
        breakdown = self._example_breakdown(matched)
        # 228 / (1 - 0.15 - 0.20) = 350.769... -> MROUND 350
        assert breakdown.materials_parking_cc_charge == Decimal("350")
        xlsx = calculate_hourly_quote(
            trade=CARPENTER,
            engineers=1,
            hours=Decimal("1.5"),
            client_fee_pct=Decimal("0.15"),
            parking=Decimal("100"),
            congestion=Decimal("18"),
            materials=Decimal("110"),
        )
        assert breakdown.materials_parking_cc_charge == xlsx.materials_charge

    def test_oig_uplift_applied_before_mround(self, carpenter_rule):
        rule = make_lambert_carpenter_xlsx_rule(xlsx_client_name="Oliver Jaques")
        matched = MatchedRule(rule=rule, match_type="test")
        breakdown = self._example_breakdown(matched, calculation_client_name="Oliver Jaques")
        xlsx = calculate_hourly_quote(
            trade=CARPENTER,
            engineers=1,
            hours=Decimal("1.5"),
            client_fee_pct=LAMBERT_FEE,
            parking=Decimal("100"),
            congestion=Decimal("18"),
            materials=Decimal("110"),
            config=XlsxCalculationConfig(client_name="Oliver Jaques"),
        )
        assert breakdown.materials_parking_cc_charge == Decimal("315")
        assert breakdown.labour_charge_to_client == Decimal("155")
        assert breakdown.materials_parking_cc_charge == xlsx.materials_charge
        assert breakdown.labour_charge_to_client == xlsx.labour_charge

    def test_missing_client_display_name_does_not_change_totals(self, carpenter_rule):
        rule = make_lambert_carpenter_xlsx_rule(xlsx_client_name=None)
        matched = MatchedRule(rule=rule, match_type="test")
        with_name = self._example_breakdown(carpenter_rule)
        without_name = self._example_breakdown(
            matched,
            calculation_client_name=None,
        )
        assert without_name.materials_parking_cc_charge == with_name.materials_parking_cc_charge
        assert without_name.labour_charge_to_client == with_name.labour_charge_to_client
        assert without_name.profit_gbp == with_name.profit_gbp
        assert "Client Comms" in without_name.internal_notes

    def test_parking_congestion_not_double_counted_in_passthrough(self, carpenter_rule):
        breakdown = self._example_breakdown(carpenter_rule)
        charge_labels = {line.label for line in breakdown.charges}
        assert "Parking" not in charge_labels
        assert "Congestion" not in charge_labels
        assert breakdown.subtotal == Decimal("430")
        assert breakdown.materials_parking_cc_charge == Decimal("285")

    def test_nhs_overhead_uplift_on_hourly_labour(self):
        cfg = XlsxCalculationConfig(client_name="NHS")
        result = calculate_hourly_quote(
            trade=CARPENTER,
            engineers=1,
            hours=Decimal("2"),
            client_fee_pct=LAMBERT_FEE,
            config=cfg,
        )
        # Excel E21: F16*AV2*1.15 = 190*0.3*1.15 = 65.55
        assert result.overhead_gbp == Decimal("65.55")
        normal = calculate_hourly_quote(
            trade=CARPENTER,
            engineers=1,
            hours=Decimal("2"),
            client_fee_pct=LAMBERT_FEE,
        )
        assert normal.overhead_gbp == Decimal("57")


class TestDefaultCarpenterXlsxQ22123Scenario:
    """Regression for Q22123: DEFAULT Carpenter fallback — parking must be consistent.

    Input: 1 Carpenter, 1.5 hours, materials £110, parking £100, CC £0,
           client fee 0%, material markup denominator 20%.

    Expected:
        labour_charge_to_client  = MROUND(95 * 1.5 / 1.0, 5) = £145
        materials_parking_cc     = MROUND((110+100) / 0.80, 5) = MROUND(262.5, 5) = £265
        work_subtotal            = 145 + 265 = £410
        additional_charges       = £0   (parking/CC are folded into the XLSX bucket)
        vat (20%)                = £82
        final_total              = £492
    """

    @staticmethod
    def _default_rule() -> "MatchedRule":
        rule = make_lambert_carpenter_xlsx_rule(
            client_fee_pct=Decimal("0"),
            xlsx_client_name="DEFAULT",
            xlsx_trade_name="Carpenter",
        )
        return MatchedRule(rule=rule, match_type="default_client_trade")

    @staticmethod
    def _breakdown(matched_rule):
        return build_calculation_breakdown(
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
            ),
            matched_rule=matched_rule,
            formula_version="1.0.0",
        )

    def test_labour_charge(self):
        bd = self._breakdown(self._default_rule())
        assert bd.labour_charge_to_client == Decimal("145")

    def test_materials_parking_cc_charge_includes_parking(self):
        """MROUND((110+100)/0.80, 5) = MROUND(262.5, 5) = £265."""
        bd = self._breakdown(self._default_rule())
        assert bd.materials_parking_cc_charge == Decimal("265")

    def test_work_subtotal_equals_labour_plus_materials_parking_cc(self):
        bd = self._breakdown(self._default_rule())
        expected_subtotal = bd.labour_charge_to_client + bd.materials_parking_cc_charge
        assert expected_subtotal == Decimal("410")
        assert bd.subtotal == Decimal("410")

    def test_additional_charges_empty_no_double_count(self):
        """Parking/CC are in the XLSX bucket; charges passthrough must be empty."""
        bd = self._breakdown(self._default_rule())
        charge_labels = {line.label for line in bd.charges}
        assert "Parking" not in charge_labels
        assert "Congestion" not in charge_labels
        assert bd.subtotal == Decimal("410")

    def test_vat_and_final_total(self):
        bd = self._breakdown(self._default_rule())
        assert bd.vat_total == Decimal("82")
        assert bd.final_total == Decimal("492")

    def test_internal_notes_budget_shows_parking_100(self):
        """Per-work internal notes must report Parking: £100, not £0."""
        bd = self._breakdown(self._default_rule())
        assert bd.internal_notes is not None
        assert "Parking: £100" in bd.internal_notes

    def test_internal_notes_total_charge_matches_work_subtotal(self):
        """TOTAL CHARGE TO CLIENT line must match labour+materials in breakdown."""
        bd = self._breakdown(self._default_rule())
        assert "TOTAL CHARGE TO CLIENT:  Labour:  £145  / Materials etc:  £265" in bd.internal_notes

    def test_per_work_and_combined_parking_values_agree(self):
        """When parking is passed through, both notes levels show the same amount."""
        matched = self._default_rule()
        bd_with_parking = self._breakdown(matched)
        # Also run with no parking to confirm parking absence shows £0
        bd_no_parking = build_calculation_breakdown(
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
            charges=ChargeInput(),
            matched_rule=matched,
            formula_version="1.0.0",
        )
        assert "Parking: £100" in bd_with_parking.internal_notes
        assert "Parking: £0" in bd_no_parking.internal_notes
        # When parking is included it changes the materials charge
        assert bd_with_parking.materials_parking_cc_charge == Decimal("265")
        assert bd_no_parking.materials_parking_cc_charge == Decimal("140")
