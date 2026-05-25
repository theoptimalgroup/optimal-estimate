"""Build PDF context for eWorks estimation documents."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.schemas.calculation import CalculationBreakdown, LineBreakdown
from app.schemas.eworks_link import (
    AggregatedQuoteSummary,
    MaterialOrderRow,
    Step1Snapshot,
    Step2Snapshot,
    WorkBlockSnapshot,
    WorkBreakdownResult,
)
from app.services.eworks_questionnaire_service import format_time_frame


def _money(amount: Decimal | float | None) -> str:
    if amount is None:
        return "—"
    value = Decimal(str(amount))
    if value <= 0:
        return "—"
    return f"£{value.quantize(Decimal('0.01')):.2f}"


def _display(value: object | None) -> str:
    if value is None:
        return "—"
    text = str(value).strip()
    return text if text else "—"


def _format_date(value: date | None) -> str:
    if not value:
        return "—"
    return value.strftime("%d %b %Y")


def _quote_description(step1: Step1Snapshot) -> str:
    if step1.quote_description and step1.quote_description.strip():
        return step1.quote_description.strip()
    parts: list[str] = []
    if step1.access_notes:
        parts.append(f"Access: {step1.access_notes.strip()}")
    if step1.original_job_description:
        parts.append(step1.original_job_description.strip())
    if step1.booked_by:
        parts.append(f"Booked by {step1.booked_by.strip()}")
    if step1.travel_notes:
        parts.append(f"Travel: {step1.travel_notes.strip()}")
    if step1.contact:
        parts.append(f"Contact: {step1.contact.strip()}")
    if step1.quote_screening_answers:
        parts.append(f"Quote Screening Answers: {step1.quote_screening_answers.strip()}")
    return "\n\n".join(parts) if parts else "—"


def _material_table_rows(rows: list[MaterialOrderRow]) -> list[dict[str, str]]:
    table: list[dict[str, str]] = []
    for row in rows:
        link = (row.link or "").strip()
        quantity = _display(row.quantity)
        cost = _money(row.cost)
        if link == "—" and cost == "—":
            continue
        table.append({"link": link or "—", "quantity": quantity, "cost": cost})
    return table or [{"link": "—", "quantity": "—", "cost": "—"}]


def _engineer_summary(block: WorkBlockSnapshot) -> dict[str, str]:
    if not block.engineers_required:
        return {"required": "No", "count": "—", "unit": "—", "duration": "—"}
    unit = block.engineer_time_unit or "hours"
    return {
        "required": "Yes",
        "count": _display(block.engineers_needed),
        "unit": "Days" if unit == "days" else "Hours",
        "duration": _display(block.engineer_time_value),
    }


def _labour_summary(block: WorkBlockSnapshot) -> dict[str, str]:
    labour_active = block.labour_required and block.engineers_required and block.engineer_time_unit == "days"
    if not labour_active:
        return {"required": "No", "count": "—", "duration": "—"}
    return {
        "required": "Yes",
        "count": _display(block.labour_needed),
        "duration": _display(block.labour_time_value),
    }


def _time_frame_display(block: WorkBlockSnapshot) -> str:
    if block.engineers_required:
        unit = block.engineer_time_unit or "hours"
        return format_time_frame(unit, block.engineer_time_value)
    if block.time_frame and block.time_frame.strip():
        return block.time_frame.strip()
    return "—"


def _estimation_form_fields(step1: Step1Snapshot) -> list[dict[str, str]]:
    return [
        {"label": "Engineer Name", "value": _display(step1.engineer_name)},
        {"label": "Quote Number", "value": _display(step1.quote_number)},
        {"label": "Job Number", "value": _display(step1.job_number)},
        {"label": "Property Address", "value": _display(step1.property_address)},
        {"label": "Congestion Charge", "value": "Yes" if step1.congestion_required else "No"},
        {"label": "Parking Notes", "value": _display(step1.parking_notes)},
        {"label": "Total Time for job", "value": _display(step1.total_time_for_job)},
        {"label": "Client", "value": _display(step1.client_name)},
        {"label": "PM", "value": _display(step1.property_manager_name)},
        {"label": "Date visited / Form completed", "value": _format_date(step1.date_visited)},
    ]


def _work_form_page(block: WorkBlockSnapshot, *, index: int, trade_name: str) -> dict:
    return {
        "index": index,
        "title": f"Work {index}",
        "scope": _display(block.scope),
        "materials_to_order": _material_table_rows(block.materials_to_order),
        "shelf_materials_rows": _material_table_rows(block.shelf_materials_rows),
        "skill_required": _display(block.skill_required or trade_name),
        "best_engineer": _display(block.best_engineer),
        "subcontractors": _display(block.subcontractors),
        "time_frame": _time_frame_display(block),
        "engineer": _engineer_summary(block),
        "labour": _labour_summary(block),
        "other_notes": _display(block.other_notes),
    }


def _charges_fields(step2: Step2Snapshot) -> list[dict[str, str]]:
    fields = [
        {"label": "Parking required", "value": "Yes" if step2.parking_required else "No"},
    ]
    if step2.parking_required:
        parking_type = (step2.parking_type or "fixed").strip().lower()
        fields.append({"label": "Parking type", "value": _display(step2.parking_type or "fixed")})
        if parking_type == "hourly":
            fields.extend(
                [
                    {"label": "Parking rate per hour (£)", "value": _money(step2.parking_rate_per_hour)},
                    {"label": "Parking hours", "value": _display(step2.parking_hours)},
                ]
            )
        else:
            fields.append({"label": "Parking fixed amount (£)", "value": _money(step2.parking_fixed_amount)})
    fields.extend(
        [
            {"label": "Congestion charge", "value": "Yes" if step2.congestion_required else "No"},
            {"label": "Congestion amount (£)", "value": _money(step2.congestion_amount)},
            {"label": "Travel charge (£)", "value": _money(step2.travel_charge)},
            {"label": "Other charge (£)", "value": _money(step2.other_charge)},
            {"label": "Other charge reason", "value": _display(step2.other_charge_reason)},
        ]
    )
    return fields


def _chunk_fields(fields: list[dict[str, str]], size: int) -> list[list[dict[str, str]]]:
    rows: list[list[dict[str, str]]] = []
    for index in range(0, len(fields), size):
        rows.append(fields[index : index + size])
    return rows


def _sum_lines(lines: list[LineBreakdown]) -> Decimal:
    return sum((line.total for line in lines), Decimal("0"))


def _truncate_scope(scope: str | None, *, limit: int = 80) -> str:
    text = (scope or "").strip()
    if not text:
        return "—"
    if len(text) <= limit:
        return text
    return f"{text[:limit]}…"


def _format_line_items(breakdown: CalculationBreakdown) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for line in breakdown.labour:
        items.append({"label": line.label, "total": _money(line.total)})
    for line in breakdown.materials:
        items.append({"label": line.label, "total": _money(line.total)})
    for line in breakdown.charges:
        items.append({"label": line.label, "total": _money(line.total)})
    return items


def _format_work_results(work_breakdowns: list[WorkBreakdownResult]) -> list[dict[str, object]]:
    works: list[dict[str, object]] = []
    for work in work_breakdowns:
        labour_total = _sum_lines(work.breakdown.labour)
        materials_total = _sum_lines(work.breakdown.materials)
        works.append(
            {
                "index": work.work_index + 1,
                "title": f"Work {work.work_index + 1}",
                "scope": _truncate_scope(work.scope),
                "labour_subtotal": _money(labour_total),
                "materials_subtotal": _money(materials_total),
                "internal_notes": (work.internal_notes or work.breakdown.internal_notes or "").strip() or None,
            }
        )
    return works


def _format_combined_quote(
    breakdown: CalculationBreakdown,
    aggregated_summary: AggregatedQuoteSummary | None,
) -> dict[str, object]:
    return {
        "subtitle": aggregated_summary.subtitle if aggregated_summary else None,
        "labour_charge": _money(breakdown.labour_charge_to_client),
        "materials_parking_cc": _money(breakdown.materials_parking_cc_charge),
        "profit": _money(breakdown.profit_gbp),
        "final_total": _money(breakdown.final_total),
        "lines": _format_line_items(breakdown),
    }


def _build_results_pages(
    *,
    work_breakdowns: list[WorkBreakdownResult],
    internal_notes: str | None,
) -> tuple[int | None, int, int | None, int]:
    base_pages = 3
    has_multiple_works = len(work_breakdowns) > 1
    has_internal_notes = bool((internal_notes or "").strip())
    page = base_pages
    per_work_page = None
    if has_multiple_works:
        page += 1
        per_work_page = page
    page += 1
    combined_page = page
    notes_page = None
    if has_internal_notes:
        page += 1
        notes_page = page
    return per_work_page, combined_page, notes_page, page


def build_eworks_estimate_pdf_context(
    *,
    step1: Step1Snapshot,
    step2: Step2Snapshot,
    breakdown: CalculationBreakdown,
    client_view: dict,
    work_breakdowns: list[WorkBreakdownResult] | None = None,
    aggregated_summary: AggregatedQuoteSummary | None = None,
    internal_notes: str | None = None,
) -> dict:
    calc = client_view.get("calculation", {})
    works = step2.works or []
    if not works and step2.scope:
        works = [WorkBlockSnapshot(scope=step2.scope, findings=step2.findings)]

    work_forms = [_work_form_page(block, index=i + 1, trade_name=step1.trade_name) for i, block in enumerate(works)]
    estimation_fields = _estimation_form_fields(step1)
    charges_fields = _charges_fields(step2)
    # Legacy keys retained for tests and compatibility.
    header_parts = [part for part in (step1.engineer_name, step1.quote_number, step1.job_number) if part]

    work_results = work_breakdowns or []
    combined_notes = (internal_notes or breakdown.internal_notes or "").strip() or None
    per_work_page, combined_page, notes_page, total_pages = _build_results_pages(
        work_breakdowns=work_results,
        internal_notes=combined_notes,
    )

    return {
        "document_title": "OPTIMAL ESTIMATE",
        "estimation_form_title": "Estimation Form",
        "questionnaire_title": "Estimating Questionnaire",
        "charges_title": "Charges",
        "summary_title": "Quote Summary",
        "estimation_fields": estimation_fields,
        "estimation_field_rows": _chunk_fields(estimation_fields, 3),
        "quote_description": _quote_description(step1),
        "findings_report": _display(step1.findings_report),
        "trade_name": _display(step1.trade_name),
        "work_forms": work_forms,
        "charges_fields": charges_fields,
        "charges_field_rows": _chunk_fields(charges_fields, 2),
        "summary": {
            "subtotal": _money(calc.get("subtotal", breakdown.subtotal)),
            "vat_rate": float(calc.get("vat_rate", breakdown.vat_rate)),
            "vat_total": _money(calc.get("vat_total", breakdown.vat_total)),
            "final_total": _money(calc.get("final_total", breakdown.final_total)),
        },
        "header_line": " ".join(header_parts),
        "property_address": step1.property_address,
        "client_manager_line": (
            f"{step1.client_name} {step1.property_manager_name} (Property Manager)"
            if step1.property_manager_name
            else step1.client_name
        ),
        "results": {
            "has_multiple_works": len(work_results) > 1,
            "works": _format_work_results(work_results),
            "combined": _format_combined_quote(breakdown, aggregated_summary),
            "internal_notes": combined_notes,
        },
        "per_work_page": per_work_page,
        "combined_page": combined_page,
        "notes_page": notes_page,
        "total_pages": total_pages,
    }
