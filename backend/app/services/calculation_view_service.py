from decimal import Decimal

from app.models.calculation_session import CalculationSession
from app.schemas.calculation import CalculationBreakdown
from app.schemas.eworks_link import Step1Snapshot, Step2Snapshot

_CLIENT_HIDDEN_CALC_KEYS = {
    "direct_labour_cost",
    "overhead_cost",
    "denominator_used",
    "profit_gbp",
    "profit_pct",
    "client_fee_pct",
    "materials_parking_cc_charge",
    "labour_charge_to_client",
    "formula_source",
    "xlsx_formula_version",
    "internal_notes",
    "margin_total",
    "warnings",
}


def _breakdown_to_dict(breakdown: CalculationBreakdown) -> dict:
    return breakdown.model_dump(mode="json")


def build_internal_view_from_session(
    session: CalculationSession,
    breakdown: CalculationBreakdown,
    step2: Step2Snapshot,
) -> dict:
    step1 = Step1Snapshot.model_validate(session.step1_snapshot)
    calc = _breakdown_to_dict(breakdown)
    return {
        "session_id": str(session.id),
        "source": session.source,
        "quote_number": step1.quote_number,
        "job_number": step1.job_number,
        "external_job_id": step1.external_job_id,
        "client_name": step1.client_name,
        "trade_name": step1.trade_name,
        "property_address": step1.property_address,
        "property_manager_name": step1.property_manager_name,
        "property_manager_email": step1.property_manager_email,
        "property_manager_phone": step1.property_manager_phone,
        "tenant_name": step1.tenant_name,
        "tenant_phone": step1.tenant_phone,
        "access_notes": step1.access_notes,
        "original_job_description": step1.original_job_description,
        "booked_by": step1.booked_by,
        "contact": step1.contact,
        "quote_screening_answers": step1.quote_screening_answers,
        "date_visited": step1.date_visited.isoformat() if step1.date_visited else None,
        "travel_time_minutes": step1.travel_time_minutes,
        "travel_notes": step1.travel_notes,
        "parking_notes": step1.parking_notes,
        "total_time_for_job": step1.total_time_for_job,
        "quote_description": step1.quote_description,
        "findings_report": step1.findings_report,
        "findings": step2.findings,
        "scope": step2.scope,
        "calculation": {
            key: calc.get(key)
            for key in (
                "formula_source",
                "xlsx_formula_version",
                "direct_labour_cost",
                "overhead_cost",
                "labour_charge_to_client",
                "materials_parking_cc_charge",
                "client_fee_pct",
                "denominator_used",
                "profit_gbp",
                "profit_pct",
                "internal_notes",
                "subtotal",
                "vat_total",
                "final_total",
                "labour",
                "materials",
                "charges",
            )
            if calc.get(key) is not None
        },
    }


def build_internal_notes_from_breakdown(session: CalculationSession, breakdown: CalculationBreakdown) -> dict:
    step1 = Step1Snapshot.model_validate(session.step1_snapshot)
    calc = _breakdown_to_dict(breakdown)
    return {
        "session_id": str(session.id),
        "quote_number": step1.quote_number,
        "job_number": step1.job_number,
        "formula_source": calc.get("formula_source"),
        "xlsx_formula_version": calc.get("xlsx_formula_version"),
        "internal_notes": calc.get("internal_notes"),
    }


def build_client_view_from_session(
    session: CalculationSession,
    breakdown: CalculationBreakdown,
    step1: Step1Snapshot,
    step2: Step2Snapshot,
) -> dict:
    calc = _breakdown_to_dict(breakdown)
    client_calc = {k: v for k, v in calc.items() if k not in _CLIENT_HIDDEN_CALC_KEYS}
    labour_total = None
    if calc.get("labour"):
        labour_total = sum(Decimal(str(line.get("total", 0))) for line in calc["labour"])
    materials_total = None
    if calc.get("materials"):
        materials_total = sum(Decimal(str(line.get("total", 0))) for line in calc["materials"])
    combined_scope = "\n\n".join(
        block.scope.strip() for block in step2.works if block.scope and block.scope.strip()
    ) if step2.works else (step2.scope or "")
    return {
        "session_id": str(session.id),
        "quote_number": step1.quote_number,
        "job_number": step1.job_number,
        "client_name": step1.client_name,
        "property_address": step1.property_address,
        "scope": combined_scope or step2.scope,
        "labour_summary": {
            "labour_type": step2.labour_type,
            "number_of_engineers": step2.engineers,
            "labour_total": float(labour_total) if labour_total is not None else None,
        },
        "materials_summary": {
            "material_name": step2.material_name if step2.unit_cost > 0 else None,
            "sell_total": float(materials_total) if materials_total is not None else None,
        },
        "calculation": client_calc,
    }
