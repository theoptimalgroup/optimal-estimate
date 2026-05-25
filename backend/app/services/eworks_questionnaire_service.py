"""Helpers for eWorks estimating questionnaire → calculation inputs."""

from __future__ import annotations

import re
from decimal import Decimal

from app.schemas.calculation import InternalNotesContext
from app.schemas.eworks_link import MaterialOrderRow, Step1Snapshot, Step2Snapshot, WorkBlockSnapshot


def format_links_and_quantity(rows: list[MaterialOrderRow]) -> str:
    parts: list[str] = []
    for row in rows:
        link = (row.link or "").strip()
        if not link:
            continue
        quantity = Decimal(str(row.quantity))
        quantity_text = (
            str(int(quantity))
            if quantity == quantity.to_integral_value()
            else str(quantity.normalize())
        )
        parts.append(f"{link} x {quantity_text}")
    return " / ".join(parts)


def build_internal_notes_context(step1: Step1Snapshot, block: WorkBlockSnapshot) -> InternalNotesContext:
    rows = [*block.materials_to_order, *block.shelf_materials_rows]
    return InternalNotesContext(
        links_and_quantity=format_links_and_quantity(rows),
        who_quoted=(step1.engineer_name or "").strip(),
        best_engineer=(block.best_engineer or "").strip(),
    )


def format_time_frame(unit: str, value: Decimal | float) -> str:
    numeric = Decimal(str(value))
    text = str(numeric).rstrip("0").rstrip(".") if numeric % 1 else str(int(numeric))
    if unit == "hours":
        return f"{text} hour" if numeric == 1 else f"{text} hours"
    return f"{text} day" if numeric == 1 else f"{text} days"


def work_block_to_step2_snapshot(block: WorkBlockSnapshot, *, trade_name: str) -> Step2Snapshot:
    labour_active = block.labour_required and block.engineers_required and block.engineer_time_unit == "days"
    primary_unit = block.engineer_time_unit if block.engineers_required else "days"
    primary_value = block.engineer_time_value if block.engineers_required else block.labour_time_value
    time_frame = block.time_frame or format_time_frame(primary_unit, primary_value)
    labourer_days = block.labour_time_value if labour_active else Decimal("0")
    step2 = Step2Snapshot(
        scope=block.scope,
        materials_to_order=block.materials_to_order,
        shelf_materials_rows=block.shelf_materials_rows,
        shelf_materials=block.shelf_materials,
        shelf_materials_cost=block.shelf_materials_cost,
        skill_required=block.skill_required or trade_name,
        best_engineer=block.best_engineer,
        subcontractors=block.subcontractors,
        time_frame=time_frame,
        engineers_needed=block.engineers_needed if block.engineers_required else 0,
        other_notes=block.other_notes,
        attachments=block.attachments,
        findings=block.findings,
        engineers=block.engineers_needed if block.engineers_required else 0,
        labourers=block.labour_needed if labour_active else 0,
        labourer_days=labourer_days,
        labour_type="hourly" if primary_unit == "hours" else "day",
        hours=primary_value if primary_unit == "hours" else Decimal("0"),
        days=primary_value if primary_unit == "days" else Decimal("0"),
        markup_value=block.markup_value,
        material_name=block.material_name,
        quantity=block.quantity,
        unit_cost=block.unit_cost,
    )
    return apply_questionnaire_defaults(step2, trade_name=trade_name)


def parse_time_frame(time_frame: str) -> tuple[str, Decimal, Decimal]:
    text = time_frame.lower().strip()
    hour_match = re.search(r"([\d.]+)\s*(?:hours?|hrs?|hr)\b", text)
    day_match = re.search(r"([\d.]+)\s*(?:days?)\b", text)
    if hour_match and not day_match:
        return "hourly", Decimal(hour_match.group(1)), Decimal("0")
    if day_match:
        return "day", Decimal("0"), Decimal(day_match.group(1))
    if hour_match:
        return "hourly", Decimal(hour_match.group(1)), Decimal("0")
    return "hourly", Decimal("1.5"), Decimal("0")


def apply_questionnaire_defaults(step2: Step2Snapshot, *, trade_name: str, default_skill: bool = True) -> Step2Snapshot:
    data = step2.model_copy(deep=True)
    if default_skill and not data.skill_required:
        data.skill_required = trade_name
    if data.time_frame:
        labour_type, hours, days = parse_time_frame(data.time_frame)
        data.labour_type = labour_type
        data.hours = hours
        data.days = days
    if data.engineers_needed and data.engineers_needed > 0:
        data.engineers = data.engineers_needed
    if data.labourers > 0 and data.labour_type in {"day", "half_day"} and data.labourer_days <= 0:
        data.labourer_days = data.days
    return data


def build_material_items(step2: Step2Snapshot) -> list[tuple[str, Decimal, Decimal]]:
    """Return (name, quantity, unit_cost) tuples for calculation."""
    items: list[tuple[str, Decimal, Decimal]] = []
    for index, row in enumerate(step2.materials_to_order, start=1):
        if row.cost <= 0:
            continue
        quantity = row.quantity if row.quantity > 0 else Decimal("1")
        unit_cost = row.cost / quantity
        label = f"Ordered material {index}"
        if row.link:
            label = row.link[:120]
        items.append((label, quantity, unit_cost))
    for index, row in enumerate(step2.shelf_materials_rows, start=1):
        if row.cost <= 0:
            continue
        quantity = row.quantity if row.quantity > 0 else Decimal("1")
        unit_cost = row.cost / quantity
        label = f"Shelf material {index}"
        if row.link:
            label = row.link[:120]
        items.append((label, quantity, unit_cost))
    if step2.shelf_materials_cost > 0 and not step2.shelf_materials_rows:
        items.append(("Shelf materials", Decimal("1"), step2.shelf_materials_cost))
    if not items and step2.unit_cost > 0:
        items.append((step2.material_name, step2.quantity, step2.unit_cost))
    return items


def step2_from_link_questionnaire(payload, trade_name: str) -> Step2Snapshot | None:
    from app.schemas.eworks_link import EworksLinkPayload, Step2Snapshot

    if not isinstance(payload, EworksLinkPayload):
        payload = EworksLinkPayload.model_validate(payload)
    has_questionnaire = any(
        [
            payload.scope,
            len(payload.materials_to_order) > 0,
            payload.shelf_materials,
            payload.shelf_materials_cost > 0,
            payload.time_frame,
            payload.best_engineer,
            payload.other_notes,
        ]
    )
    if not has_questionnaire:
        return None
    step2 = Step2Snapshot(
        scope=payload.scope,
        materials_to_order=payload.materials_to_order,
        shelf_materials=payload.shelf_materials,
        shelf_materials_cost=payload.shelf_materials_cost,
        skill_required=payload.skill_required,
        best_engineer=payload.best_engineer,
        subcontractors=payload.subcontractors,
        time_frame=payload.time_frame,
        engineers_needed=payload.engineers_needed,
        other_notes=payload.other_notes,
        findings=payload.findings_report,
    )
    return apply_questionnaire_defaults(step2, trade_name=trade_name, default_skill=False)
