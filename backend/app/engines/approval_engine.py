from decimal import Decimal

from app.models.rate_rule import RateRule
from app.schemas.calculation import CalculationBreakdown, ChargeInput, InternalNotesContext, LabourInput, MaterialInput
from app.engines.calculation_engine import (
    calculate_charges,
    calculate_combined_labour,
    calculate_material,
    calculate_margin,
    calculate_vat,
    round_money,
)
from app.engines.rules_engine import MatchedRule


def evaluate_approval_requirements(
    final_total: Decimal,
    rule: RateRule | None,
    manual_override: bool,
    margin_percentage: Decimal | None,
    rule_found: bool,
    other_charge: Decimal,
    other_charge_reason: str | None,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if not rule_found:
        reasons.append("No matching active rate rule found")
    if manual_override:
        reasons.append("Manual rate override used")
    if rule and rule.approval_threshold and final_total > rule.approval_threshold:
        reasons.append(f"Final total exceeds approval threshold of {rule.approval_threshold}")
    if rule and rule.minimum_margin_percentage is not None and margin_percentage is not None:
        if margin_percentage < rule.minimum_margin_percentage:
            reasons.append(f"Margin {margin_percentage}% below minimum {rule.minimum_margin_percentage}%")
    if other_charge > 0 and not other_charge_reason:
        reasons.append("Other charge added without reason")
    return bool(reasons), reasons


def _build_simplified_calculation_breakdown(
    labour_items: list[LabourInput],
    material_items: list[MaterialInput],
    charges: ChargeInput | None,
    matched_rule: MatchedRule | None,
    formula_version: str,
) -> CalculationBreakdown:
    rule = matched_rule.rule if matched_rule else None
    warnings: list[str] = []
    if matched_rule is None:
        warnings.append("RATE_RULE_NOT_FOUND")

    labour_breakdown = []
    labour_total = Decimal("0")
    manual_override_used = False
    for item in labour_items:
        result = calculate_combined_labour(
            labour_type=item.labour_type,
            engineers=item.number_of_engineers,
            labourers=item.number_of_labourers,
            hours=item.hours_on_site,
            days=item.days_on_site,
            hourly_rate=rule.hourly_rate if rule else Decimal("0"),
            half_day_rate=rule.half_day_rate if rule else Decimal("0"),
            day_rate=rule.day_rate if rule else Decimal("0"),
            labourer_hourly_rate=item.labourer_hourly_rate,
            labourer_half_day_rate=item.labourer_half_day_rate,
            labourer_day_rate=item.labourer_day_rate,
            minimum_hours=rule.minimum_hours if rule else None,
            minimum_charge=rule.minimum_charge if rule else None,
            manual_override=item.manual_override,
            manual_rate=item.manual_rate,
        )
        if item.manual_override:
            manual_override_used = True
        labour_total += result.total
        labour_breakdown.append({"label": f"Labour ({item.labour_type})", "formula": result.formula, "total": result.total})

    material_breakdown = []
    material_sell_total = Decimal("0")
    material_base_total = Decimal("0")
    for item in material_items:
        result = calculate_material(
            quantity=item.quantity,
            unit_cost=item.unit_cost,
            delivery_cost=item.delivery_cost,
            markup_type=item.markup_type,
            markup_value=item.markup_value,
            rule_markup_type=rule.material_markup_type if rule else None,
            rule_markup_value=rule.material_markup_value if rule else None,
        )
        material_sell_total += result.sell_total
        material_base_total += result.base_cost
        material_breakdown.append(
            {"label": item.material_name, "formula": result.formula, "total": result.sell_total}
        )

    charge_result = calculate_charges(charges)
    charges_total = (
        charge_result.parking_total
        + charge_result.congestion_total
        + charge_result.ulez_total
        + charge_result.waste_total
        + charge_result.travel_total
        + charge_result.other_total
    )
    charge_breakdown = [
        {"label": label, "formula": formula, "total": total}
        for label, formula, total in charge_result.breakdown
    ]

    subtotal = round_money(labour_total + material_sell_total + charges_total)
    vat_rate = rule.vat_rate if rule else Decimal("20.00")
    vat_total = calculate_vat(subtotal, vat_rate)
    final_total = round_money(subtotal + vat_total)
    margin_total = round_money(material_sell_total - material_base_total) if material_items else None
    margin_pct = calculate_margin(material_sell_total, material_base_total) if material_items else None

    other_charge = charges.other_charge if charges else Decimal("0")
    other_reason = charges.other_charge_reason if charges else None
    approval_required, approval_reasons = evaluate_approval_requirements(
        final_total=final_total,
        rule=rule,
        manual_override=manual_override_used,
        margin_percentage=margin_pct,
        rule_found=matched_rule is not None,
        other_charge=other_charge,
        other_charge_reason=other_reason,
    )

    from app.schemas.calculation import LineBreakdown

    return CalculationBreakdown(
        labour=[LineBreakdown(**x) for x in labour_breakdown],
        materials=[LineBreakdown(**x) for x in material_breakdown],
        charges=[LineBreakdown(**x) for x in charge_breakdown],
        subtotal=subtotal,
        vat_rate=vat_rate,
        vat_total=vat_total,
        final_total=final_total,
        margin_total=margin_total,
        rule_version=rule.version if rule else None,
        formula_version=formula_version,
        approval_required=approval_required,
        approval_reasons=approval_reasons,
        warnings=warnings,
        formula_source="simplified",
    )


def build_calculation_breakdown(
    labour_items: list[LabourInput],
    material_items: list[MaterialInput],
    charges: ChargeInput | None,
    matched_rule: MatchedRule | None,
    formula_version: str,
    internal_notes_context: InternalNotesContext | None = None,
) -> CalculationBreakdown:
    rule = matched_rule.rule if matched_rule else None
    if (
        rule
        and getattr(rule, "formula_source", "simplified") == "xlsx"
        and labour_items
        and all(item.labour_type in ("hourly", "day") for item in labour_items)
    ):
        from app.engines.xlsx_breakdown_engine import build_xlsx_calculation_breakdown

        return build_xlsx_calculation_breakdown(
            labour_items=labour_items,
            material_items=material_items,
            charges=charges,
            matched_rule=matched_rule,
            formula_version=formula_version,
            internal_notes_context=internal_notes_context,
        )
    return _build_simplified_calculation_breakdown(
        labour_items=labour_items,
        material_items=material_items,
        charges=charges,
        matched_rule=matched_rule,
        formula_version=formula_version,
    )
