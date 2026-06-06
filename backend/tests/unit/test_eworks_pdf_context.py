from decimal import Decimal

from app.schemas.calculation import CalculationBreakdown, LineBreakdown
from app.schemas.eworks_link import (
    AggregatedQuoteSummary,
    MaterialLinkRow,
    MaterialSupplier,
    Step1Snapshot,
    Step2Snapshot,
    WorkBlockSnapshot,
    WorkBreakdownResult,
    quote_additional_charge_lines,
)
from app.services.eworks_pdf_context_service import _supplier_display_title, build_eworks_estimate_pdf_context


def _step1(**overrides) -> Step1Snapshot:
    base = {
        "quote_number": "Q21863",
        "job_number": "33629",
        "engineer_name": "Alex Alves",
        "client_name": "Lamberts Chartered Surveyors",
        "trade_name": "Carpenter",
        "property_address": "The Factory, 1 Nile Street",
        "property_manager_name": "Kira Mcintyre",
        "access_notes": "To meet caretaker on site on 22nd May at 8am. Alex - 07960696064",
        "original_job_description": "Please can you provide a quote\nTo upgrade all doors marked for upgrade",
        "booked_by": "Billie",
        "travel_notes": "1st appt",
        "quote_screening_answers": "1. Unfortunately we do not have any pictures.\n2. We would like it back ASAP",
        "congestion_required": False,
        "congestion_amount": Decimal("0"),
        "travel": Decimal("0"),
    }
    base.update(overrides)
    return Step1Snapshot(**base)


def test_build_eworks_pdf_cover_matches_reference_fields():
    step1 = _step1()
    step2 = Step2Snapshot(
        works=[
            WorkBlockSnapshot(
                scope="Door no 12. B2. Stairwell entrance 8, single timber, FD30S\n"
                "1. Recommend the 5mm gap is monitored\n"
                "Supply and fit hardwood lipping\n"
                "Supply and fit push plate",
                findings="1. Recommend the 5mm gap is monitored",
                time_frame="1 day",
                materials_to_order=[{"link": "Lipping", "quantity": 1, "cost": 30}],
                shelf_materials_rows=[{"link": "Push plate", "quantity": 1, "cost": 40}],
            )
        ]
    )
    breakdown = CalculationBreakdown(
        labour=[],
        materials=[],
        charges=[],
        subtotal=Decimal("120"),
        vat_rate=Decimal("20"),
        vat_total=Decimal("24"),
        final_total=Decimal("144"),
        formula_version="test",
    )
    context = build_eworks_estimate_pdf_context(
        step1=step1,
        step2=step2,
        breakdown=breakdown,
        client_view={"calculation": breakdown.model_dump(mode="json")},
    )

    assert context["document_title"] == "OPTIMAL ESTIMATE"
    assert context["header_line"] == "Alex Alves Q21863 33629"
    assert context["property_address"] == "The Factory, 1 Nile Street"
    assert "Kira Mcintyre" in context["estimation_fields"][8]["value"]
    assert context["work_forms"][0]["scope"].startswith("Door no 12")
    assert context["work_forms"][0]["material_suppliers"][0]["links"][0]["cost"] == "£30.00"
    assert context["total_pages"] == 4
    assert context["combined_page"] == 4


def test_pdf_uses_supplier_name_when_present():
    step1 = _step1()
    step2 = Step2Snapshot(
        works=[
            WorkBlockSnapshot(
                scope="Install door",
                materials_to_order=[
                    {
                        "supplier_name": "Travis Perkins",
                        "links": [{"link": "Lipping", "quantity": 1, "cost": 30}],
                        "delivery_charge": 0,
                    }
                ],
            )
        ]
    )
    breakdown = CalculationBreakdown(
        labour=[],
        materials=[],
        charges=[],
        subtotal=Decimal("30"),
        vat_rate=Decimal("20"),
        vat_total=Decimal("6"),
        final_total=Decimal("36"),
        formula_version="test",
    )
    context = build_eworks_estimate_pdf_context(
        step1=step1,
        step2=step2,
        breakdown=breakdown,
        client_view={"calculation": breakdown.model_dump(mode="json")},
    )

    assert context["work_forms"][0]["material_suppliers"][0]["title"] == "Travis Perkins"


def test_supplier_display_title_falls_back_when_blank():
    supplier = MaterialSupplier(links=[MaterialLinkRow()], supplier_name="  ")
    assert _supplier_display_title(supplier, 2) == "Supplier 2"


