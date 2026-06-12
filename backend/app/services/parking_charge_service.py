"""Parking and congestion charge duration calculations (1 day = 8 hours)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal

from app.engines.calculation_engine import round_money
from app.schemas.eworks_link import Step2Snapshot, WorkBlockSnapshot
from app.services.trade_service import normalize_trade_name

HOURS_PER_DAY = Decimal("8")

PARKING_TYPE_PER_DAY = "fixed"
PARKING_TYPE_PER_HOUR = "hourly"


def duration_to_hours(days: Decimal | float | int, hours: Decimal | float | int) -> Decimal:
    return Decimal(str(days)) * HOURS_PER_DAY + Decimal(str(hours))


def hours_to_days(hours: Decimal | float | int) -> Decimal:
    return Decimal(str(hours)) / HOURS_PER_DAY


def decompose_duration_hours(total_hours: Decimal) -> tuple[Decimal, Decimal]:
    """Return whole days and remaining hours for display (e.g. 10h -> 1 day, 2 hours)."""
    if total_hours <= 0:
        return Decimal("0"), Decimal("0")
    whole_days = total_hours // HOURS_PER_DAY
    remainder = total_hours - whole_days * HOURS_PER_DAY
    return whole_days, remainder


def work_duration_components(block: WorkBlockSnapshot) -> tuple[Decimal, Decimal]:
    """Engineer on-site duration for one work block (days component, hours component)."""
    if not block.engineers_required:
        return Decimal("0"), Decimal("0")
    engineers = Decimal(str(block.engineers_needed or 1))
    duration = Decimal(str(block.engineer_time_value or 0))
    if block.engineer_time_unit == "days":
        return engineers * duration, Decimal("0")
    return Decimal("0"), engineers * duration


def works_combined_duration_hours(works: list[WorkBlockSnapshot]) -> Decimal:
    return sum((duration_to_hours(days, hours) for days, hours in (work_duration_components(w) for w in works)), Decimal("0"))


def works_combined_duration_decomposed(works: list[WorkBlockSnapshot]) -> tuple[Decimal, Decimal]:
    total_hours = works_combined_duration_hours(works)
    return decompose_duration_hours(total_hours)


def calculate_parking_charge(
    parking_type: str | None,
    *,
    rate_per_day: Decimal | float | int,
    rate_per_hour: Decimal | float | int,
    days: Decimal | float | int,
    hours: Decimal | float | int,
    vehicles: int = 1,
) -> Decimal:
    vehicle_count = Decimal(str(max(1, vehicles)))
    total_hours = duration_to_hours(days, hours)
    normalized = (parking_type or PARKING_TYPE_PER_DAY).strip().lower()
    if normalized == PARKING_TYPE_PER_HOUR:
        rate = Decimal(str(rate_per_hour))
        return round_money(rate * total_hours * vehicle_count)
    rate = Decimal(str(rate_per_day))
    total_days = hours_to_days(total_hours)
    return round_money(rate * total_days * vehicle_count)


def cc_chargeable_days(total_hours: Decimal | float | int) -> int:
    """Whole CC charge days: any time on a day counts as a full day (ceil hours / 8)."""
    hours = Decimal(str(total_hours))
    if hours <= 0:
        return 0
    return math.ceil(float(hours / HOURS_PER_DAY))


def calculate_cc_charge(
    days: Decimal | float | int,
    hours: Decimal | float | int,
    cc_rate_per_day: Decimal | float | int,
    *,
    enabled: bool = True,
) -> Decimal:
    """Congestion charge: fixed per whole day, never prorated by hours."""
    if not enabled:
        return Decimal("0")
    rate = Decimal(str(cc_rate_per_day))
    if rate <= 0:
        return Decimal("0")
    total_hours = duration_to_hours(days, hours)
    chargeable_days = cc_chargeable_days(total_hours)
    if chargeable_days <= 0:
        return Decimal("0")
    return round_money(rate * Decimal(chargeable_days))


def charge_allocation_trade_key(block: WorkBlockSnapshot) -> str:
    return normalize_trade_name((block.skill_required or "").strip())


def charge_allocation_engineer_key(block: WorkBlockSnapshot, work_index: int) -> str:
    engineer = (block.best_engineer or "").strip()
    if engineer:
        return engineer.casefold()
    return f"__work_{work_index}__"


def charge_allocation_group_key(block: WorkBlockSnapshot, work_index: int) -> tuple[str, str]:
    return (
        charge_allocation_trade_key(block),
        charge_allocation_engineer_key(block, work_index),
    )


def group_works_for_charge_allocation(works: list[WorkBlockSnapshot]) -> list[list[int]]:
    """Group work indices by same trade + same engineer (blank engineer => separate per work)."""
    groups: dict[t[str, str], list[int]] = {}
    order: list[t[str, str]] = []
    for index, block in enumerate(works):
        key = charge_allocation_group_key(block, index)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(index)
    return [groups[key] for key in order]


def _group_combined_hours(works: list[WorkBlockSnapshot], group_indices: list[int]) -> Decimal:
    return sum(
        duration_to_hours(*work_duration_components(works[index])) for index in group_indices
    )


def _allocate_proportional(
    group_total: Decimal,
    total_hours_list: list[Decimal],
    group_indices: list[int],
) -> list[Decimal]:
    group_hours = sum(total_hours_list[index] for index in group_indices)
    parts: list[Decimal] = []
    for index in group_indices:
        if group_hours <= 0:
            parts.append(Decimal("0"))
            continue
        parts.append(round_money(group_total * total_hours_list[index] / group_hours))
    return _reconcile_rounded_parts(parts, group_total)


def calculate_cc_total(step2: Step2Snapshot, works: list[WorkBlockSnapshot] | None = None) -> Decimal:
    if not step2.congestion_required:
        return Decimal("0")
    work_blocks = works or step2.works
    if not work_blocks:
        return Decimal("0")
    total = Decimal("0")
    for group_indices in group_works_for_charge_allocation(work_blocks):
        group_hours = _group_combined_hours(work_blocks, group_indices)
        total += calculate_cc_charge(
            Decimal("0"),
            group_hours,
            step2.congestion_amount,
            enabled=True,
        )
    return total


def calculate_cc_total_days(step2: Step2Snapshot, works: list[WorkBlockSnapshot] | None = None) -> int:
    if not step2.congestion_required:
        return 0
    work_blocks = works or step2.works
    if not work_blocks:
        return 0
    return sum(
        cc_chargeable_days(_group_combined_hours(work_blocks, group_indices))
        for group_indices in group_works_for_charge_allocation(work_blocks)
    )


def calculate_parking_total(step2: Step2Snapshot, works: list[WorkBlockSnapshot] | None = None) -> Decimal:
    if not step2.parking_required:
        return Decimal("0")
    work_blocks = works or step2.works
    if not work_blocks:
        return Decimal("0")
    total = Decimal("0")
    for group_indices in group_works_for_charge_allocation(work_blocks):
        group_hours = _group_combined_hours(work_blocks, group_indices)
        total += calculate_parking_charge(
            step2.parking_type,
            rate_per_day=step2.parking_fixed_amount or Decimal("0"),
            rate_per_hour=step2.parking_rate_per_hour or Decimal("0"),
            days=Decimal("0"),
            hours=group_hours,
            vehicles=step2.parking_vehicles or 1,
        )
    return total


def format_cc_summary(
    step2: Step2Snapshot,
    *,
    days: Decimal,
    hours: Decimal,
    cc_total: Decimal,
    chargeable_days: int | None = None,
) -> str:
    if not step2.congestion_required or cc_total <= 0:
        return ""
    total_hours = duration_to_hours(days, hours)
    cc_days = chargeable_days if chargeable_days is not None else cc_chargeable_days(total_hours)
    rate = step2.congestion_amount or Decimal("0")
    day_label = "day" if cc_days == 1 else "days"
    return f"CC: £{rate} × {cc_days} {day_label} = £{cc_total}"


def format_combined_cc_review_lines(step2: Step2Snapshot, works: list[WorkBlockSnapshot]) -> list[str]:
    cc_total = calculate_cc_total(step2, works)
    if not step2.congestion_required or cc_total <= 0:
        return []
    cc_days = calculate_cc_total_days(step2, works)
    rate = step2.congestion_amount or Decimal("0")
    return [
        f"CC charge per day: £{rate}",
        f"CC days: {cc_days}",
        f"CC total: £{cc_total}",
    ]


def format_parking_type_label(parking_type: str | None) -> str:
    if (parking_type or "").strip().lower() == PARKING_TYPE_PER_HOUR:
        return "Per Hour"
    return "Per Day"


def format_parking_summary(
    step2: Step2Snapshot,
    *,
    days: Decimal,
    hours: Decimal,
    parking_total: Decimal,
) -> str:
    if not step2.parking_required or parking_total <= 0:
        return ""
    vehicles = max(1, step2.parking_vehicles or 1)
    vehicle_suffix = f" × {vehicles} vehicles" if vehicles > 1 else " × 1 vehicle"
    label = format_parking_type_label(step2.parking_type)
    normalized = (step2.parking_type or PARKING_TYPE_PER_DAY).strip().lower()
    total_hours = duration_to_hours(days, hours)
    if normalized == PARKING_TYPE_PER_HOUR:
        rate = step2.parking_rate_per_hour or Decimal("0")
        return f"Parking: {label} £{rate}/hr × {total_hours.normalize()} hr{vehicle_suffix} = £{parking_total}"
    rate = step2.parking_fixed_amount or Decimal("0")
    total_days = hours_to_days(total_hours)
    return f"Parking: {label} £{rate}/day × {total_days.normalize()} day{vehicle_suffix} = £{parking_total}"


@dataclass(frozen=True)
class WorkSessionChargeAllocation:
    work_index: int
    duration_days: Decimal
    duration_hours: Decimal
    total_hours: Decimal
    cc_chargeable_days: int
    parking_total: Decimal
    cc_total: Decimal


def _reconcile_rounded_parts(parts: list[Decimal], target: Decimal) -> list[Decimal]:
    if not parts:
        return parts
    remainder = round_money(target - sum(parts, Decimal("0")))
    if remainder == 0:
        return parts
    adjusted = list(parts)
    adjusted[-1] = round_money(adjusted[-1] + remainder)
    return adjusted


def allocate_parking_cc_to_work_blocks(step2: Step2Snapshot, works: list[WorkBlockSnapshot]) -> list[WorkSessionChargeAllocation]:
    if not works:
        return []

    components = [work_duration_components(block) for block in works]
    total_hours_list = [duration_to_hours(days, hours) for days, hours in components]

    parking_parts = [Decimal("0")] * len(works)
    cc_parts = [Decimal("0")] * len(works)
    cc_days_list = [0] * len(works)

    for group_indices in group_works_for_charge_allocation(works):
        group_hours = _group_combined_hours(works, group_indices)
        group_cc_days = cc_chargeable_days(group_hours)

        if step2.parking_required:
            group_parking = calculate_parking_charge(
                step2.parking_type,
                rate_per_day=step2.parking_fixed_amount or Decimal("0"),
                rate_per_hour=step2.parking_rate_per_hour or Decimal("0"),
                days=Decimal("0"),
                hours=group_hours,
                vehicles=step2.parking_vehicles or 1,
            )
            allocated_parking = _allocate_proportional(group_parking, total_hours_list, group_indices)
            for part_index, work_index in enumerate(group_indices):
                parking_parts[work_index] = allocated_parking[part_index]

        if step2.congestion_required:
            group_cc = calculate_cc_charge(
                Decimal("0"),
                group_hours,
                step2.congestion_amount,
                enabled=True,
            )
            allocated_cc = _allocate_proportional(group_cc, total_hours_list, group_indices)
            for part_index, work_index in enumerate(group_indices):
                cc_parts[work_index] = allocated_cc[part_index]
                if allocated_cc[part_index] > 0:
                    cc_days_list[work_index] = group_cc_days

    allocations: list[WorkSessionChargeAllocation] = []
    for index, (days, hours) in enumerate(components):
        allocations.append(
            WorkSessionChargeAllocation(
                work_index=index,
                duration_days=days,
                duration_hours=hours,
                total_hours=total_hours_list[index],
                cc_chargeable_days=cc_days_list[index],
                parking_total=parking_parts[index],
                cc_total=cc_parts[index],
            )
        )
    return allocations


def charge_input_for_allocation(step2: Step2Snapshot, allocation: WorkSessionChargeAllocation):
    from app.schemas.calculation import ChargeInput

    return ChargeInput(
        parking_required=step2.parking_required and allocation.parking_total > 0,
        parking_type=step2.parking_type,
        parking_rate_per_hour=step2.parking_rate_per_hour,
        parking_hours=allocation.total_hours,
        parking_fixed_amount=step2.parking_fixed_amount,
        parking_vehicles=step2.parking_vehicles or 1,
        parking_duration_days=allocation.duration_days,
        parking_duration_hours=allocation.duration_hours,
        parking_amount_override=allocation.parking_total if step2.parking_required else None,
        congestion_required=step2.congestion_required and allocation.cc_total > 0,
        congestion_amount=allocation.cc_total,
    )


def charge_input_for_combined(step2: Step2Snapshot, works: list[WorkBlockSnapshot]):
    from app.schemas.calculation import ChargeInput

    combined_hours = works_combined_duration_hours(works)
    days, hours = decompose_duration_hours(combined_hours)
    parking_total = calculate_parking_total(step2, works)
    combined_cc = calculate_cc_total(step2, works)
    return ChargeInput(
        parking_required=step2.parking_required,
        parking_type=step2.parking_type,
        parking_rate_per_hour=step2.parking_rate_per_hour,
        parking_hours=combined_hours,
        parking_fixed_amount=step2.parking_fixed_amount,
        parking_vehicles=step2.parking_vehicles or 1,
        parking_duration_days=days,
        parking_duration_hours=hours,
        parking_amount_override=parking_total if step2.parking_required else None,
        congestion_required=step2.congestion_required,
        congestion_amount=combined_cc,
        travel_charge=step2.travel_charge,
        other_charge=step2.other_charge,
        other_charge_reason=step2.other_charge_reason,
    )


def build_work_internal_notes_context(
    step1,
    block: WorkBlockSnapshot,
    step2: Step2Snapshot,
    allocation: WorkSessionChargeAllocation | None,
):
    from app.schemas.calculation import InternalNotesContext
    from app.services.eworks_questionnaire_service import build_internal_notes_context

    base = build_internal_notes_context(step1, block)
    if allocation is None:
        return base
    parking_summary = ""
    if step2.parking_required and allocation.parking_total > 0:
        parking_summary = format_parking_summary(
            step2,
            days=allocation.duration_days,
            hours=allocation.duration_hours,
            parking_total=allocation.parking_total,
        )
    cc_summary = ""
    if allocation.cc_total > 0:
        cc_summary = format_cc_summary(
            step2,
            days=allocation.duration_days,
            hours=allocation.duration_hours,
            cc_total=allocation.cc_total,
            chargeable_days=allocation.cc_chargeable_days,
        )
    return base.model_copy(
        update={
            "duration_days": str(allocation.duration_days.normalize()),
            "duration_hours": str(allocation.duration_hours.normalize()),
            "parking_summary": parking_summary,
            "cc_summary": cc_summary,
        }
    )
