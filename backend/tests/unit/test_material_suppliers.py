"""Unit tests for supplier-based materials to order."""

from __future__ import annotations

from decimal import Decimal

from app.schemas.eworks_link import (
    MaterialLinkRow,
    MaterialSupplier,
    Step2Snapshot,
    WorkBlockSnapshot,
    migrate_legacy_material_rows,
)
from app.services.eworks_questionnaire_service import build_material_items


def test_migrate_legacy_flat_rows_to_single_supplier() -> None:
    migrated = migrate_legacy_material_rows(
        [
            {"link": "Item A", "quantity": 2, "cost": 100},
            {"link": "Item B", "quantity": 1, "cost": 50},
        ]
    )
    assert len(migrated) == 1
    supplier = MaterialSupplier.model_validate(migrated[0])
    assert len(supplier.links) == 2
    assert supplier.links[0].cost == Decimal("50")
    assert supplier.links[1].cost == Decimal("50")
    assert supplier.delivery_charge == Decimal("0")


def test_work_block_snapshot_migrates_legacy_material_rows() -> None:
    block = WorkBlockSnapshot.model_validate(
        {
            "scope": "Test",
            "materials_to_order": [{"link": "Bolt", "quantity": 4, "cost": 40}],
        }
    )
    assert len(block.materials_to_order) == 1
    assert block.materials_to_order[0].links[0].cost == Decimal("10")


def test_build_material_items_uses_per_item_cost_and_delivery() -> None:
    step2 = Step2Snapshot(
        materials_to_order=[
            MaterialSupplier(
                links=[
                    MaterialLinkRow(link="Widget", quantity=Decimal("2"), cost=Decimal("25")),
                    MaterialLinkRow(link="Bracket", quantity=Decimal("1"), cost=Decimal("10")),
                ],
                delivery_charge=Decimal("5"),
            )
        ],
        markup_value=Decimal("20"),
    )
    items = build_material_items(step2)
    assert len(items) == 2
    assert items[0][0] == "Widget"
    assert items[0][1] == Decimal("2")
    assert items[0][2] == Decimal("25")
    assert items[0][3] == Decimal("5")
    assert items[1][0] == "Bracket"
    assert items[1][2] == Decimal("10")
    assert items[1][3] == Decimal("0")
