from datetime import date
from decimal import Decimal

import pytest

from app.engines.approval_engine import build_calculation_breakdown, evaluate_approval_requirements
from app.engines.calculation_engine import (
    calculate_charges,
    calculate_combined_labour,
    calculate_labour,
    calculate_margin,
    calculate_material,
    calculate_vat,
    round_money,
)
from app.models.rate_rule import RateRule
from app.schemas.calculation import ChargeInput, LabourInput, MaterialInput


# --- Labour ---

def test_hourly_labour_single_engineer():
    result = calculate_labour("hourly", 1, Decimal("2"), None, Decimal("75"), None, None)
    assert result.total == Decimal("150.00")
    assert result.formula == "1 × 2 × 75"


def test_hourly_labour_multiple_engineers():
    result = calculate_labour("hourly", 2, Decimal("3"), None, Decimal("75"), None, None)
    assert result.total == Decimal("450.00")


def test_hourly_labour_with_labourer():
    result = calculate_combined_labour(
        labour_type="hourly",
        engineers=1,
        labourers=1,
        hours=Decimal("2"),
        days=None,
        hourly_rate=Decimal("75"),
        half_day_rate=None,
        day_rate=None,
        labourer_hourly_rate=Decimal("40"),
    )
    assert result.total == Decimal("230.00")  # 150 + 80


def test_half_day_labour():
    result = calculate_labour("half_day", 1, None, None, None, Decimal("280"), None)
    assert result.total == Decimal("280.00")


def test_day_labour():
    result = calculate_labour("day", 1, None, Decimal("2"), None, None, Decimal("520"))
    assert result.total == Decimal("1040.00")


def test_minimum_hours_applied():
    result = calculate_labour("hourly", 1, Decimal("0.5"), None, Decimal("75"), None, None, minimum_hours=Decimal("1"))
    assert result.total == Decimal("75.00")
    assert result.minimum_applied is True


def test_minimum_charge_applied():
    result = calculate_labour("hourly", 1, Decimal("0.25"), None, Decimal("75"), None, None, minimum_charge=Decimal("75"))
    assert result.total == Decimal("75.00")


def test_manual_labour_override():
    result = calculate_labour(
        "hourly", 1, Decimal("2"), None, Decimal("75"), None, None, manual_override=True, manual_rate=Decimal("90")
    )
    assert result.total == Decimal("180.00")
    assert "override" in result.formula


def test_manual_override_requires_approval():
    required, reasons = evaluate_approval_requirements(
        final_total=Decimal("180"),
        rule=None,
        manual_override=True,
        margin_percentage=None,
        rule_found=True,
        other_charge=Decimal("0"),
        other_charge_reason=None,
    )
    assert required is True
    assert "Manual rate override used" in reasons


# --- Materials ---

def test_material_markup_percentage():
    result = calculate_material(Decimal("1"), Decimal("82.49"), Decimal("0"), "percentage", Decimal("20"))
    assert result.base_cost == Decimal("82.49")
    assert result.markup_total == Decimal("16.50")
    assert result.sell_total == Decimal("98.99")


def test_material_markup_fixed():
    result = calculate_material(Decimal("1"), Decimal("100"), Decimal("0"), "fixed", Decimal("25"))
    assert result.sell_total == Decimal("125.00")


def test_material_no_markup():
    result = calculate_material(Decimal("1"), Decimal("100"), Decimal("0"), "none", Decimal("0"))
    assert result.sell_total == Decimal("100.00")


def test_material_delivery_cost_added():
    result = calculate_material(Decimal("2"), Decimal("50"), Decimal("10"), "percentage", Decimal("15"))
    assert result.base_cost == Decimal("110.00")
    assert result.sell_total == Decimal("126.50")


def test_multiple_materials_total():
    m1 = calculate_material(Decimal("1"), Decimal("50"), Decimal("0"), "percentage", Decimal("10"))
    m2 = calculate_material(Decimal("2"), Decimal("25"), Decimal("5"), "none", Decimal("0"))
    assert round_money(m1.sell_total + m2.sell_total) == Decimal("110.00")


