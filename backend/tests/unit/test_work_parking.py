from decimal import Decimal

from app.schemas.eworks_link import Step2Snapshot, WorkBlockSnapshot, quote_parking_raw, work_parking_raw


def test_work_parking_raw_fixed_single_vehicle():
    block = WorkBlockSnapshot(
        parking_required=True,
        parking_type="fixed",
        parking_fixed_amount=Decimal("100"),
        parking_vehicles=1,
    )
    assert work_parking_raw(block) == Decimal("100")


def test_work_parking_raw_fixed_multiple_vehicles():
    block = WorkBlockSnapshot(
        parking_required=True,
        parking_type="fixed",
        parking_fixed_amount=Decimal("100"),
        parking_vehicles=2,
    )
    assert work_parking_raw(block) == Decimal("200")


def test_work_parking_raw_hourly_multiple_vehicles():
    block = WorkBlockSnapshot(
        parking_required=True,
        parking_type="hourly",
        parking_rate_per_hour=Decimal("10"),
        parking_hours=Decimal("2"),
        parking_vehicles=2,
    )
    assert work_parking_raw(block) == Decimal("40")


def test_work_parking_raw_not_required():
    block = WorkBlockSnapshot(parking_required=False, parking_fixed_amount=Decimal("100"))
    assert work_parking_raw(block) == Decimal("0")


def test_quote_parking_raw_fixed_multiple_vehicles():
    step2 = Step2Snapshot(
        parking_required=True,
        parking_type="fixed",
        parking_fixed_amount=Decimal("100"),
        parking_vehicles=2,
    )
    assert quote_parking_raw(step2) == Decimal("200")
