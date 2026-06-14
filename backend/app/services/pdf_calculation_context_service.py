"""Shared calculation resolution for PDF generation — uses cached submitted results."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.calculation_session import CalculationSession
from app.schemas.calculation import CalculationBreakdown
from app.schemas.eworks_link import (
    AggregatedQuoteSummary,
    Step1Snapshot,
    Step2Snapshot,
    WorkBlockSnapshot,
    WorkBreakdownResult,
)
from app.services.calculation_session_service import _session_ui_state

logger = logging.getLogger(__name__)

PdfCalculationSource = Literal["cached", "preview"]


@dataclass(frozen=True)
class PdfCalculationContext:
    breakdown: CalculationBreakdown
    work_breakdowns: list[WorkBreakdownResult]
    aggregated_summary: AggregatedQuoteSummary | None
    internal_notes: str | None
    step1: Step1Snapshot
    step2: Step2Snapshot
    source: PdfCalculationSource


def session_blocks_recalculation(session: CalculationSession) -> bool:
    """Submitted or locked sessions must use stored calculation results only."""
    return session.status == "submitted" or bool(session.locked)


def _cached_last_result(session: CalculationSession) -> dict | None:
    ui_state = _session_ui_state(session)
    last_result = ui_state.last_result if ui_state else None
    if not isinstance(last_result, dict):
        return None
    breakdown = last_result.get("breakdown") or {}
    if not last_result.get("work_breakdowns") or breakdown.get("final_total") is None:
        return None
    return last_result


def resolve_session_calculation_result(
    db: Session,
    session: CalculationSession,
    *,
    allow_recalculate: bool = False,
    session_id: UUID | None = None,
    session_token: str | None = None,
) -> tuple[dict, PdfCalculationSource]:
    """Return raw last_result payload; uses preview fallback when cache is missing."""
    _ = allow_recalculate, session_id, session_token
    cached = _cached_last_result(session)
    if cached is not None:
        return cached, "cached"

    if not session.step2_snapshot:
        raise AppError("STEP2_REQUIRED", "Estimator inputs are required before generating PDF", 400)

    from app.services.work_quote_review_fallback_service import build_preview_calculation_last_result

    preview = build_preview_calculation_last_result(db, session)
    if preview is None:
        raise AppError("CALCULATION_REQUIRED", "No calculation result available for this quote", 400)
    return preview, "preview"


def build_pdf_calculation_context(
    db: Session,
    session: CalculationSession,
    *,
    allow_recalculate: bool = False,
    session_id: UUID | None = None,
    session_token: str | None = None,
    version_number: int | None = None,
    view_type: str | None = None,
) -> PdfCalculationContext:
    """Resolve breakdown and work rows for PDF rendering from cached or preview calculation."""
    last_result, source = resolve_session_calculation_result(
        db,
        session,
        allow_recalculate=allow_recalculate,
        session_id=session_id,
        session_token=session_token,
    )

    if not session.step2_snapshot:
        raise AppError("STEP2_REQUIRED", "Estimator inputs are required before generating PDF", 400)

    step1 = Step1Snapshot.model_validate(session.step1_snapshot)
    step2 = Step2Snapshot.model_validate(session.step2_snapshot)
    from app.services.eworks_site_address_service import resolve_step1_for_display

    step1 = resolve_step1_for_display(db, session, step1)
    breakdown = CalculationBreakdown.model_validate(last_result["breakdown"])
    work_breakdowns = [
        WorkBreakdownResult.model_validate(item) for item in last_result.get("work_breakdowns") or []
    ]
    aggregated_summary = None
    if last_result.get("aggregated_summary"):
        aggregated_summary = AggregatedQuoteSummary.model_validate(last_result["aggregated_summary"])
    internal_notes = last_result.get("internal_notes") or breakdown.internal_notes

    log_pdf_calculation_totals(
        session_id=session.id,
        version_number=version_number,
        view_type=view_type,
        source=source,
        breakdown=breakdown,
    )

    return PdfCalculationContext(
        breakdown=breakdown,
        work_breakdowns=work_breakdowns,
        aggregated_summary=aggregated_summary,
        internal_notes=internal_notes,
        step1=step1,
        step2=step2,
        source=source,
    )


def log_pdf_calculation_totals(
    *,
    session_id: UUID,
    version_number: int | None,
    view_type: str | None,
    source: PdfCalculationSource,
    breakdown: CalculationBreakdown,
) -> None:
    """Debug-safe logging: ids and totals only, no secrets or PII."""
    logger.debug(
        "pdf_calculation_context session_id=%s version=%s view_type=%s source=%s "
        "subtotal=%s vat_total=%s final_total=%s",
        session_id,
        version_number,
        view_type,
        source,
        breakdown.subtotal,
        breakdown.vat_total,
        breakdown.final_total,
    )


def work_breakdown_map(work_breakdowns: list[WorkBreakdownResult]) -> dict[int, WorkBreakdownResult]:
    return {item.work_index: item for item in work_breakdowns}


def build_work_internal_calculation_note(
    *,
    work_index: int,
    work_block: WorkBlockSnapshot | None,
    work_result: WorkBreakdownResult | None,
    quote_internal_notes: str | None,
    quote_breakdown: CalculationBreakdown | None,
    work_count: int,
    who_quoted: str | None = None,
) -> str | None:
    """Resolve internal notes for PDF from manual notes and cached calculation breakdown."""
    from app.services.pdf_estimator_identity_service import patch_who_quoted_in_internal_notes

    _ = work_index  # reserved for future per-work labelling
    manual = (work_block.other_notes or "").strip() if work_block else ""

    generated: str | None = None
    # For single-work quotes, always prefer combined (quote-level) notes over per-work
    # notes. Per-work breakdowns are computed with an empty ChargeInput, so their
    # generated notes show Parking: £0 / Materials: £140 (raw) instead of the correct
    # combined values that include parking/CC charges.
    if work_count == 1:
        for candidate in (
            quote_internal_notes,
            quote_breakdown.internal_notes if quote_breakdown else None,
        ):
            if candidate and str(candidate).strip():
                generated = str(candidate).strip()
                break

    if not generated and work_result is not None:
        for candidate in (work_result.internal_notes, work_result.breakdown.internal_notes):
            if candidate and str(candidate).strip():
                generated = str(candidate).strip()
                break

    if who_quoted:
        generated = patch_who_quoted_in_internal_notes(generated, who_quoted)

    parts: list[str] = []
    if manual:
        parts.append(manual)
    if generated and generated != manual:
        parts.append(generated)
    return "\n\n".join(parts) if parts else None


def build_combined_internal_notes_for_pdf(
    *,
    work_blocks: list[WorkBlockSnapshot],
    work_breakdowns: list[WorkBreakdownResult],
    quote_internal_notes: str | None,
    quote_breakdown: CalculationBreakdown,
    who_quoted: str | None = None,
) -> str | None:
    """Build combined internal notes page content from cached calculation results."""
    from app.services.pdf_estimator_identity_service import patch_who_quoted_in_internal_notes

    work_count = len(work_blocks)
    breakdown_map = work_breakdown_map(work_breakdowns)

    if work_count == 1:
        return build_work_internal_calculation_note(
            work_index=0,
            work_block=work_blocks[0] if work_blocks else None,
            work_result=breakdown_map.get(0),
            quote_internal_notes=quote_internal_notes,
            quote_breakdown=quote_breakdown,
            work_count=1,
            who_quoted=who_quoted,
        )

    quote_combined = (quote_internal_notes or quote_breakdown.internal_notes or "").strip()
    if quote_combined:
        return patch_who_quoted_in_internal_notes(quote_combined, who_quoted or "")

    sections: list[str] = []
    for index, block in enumerate(work_blocks):
        note = build_work_internal_calculation_note(
            work_index=index,
            work_block=block,
            work_result=breakdown_map.get(index),
            quote_internal_notes=quote_internal_notes,
            quote_breakdown=quote_breakdown,
            work_count=work_count,
            who_quoted=who_quoted,
        )
        if note:
            sections.append(f"--- Work {index + 1} ---\n{note}")
    return "\n\n".join(sections) if sections else None


def quote_level_totals_for_works(
    *,
    breakdown: CalculationBreakdown,
    work_breakdowns: list[WorkBreakdownResult],
    work_indexes: list[int],
    all_work_indexes: set[int],
) -> tuple[Decimal, Decimal, Decimal]:
    """Return (subtotal ex-VAT, vat_total, final_total) for selected works."""
    selected = set(work_indexes)
    if selected == all_work_indexes and len(work_indexes) == len(all_work_indexes):
        return breakdown.subtotal, breakdown.vat_total, breakdown.final_total

    from app.services.quote_job_assignment_service import (
        _comparison_additional_charges_total,
        _comparison_charge_lines,
    )

    breakdown_map = work_breakdown_map(work_breakdowns)
    works_subtotal = Decimal("0")
    for index in work_indexes:
        work_result = breakdown_map.get(index)
        if work_result is None:
            continue
        labour = work_result.breakdown.labour_charge_to_client
        materials = work_result.breakdown.materials_parking_cc_charge
        if labour is not None or materials is not None:
            works_subtotal += (labour or Decimal("0")) + (materials or Decimal("0"))
            continue
        works_subtotal += work_result.breakdown.subtotal

    charge_lines = _comparison_charge_lines(breakdown.model_dump(mode="json"))
    additional_charges = _comparison_additional_charges_total(charge_lines)
    subtotal = works_subtotal + additional_charges
    rate = breakdown.vat_rate or Decimal("0")
    vat_total = (subtotal * rate / Decimal("100")).quantize(Decimal("0.01"))
    final_total = subtotal + vat_total
    return subtotal, vat_total, final_total
