"""Unit tests for off-shelf materials calculation and snapshots."""

from __future__ import annotations

from decimal import Decimal

from app.engines.approval_engine import _build_simplified_calculation_breakdown
from app.schemas.calculation import ChargeInput, LabourInput, MaterialInput
from app.schemas.eworks_link import MaterialOrderRow, Step2Snapshot
from app.services.eworks_pdf_context_service import build_eworks_estimate_pdf_context
from app.services.eworks_questionnaire_service import (
    build_material_items,
    calculate_off_shelf_materials_total,
    enrich_off_shelf_material_rows,
    off_shelf_material_line_total,
)


def test_off_shelf_line_total_quantity_times_cost_per_item() -> None:
    row = MaterialOrderRow(link="1sdvas", quantity=Decimal("10"), cost=Decimal("10"))
    assert off_shelf_material_line_total(row) == Decimal("100")


def test_off_shelf_materials_total_sums_multiple_rows() -> None:
    rows = [
        MaterialOrderRow(link="Screw", quantity=Decimal("10"), cost=Decimal("2.5")),
        MaterialOrderRow(link="Plug", quantity=Decimal("1"), cost=Decimal("20")),
    ]
    assert calculate_off_shelf_materials_total(rows) == Decimal("45")


def test_build_material_items_treats_shelf_cost_as_per_item() -> None:
    step2 = Step2Snapshot(
        shelf_materials_rows=[MaterialOrderRow(link="1sdvas", quantity=Decimal("10"), cost=Decimal("10"))],
        markup_value=Decimal("20"),
    )
    items = build_material_items(step2)
    assert len(items) == 1
    assert items[0][1] == Decimal("10")
    assert items[0][2] == Decimal("10")


def test_off_shelf_total_contributes_to_materials_subtotal() -> None:
    materials = [
        MaterialInput(
            material_name="1sdvas",
            quantity=Decimal("10"),
            unit_cost=Decimal("10"),
            delivery_cost=Decimal("0"),
            markup_type="percentage",
            markup_value=Decimal("20"),
            client_visible=True,
        )
    ]
    breakdown = _build_simplified_calculation_breakdown(
        labour_items=[
            LabourInput(
                labour_type="hourly",
                number_of_engineers=1,
                number_of_labourers=0,
                hours_on_site=Decimal("1"),
                trade_id=None,
            )
        ],
        material_items=materials,
        charges=ChargeInput(),
        matched_rule=None,
        formula_version="test",
    )
    material_base = sum((line.total for line in breakdown.materials), Decimal("0"))
    assert material_base == Decimal("120")


def test_enriched_snapshot_includes_line_total_and_section_total() -> None:
    rows = [MaterialOrderRow(link="1sdvas", quantity=Decimal("10"), cost=Decimal("10"))]
    enriched = enrich_off_shelf_material_rows(rows)
    assert enriched[0].line_total == Decimal("100")
    assert calculate_off_shelf_materials_total(enriched) == Decimal("100")


def test_pdf_context_includes_off_shelf_line_totals() -> None:
    from app.schemas.eworks_link import Step1Snapshot, WorkBlockSnapshot

    step1 = Step1Snapshot(
        quote_number="Q1",
        job_number="J1",
        engineer_name="Alex",
        client_name="Client",
        trade_name="Electrician",
        property_address="1 High Street",
    )
    step2 = Step2Snapshot(
        works=[
            WorkBlockSnapshot(
                scope="Install item",
                shelf_materials_rows=[{"link": "1sdvas", "quantity": 10, "cost": 10}],
            )
        ]
    )
    context = build_eworks_estimate_pdf_context(
        step1=step1,
        step2=step2,
        breakdown=_build_simplified_calculation_breakdown(
            labour_items=[],
            material_items=[],
            charges=ChargeInput(),
            matched_rule=None,
            formula_version="test",
        ),
        client_view={"calculation": {}},
    )
    shelf = context["work_forms"][0]["shelf_materials"]
    assert shelf["rows"][0]["line_total"] == "£100.00"
    assert shelf["total"] == "£100.00"
