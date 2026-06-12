"""Display-only fallbacks for Quote Review when stored per-work calculation snapshots are missing."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from app.models.calculation_session import CalculationSession
from app.schemas.calculation import CalculationBreakdown, ChargeInput
from app.schemas.eworks_link import Step1Snapshot, Step2Snapshot, WorkBlockSnapshot, step2_to_calculation_inputs
from app.services.eworks_link_service import resolve_skill_trade, work_skill_name
from app.services.eworks_questionnaire_service import work_block_to_step2_snapshot
from app.services.parking_charge_service import (
    WorkSessionChargeAllocation,
    build_work_internal_notes_context,
    charge_input_for_allocation,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

UNAVAILABLE_INTERNAL_NOTES = "Internal notes unavailable. Please recalculate this estimate."


@dataclass(frozen=True)
class PreviewWorkDisplay:
    internal_notes: str | None
    labour_subtotal: Decimal | None
    materials_subtotal: Decimal | None


def stored_work_internal_notes(work_result: dict) -> str | None:
    """Return persisted per-work internal notes when present."""
    for source in (work_result.get("internal_notes"), (work_result.get("breakdown") or {}).get("internal_notes")):
        if isinstance(source, str) and source.strip():
            return source.strip()
    return None


def subtotals_from_calculation_breakdown(
    breakdown: CalculationBreakdown,
) -> tuple[Decimal | None, Decimal | None]:
    """Mirror dashboard subtotal extraction for a preview breakdown."""
    labour_lines = breakdown.labour or []
    materials_lines = breakdown.materials or []
    labour_subtotal = sum((line.total for line in labour_lines), Decimal("0")) if labour_lines else None
    materials_subtotal = sum((line.total for line in materials_lines), Decimal("0")) if materials_lines else None
    if labour_subtotal is None and breakdown.labour_charge_to_client is not None:
        labour_subtotal = breakdown.labour_charge_to_client
    if materials_subtotal is None and breakdown.materials_parking_cc_charge is not None:
        materials_subtotal = breakdown.materials_parking_cc_charge
    return labour_subtotal, materials_subtotal


def build_standard_preview_work_breakdown(
    db: Session,
    *,
    session: CalculationSession,
    step1: Step1Snapshot,
    step2: Step2Snapshot,
    block: WorkBlockSnapshot,
    work_index: int,
    allocation: WorkSessionChargeAllocation | None,
) -> CalculationBreakdown | None:
    """Run the same per-work preview pipeline as calculate_session (display-only)."""
    from app.services.calculation_service import preview_calculation
    from app.services.calculation_session_service import _eworks_preview_request

    skill = work_skill_name(block, step1.trade_name)
    trade = resolve_skill_trade(db, skill, fallback_trade_name=step1.trade_name)
    work_step2 = work_block_to_step2_snapshot(block, trade_name=step1.trade_name)
    labour, materials, _ = step2_to_calculation_inputs(
        step1,
        work_step2,
        trade_id=trade.id,
        include_charges=False,
    )
    work_charges = charge_input_for_allocation(step2, allocation) if allocation else ChargeInput()
    try:
        return preview_calculation(
            db,
            _eworks_preview_request(
                db,
                session=session,
                step1=step1,
                trade_id=trade.id,
                labour_items=labour,
                material_items=materials,
                charges=work_charges,
                internal_notes_context=build_work_internal_notes_context(
                    step1, block, step2, allocation
                ),
            ),
        )
    except Exception:
        logger.exception(
            "Quote review preview failed for session=%s work_index=%s",
            session.id,
            work_index,
        )
        return None


def preview_work_display_for_quote_review(
    db: Session | None,
    *,
    session: CalculationSession | None,
    step1: Step1Snapshot,
    step2: Step2Snapshot,
    block: WorkBlockSnapshot,
    work_index: int,
    allocation: WorkSessionChargeAllocation | None,
) -> PreviewWorkDisplay | None:
    if db is None or session is None:
        return None
    breakdown = build_standard_preview_work_breakdown(
        db,
        session=session,
        step1=step1,
        step2=step2,
        block=block,
        work_index=work_index,
        allocation=allocation,
    )
    if breakdown is None:
        return None
    labour_subtotal, materials_subtotal = subtotals_from_calculation_breakdown(breakdown)
    notes = (breakdown.internal_notes or "").strip() or None
    return PreviewWorkDisplay(
        internal_notes=notes,
        labour_subtotal=labour_subtotal,
        materials_subtotal=materials_subtotal,
    )


def resolve_work_quote_review_display(
    db: Session | None,
    session: CalculationSession | None,
    step1: Step1Snapshot,
    step2: Step2Snapshot,
    block: WorkBlockSnapshot,
    *,
    work_index: int,
    work_result: dict,
    allocation: WorkSessionChargeAllocation | None,
    labour_subtotal: Decimal | None,
    materials_subtotal: Decimal | None,
) -> tuple[str | None, Decimal | None, Decimal | None]:
    """Apply display fallbacks without mutating stored session data."""
    internal_notes = stored_work_internal_notes(work_result)
    preview: PreviewWorkDisplay | None = None
    needs_preview = (
        internal_notes is None or labour_subtotal is None or materials_subtotal is None
    )
    if needs_preview:
        preview = preview_work_display_for_quote_review(
            db,
            session=session,
            step1=step1,
            step2=step2,
            block=block,
            work_index=work_index,
            allocation=allocation,
        )

    if internal_notes is None:
        if preview and preview.internal_notes:
            internal_notes = preview.internal_notes
        else:
            internal_notes = UNAVAILABLE_INTERNAL_NOTES

    if labour_subtotal is None and preview is not None:
        labour_subtotal = preview.labour_subtotal
    if materials_subtotal is None and preview is not None:
        materials_subtotal = preview.materials_subtotal

    return internal_notes, labour_subtotal, materials_subtotal
