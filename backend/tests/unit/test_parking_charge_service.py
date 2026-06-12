from decimal import Decimal

from app.schemas.eworks_link import Step2Snapshot, WorkBlockSnapshot
from app.services.parking_charge_service import (
    allocate_parking_cc_to_work_blocks,
    calculate_cc_charge,
    calculate_cc_total,
    calculate_cc_total_days,
    calculate_parking_charge,
    calculate_parking_total,
    cc_chargeable_days,
    charge_allocation_group_key,
    duration_to_hours,
    group_works_for_charge_allocation,
    hours_to_days,
    works_combined_duration_hours,
)

CC_RATE = Decimal("28.80")
PARKING_RATE = Decimal("126")


def _work(
    *,
    unit: str = "hours",
    value: str,
    engineers: int = 1,
    skill: str | None = None,
    best_engineer: str | None = None,
) -> WorkBlockSnapshot:
    return WorkBlockSnapshot(
        engineers_required=True,
        engineers_needed=engineers,
        engineer_time_unit=unit,
        engineer_time_value=Decimal(value),
        skill_required=skill,
        best_engineer=best_engineer,
    )


def _step2(**overrides) -> Step2Snapshot:
    base = {
        "parking_required": True,
        "parking_type": "fixed",
        "parking_fixed_amount": PARKING_RATE,
        "parking_vehicles": 1,
        "congestion_required": True,
        "congestion_amount": CC_RATE,
    }
    base.update(overrides)
    return Step2Snapshot(**base)


def test_per_hour_one_day_plus_two_hours():
    charge = calculate_parking_charge(
        "hourly",
        rate_per_day=Decimal("0"),
        rate_per_hour=Decimal("10"),
        days=Decimal("1"),
        hours=Decimal("2"),
        vehicles=1,
    )
    assert charge == Decimal("100.00")


def test_per_day_four_hours():
    charge = calculate_parking_charge(
        "fixed",
        rate_per_day=Decimal("126"),
        rate_per_hour=Decimal("0"),
        days=Decimal("0"),
        hours=Decimal("4"),
        vehicles=1,
    )
    assert charge == Decimal("63.00")


def test_per_day_one_day_plus_four_hours():
    charge = calculate_parking_charge(
        "fixed",
        rate_per_day=Decimal("126"),
        rate_per_hour=Decimal("0"),
        days=Decimal("1"),
        hours=Decimal("4"),
        vehicles=1,
    )
    assert charge == Decimal("189.00")


def test_vehicles_multiply_parking():
    charge = calculate_parking_charge(
        "fixed",
        rate_per_day=Decimal("126"),
        rate_per_hour=Decimal("0"),
        days=Decimal("0"),
        hours=Decimal("8"),
        vehicles=2,
    )
    assert charge == Decimal("252.00")


def test_combined_duration_sums_work_blocks():
    works = [_work(unit="hours", value="4"), _work(unit="days", value="1")]
    assert works_combined_duration_hours(works) == Decimal("12")


def test_allocation_same_trade_same_engineer_clubs_parking_and_cc():
    step2 = _step2(congestion_amount=Decimal("15"))
    works = [
        _work(unit="hours", value="4", skill="Painter", best_engineer="Person A"),
        _work(unit="hours", value="4", skill="Painter", best_engineer="Person A"),
    ]
    allocations = allocate_parking_cc_to_work_blocks(step2, works)
    assert len(allocations) == 2
    assert sum(item.parking_total for item in allocations) == Decimal("126.00")
    assert sum(item.cc_total for item in allocations) == Decimal("15.00")
    assert all(item.cc_total > 0 for item in allocations)


def test_per_day_parking_fractional_hours():
    charge = calculate_parking_charge(
        "fixed",
        rate_per_day=Decimal("126"),
        rate_per_hour=Decimal("0"),
        days=Decimal("0"),
        hours=Decimal("4.5"),
        vehicles=1,
    )
    assert charge == Decimal("70.88")


def test_duration_conversion_helpers():
    assert duration_to_hours(Decimal("1"), Decimal("2")) == Decimal("10")
    assert hours_to_days(Decimal("10")) == Decimal("1.25")


def test_cc_chargeable_days_uses_whole_days_only():
    assert cc_chargeable_days(Decimal("4.5")) == 1
    assert cc_chargeable_days(Decimal("8")) == 1
    assert cc_chargeable_days(Decimal("9")) == 2
    assert cc_chargeable_days(duration_to_hours(Decimal("1"), Decimal("4"))) == 2


