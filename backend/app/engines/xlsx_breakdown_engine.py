from decimal import Decimal

from app.core.config import settings
from app.engines.approval_engine import evaluate_approval_requirements
from app.engines.calculation_engine import calculate_charges, calculate_vat, round_money
from app.engines.rules_engine import MatchedRule
from app.engines.xlsx_quote_calculator import (
    XlsxCalculationConfig,
    XlsxTradeRates,
    build_internal_notes_daily,
    build_internal_notes_hourly,
    calculate_daily_quote,
    calculate_hourly_quote,
)
from app.models.rate_rule import RateRule
from app.schemas.calculation import CalculationBreakdown, ChargeInput, InternalNotesContext, LabourInput, LineBreakdown, MaterialInput


def config_from_rule(
    rule: RateRule,
    *,
    client_fee_pct_override: Decimal | None = None,
    client_name_override: str | None = None,
) -> XlsxCalculationConfig:
    fee_pct = client_fee_pct_override if client_fee_pct_override is not None else rule.client_fee_pct
    return XlsxCalculationConfig(
        client_fee_pct=fee_pct,
        hourly_overhead_pct=rule.hourly_overhead_pct,
        daily_overhead_pct=rule.daily_overhead_pct,
        daily_overhead_long_job_pct=rule.daily_overhead_long_job_pct,
        labourer_hourly_cost=rule.labourer_hourly_cost,
        labourer_daily_cost=rule.labourer_daily_cost,
        material_charge_denominator=rule.material_charge_denominator,
        mround_increment=rule.mround_increment,
        oj_uplift_pct=rule.oj_uplift_pct,
        nhs_overhead_uplift_pct=rule.nhs_overhead_uplift_pct,
        eaf_flat_fee=rule.eaf_flat_fee,
        client_name=client_name_override or rule.xlsx_client_name or "",
    )


def trade_from_rule(rule: RateRule) -> XlsxTradeRates:
    return XlsxTradeRates.from_rule_fields(
        trade_name=rule.xlsx_trade_name or "",
        hourly_client_rate=rule.hourly_rate or Decimal("0"),
        direct_hourly_cost=rule.direct_hourly_cost,
        direct_daily_cost=rule.direct_daily_cost or rule.day_rate,
    )


def _material_input_total(material_items: list[MaterialInput]) -> Decimal:
    total = Decimal("0")
    for item in material_items:
        total += round_money(item.quantity * item.unit_cost + item.delivery_cost)
    return total


def _parking_input_cost(charges: ChargeInput | None) -> Decimal:
    if not charges or not charges.parking_required:
        return Decimal("0")
    # Vehicle count multiplies parking (same rule as work_parking_raw / quote_parking_raw).
    vehicles = Decimal(max(1, charges.parking_vehicles or 1))
    if charges.parking_type == "hourly" and charges.parking_rate_per_hour and charges.parking_hours:
        return round_money(charges.parking_rate_per_hour * charges.parking_hours * vehicles)
    if charges.parking_fixed_amount is not None:
        return round_money(charges.parking_fixed_amount * vehicles)
    return Decimal("0")


def _congestion_input_cost(charges: ChargeInput | None) -> Decimal:
    if charges and charges.congestion_required:
        return round_money(charges.congestion_amount)
    return Decimal("0")


def _passthrough_charges(charges: ChargeInput | None) -> tuple[Decimal, list[LineBreakdown]]:
    charge_result = calculate_charges(charges)
    passthrough_total = Decimal("0")
    passthrough_lines: list[LineBreakdown] = []
    for label, formula, total in charge_result.breakdown:
        if label in {"Parking", "Congestion"}:
            continue
        passthrough_total += total
        passthrough_lines.append(LineBreakdown(label=label, formula=formula, total=total))
    return passthrough_total, passthrough_lines


