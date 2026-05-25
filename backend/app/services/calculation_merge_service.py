"""Merge per-work calculation breakdowns and apply session charges once."""

from __future__ import annotations

from decimal import Decimal

from app.engines.calculation_engine import calculate_charges, calculate_vat, round_money
from app.schemas.calculation import CalculationBreakdown, ChargeInput, LineBreakdown
from app.schemas.eworks_link import WorkBreakdownResult


def _breakdown_group_label(result: WorkBreakdownResult) -> str:
    scope = (result.scope or "").strip()
    if scope and len(scope) <= 40 and "\n" not in scope:
        return scope
    return f"Work {result.work_index + 1}"


def merge_work_breakdowns(
    work_results: list[WorkBreakdownResult],
    *,
    charges: ChargeInput | None,
    vat_rate: Decimal,
    formula_version: str,
    formula_source: str | None = None,
    xlsx_formula_version: str | None = None,
) -> CalculationBreakdown:
    labour_lines: list[LineBreakdown] = []
    material_lines: list[LineBreakdown] = []
    merged_subtotal = Decimal("0")
    direct_labour_cost = Decimal("0")
    labour_charge_to_client = Decimal("0")
    materials_parking_cc_charge = Decimal("0")
    profit_gbp = Decimal("0")
    internal_notes_parts: list[str] = []

    for result in work_results:
        prefix = _breakdown_group_label(result)
        breakdown = result.breakdown
        merged_subtotal += breakdown.subtotal
        if breakdown.direct_labour_cost:
            direct_labour_cost += breakdown.direct_labour_cost
        if breakdown.labour_charge_to_client:
            labour_charge_to_client += breakdown.labour_charge_to_client
        if breakdown.materials_parking_cc_charge:
            materials_parking_cc_charge += breakdown.materials_parking_cc_charge
        if breakdown.profit_gbp:
            profit_gbp += breakdown.profit_gbp
        for line in breakdown.labour:
            labour_lines.append(
                LineBreakdown(label=f"{prefix}: {line.label}", formula=line.formula, total=line.total)
            )
        for line in breakdown.materials:
            material_lines.append(
                LineBreakdown(label=f"{prefix}: {line.label}", formula=line.formula, total=line.total)
            )
        if result.internal_notes:
            internal_notes_parts.append(f"--- {prefix} ---\n{result.internal_notes}")

    charge_result = calculate_charges(charges)
    charge_lines = [
        LineBreakdown(label=label, formula=formula, total=total)
        for label, formula, total in charge_result.breakdown
    ]
    charges_total = (
        charge_result.parking_total
        + charge_result.congestion_total
        + charge_result.ulez_total
        + charge_result.waste_total
        + charge_result.travel_total
        + charge_result.other_total
    )

    subtotal = round_money(merged_subtotal + charges_total)
    vat_total = calculate_vat(subtotal, vat_rate)
    final_total = round_money(subtotal + vat_total)

    profit_pct = None
    if labour_charge_to_client + materials_parking_cc_charge > 0:
        profit_pct = round_money(
            (profit_gbp / (labour_charge_to_client + materials_parking_cc_charge)) * Decimal("100")
        )

    return CalculationBreakdown(
        labour=labour_lines,
        materials=material_lines,
        charges=charge_lines,
        subtotal=subtotal,
        vat_rate=vat_rate,
        vat_total=vat_total,
        final_total=final_total,
        formula_version=formula_version,
        formula_source=formula_source,
        xlsx_formula_version=xlsx_formula_version,
        direct_labour_cost=direct_labour_cost or None,
        labour_charge_to_client=labour_charge_to_client or None,
        materials_parking_cc_charge=materials_parking_cc_charge or None,
        profit_gbp=profit_gbp or None,
        profit_pct=profit_pct,
        internal_notes="\n\n".join(internal_notes_parts) if internal_notes_parts else None,
    )