def test_cc_four_and_half_hours_charges_one_full_day():
    charge = calculate_cc_charge(Decimal("0"), Decimal("4.5"), CC_RATE)
    assert charge == Decimal("28.80")


def test_cc_allocation_single_work():
    step2 = _step2()
    works = [_work(unit="hours", value="4.5")]
    allocations = allocate_parking_cc_to_work_blocks(step2, works)
    assert allocations[0].cc_chargeable_days == 1
    assert allocations[0].cc_total == Decimal("28.80")
    assert calculate_cc_total(step2, works) == Decimal("28.80")


def test_different_trade_different_engineer_separate_cc():
    step2 = _step2()
    works = [
        _work(unit="hours", value="2", skill="Electrician", best_engineer="Person A"),
        _work(unit="hours", value="2.5", skill="Painter & Decorator", best_engineer="Person B"),
    ]
    allocations = allocate_parking_cc_to_work_blocks(step2, works)
    assert allocations[0].cc_total == Decimal("28.80")
    assert allocations[1].cc_total == Decimal("28.80")
    assert calculate_cc_total(step2, works) == Decimal("57.60")
    assert calculate_cc_total_days(step2, works) == 2


def test_same_trade_same_engineer_clubs_cc():
    step2 = _step2()
    works = [
        _work(unit="hours", value="2", skill="Painter", best_engineer="Person A"),
        _work(unit="hours", value="2.5", skill="Painter", best_engineer="Person A"),
    ]
    allocations = allocate_parking_cc_to_work_blocks(step2, works)
    assert sum(item.cc_total for item in allocations) == Decimal("28.80")
    assert allocations[0].cc_total > 0
    assert allocations[1].cc_total > 0
    assert calculate_cc_total(step2, works) == Decimal("28.80")
    assert calculate_cc_total_days(step2, works) == 1


def test_same_trade_different_engineer_separate_cc():
    step2 = _step2()
    works = [
        _work(unit="hours", value="2", skill="Painter", best_engineer="Person A"),
        _work(unit="hours", value="2.5", skill="Painter", best_engineer="Person B"),
    ]
    allocations = allocate_parking_cc_to_work_blocks(step2, works)
    assert allocations[0].cc_total == Decimal("28.80")
    assert allocations[1].cc_total == Decimal("28.80")
    assert calculate_cc_total(step2, works) == Decimal("57.60")


def test_different_trade_same_engineer_separate_cc():
    step2 = _step2()
    works = [
        _work(unit="hours", value="2", skill="Electrician", best_engineer="Person A"),
        _work(unit="hours", value="2.5", skill="Painter", best_engineer="Person A"),
    ]
    allocations = allocate_parking_cc_to_work_blocks(step2, works)
    assert allocations[0].cc_total == Decimal("28.80")
    assert allocations[1].cc_total == Decimal("28.80")
    assert calculate_cc_total(step2, works) == Decimal("57.60")


def test_missing_engineer_does_not_club():
    step2 = _step2()
    works = [
        _work(unit="hours", value="2", skill="Painter"),
        _work(unit="hours", value="2.5", skill="Painter"),
    ]
    groups = group_works_for_charge_allocation(works)
    assert len(groups) == 2
    assert charge_allocation_group_key(works[0], 0) != charge_allocation_group_key(works[1], 1)
    allocations = allocate_parking_cc_to_work_blocks(step2, works)
    assert allocations[0].cc_total == Decimal("28.80")
    assert allocations[1].cc_total == Decimal("28.80")
    assert calculate_cc_total(step2, works) == Decimal("57.60")


def test_grouped_parking_totals_match_allocation_sum():
    step2 = _step2()
    works = [
        _work(unit="hours", value="2", skill="Electrician", best_engineer="Person A"),
        _work(unit="hours", value="2.5", skill="Painter", best_engineer="Person B"),
    ]
    allocations = allocate_parking_cc_to_work_blocks(step2, works)
    assert calculate_parking_total(step2, works) == sum(item.parking_total for item in allocations)


def test_grouped_parking_clubs_same_trade_and_engineer():
    step2 = _step2()
    works = [
        _work(unit="hours", value="2", skill="Painter", best_engineer="Person A"),
        _work(unit="hours", value="2.5", skill="Painter", best_engineer="Person A"),
    ]
    allocations = allocate_parking_cc_to_work_blocks(step2, works)
    assert calculate_parking_total(step2, works) == Decimal("70.88")
    assert sum(item.parking_total for item in allocations) == Decimal("70.88")