def test_render_eworks_estimate_document_includes_form_sections():
    from app.adapters.pdf_renderer import render_eworks_estimate_document

    context = build_eworks_estimate_pdf_context(
        step1=_step1(),
        step2=Step2Snapshot(works=[WorkBlockSnapshot(scope="Door no 11. B2 stairwell", time_frame="2 hours")]),
        breakdown=CalculationBreakdown(
            labour=[],
            materials=[],
            charges=[],
            subtotal=Decimal("100"),
            vat_rate=Decimal("20"),
            vat_total=Decimal("20"),
            final_total=Decimal("120"),
            formula_version="test",
        ),
        client_view={"calculation": {"subtotal": 100, "vat_rate": 20, "vat_total": 20, "final_total": 120}},
    )
    context["quote_number"] = "Q21863"
    content, file_name, media_type = render_eworks_estimate_document(context, is_draft=False)
    html = content.decode("utf-8") if media_type != "application/pdf" else ""
    if media_type == "application/pdf":
        assert content.startswith(b"%PDF")
    else:
        assert "OPTIMAL ESTIMATE" in html
        assert "Estimation Form" in html
        assert "Estimating Questionnaire" in html
        assert "Scope of Works" in html
        assert "Door no 11. B2 stairwell" in html
        assert "#000000" in html
        assert "#f9a825" in html
        assert "-- 1 of" in html
        assert "Combined Quote" in html
    assert file_name.startswith("document_Q21863")


def test_quote_additional_charge_lines_omits_ulez_and_waste():
    step2 = Step2Snapshot(
        congestion_required=True,
        congestion_amount=Decimal("18"),
        travel_charge=Decimal("10"),
        other_charge=Decimal("5"),
        other_charge_reason="Access fee",
        ulez_required=True,
        ulez_amount=Decimal("12.50"),
        waste_disposal_required=True,
        waste_disposal_amount=Decimal("45"),
    )
    lines = quote_additional_charge_lines(step2)
    joined = " ".join(lines)
    assert "Congestion: £18" in joined
    assert "Travel: £10" in joined
    assert "Other: £5" in joined
    assert "ULEZ" not in joined
    assert "Waste disposal" not in joined


def test_pdf_charges_omits_ulez_and_waste():
    step2 = Step2Snapshot(
        ulez_required=True,
        ulez_amount=Decimal("12.50"),
        waste_disposal_required=True,
        waste_disposal_amount=Decimal("45"),
        congestion_required=True,
        congestion_amount=Decimal("18"),
    )
    context = build_eworks_estimate_pdf_context(
        step1=_step1(),
        step2=step2,
        breakdown=CalculationBreakdown(
            labour=[],
            materials=[],
            charges=[],
            subtotal=Decimal("100"),
            vat_rate=Decimal("20"),
            vat_total=Decimal("20"),
            final_total=Decimal("120"),
            formula_version="test",
        ),
        client_view={"calculation": {"subtotal": 100, "vat_rate": 20, "vat_total": 20, "final_total": 120}},
    )
    labels = [field["label"] for field in context["charges_fields"]]
    assert "Congestion charge" in labels
    assert "ULEZ charge" not in labels
    assert "Waste disposal charge" not in labels


def test_pdf_charges_fixed_parking_omits_hourly_fields():
    step2 = Step2Snapshot(
        parking_required=True,
        parking_type="fixed",
        parking_rate_per_hour=Decimal("30"),
        parking_hours=Decimal("1"),
        parking_fixed_amount=Decimal("100"),
        congestion_required=True,
        congestion_amount=Decimal("100"),
    )
    context = build_eworks_estimate_pdf_context(
        step1=_step1(),
        step2=step2,
        breakdown=CalculationBreakdown(
            labour=[],
            materials=[],
            charges=[],
            subtotal=Decimal("565"),
            vat_rate=Decimal("20"),
            vat_total=Decimal("113"),
            final_total=Decimal("678"),
            formula_version="test",
        ),
        client_view={"calculation": {"subtotal": 565, "vat_rate": 20, "vat_total": 113, "final_total": 678}},
    )
    labels = [field["label"] for field in context["charges_fields"]]
    assert "Parking fixed amount (£)" in labels
    assert "Parking rate per hour (£)" not in labels
    assert "Parking hours" not in labels
    fixed = next(field for field in context["charges_fields"] if field["label"] == "Parking fixed amount (£)")
    assert fixed["value"] == "£100.00"


def test_pdf_charges_hourly_parking_shows_rate_and_hours():
    step2 = Step2Snapshot(
        parking_required=True,
        parking_type="hourly",
        parking_rate_per_hour=Decimal("30"),
        parking_hours=Decimal("2"),
        parking_fixed_amount=Decimal("100"),
    )
    context = build_eworks_estimate_pdf_context(
        step1=_step1(),
        step2=step2,
        breakdown=CalculationBreakdown(
            labour=[],
            materials=[],
            charges=[],
            subtotal=Decimal("100"),
            vat_rate=Decimal("20"),
            vat_total=Decimal("20"),
            final_total=Decimal("120"),
            formula_version="test",
        ),
        client_view={"calculation": {"subtotal": 100, "vat_rate": 20, "vat_total": 20, "final_total": 120}},
    )
    labels = [field["label"] for field in context["charges_fields"]]
    assert "Parking rate per hour (£)" in labels
    assert "Parking hours" in labels
    assert "Parking fixed amount (£)" not in labels


