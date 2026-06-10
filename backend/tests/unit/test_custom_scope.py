"""Tests for custom scope / product entry on work blocks."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.exceptions import AppError
from app.models.client import Client
from app.models.client_alias import ClientAlias
from app.models.product import Product
from app.models.support import AuditLog
from app.models.trade import Trade
from app.models.user import User
from app.schemas.eworks_link import Step2Snapshot, WorkBlockSnapshot
from app.services.calculation_session_service import _build_dashboard_work_item, _resolve_work_product_fields, _validate_work_block
from app.services.quote_work_snapshot_service import normalize_shared_work_blocks
from app.services.eworks_pdf_context_service import _work_form_page
from app.utils.work_label import format_work_label


def test_work_block_snapshot_accepts_custom_scope_fields():
    block = WorkBlockSnapshot.model_validate(
        {
            "is_custom_scope": True,
            "custom_title": "One-off roof repair",
            "scope": "Replace damaged tiles on south elevation.",
            "selected_product_id": None,
            "skill_required": "Roofer",
        }
    )
    assert block.is_custom_scope is True
    assert block.custom_title == "One-off roof repair"
    assert block.selected_product_id is None


def test_resolve_work_product_fields_uses_custom_title():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for model in (User, Client, ClientAlias, Trade, AuditLog, Product):
        model.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    block = WorkBlockSnapshot(
        is_custom_scope=True,
        custom_title="Emergency leak repair",
        scope="Locate and seal active leak.",
        product_name="Emergency leak repair",
    )
    product_name, product_code = _resolve_work_product_fields(db, block)
    assert product_name == "Emergency leak repair"
    assert product_code is None


def test_validate_work_block_custom_scope_requires_title_and_scope():
    step2 = Step2Snapshot(
        works=[
            WorkBlockSnapshot(
                is_custom_scope=True,
                custom_title="",
                scope="",
                engineers_required=True,
                engineers_needed=1,
                engineer_time_value=Decimal("1.5"),
            )
        ]
    )
    with pytest.raises(AppError) as title_error:
        _validate_work_block(step2, 0)
    assert title_error.value.code == "CUSTOM_TITLE_REQUIRED"

    step2.works[0].custom_title = "Custom item"
    with pytest.raises(AppError) as scope_error:
        _validate_work_block(step2, 0)
    assert scope_error.value.code == "SCOPE_REQUIRED"


def test_validate_work_block_product_flow_unchanged():
    step2 = Step2Snapshot(
        works=[
            WorkBlockSnapshot(
                selected_product_id=12,
                product_name="Painting",
                scope="Repaint hallway",
                engineers_required=True,
                engineers_needed=1,
                engineer_time_value=Decimal("2"),
            )
        ]
    )
    _validate_work_block(step2, 0)


def test_validate_work_block_accepts_product_name_without_selected_id():
    step2 = Step2Snapshot(
        works=[
            WorkBlockSnapshot(
                product_name="Shared dishwasher",
                scope="Supply and fit dishwasher",
                engineers_required=True,
                engineers_needed=1,
                engineer_time_value=Decimal("1.5"),
            )
        ]
    )
    _validate_work_block(step2, 0)


def test_validate_work_block_requires_product_or_custom_scope():
    step2 = Step2Snapshot(
        works=[
            WorkBlockSnapshot(
                scope="Some scope only",
                engineers_required=True,
                engineers_needed=1,
                engineer_time_value=Decimal("1.5"),
            )
        ]
    )
    with pytest.raises(AppError) as error:
        _validate_work_block(step2, 0)
    assert error.value.code == "PRODUCT_OR_CUSTOM_REQUIRED"


def test_normalize_shared_scope_only_to_custom_scope():
    step2 = Step2Snapshot(
        works=[
            WorkBlockSnapshot(
                scope="Repair leaking roof hatch and replace flashing",
                engineers_required=True,
                engineers_needed=1,
                engineer_time_value=Decimal("1.5"),
            )
        ]
    )
    normalized = normalize_shared_work_blocks(step2)
    block = normalized.works[0]
    assert block.is_custom_scope is True
    assert block.custom_title == "Repair leaking roof hatch and replace flashing"
    assert block.product_name == "Repair leaking roof hatch and replace flashing"
    assert block.selected_product_id is None
    _validate_work_block(normalized, 0)


def test_normalize_shared_does_not_overwrite_real_product():
    step2 = Step2Snapshot(works=[_dishwasher_like_block()])
    normalized = normalize_shared_work_blocks(step2)
    block = normalized.works[0]
    assert block.is_custom_scope is False
    assert block.selected_product_id == 42
    assert block.product_name == "Dishwasher"


def test_normalize_shared_preserves_manual_custom_scope():
    step2 = Step2Snapshot(
        works=[
            WorkBlockSnapshot(
                is_custom_scope=True,
                custom_title="One-off roof hatch",
                scope="Detailed bespoke scope text.",
                engineers_required=True,
                engineers_needed=1,
                engineer_time_value=Decimal("1.5"),
            )
        ]
    )
    normalized = normalize_shared_work_blocks(step2)
    block = normalized.works[0]
    assert block.is_custom_scope is True
    assert block.custom_title == "One-off roof hatch"
    assert block.scope == "Detailed bespoke scope text."


def test_normalize_shared_empty_block_still_fails_validation():
    step2 = Step2Snapshot(
        works=[
            WorkBlockSnapshot(
                engineers_required=True,
                engineers_needed=1,
                engineer_time_value=Decimal("1.5"),
            )
        ]
    )
    normalized = normalize_shared_work_blocks(step2)
    with pytest.raises(AppError) as error:
        _validate_work_block(normalized, 0)
    assert error.value.code == "PRODUCT_OR_CUSTOM_REQUIRED"


def _dishwasher_like_block(**overrides) -> WorkBlockSnapshot:
    block = WorkBlockSnapshot(
        scope="Repair dishwasher",
        selected_product_id=42,
        product_name="Dishwasher",
        product_code="DW-001",
        is_custom_scope=False,
        engineers_required=True,
        engineers_needed=1,
        engineer_time_value=Decimal("1.5"),
    )
    return block.model_copy(update=overrides)


def test_format_work_label_prefers_custom_title():
    assert (
        format_work_label(
            is_custom_scope=True,
            custom_title="Bespoke glazing",
            scope="Install custom glass panel",
            index=0,
        )
        == "Bespoke glazing"
    )


def test_build_dashboard_work_item_displays_custom_scope_title():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for model in (User, Client, ClientAlias, Trade, AuditLog, Product):
        model.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    block = WorkBlockSnapshot(
        is_custom_scope=True,
        custom_title="Ad-hoc carpentry",
        product_name="Ad-hoc carpentry",
        scope="Repair door frame and architrave.",
    )
    item = _build_dashboard_work_item(
        db,
        index=0,
        block=block,
        labour_subtotal=Decimal("100"),
        materials_subtotal=Decimal("20"),
        work_internal_notes=None,
    )
    assert item.display_label == "Ad-hoc carpentry"
    assert item.product_name == "Ad-hoc carpentry"


def test_pdf_work_form_page_includes_custom_scope_fields():
    block = WorkBlockSnapshot(
        is_custom_scope=True,
        custom_title="Specialist clean",
        scope="Deep clean plant room.",
        findings="Heavy grease buildup noted.",
        other_notes="Client to provide access keys.",
        skill_required="Cleaner",
    )
    page = _work_form_page(block, index=1, trade_name="Cleaner")
    assert page["title"] == "Specialist clean"
    assert page["is_custom_scope"] is True
    assert page["findings"] == "Heavy grease buildup noted."
    assert page["other_notes"] == "Client to provide access keys."