# --- Charges ---

def test_parking_hourly():
    charges = ChargeInput(parking_required=True, parking_type="hourly", parking_rate_per_hour=Decimal("6.50"), parking_hours=Decimal("2"))
    result = calculate_charges(charges)
    assert result.parking_total == Decimal("13.00")


def test_parking_fixed():
    charges = ChargeInput(
        parking_required=True,
        parking_type="fixed",
        parking_fixed_amount=Decimal("20"),
        parking_duration_days=Decimal("1"),
    )
    result = calculate_charges(charges)
    assert result.parking_total == Decimal("20.00")


def test_parking_fixed_multiple_vehicles():
    charges = ChargeInput(
        parking_required=True,
        parking_type="fixed",
        parking_fixed_amount=Decimal("20"),
        parking_duration_days=Decimal("1"),
        parking_vehicles=2,
    )
    result = calculate_charges(charges)
    assert result.parking_total == Decimal("40.00")


def test_parking_hourly_multiple_vehicles():
    charges = ChargeInput(
        parking_required=True,
        parking_type="hourly",
        parking_rate_per_hour=Decimal("6.50"),
        parking_hours=Decimal("2"),
        parking_vehicles=2,
    )
    result = calculate_charges(charges)
    assert result.parking_total == Decimal("26.00")


def test_parking_included():
    charges = ChargeInput(parking_required=True, parking_type="included")
    result = calculate_charges(charges)
    assert result.parking_total == Decimal("0.00")
    assert any("Included" in b[1] for b in result.breakdown)


def test_parking_not_chargeable():
    charges = ChargeInput(parking_required=True, parking_type="not_chargeable")
    result = calculate_charges(charges)
    assert result.parking_total == Decimal("0.00")
    assert any("Not chargeable" in b[1] for b in result.breakdown)


def test_congestion_yes():
    charges = ChargeInput(congestion_required=True, congestion_amount=Decimal("15"))
    result = calculate_charges(charges)
    assert result.congestion_total == Decimal("15.00")


def test_congestion_no():
    charges = ChargeInput(congestion_required=False, congestion_amount=Decimal("15"))
    result = calculate_charges(charges)
    assert result.congestion_total == Decimal("0.00")


def test_ulez_yes():
    charges = ChargeInput(ulez_required=True, ulez_amount=Decimal("12.50"))
    result = calculate_charges(charges)
    assert result.ulez_total == Decimal("12.50")


def test_ulez_no():
    charges = ChargeInput(ulez_required=False, ulez_amount=Decimal("12.50"))
    result = calculate_charges(charges)
    assert result.ulez_total == Decimal("0.00")


def test_waste_disposal_added():
    charges = ChargeInput(waste_disposal_required=True, waste_disposal_amount=Decimal("45"))
    result = calculate_charges(charges)
    assert result.waste_total == Decimal("45.00")


def test_travel_charge_added():
    charges = ChargeInput(travel_charge=Decimal("30"))
    result = calculate_charges(charges)
    assert result.travel_total == Decimal("30.00")


def test_other_charge_added():
    charges = ChargeInput(other_charge=Decimal("25"), other_charge_reason="Special access fee")
    result = calculate_charges(charges)
    assert result.other_total == Decimal("25.00")


def test_other_charge_requires_reason():
    required, reasons = evaluate_approval_requirements(
        final_total=Decimal("100"),
        rule=None,
        manual_override=False,
        margin_percentage=None,
        rule_found=True,
        other_charge=Decimal("25"),
        other_charge_reason=None,
    )
    assert required is True
    assert any("Other charge" in r for r in reasons)


# --- VAT & Totals ---

def test_vat_default():
    assert calculate_vat(Decimal("261.99"), Decimal("20")) == Decimal("52.40")


def test_vat_exempt_client():
    assert calculate_vat(Decimal("261.99"), Decimal("0")) == Decimal("0.00")


def test_subtotal_calculation():
    labour = Decimal("150.00")
    material = Decimal("98.99")
    parking = Decimal("13.00")
    assert round_money(labour + material + parking) == Decimal("261.99")