def build_xlsx_calculation_breakdown(
    labour_items: list[LabourInput],
    material_items: list[MaterialInput],
    charges: ChargeInput | None,
    matched_rule: MatchedRule,
    formula_version: str,
    internal_notes_context: InternalNotesContext | None = None,
    *,
    client_fee_pct_override: Decimal | None = None,
    calculation_client_name: str | None = None,
) -> CalculationBreakdown:
    rule = matched_rule.rule
    fee_pct = client_fee_pct_override if client_fee_pct_override is not None else rule.client_fee_pct
    notes_client_name = calculation_client_name or rule.xlsx_client_name or "Client"
    cfg = config_from_rule(
        rule,
        client_fee_pct_override=client_fee_pct_override,
        client_name_override=calculation_client_name,
    )
    trade = trade_from_rule(rule)
    warnings: list[str] = []

    labour_item = labour_items[0] if labour_items else LabourInput(labour_type="hourly", number_of_engineers=1)
    materials_input = _material_input_total(material_items)
    parking_input = _parking_input_cost(charges)
    congestion_input = _congestion_input_cost(charges)

    manual_override_used = labour_item.manual_override
    if manual_override_used:
        warnings.append("MANUAL_OVERRIDE_IN_XLSX_MODE")

    if labour_item.labour_type == "hourly":
        hours = labour_item.hours_on_site or Decimal("0")
        result = calculate_hourly_quote(
            trade=trade,
            engineers=labour_item.number_of_engineers,
            hours=hours,
            client_fee_pct=fee_pct,
            parking=parking_input,
            congestion=congestion_input,
            materials=materials_input,
            config=cfg,
        )
        internal_notes = rule.internal_notes_template or build_internal_notes_hourly(
            client_name=notes_client_name,
            client_fee_pct=fee_pct,
            trade=trade.trade,
            engineers=labour_item.number_of_engineers,
            hours=hours,
            result=result,
            parking=parking_input,
            congestion=congestion_input,
            materials_amount=materials_input,
            notes_context=internal_notes_context,
            trade_rates=trade,
        )
        labour_formula = f"XLSX hourly MROUND({trade.hourly_client_rate}×{labour_item.number_of_engineers}×{hours}/(1-{fee_pct}), {rule.mround_increment})"
        denominator_used = result.materials_denominator
    else:
        days = labour_item.days_on_site or Decimal("1")
        labourer_days = labour_item.labourer_days if labour_item.labourer_days is not None else days
        result = calculate_daily_quote(
            trade=trade,
            engineers=labour_item.number_of_engineers,
            days=days,
            labourers=labour_item.number_of_labourers,
            labourer_days=labourer_days,
            client_fee_pct=fee_pct,
            parking=parking_input,
            congestion=congestion_input,
            materials=materials_input,
            config=cfg,
        )
        labourer_days = labour_item.labourer_days if labour_item.labourer_days is not None else days
        helper_label = (
            "DAILY (3 Days >) QUOTE HELPER USED"
            if days > Decimal("2")
            else "DAILY (Up to 2 Days) QUOTE HELPER USED"
        )
        internal_notes = rule.internal_notes_template or build_internal_notes_daily(
            client_name=notes_client_name,
            client_fee_pct=fee_pct,
            trade=trade.trade,
            engineers=labour_item.number_of_engineers,
            days=days,
            labourers=labour_item.number_of_labourers,
            labourer_days=labourer_days,
            result=result,
            parking=parking_input,
            congestion=congestion_input,
            materials_amount=materials_input,
            helper_label=helper_label,
            notes_context=internal_notes_context,
            config=cfg,
            trade_rates=trade,
        )
        labour_formula = f"XLSX daily MROUND(direct+OH)/(1-{fee_pct}-{rule.material_charge_denominator}), {rule.mround_increment})"
        denominator_used = result.charge_denominator_materials

    if manual_override_used and labour_item.manual_rate is not None:
        result.labour_charge = round_money(labour_item.manual_rate)

    labour_breakdown = [
        LineBreakdown(
            label=f"Labour ({labour_item.labour_type})",
            formula=labour_formula,
            total=result.labour_charge,
        )
    ]
    material_breakdown: list[LineBreakdown] = []
    if result.materials_charge > 0:
        material_breakdown.append(
            LineBreakdown(
                label="Materials, parking & congestion",
                formula=f"XLSX MROUND(inputs/(1-{fee_pct}-{rule.material_charge_denominator}), {rule.mround_increment})",
                total=result.materials_charge,
            )
        )

    passthrough_total, passthrough_lines = _passthrough_charges(charges)
    subtotal = round_money(result.labour_charge + result.materials_charge + passthrough_total)
    vat_rate = rule.vat_rate
    vat_total = calculate_vat(subtotal, vat_rate)
    final_total = round_money(subtotal + vat_total)

    other_charge = charges.other_charge if charges else Decimal("0")
    other_reason = charges.other_charge_reason if charges else None
    approval_required, approval_reasons = evaluate_approval_requirements(
        final_total=final_total,
        rule=rule,
        manual_override=manual_override_used,
        margin_percentage=result.profit_pct,
        rule_found=True,
        other_charge=other_charge,
        other_charge_reason=other_reason,
    )

    return CalculationBreakdown(
        labour=labour_breakdown,
        materials=material_breakdown,
        charges=passthrough_lines,
        subtotal=subtotal,
        vat_rate=vat_rate,
        vat_total=vat_total,
        final_total=final_total,
        margin_total=result.profit_gbp,
        rule_version=rule.version,
        formula_version=formula_version,
        approval_required=approval_required,
        approval_reasons=approval_reasons,
        warnings=warnings,
        formula_source="xlsx",
        xlsx_formula_version=settings.xlsx_formula_version,
        direct_labour_cost=result.direct_labour_cost,
        overhead_cost=result.overhead_gbp,
        labour_charge_to_client=result.labour_charge,
        materials_parking_cc_charge=result.materials_charge,
        client_fee_pct=fee_pct,
        denominator_used=denominator_used,
        profit_gbp=result.profit_gbp,
        profit_pct=result.profit_pct,
        internal_notes=internal_notes,
    )
