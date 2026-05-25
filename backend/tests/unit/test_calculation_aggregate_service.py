"""Unit tests for multi-work calculation aggregation."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.schemas.eworks_link import MaterialOrderRow, WorkBlockSnapshot
from app.services.calculation_aggregate_service import (
    aggregate_work_blocks,
    format_aggregated_quote_subtitle,
    round_to_half,
)


def _work_block(**overrides) -> WorkBlockSnapshot:
    defaults = {
        "scope": "Test scope",
        "engineers_required": True,
        "engineers_needed": 1,
        "engineer_time_unit": "hours",
        "engineer_time_value": Decimal("1.5"),
        "labour_required": False,
        "labour_needed": 0,
        "labour_time_value": Decimal("1"),
    }
    defaults.update(overrides)
    return WorkBlockSnapshot(**defaults)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("2.3"), Decimal("2.5")),
        (Decimal("2.1"), Decimal("2.0")),
        (Decimal("2.25"), Decimal("2.5")),
        (Decimal("2.24"), Decimal("2.0")),
        (Decimal("3.0"), Decimal("3.0")),
        (Decimal("0.24"), Decimal("0.0")),
        (Decimal("0.25"), Decimal("0.5")),
    ],
)
def test_round_to_half(value: Decimal, expected: Decimal) -> None:
    assert round_to_half(value) == expected


def test_aggregate_identical_hourly_works() -> None:
    works = [_work_block(), _work_block()]
    aggregated = aggregate_work_blocks(works)
    assert aggregated.labour_type == "hourly"
    assert aggregated.engineers == 1
    assert aggregated.hours == Decimal("3.0")
    assert aggregated.labourers == 0
    assert aggregated.uses_mixed_units is False
    assert aggregated.converted_from_hours is False
    assert aggregated.total_engineer_hours == Decimal("3.0")


def test_aggregate_engineer_hours_with_multiple_engineers() -> None:
    works = [_work_block(engineers_needed=2, engineer_time_value=Decimal("1.5"))]
    aggregated = aggregate_work_blocks(works)
    assert aggregated.total_engineer_hours == Decimal("3.0")
    assert aggregated.hours == Decimal("3.0")


def test_aggregate_hours_to_days_conversion() -> None:
    works = [
        _work_block(engineer_time_unit="hours", engineer_time_value=Decimal("8")),
        _work_block(engineer_time_unit="days", engineer_time_value=Decimal("1")),
    ]
    aggregated = aggregate_work_blocks(works)
    assert aggregated.labour_type == "day"
    assert aggregated.days == Decimal("2.0")
    assert aggregated.converted_from_hours is True
    assert aggregated.total_engineer_hours == Decimal("16")


def test_aggregate_mixed_units_converts_to_days() -> None:
    works = [
        _work_block(engineer_time_unit="hours", engineer_time_value=Decimal("8")),
        _work_block(engineer_time_unit="days", engineer_time_value=Decimal("1")),
    ]
    aggregated = aggregate_work_blocks(works)
    assert aggregated.labour_type == "day"
    assert aggregated.uses_mixed_units is True
    assert aggregated.converted_from_hours is True
    assert aggregated.days == Decimal("2.0")


def test_aggregate_labour_days_sum() -> None:
    works = [
        _work_block(
            engineer_time_unit="days",
            engineer_time_value=Decimal("1"),
            labour_required=True,
            labour_needed=2,
            labour_time_value=Decimal("1.5"),
        ),
        _work_block(
            engineer_time_unit="days",
            engineer_time_value=Decimal("2"),
            labour_required=True,
            labour_needed=1,
            labour_time_value=Decimal("1"),
        ),
    ]
    aggregated = aggregate_work_blocks(works)
    assert aggregated.labour_type == "day"
    assert aggregated.labourers == 1
    assert aggregated.total_labour_days == Decimal("4.0")
    assert aggregated.labourer_days == Decimal("4.0")
    assert aggregated.days == Decimal("3.0")


def test_aggregate_all_days_no_labour() -> None:
    works = [
        _work_block(engineer_time_unit="days", engineer_time_value=Decimal("1")),
        _work_block(engineer_time_unit="days", engineer_time_value=Decimal("2")),
    ]
    aggregated = aggregate_work_blocks(works)
    assert aggregated.labour_type == "day"
    assert aggregated.days == Decimal("3.0")
    assert aggregated.labourers == 0


def test_format_aggregated_quote_subtitle_hourly() -> None:
    aggregated = aggregate_work_blocks([_work_block(), _work_block()])
    subtitle = format_aggregated_quote_subtitle(aggregated, 2)
    assert subtitle == "3 hours total across 2 works"


def test_format_aggregated_quote_subtitle_mixed_skills() -> None:
    aggregated = aggregate_work_blocks([_work_block(), _work_block()])
    subtitle = format_aggregated_quote_subtitle(
        aggregated,
        3,
        skills=["Carpenter", "Electrician", "Gas Safe"],
    )
    assert subtitle == "3 hours total across 3 works (Carpenter, Electrician, Gas Safe)"


def test_format_aggregated_quote_subtitle_daily_with_labour() -> None:
    works = [
        _work_block(
            engineer_time_unit="days",
            engineer_time_value=Decimal("1"),
            labour_required=True,
            labour_needed=2,
            labour_time_value=Decimal("1.5"),
        ),
        _work_block(
            engineer_time_unit="days",
            engineer_time_value=Decimal("2"),
            labour_required=True,
            labour_needed=1,
            labour_time_value=Decimal("1"),
        ),
    ]
    aggregated = aggregate_work_blocks(works)
    subtitle = format_aggregated_quote_subtitle(aggregated, 2)
    assert subtitle == "3 engineer days + 4 labour days across 2 works"


def test_aggregate_rounds_before_quote() -> None:
    works = [
        _work_block(engineer_time_value=Decimal("1.3")),
        _work_block(engineer_time_value=Decimal("1.3")),
    ]
    aggregated = aggregate_work_blocks(works)
    assert aggregated.total_engineer_hours == Decimal("2.6")
    assert aggregated.hours == Decimal("2.5")
