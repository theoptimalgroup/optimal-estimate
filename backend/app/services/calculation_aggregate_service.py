"""Aggregate multi-work questionnaire inputs into a single XLSX calculation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.schemas.calculation import (
    CalculationBreakdown,
    CalculationPreviewRequest,
    ChargeInput,
    InternalNotesContext,
    LabourInput,
    LineBreakdown,
    MaterialInput,
)
from app.schemas.eworks_link import Step1Snapshot, Step2Snapshot, WorkBlockSnapshot, step2_session_charges
from app.services.eworks_link_service import collect_work_skills, resolve_skill_trade, work_skill_name
from app.services.eworks_questionnaire_service import (
    build_material_items,
    format_links_and_quantity,
    work_block_to_step2_snapshot,
)

HOURS_PER_DAY = Decimal("8")


def round_to_half(value: Decimal) -> Decimal:
    return (value * 2).quantize(Decimal("1"), rounding=ROUND_HALF_UP) / 2


def _decimal(value: object) -> Decimal:
    return Decimal(str(value))


def _block_engineer_hours(block: WorkBlockSnapshot) -> Decimal:
    if not block.engineers_required:
        return Decimal("0")
    count = _decimal(block.engineers_needed)
    duration = _decimal(block.engineer_time_value)
    if block.engineer_time_unit == "days":
        return count * duration * HOURS_PER_DAY
    return count * duration


def _block_labour_days(block: WorkBlockSnapshot) -> Decimal:
    labour_active = block.labour_required and block.engineers_required and block.engineer_time_unit == "days"
    if not labour_active:
        return Decimal("0")
    return _decimal(block.labour_needed) * _decimal(block.labour_time_value)


@dataclass(frozen=True)
class AggregatedWorkInputs:
    labour_type: str
    engineers: int
    hours: Decimal
    days: Decimal
    labourers: int
    labourer_days: Decimal
    uses_mixed_units: bool
    converted_from_hours: bool
    total_engineer_hours: Decimal
    total_labour_days: Decimal


def aggregate_work_blocks(works: list[WorkBlockSnapshot]) -> AggregatedWorkInputs:
    engineer_units: set[str] = set()
    total_engineer_hours = Decimal("0")
    total_labour_days = Decimal("0")
    has_labour = False

    for block in works:
        if block.engineers_required:
            engineer_units.add(block.engineer_time_unit)
            total_engineer_hours += _block_engineer_hours(block)
        labour_days = _block_labour_days(block)
        if labour_days > 0:
            has_labour = True
            total_labour_days += labour_days

    uses_mixed_units = "hours" in engineer_units and "days" in engineer_units
    use_hourly = engineer_units == {"hours"} and not has_labour

    if use_hourly:
        rounded_hours = round_to_half(total_engineer_hours)
        return AggregatedWorkInputs(
            labour_type="hourly",
            engineers=1,
            hours=rounded_hours,
            days=Decimal("0"),
            labourers=0,
            labourer_days=Decimal("0"),
            uses_mixed_units=uses_mixed_units,
            converted_from_hours=False,
            total_engineer_hours=total_engineer_hours,
            total_labour_days=total_labour_days,
        )

    engineer_days = round_to_half(total_engineer_hours / HOURS_PER_DAY)
    labour_days = round_to_half(total_labour_days) if has_labour else Decimal("0")
    return AggregatedWorkInputs(
        labour_type="day",
        engineers=1,
        hours=Decimal("0"),
        days=engineer_days,
        labourers=1 if has_labour and labour_days > 0 else 0,
        labourer_days=labour_days,
        uses_mixed_units=uses_mixed_units,
        converted_from_hours="hours" in engineer_units,
        total_engineer_hours=total_engineer_hours,
        total_labour_days=total_labour_days,
    )


def build_combined_internal_notes_context(step1: Step1Snapshot, works: list[WorkBlockSnapshot]) -> InternalNotesContext:
    link_parts: list[str] = []
    best_engineers: list[str] = []
    for block in works:
        rows = [*block.materials_to_order, *block.shelf_materials_rows]
        formatted = format_links_and_quantity(rows)
        if formatted:
            link_parts.append(formatted)
        if block.best_engineer and block.best_engineer.strip():
            best_engineers.append(block.best_engineer.strip())
    return InternalNotesContext(
        links_and_quantity=" / ".join(link_parts),
        who_quoted=(step1.engineer_name or "").strip(),
        best_engineer=" / ".join(dict.fromkeys(best_engineers)),
    )


def build_combined_material_inputs(step1: Step1Snapshot, step2: Step2Snapshot) -> list[MaterialInput]:
    materials: list[MaterialInput] = []
    for index, block in enumerate(step2.works, start=1):
        work_step2 = work_block_to_step2_snapshot(block, trade_name=step1.trade_name)
        for material_name, quantity, unit_cost in build_material_items(work_step2):
            materials.append(
                MaterialInput(
                    material_name=f"Work {index}: {material_name}",
                    quantity=quantity,
                    unit_cost=unit_cost,
                    markup_type="percentage",
                    markup_value=work_step2.markup_value,
                    client_visible=True,
                )
            )
    return materials


def build_skill_group_labour_inputs(
    group_works: list[WorkBlockSnapshot],
    *,
    trade_id: UUID,
) -> tuple[list[LabourInput], AggregatedWorkInputs]:
    aggregated = aggregate_work_blocks(group_works)
    labour = LabourInput(
        labour_type=aggregated.labour_type,
        number_of_engineers=aggregated.engineers,
        number_of_labourers=aggregated.labourers,
        hours_on_site=aggregated.hours if aggregated.labour_type == "hourly" else None,
        days_on_site=aggregated.days if aggregated.labour_type == "day" else None,
        labourer_days=aggregated.labourer_days if aggregated.labour_type == "day" else None,
        trade_id=trade_id,
    )
    return [labour], aggregated


def build_combined_calculation_inputs(
    step1: Step1Snapshot,
    step2: Step2Snapshot,
    *,
    trade_id: UUID,
) -> tuple[list[LabourInput], list[MaterialInput], ChargeInput, AggregatedWorkInputs]:
    aggregated = aggregate_work_blocks(step2.works)
    labour, _ = build_skill_group_labour_inputs(step2.works, trade_id=trade_id)
    materials = build_combined_material_inputs(step1, step2)
    charges = step2_session_charges(step1, step2)
    return labour, materials, charges, aggregated


def group_works_by_skill(
    works: list[WorkBlockSnapshot],
    fallback_trade_name: str,
) -> list[tuple[str, list[WorkBlockSnapshot]]]:
    groups: dict[str, list[WorkBlockSnapshot]] = {}
    order: list[str] = []
    for block in works:
        skill = work_skill_name(block, fallback_trade_name)
        if skill not in groups:
            groups[skill] = []
            order.append(skill)
        groups[skill].append(block)
    return [(skill, groups[skill]) for skill in order]


def _assemble_mixed_skill_breakdown(
    skill_parts: list[tuple[str, CalculationBreakdown]],
    materials_breakdown: CalculationBreakdown,
    *,
    vat_rate: Decimal,
    formula_version: str,
    formula_source: str | None = None,
    xlsx_formula_version: str | None = None,
) -> CalculationBreakdown:
    from app.engines.calculation_engine import calculate_vat, round_money

    labour_lines: list[LineBreakdown] = []
    labour_charge = Decimal("0")
    direct_labour_cost = Decimal("0")
    profit_gbp = Decimal("0")
    internal_notes_parts: list[str] = []

    for skill, breakdown in skill_parts:
        if breakdown.labour_charge_to_client:
            labour_charge += breakdown.labour_charge_to_client
        if breakdown.direct_labour_cost:
            direct_labour_cost += breakdown.direct_labour_cost
        if breakdown.profit_gbp:
            profit_gbp += breakdown.profit_gbp
        for line in breakdown.labour:
            labour_lines.append(
                LineBreakdown(label=f"{skill}: {line.label}", formula=line.formula, total=line.total)
            )
        if breakdown.internal_notes:
            internal_notes_parts.append(f"--- {skill} ---\n{breakdown.internal_notes}")

    materials_charge = materials_breakdown.materials_parking_cc_charge or Decimal("0")
    if materials_breakdown.profit_gbp:
        profit_gbp += materials_breakdown.profit_gbp

    passthrough_total = Decimal("0")
    for line in materials_breakdown.charges:
        passthrough_total += line.total

    subtotal = round_money(labour_charge + materials_charge + passthrough_total)
    vat_total = calculate_vat(subtotal, vat_rate)
    final_total = round_money(subtotal + vat_total)

    profit_pct = None
    if labour_charge + materials_charge > 0:
        profit_pct = round_money((profit_gbp / (labour_charge + materials_charge)) * Decimal("100"))

    if materials_breakdown.internal_notes:
        internal_notes_parts.append(
            f"--- Combined materials & session charges ---\n{materials_breakdown.internal_notes}"
        )

    return CalculationBreakdown(
        labour=labour_lines,
        materials=materials_breakdown.materials,
        charges=materials_breakdown.charges,
        subtotal=subtotal,
        vat_rate=vat_rate,
        vat_total=vat_total,
        final_total=final_total,
        formula_version=formula_version,
        formula_source=formula_source or materials_breakdown.formula_source,
        xlsx_formula_version=xlsx_formula_version or materials_breakdown.xlsx_formula_version,
        direct_labour_cost=direct_labour_cost or None,
        overhead_cost=materials_breakdown.overhead_cost,
        labour_charge_to_client=labour_charge or None,
        materials_parking_cc_charge=materials_charge or None,
        client_fee_pct=materials_breakdown.client_fee_pct,
        denominator_used=materials_breakdown.denominator_used,
        profit_gbp=profit_gbp or None,
        profit_pct=profit_pct,
        internal_notes="\n\n".join(internal_notes_parts) if internal_notes_parts else None,
    )


def build_mixed_skill_combined_breakdown(
    db: Session,
    *,
    client_id: UUID,
    step1: Step1Snapshot,
    step2: Step2Snapshot,
    fallback_trade_name: str,
    charges: ChargeInput,
    vat_rate: Decimal,
    formula_version: str,
    formula_source: str | None = None,
    xlsx_formula_version: str | None = None,
) -> tuple[CalculationBreakdown, AggregatedWorkInputs, list[str]]:
    from app.services.calculation_service import preview_calculation

    skills = collect_work_skills(step2.works, fallback_trade_name)
    skill_parts: list[tuple[str, CalculationBreakdown]] = []
    for skill, group_works in group_works_by_skill(step2.works, fallback_trade_name):
        trade = resolve_skill_trade(db, skill, fallback_trade_name=fallback_trade_name)
        labour, _group_aggregated = build_skill_group_labour_inputs(group_works, trade_id=trade.id)
        breakdown = preview_calculation(
            db,
            CalculationPreviewRequest(
                client_id=client_id,
                trade_id=trade.id,
                labour_items=labour,
                material_items=[],
                charges=None,
                internal_notes_context=build_combined_internal_notes_context(step1, group_works),
            ),
        )
        skill_parts.append((skill, breakdown))

    materials_trade = resolve_skill_trade(db, skills[0], fallback_trade_name=fallback_trade_name)
    materials_labour = [
        LabourInput(
            labour_type="hourly",
            number_of_engineers=1,
            number_of_labourers=0,
            hours_on_site=Decimal("0"),
            trade_id=materials_trade.id,
        )
    ]
    materials_breakdown = preview_calculation(
        db,
        CalculationPreviewRequest(
            client_id=client_id,
            trade_id=materials_trade.id,
            labour_items=materials_labour,
            material_items=build_combined_material_inputs(step1, step2),
            charges=charges,
            internal_notes_context=build_combined_internal_notes_context(step1, step2.works),
        ),
    )

    merged = _assemble_mixed_skill_breakdown(
        skill_parts,
        materials_breakdown,
        vat_rate=vat_rate,
        formula_version=formula_version,
        formula_source=formula_source,
        xlsx_formula_version=xlsx_formula_version,
    )
    aggregated = aggregate_work_blocks(step2.works)
    return merged, aggregated, skills


def _format_quantity(value: Decimal) -> str:
    if value == value.to_integral_value():
        return str(int(value))
    return str(value.normalize())


def format_aggregated_quote_subtitle(
    aggregated: AggregatedWorkInputs,
    work_count: int,
    *,
    skills: list[str] | None = None,
) -> str:
    work_label = "work" if work_count == 1 else "works"
    if aggregated.labour_type == "hourly":
        hours = _format_quantity(aggregated.hours)
        unit = "hour" if aggregated.hours == 1 else "hours"
        base = f"{hours} {unit} total across {work_count} {work_label}"
    elif aggregated.labourers > 0 and aggregated.labourer_days > 0:
        days = _format_quantity(aggregated.days)
        day_unit = "day" if aggregated.days == 1 else "days"
        labour = _format_quantity(aggregated.labourer_days)
        labour_unit = "labour day" if aggregated.labourer_days == 1 else "labour days"
        base = f"{days} engineer {day_unit} + {labour} {labour_unit} across {work_count} {work_label}"
    else:
        days = _format_quantity(aggregated.days)
        day_unit = "day" if aggregated.days == 1 else "days"
        base = f"{days} {day_unit} total across {work_count} {work_label}"

    if skills and len(skills) > 1:
        return f"{base} ({', '.join(skills)})"
    return base


def aggregated_quote_summary(
    aggregated: AggregatedWorkInputs,
    work_count: int,
    *,
    skills: list[str] | None = None,
) -> dict[str, object]:
    skill_list = skills or []
    return {
        "work_count": work_count,
        "labour_type": aggregated.labour_type,
        "quoted_engineer_hours": aggregated.hours if aggregated.labour_type == "hourly" else None,
        "quoted_engineer_days": aggregated.days if aggregated.labour_type == "day" else None,
        "quoted_labour_days": aggregated.labourer_days if aggregated.labourers > 0 else None,
        "uses_mixed_units": aggregated.uses_mixed_units,
        "converted_from_hours": aggregated.converted_from_hours,
        "mixed_skills": len(skill_list) > 1,
        "skills": skill_list,
        "subtitle": format_aggregated_quote_subtitle(aggregated, work_count, skills=skill_list),
    }