def test_pdf_quote_level_parking_in_charges_not_work_form():
    step2 = Step2Snapshot(
        works=[
            WorkBlockSnapshot(
                scope="Work with legacy parking fields",
                parking_required=True,
                parking_type="fixed",
                parking_fixed_amount=Decimal("50"),
                parking_vehicles=2,
                parking_notes="Legacy work note",
                parking_latitude=Decimal("51.5074"),
                parking_longitude=Decimal("-0.1278"),
            )
        ],
        parking_required=True,
        parking_type="fixed",
        parking_fixed_amount=Decimal("100"),
        parking_vehicles=2,
        parking_latitude=Decimal("51.5074"),
        parking_longitude=Decimal("-0.1278"),
        parking_notes="Quote-level parking notes",
    )
    context = build_eworks_estimate_pdf_context(
        step1=_step1(),
        step2=step2,
        breakdown=CalculationBreakdown(
            labour=[],
            materials=[],
            charges=[],
            subtotal=Decimal("100"),
            vat_rate=Decimal("20"),
            vat_total=Decimal("20"),
            final_total=Decimal("120"),
            formula_version="test",
        ),
        client_view={"calculation": {"subtotal": 100, "vat_rate": 20, "vat_total": 20, "final_total": 120}},
    )
    parking = context["work_forms"][0]["parking"]
    assert parking["required"] is False
    charge_labels = [field["label"] for field in context["charges_fields"]]
    assert "Parking fixed amount (£)" in charge_labels
    assert "Number of vehicles" in charge_labels
    assert "GPS snapshot" in charge_labels
    parking_notes = next(field for field in context["charges_fields"] if field["label"] == "Parking notes")
    assert parking_notes["value"] == "Quote-level parking notes"
    gps = next(field for field in context["charges_fields"] if field["label"] == "GPS snapshot")
    assert "51.5074" in gps["value"]


def test_build_eworks_pdf_results_context():
    breakdown = CalculationBreakdown(
        labour=[LineBreakdown(label="Labour", formula="x", total=Decimal("145"))],
        materials=[LineBreakdown(label="Materials", formula="x", total=Decimal("260"))],
        charges=[LineBreakdown(label="Congestion", formula="x", total=Decimal("18"))],
        subtotal=Decimal("405"),
        vat_rate=Decimal("20"),
        vat_total=Decimal("81"),
        final_total=Decimal("486"),
        formula_version="test",
        labour_charge_to_client=Decimal("145"),
        materials_parking_cc_charge=Decimal("260"),
        profit_gbp=Decimal("153"),
        internal_notes="BUDGET: Materials: £190 / Parking: £0 / CC: £18",
    )
    work_breakdowns = [
        WorkBreakdownResult(
            work_index=0,
            scope="Work one scope",
            breakdown=CalculationBreakdown(
                labour=[LineBreakdown(label="Labour", formula="x", total=Decimal("80"))],
                materials=[LineBreakdown(label="Materials", formula="x", total=Decimal("90"))],
                charges=[],
                subtotal=Decimal("170"),
                vat_rate=Decimal("20"),
                vat_total=Decimal("34"),
                final_total=Decimal("204"),
                formula_version="test",
                internal_notes="Work one notes",
            ),
            internal_notes="Work one notes",
        ),
        WorkBreakdownResult(
            work_index=1,
            scope="Work two scope",
            breakdown=CalculationBreakdown(
                labour=[LineBreakdown(label="Labour", formula="x", total=Decimal("65"))],
                materials=[LineBreakdown(label="Materials", formula="x", total=Decimal("170"))],
                charges=[],
                subtotal=Decimal("235"),
                vat_rate=Decimal("20"),
                vat_total=Decimal("47"),
                final_total=Decimal("282"),
                formula_version="test",
                internal_notes="Work two notes",
            ),
            internal_notes="Work two notes",
        ),
    ]
    context = build_eworks_estimate_pdf_context(
        step1=_step1(),
        step2=Step2Snapshot(
            works=[
                WorkBlockSnapshot(scope="Work one scope"),
                WorkBlockSnapshot(scope="Work two scope"),
            ]
        ),
        breakdown=breakdown,
        client_view={"calculation": breakdown.model_dump(mode="json")},
        work_breakdowns=work_breakdowns,
        aggregated_summary=AggregatedQuoteSummary(
            work_count=2,
            labour_type="hourly",
            subtitle="3 hours total across 2 works",
        ),
        internal_notes=breakdown.internal_notes,
    )

    assert context["results"]["has_multiple_works"] is True
    assert len(context["results"]["works"]) == 2
    assert context["results"]["combined"]["profit"] == "£153.00"
    assert context["results"]["combined"]["subtitle"] == "3 hours total across 2 works"
    assert context["results"]["internal_notes"] == breakdown.internal_notes
    assert context["per_work_page"] == 4
    assert context["combined_page"] == 5
    assert context["notes_page"] == 6
    assert context["total_pages"] == 6

    from app.adapters.pdf_renderer import render_eworks_estimate_document

    context["quote_number"] = "Q21863"
    content, _, media_type = render_eworks_estimate_document(context, is_draft=False)
    if media_type != "application/pdf":
        html = content.decode("utf-8")
        assert "Per-work Breakdown" in html
        assert "Combined Quote" in html
        assert "Internal Notes (Combined)" in html
        assert "£153.00" in html
        assert "BUDGET: Materials: £190 / Parking: £0 / CC: £18" in html
