"""PDF rich-text rendering tests (pre-WeasyPrint HTML assertions)."""

import re
from decimal import Decimal

from app.adapters.pdf_renderer import render_all_trades_document, render_combined_works_document, render_eworks_estimate_document
from app.schemas.calculation import CalculationBreakdown
from app.schemas.eworks_link import Step1Snapshot, Step2Snapshot, WorkBlockSnapshot
from app.services.eworks_pdf_context_service import build_all_trades_pdf_context, build_eworks_estimate_pdf_context

EWORKS_SCOPE_HTML = (
    '<span style="text-decoration: underline;"><strong>Access</strong></span><br />&nbsp;<br />'
    "Supply and fit hardwood lipping"
)


def _step1(**overrides) -> Step1Snapshot:
    base = {
        "quote_number": "Q21863",
        "job_number": "33629",
        "engineer_name": "Alex Alves",
        "client_name": "Lamberts Chartered Surveyors",
        "trade_name": "Carpenter",
        "property_address": "The Factory, 1 Nile Street",
        "quote_description": EWORKS_SCOPE_HTML,
        "findings_report": EWORKS_SCOPE_HTML,
    }
    base.update(overrides)
    return Step1Snapshot(**base)


def _breakdown() -> CalculationBreakdown:
    return CalculationBreakdown(
        labour=[],
        materials=[],
        charges=[],
        subtotal=Decimal("100"),
        vat_rate=Decimal("20"),
        vat_total=Decimal("20"),
        final_total=Decimal("120"),
        formula_version="test",
    )


def _visible_html(html: str) -> str:
    return re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)


def _assert_no_raw_html_artifacts(html: str) -> None:
    body = _visible_html(html)
    assert "&lt;span" not in body
    assert "&nbsp;" not in body
    assert '<span style="' not in body


def test_eworks_estimate_pdf_renders_rich_text_fields():
    context = build_eworks_estimate_pdf_context(
        step1=_step1(),
        step2=Step2Snapshot(works=[WorkBlockSnapshot(scope=EWORKS_SCOPE_HTML)]),
        breakdown=_breakdown(),
        client_view={"calculation": _breakdown().model_dump(mode="json")},
    )
    context["quote_number"] = "Q21863"
    content, _, media_type = render_eworks_estimate_document(context, is_draft=False)
    if media_type == "application/pdf":
        return
    html = content.decode("utf-8")
    _assert_no_raw_html_artifacts(html)
    assert "Access" in html
    assert "Supply and fit hardwood lipping" in html


def test_all_trades_pdf_scope_preview_is_plain_text():
    from unittest.mock import MagicMock

    step1 = _step1()
    step2 = Step2Snapshot(works=[WorkBlockSnapshot(scope=EWORKS_SCOPE_HTML, product_code="P-001")])
    breakdown = {
        "final_total": "120.00",
        "vat_rate": "20",
        "vat_total": "20.00",
        "labour": [],
        "materials": [],
        "charges": [],
    }
    work_breakdowns = [
        {
            "work_index": 0,
            "breakdown": {"labour": [{"total": "80"}], "materials": [{"total": "20"}]},
        }
    ]
    db = MagicMock()
    context = build_all_trades_pdf_context(
        db=db,
        step1=step1,
        step2=step2,
        breakdown=breakdown,
        work_breakdowns=work_breakdowns,
    )
    preview = context["all_trades_works"][0]["scope_preview"]
    assert "Access" in preview
    assert "<span" not in preview
    assert "&nbsp;" not in preview

    content, _, media_type = render_all_trades_document(context)
    if media_type == "application/pdf":
        return
    html = content.decode("utf-8")
    _assert_no_raw_html_artifacts(html)
    assert "Access" in html


def test_client_pdf_context_excludes_internal_notes():
    item = {
        "index": 1,
        "description": "Work",
        "description_html": "Work",
        "findings": "Finding",
        "findings_html": "Finding",
        "scope": "Scope",
        "scope_html": "Scope",
        "notes_exclusions": "",
        "notes_exclusions_html": "",
        "quoted_price": "£100.00",
    }
    context = {
        "quote_number": "Q21863",
        "job_number": "33629",
        "client_name": "ACME",
        "property_address": "1 Test Street",
        "engineer_name": "Alex",
        "trade_name": "Carpenter",
        "prepared_by": "The Optimal Group",
        "property_manager": "PM",
        "total_items": 1,
        "vat_label": "VAT + 20%",
        "document_title": "QUOTE SUMMARY",
        "report_notes": "Notes",
        "report_notes_html": "Notes",
        "subtotal": "£100.00",
        "vat_total": "£20.00",
        "grand_total": "£120.00",
        "generated_at": "01 Jan 2026",
        "items": [item],
        "cost_summary": {
            "material_cost": "£0.00",
            "labour_charge": "£0.00",
            "materials_charge": "£0.00",
            "client_price": "£100.00",
            "optimal_cost": "£0.00",
            "profit_gbp": "£0.00",
            "margin_pct": "0.00%",
        },
    }
    content, _, media_type = render_combined_works_document(context, view_type="client")
    if media_type == "application/pdf":
        return
    html = _visible_html(content.decode("utf-8")).lower()
    assert "internal notes" not in html
    assert "profit" not in html
    assert "margin %" not in html
    assert "calc profit" not in html