def test_final_total_calculation():
    subtotal = Decimal("261.99")
    vat = calculate_vat(subtotal, Decimal("20"))
    assert round_money(subtotal + vat) == Decimal("314.39")


def test_margin_calculation():
    assert calculate_margin(Decimal("98.99"), Decimal("82.49")) == Decimal("16.67")


def test_low_margin_requires_approval():
    rule = RateRule(minimum_margin_percentage=Decimal("20"))
    required, _ = evaluate_approval_requirements(
        final_total=Decimal("200"),
        rule=rule,
        manual_override=False,
        margin_percentage=Decimal("10"),
        rule_found=True,
        other_charge=Decimal("0"),
        other_charge_reason=None,
    )
    assert required is True


def test_high_total_requires_approval():
    rule = RateRule(approval_threshold=Decimal("300"))
    required, _ = evaluate_approval_requirements(
        final_total=Decimal("314.39"),
        rule=rule,
        manual_override=False,
        margin_percentage=None,
        rule_found=True,
        other_charge=Decimal("0"),
        other_charge_reason=None,
    )
    assert required is True


def test_no_rate_rule_requires_approval():
    breakdown = build_calculation_breakdown(
        labour_items=[LabourInput(labour_type="hourly", number_of_engineers=1, hours_on_site=Decimal("2"))],
        material_items=[],
        charges=None,
        matched_rule=None,
        formula_version="1.0.0",
    )
    assert breakdown.approval_required is True
    assert "RATE_RULE_NOT_FOUND" in breakdown.warnings


def test_round_money_to_two_decimals():
    assert round_money(Decimal("10.005")) == Decimal("10.01")


# --- Regression: Napier Watt / Handyman ---

def test_regression_napier_watt_handyman():
    """Fixed regression case from Formula Specification §25.1."""
    labour = calculate_labour("hourly", 1, Decimal("2"), None, Decimal("75"), None, None)
    assert labour.total == Decimal("150.00")

    material = calculate_material(Decimal("1"), Decimal("82.49"), Decimal("0"), "percentage", Decimal("20"))
    assert material.base_cost == Decimal("82.49")
    assert material.markup_total == Decimal("16.50")
    assert material.sell_total == Decimal("98.99")

    charges = calculate_charges(
        ChargeInput(parking_required=True, parking_type="hourly", parking_rate_per_hour=Decimal("6.50"), parking_hours=Decimal("2"))
    )
    assert charges.parking_total == Decimal("13.00")
    assert charges.congestion_total == Decimal("0.00")

    subtotal = round_money(labour.total + material.sell_total + charges.parking_total)
    assert subtotal == Decimal("261.99")

    vat = calculate_vat(subtotal, Decimal("20"))
    assert vat == Decimal("52.40")

    final = round_money(subtotal + vat)
    assert final == Decimal("314.39")


def test_regression_napier_watt_via_breakdown_engine():
    from app.engines.rules_engine import MatchedRule
    from app.models.rate_rule import RateRule

    rule = RateRule(
        version="test",
        hourly_rate=Decimal("75"),
        vat_rate=Decimal("20"),
        active_from=date.today(),
        is_active=True,
    )
    matched = MatchedRule(rule=rule, match_type="exact_client_trade")
    breakdown = build_calculation_breakdown(
        labour_items=[LabourInput(labour_type="hourly", number_of_engineers=1, hours_on_site=Decimal("2"))],
        material_items=[
            MaterialInput(material_name="Part", quantity=Decimal("1"), unit_cost=Decimal("82.49"), markup_type="percentage", markup_value=Decimal("20"))
        ],
        charges=ChargeInput(
            parking_required=True,
            parking_type="hourly",
            parking_rate_per_hour=Decimal("6.50"),
            parking_hours=Decimal("2"),
            congestion_required=False,
        ),
        matched_rule=matched,
        formula_version="1.0.0",
    )
    assert breakdown.subtotal == Decimal("261.99")
    assert breakdown.vat_total == Decimal("52.40")
    assert breakdown.final_total == Decimal("314.39")
