"""Comparison summary helpers for manager quote review (shared with PDF generation)."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.calculation_session import CalculationSession
from app.schemas.dashboard_quote_groups import (
    DashboardQuoteGroupComparisonChargeLine,
    DashboardQuoteGroupComparisonSummary,
    DashboardQuoteGroupComparisonWorkBreakdown,
)
from app.schemas.eworks_link import Step2Snapshot
from app.services.calculation_session_service import (
    _dashboard_last_result,
    _dashboard_quote_summary_breakdown,
    _resolve_work_product_fields,
    _work_subtotals_from_breakdown,
)

_COMPARISON_CHARGE_LABELS = ("Parking", "Congestion", "Travel", "Other")
_EXCLUDED_COMPARISON_CHARGE_LABELS = frozenset({"ULEZ", "Waste Disposal"})


def _comparison_charge_label(raw_label: str) -> str | None:
    normalized = (raw_label or "").strip()
    if not normalized or normalized in _EXCLUDED_COMPARISON_CHARGE_LABELS:
        return None
    for label in _COMPARISON_CHARGE_LABELS:
        if normalized == label or normalized.startswith(f"{label} "):
            return label
    if normalized == "Other charge":
        return "Other"
    return None


def _comparison_charge_lines(breakdown: dict) -> list[DashboardQuoteGroupComparisonChargeLine]:
    amounts = {label: Decimal("0") for label in _COMPARISON_CHARGE_LABELS}
    for line in breakdown.get("charges") or []:
        mapped_label = _comparison_charge_label(str(line.get("label") or ""))
        if mapped_label is None or line.get("total") is None:
            continue
        amounts[mapped_label] += Decimal(str(line["total"]))
    return [
        DashboardQuoteGroupComparisonChargeLine(label=label, amount=amounts[label])
        for label in _COMPARISON_CHARGE_LABELS
    ]


def _comparison_additional_charges_total(charge_lines: list[DashboardQuoteGroupComparisonChargeLine]) -> Decimal:
    return sum((line.amount for line in charge_lines), Decimal("0"))


_XLSX_MATERIALS_LABEL = "Materials / Parking / CC"


def _comparison_work_rows(
    db: Session,
    *,
    step2: Step2Snapshot,
    breakdown_map: dict[int, dict],
    combined_breakdown: dict | None = None,
) -> list[DashboardQuoteGroupComparisonWorkBreakdown]:
    rows: list[DashboardQuoteGroupComparisonWorkBreakdown] = []
    for index, block in enumerate(step2.works):
        work_result = breakdown_map.get(index, {})
        work_breakdown = work_result.get("breakdown") or {}

        # For single-work XLSX quotes, parking/CC are folded into the combined
        # (quote-level) materials bucket and are absent from the per-work breakdown
        # (which is computed with an empty ChargeInput).  Use the combined breakdown
        # so the work card subtotal matches the Quote Summary.
        if len(step2.works) == 1 and combined_breakdown:
            labour_subtotal, materials_subtotal = _work_subtotals_from_breakdown(combined_breakdown)
            if labour_subtotal is None and materials_subtotal is None:
                labour_subtotal, materials_subtotal = _work_subtotals_from_breakdown(work_breakdown)
        else:
            labour_subtotal, materials_subtotal = _work_subtotals_from_breakdown(work_breakdown)

        work_subtotal = None
        if labour_subtotal is not None or materials_subtotal is not None:
            work_subtotal = (labour_subtotal or Decimal("0")) + (materials_subtotal or Decimal("0"))
        product_name, product_code = _resolve_work_product_fields(db, block)
        scope_preview = (block.scope or "").strip() or None

        materials_label: str | None = None
        if combined_breakdown and combined_breakdown.get("formula_source") == "xlsx":
            materials_label = _XLSX_MATERIALS_LABEL

        rows.append(
            DashboardQuoteGroupComparisonWorkBreakdown(
                product_name=product_name,
                product_code=product_code,
                scope_preview=scope_preview,
                labour_subtotal=labour_subtotal,
                materials_subtotal=materials_subtotal,
                work_subtotal=work_subtotal,
                materials_label=materials_label,
            )
        )
    return rows


def _session_comparison_summary(db: Session, session: CalculationSession) -> DashboardQuoteGroupComparisonSummary | None:
    last_result = _dashboard_last_result(db, session)
    if not last_result:
        return None

    breakdown = last_result.get("breakdown") or {}
    summary = _dashboard_quote_summary_breakdown(breakdown)
    if summary is None:
        return None

    step2 = Step2Snapshot.model_validate(session.step2_snapshot) if session.step2_snapshot else Step2Snapshot()
    work_breakdowns = last_result.get("work_breakdowns") or []
    breakdown_map = {item["work_index"]: item for item in work_breakdowns}

    labour_total = Decimal("0")
    materials_total = Decimal("0")
    has_labour = False
    has_materials = False

    # For single-work XLSX quotes, parking/CC are folded into the combined
    # (quote-level) materials_parking_cc_charge bucket and are absent from the
    # per-work breakdown.  Use the combined breakdown directly so the summary
    # labour/materials match works_subtotal (which is already correct).
    if len(step2.works) == 1:
        labour_sub, materials_sub = _work_subtotals_from_breakdown(breakdown)
        if labour_sub is None and materials_sub is None:
            work_bd = (breakdown_map.get(0) or {}).get("breakdown") or {}
            labour_sub, materials_sub = _work_subtotals_from_breakdown(work_bd)
        if labour_sub is not None:
            labour_total = labour_sub
            has_labour = True
        if materials_sub is not None:
            materials_total = materials_sub
            has_materials = True
    else:
        for index, block in enumerate(step2.works):
            work_result = breakdown_map.get(index, {})
            work_breakdown = work_result.get("breakdown") or {}
            labour_subtotal, materials_subtotal = _work_subtotals_from_breakdown(work_breakdown)
            if labour_subtotal is not None:
                labour_total += labour_subtotal
                has_labour = True
            if materials_subtotal is not None:
                materials_total += materials_subtotal
                has_materials = True

    scope_preview = None
    product_preview = None
    if step2.works:
        first_block = step2.works[0]
        scope_preview = (first_block.scope or "").strip() or None
        product_name, product_code = _resolve_work_product_fields(db, first_block)
        if product_name:
            product_preview = product_name
        elif product_code:
            product_preview = product_code

    charge_lines = _comparison_charge_lines(breakdown)
    vat_rate = breakdown.get("vat_rate")
    is_xlsx = breakdown.get("formula_source") == "xlsx"
    return DashboardQuoteGroupComparisonSummary(
        final_total=Decimal(str(breakdown["final_total"])),
        works_subtotal=summary.works_subtotal,
        labour_subtotal=labour_total if has_labour else None,
        materials_subtotal=materials_total if has_materials else None,
        additional_charges_total=_comparison_additional_charges_total(charge_lines),
        vat_total=summary.vat_total,
        vat_rate=Decimal(str(vat_rate)) if vat_rate is not None else None,
        scope_preview=scope_preview,
        product_preview=product_preview,
        materials_label=_XLSX_MATERIALS_LABEL if is_xlsx else None,
        works=_comparison_work_rows(db, step2=step2, breakdown_map=breakdown_map, combined_breakdown=breakdown),
        additional_charges=charge_lines,
    )
