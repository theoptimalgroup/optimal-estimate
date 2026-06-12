from decimal import Decimal

from app.schemas.eworks_link import Step2Snapshot, WorkBlockSnapshot, quote_parking_raw, work_parking_raw


def _work(*, unit: str, value: str, engineers: int = 1) -> WorkBlockSnapshot:
    return WorkBlockSnapshot(
        engineers_required=True,
        engineers_needed=engineers,
        engineer_time_unit=unit,
        engineer_time_value=Decimal(value),
    )


def test_work_parking_raw_per_day_four_hours():
    block = _work(unit="hours", value="4")
    step2 = Step2Snapshot(
        parking_required=True,
        parking_type="fixed",
        parking_fixed_amount=Decimal("126"),
        parking_vehicles=1,
    )
    assert work_parking_raw(block, step2=step2) == Decimal("63")


def test_work_parking_raw_per_day_multiple_vehicles():
    block = _work(unit="hours", value="8")
    step2 = Step2Snapshot(
        parking_required=True,
        parking_type="fixed",
        parking_fixed_amount=Decimal("126"),
        parking_vehicles=2,
    )
    assert work_parking_raw(block, step2=step2) == Decimal("252")


def test_work_parking_raw_per_hour_multiple_vehicles():
    block = _work(unit="hours", value="2")
    step2 = Step2Snapshot(
        parking_required=True,
        parking_type="hourly",
        parking_rate_per_hour=Decimal("10"),
        parking_vehicles=2,
    )
    assert work_parking_raw(block, step2=step2) == Decimal("40")


def test_work_parking_raw_not_required():
    block = _work(unit="hours", value="4")
    step2 = Step2Snapshot(parking_required=False, parking_fixed_amount=Decimal("100"))
    assert work_parking_raw(block, step2=step2) == Decimal("0")


def test_quote_parking_raw_combined_duration():
    step2 = Step2Snapshot(
        parking_required=True,
        parking_type="fixed",
        parking_fixed_amount=Decimal("126"),
        parking_vehicles=2,
        works=[_work(unit="hours", value="4")],
    )
    assert quote_parking_raw(step2, step2.works) == Decimal("126")
