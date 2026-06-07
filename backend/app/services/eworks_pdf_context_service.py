"""Build PDF context for eWorks estimation documents."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.schemas.calculation import CalculationBreakdown, LineBreakdown
from app.schemas.eworks_link import (
    AggregatedQuoteSummary,
    MaterialLinkRow,
    MaterialOrderRow,
    MaterialSupplier,
    Step1Snapshot,
    Step2Snapshot,
    WorkBlockSnapshot,
    WorkBreakdownResult,
    migrate_legacy_material_rows,
)
from sqlalchemy.orm import Session

from app.schemas.eworks_link import Step1Snapshot, Step2Snapshot
from app.services.eworks_link_service import work_skill_name
from app.services.eworks_questionnaire_service import format_time_frame
from app.utils.html_text import html_to_plain_text, prepare_pdf_rich_text
from app.utils.work_label import format_product_label, format_work_label


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


def _material_link_table_rows(rows: list[MaterialLinkRow] | list[MaterialOrderRow]) -> list[dict[str, str]]:
    table: list[dict[str, str]] = []
    for row in rows:
        link = (row.link or "").strip()
        quantity = _display(row.quantity)
        cost = _money(row.cost)
        if link == "—" and cost == "—":
            continue
        table.append({"link": link or "—", "quantity": quantity, "cost": cost})
    return table or [{"link": "—", "quantity": "—", "cost": "—"}]


def _supplier_display_title(supplier: MaterialSupplier, index: int) -> str:
    name = (supplier.supplier_name or "").strip()
    return name if name else f"Supplier {index}"


def _supplier_material_sections(suppliers: list[MaterialSupplier]) -> list[dict[str, object]]:
    sections: list[dict[str, object]] = []
    for index, supplier in enumerate(suppliers, start=1):
        link_rows = _material_link_table_rows(supplier.links)
        links_total = sum(
            (Decimal(str(row.quantity)) * Decimal(str(row.cost)) for row in supplier.links if row.cost > 0),
            Decimal("0"),
        )
        delivery = supplier.delivery_charge or Decimal("0")
        subtotal = links_total + delivery
        if link_rows == [{"link": "—", "quantity": "—", "cost": "—"}] and delivery <= 0:
            continue
        sections.append(
            {
                "title": _supplier_display_title(supplier, index),
                "links": link_rows,
                "delivery_charge": _money(delivery),
                "subtotal": _money(subtotal),
            }
        )
    return sections or [
        {
            "title": "Supplier 1",
            "links": [{"link": "—", "quantity": "—", "cost": "—"}],
            "delivery_charge": "—",
            "subtotal": "—",
        }
    ]


def _material_table_rows(rows: list[MaterialOrderRow]) -> list[dict[str, str]]:
    return _material_link_table_rows(rows)


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


def _google_maps_url(latitude: Decimal | float | None, longitude: Decimal | float | None) -> str | None:
    if latitude is None or longitude is None:
        return None
    return f"https://www.google.com/maps?q={latitude},{longitude}"


def _work_parking_section(block: WorkBlockSnapshot) -> dict[str, object]:
    if not block.parking_required:
        return {"required": False, "fields": [], "notes": None, "maps_url": None}
    parking_type = (block.parking_type or "fixed").strip().lower()
    fields: list[dict[str, str]] = [
        {"label": "Parking type", "value": _display(block.parking_type or "fixed")},
        {"label": "Number of vehicles", "value": _display(max(1, block.parking_vehicles or 1))},
    ]
    if parking_type == "hourly":
        fields.extend(
            [
                {"label": "Parking rate per hour (£)", "value": _money(block.parking_rate_per_hour)},
                {"label": "Parking hours", "value": _display(block.parking_hours)},
            ]
        )
    else:
        fields.append({"label": "Parking fixed amount (£)", "value": _money(block.parking_fixed_amount)})
    return {
        "required": True,
        "fields": fields,
        "notes": _display(block.parking_notes) if block.parking_notes and block.parking_notes.strip() else None,
        "maps_url": _google_maps_url(block.parking_latitude, block.parking_longitude),
    }


def _work_form_page(block: WorkBlockSnapshot, *, index: int, trade_name: str) -> dict:
    suppliers = [MaterialSupplier.model_validate(item) for item in migrate_legacy_material_rows(block.materials_to_order)]
    product_label = format_product_label(block.product_name, block.product_code)
    scope_plain, scope_html = _rich_text_fields(block.scope)
    other_notes_plain, other_notes_html = _rich_text_fields(block.other_notes)
    return {
        "index": index,
        "title": format_work_label(
            product_name=block.product_name,
            product_code=block.product_code,
            scope=html_to_plain_text(block.scope),
            index=index - 1,
        ),
        "product_label": product_label,
        "scope": scope_plain,
        "scope_html": scope_html,
        "material_suppliers": _supplier_material_sections(suppliers),
        "shelf_materials_rows": _material_table_rows(block.shelf_materials_rows),
        "skill_required": _display(block.skill_required or trade_name),
        "best_engineer": _display(block.best_engineer),
        "subcontractors": _display(block.subcontractors),
        "time_frame": _time_frame_display(block),
        "engineer": _engineer_summary(block),
        "labour": _labour_summary(block),
        "parking": {"required": False, "fields": [], "notes": None, "maps_url": None},
        "other_notes": other_notes_plain,
        "other_notes_html": other_notes_html,
    }


def _charges_fields(step2: Step2Snapshot) -> list[dict[str, str]]:
    fields = [
        {"label": "Parking required", "value": "Yes" if step2.parking_required else "No"},
    ]
    if step2.parking_required:
        parking_type = (step2.parking_type or "fixed").strip().lower()
        fields.append({"label": "Parking type", "value": _display(step2.parking_type or "fixed")})
        fields.append({"label": "Number of vehicles", "value": _display(max(1, step2.parking_vehicles or 1))})
        if parking_type == "hourly":
            fields.extend(
                [
                    {"label": "Parking rate per hour (£)", "value": _money(step2.parking_rate_per_hour)},
                    {"label": "Parking hours", "value": _display(step2.parking_hours)},
                ]
            )
        else:
            fields.append({"label": "Parking fixed amount (£)", "value": _money(step2.parking_fixed_amount)})
        maps_url = _google_maps_url(step2.parking_latitude, step2.parking_longitude)
        if maps_url:
            fields.append({"label": "GPS snapshot", "value": maps_url})
    fields.extend(
        [
            {"label": "Congestion charge", "value": "Yes" if step2.congestion_required else "No"},
            {"label": "Congestion amount (£)", "value": _money(step2.congestion_amount)},
            {"label": "Travel charge (£)", "value": _money(step2.travel_charge)},
            {"label": "Other charge (£)", "value": _money(step2.other_charge)},
            {"label": "Other charge notes", "value": _display(step2.other_charge_reason)},
            {"label": "Parking notes", "value": _display(step2.parking_notes)},
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
    text = html_to_plain_text(scope).strip()
    if not text:
        return "—"
    if len(text) <= limit:
        return text
    return f"{text[:limit]}…"


def _rich_text_fields(value: object | None) -> tuple[str, str]:
    if value is None or not str(value).strip():
        return "—", ""
    text = str(value).strip()
    return _display(html_to_plain_text(text)), prepare_pdf_rich_text(text)


def _format_line_items(breakdown: CalculationBreakdown) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for line in breakdown.labour:
        items.append({"label": line.label, "total": _money(line.total)})
    for line in breakdown.materials:
        items.append({"label": line.label, "total": _money(line.total)})
    for line in breakdown.charges:
        items.append({"label": line.label, "total": _money(line.total)})
    return items


def _format_work_results(
    work_breakdowns: list[WorkBreakdownResult],
    work_blocks: list[WorkBlockSnapshot] | None = None,
) -> list[dict[str, object]]:
    blocks = work_blocks or []
    works: list[dict[str, object]] = []
    for work in work_breakdowns:
        block = blocks[work.work_index] if work.work_index < len(blocks) else None
        labour_total = _sum_lines(work.breakdown.labour)
        materials_total = _sum_lines(work.breakdown.materials)
        title = format_work_label(
            product_name=block.product_name if block else None,
            product_code=block.product_code if block else None,
            scope=html_to_plain_text(work.scope or (block.scope if block else None)),
            index=work.work_index,
        )
        notes_raw = (work.internal_notes or work.breakdown.internal_notes or "").strip() or None
        notes_plain, notes_html = _rich_text_fields(notes_raw)
        works.append(
            {
                "index": work.work_index + 1,
                "title": title,
                "scope": _truncate_scope(work.scope),
                "labour_subtotal": _money(labour_total),
                "materials_subtotal": _money(materials_total),
                "internal_notes": None if notes_plain == "—" else notes_plain,
                "internal_notes_html": notes_html,
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
    combined_notes_raw = (internal_notes or breakdown.internal_notes or "").strip() or None
    combined_notes_plain, combined_notes_html = _rich_text_fields(combined_notes_raw)
    combined_notes = None if combined_notes_plain == "—" else combined_notes_plain
    quote_description_plain = _quote_description(step1)
    quote_description_html = prepare_pdf_rich_text(quote_description_plain)
    findings_plain, findings_html = _rich_text_fields(step1.findings_report)
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
        "quote_description": quote_description_plain,
        "quote_description_html": quote_description_html,
        "findings_report": findings_plain,
        "findings_report_html": findings_html,
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
            "works": _format_work_results(work_results, works),
            "combined": _format_combined_quote(breakdown, aggregated_summary),
            "internal_notes": combined_notes,
            "internal_notes_html": combined_notes_html,
        },
        "per_work_page": per_work_page,
        "combined_page": combined_page,
        "notes_page": notes_page,
        "total_pages": total_pages,
    }


def build_all_trades_pdf_context(
    *,
    db: Session,
    step1: Step1Snapshot,
    step2: Step2Snapshot,
    breakdown: dict,
    work_breakdowns: list[dict],
    work_indexes: list[int] | None = None,
) -> dict:
    from app.services.calculation_session_service import (
        _dashboard_quote_summary_breakdown,
        _resolve_work_product_fields,
        _work_subtotals_from_breakdown,
    )
    from app.services.quote_job_assignment_service import (
        _comparison_additional_charges_total,
        _comparison_charge_lines,
    )

    summary_breakdown = _dashboard_quote_summary_breakdown(breakdown)
    if summary_breakdown is None:
        raise ValueError("Quote breakdown is required for all-trades PDF")

    breakdown_map = {item["work_index"]: item for item in work_breakdowns}
    all_trades_works: list[dict[str, object]] = []
    selected_indexes = set(work_indexes) if work_indexes is not None else None
    works_subtotal = Decimal("0")

    for index, block in enumerate(step2.works):
        if selected_indexes is not None and index not in selected_indexes:
            continue
        work_result = breakdown_map.get(index, {})
        work_breakdown = work_result.get("breakdown") or {}
        labour_subtotal, materials_subtotal = _work_subtotals_from_breakdown(work_breakdown)
        labour_amount = labour_subtotal or Decimal("0")
        materials_amount = materials_subtotal or Decimal("0")
        work_subtotal = labour_amount + materials_amount
        works_subtotal += work_subtotal
        product_name, product_code = _resolve_work_product_fields(db, block)
        trade_name = work_skill_name(block, step1.trade_name or "")
        product_label = format_work_label(
            product_name=product_name,
            product_code=product_code,
            scope=html_to_plain_text(block.scope),
            index=index,
        )
        all_trades_works.append(
            {
                "index": index + 1,
                "trade_name": _display(trade_name),
                "product_name": _display(product_name),
                "product_code": _display(product_code) if product_code else None,
                "product_label": product_label,
                "scope_preview": _truncate_scope(block.scope),
                "labour_subtotal": _money(labour_subtotal),
                "materials_subtotal": _money(materials_subtotal),
                "work_subtotal": _money(work_subtotal),
            }
        )

    charge_lines = _comparison_charge_lines(breakdown)
    additional_charges = [
        {"label": line.label, "amount": _money(line.amount)}
        for line in charge_lines
        if line.amount > 0
    ]
    vat_rate = breakdown.get("vat_rate")
    additional_charges_total = _comparison_additional_charges_total(charge_lines)

    if work_indexes is not None:
        vat_total = summary_breakdown.vat_total
        if vat_rate is not None:
            rate = Decimal(str(vat_rate))
            vat_total = ((works_subtotal + additional_charges_total) * rate / Decimal("100")).quantize(
                Decimal("0.01")
            )
        final_total = works_subtotal + additional_charges_total + vat_total
        summary = {
            "works_subtotal": _money(works_subtotal),
            "additional_charges_total": _money(additional_charges_total),
            "vat_rate": float(vat_rate) if vat_rate is not None else None,
            "vat_total": _money(vat_total),
            "final_total": _money(final_total),
        }
    else:
        summary = {
            "works_subtotal": _money(summary_breakdown.works_subtotal),
            "additional_charges_total": _money(additional_charges_total),
            "vat_rate": float(vat_rate) if vat_rate is not None else None,
            "vat_total": _money(summary_breakdown.vat_total),
            "final_total": _money(summary_breakdown.final_total),
        }

    return {
        "document_title": "All Trades / Skills",
        "quote_number": step1.quote_number,
        "job_number": step1.job_number,
        "client_name": _display(step1.client_name),
        "property_address": _display(step1.property_address),
        "engineer_name": _display(step1.engineer_name),
        "all_trades_works": all_trades_works,
        "summary": summary,
        "additional_charges": additional_charges,
    }
