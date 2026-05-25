from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.exceptions import AppError
from app.engines.approval_engine import build_calculation_breakdown
from app.engines.calculation_engine import round_money
from app.engines.rules_engine import find_active_rule, rule_to_dict
from app.models.job import Job
from app.models.quote import Quote, QuoteCharge, QuoteLabour, QuoteMaterial, QuoteScopeItem
from app.models.support import CalculationSnapshot
from app.schemas.calculation import (
    CalculationBreakdown,
    CalculationFinalizeRequest,
    CalculationPreviewRequest,
    ChargeInput,
    LabourInput,
    MaterialInput,
)


def _quote_to_inputs(quote: Quote) -> tuple[list[LabourInput], list[MaterialInput], ChargeInput | None]:
    labour = [
        LabourInput(
            labour_type=item.labour_type,
            number_of_engineers=item.number_of_engineers,
            hours_on_site=item.hours_on_site,
            days_on_site=item.days_on_site,
            manual_override=item.manual_override,
            manual_rate=item.manual_rate,
            override_reason=item.override_reason,
            trade_id=item.trade_id,
        )
        for item in quote.labour_items
    ]
    materials = [
        MaterialInput(
            material_name=item.material_name,
            quantity=item.quantity,
            unit_cost=item.unit_cost,
            delivery_cost=item.delivery_cost,
            markup_type=item.markup_type,
            markup_value=item.markup_value,
            client_visible=item.client_visible,
        )
        for item in quote.material_items
    ]
    charges = None
    if quote.charges:
        c = quote.charges
        charges = ChargeInput(
            parking_required=c.parking_required,
            parking_type=c.parking_type,
            parking_rate_per_hour=c.parking_rate_per_hour,
            parking_hours=c.parking_hours,
            parking_fixed_amount=c.parking_fixed_amount,
            congestion_required=c.congestion_required,
            congestion_amount=c.congestion_amount,
            ulez_required=c.ulez_required,
            ulez_amount=c.ulez_amount,
            waste_disposal_required=c.waste_disposal_required,
            waste_disposal_amount=c.waste_disposal_amount,
            travel_charge=c.travel_charge,
            other_charge=c.other_charge,
            other_charge_reason=c.other_charge_reason,
        )
    return labour, materials, charges


def preview_calculation(db: Session, payload: CalculationPreviewRequest) -> CalculationBreakdown:
    client_id = payload.client_id
    trade_id = payload.trade_id
    quote_date = payload.quote_date or date.today()

    if payload.quote_id:
        quote = db.get(Quote, payload.quote_id)
        if quote is None:
            raise AppError("QUOTE_NOT_FOUND", "Quote not found", 404)
        job = db.get(Job, quote.job_id)
        client_id = client_id or (job.client_id if job else None)
        labour, materials, charges = _quote_to_inputs(quote)
        if payload.labour_items:
            labour = payload.labour_items
        if payload.material_items:
            materials = payload.material_items
        if payload.charges:
            charges = payload.charges
        if labour and labour[0].trade_id:
            trade_id = trade_id or labour[0].trade_id
    else:
        labour = payload.labour_items
        materials = payload.material_items
        charges = payload.charges
        if labour and labour[0].trade_id:
            trade_id = trade_id or labour[0].trade_id

    matched = find_active_rule(db, client_id, trade_id, quote_date)
    return build_calculation_breakdown(
        labour_items=labour,
        material_items=materials,
        charges=charges,
        matched_rule=matched,
        formula_version=settings.formula_version,
        internal_notes_context=payload.internal_notes_context,
    )


def finalize_calculation(db: Session, payload: CalculationFinalizeRequest, user_id: UUID) -> CalculationBreakdown:
    quote = db.scalar(
        select(Quote)
        .options(
            joinedload(Quote.labour_items),
            joinedload(Quote.material_items),
            joinedload(Quote.charges),
            joinedload(Quote.job),
        )
        .where(Quote.id == payload.quote_id)
    )
    if quote is None:
        raise AppError("QUOTE_NOT_FOUND", "Quote not found", 404)

    job = quote.job
    labour, materials, charges = _quote_to_inputs(quote)
    trade_id = labour[0].trade_id if labour else None
    matched = find_active_rule(db, job.client_id if job else None, trade_id, date.today())
    breakdown = build_calculation_breakdown(
        labour_items=labour,
        material_items=materials,
        charges=charges,
        matched_rule=matched,
        formula_version=settings.formula_version,
    )

    # Update labour/material line totals
    rule = matched.rule if matched else None
    if rule and rule.formula_source == "xlsx":
        for item, line in zip(quote.labour_items, breakdown.labour):
            item.rate_used = breakdown.labour_charge_to_client
            item.labour_total = line.total
        if breakdown.materials_parking_cc_charge and quote.material_items:
            base_total = sum(
                round_money(item.quantity * item.unit_cost + item.delivery_cost) for item in quote.material_items
            )
            remaining = breakdown.materials_parking_cc_charge
            for index, item in enumerate(quote.material_items):
                base = round_money(item.quantity * item.unit_cost + item.delivery_cost)
                if index == len(quote.material_items) - 1:
                    sell = remaining
                else:
                    share = breakdown.materials_parking_cc_charge * (base / base_total if base_total else Decimal("1"))
                    sell = round_money(share)
                    remaining -= sell
                item.base_cost = base
                item.markup_total = round_money(sell - base)
                item.sell_total = sell
        if quote.charges:
            quote.charges.parking_total = Decimal("0")
        if breakdown.internal_notes:
            quote.internal_notes = breakdown.internal_notes
    elif matched:
        from app.engines.calculation_engine import calculate_labour, calculate_material

        rule = matched.rule
        for item, line in zip(quote.labour_items, breakdown.labour):
            result = calculate_labour(
                labour_type=item.labour_type,
                engineers=item.number_of_engineers,
                hours=item.hours_on_site,
                days=item.days_on_site,
                hourly_rate=rule.hourly_rate,
                half_day_rate=rule.half_day_rate,
                day_rate=rule.day_rate,
                minimum_hours=rule.minimum_hours,
                minimum_charge=rule.minimum_charge,
                manual_override=item.manual_override,
                manual_rate=item.manual_rate,
            )
            item.rate_used = result.rate_used
            item.labour_total = result.total

        for item in quote.material_items:
            result = calculate_material(
                quantity=item.quantity,
                unit_cost=item.unit_cost,
                delivery_cost=item.delivery_cost,
                markup_type=item.markup_type,
                markup_value=item.markup_value,
                rule_markup_type=rule.material_markup_type,
                rule_markup_value=rule.material_markup_value,
            )
            item.base_cost = result.base_cost
            item.markup_total = result.markup_total
            item.sell_total = result.sell_total

        if quote.charges and breakdown.charges:
            quote.charges.parking_total = next(
                (c.total for c in breakdown.charges if c.label == "Parking"), Decimal("0")
            )

    quote.subtotal = breakdown.subtotal
    quote.vat_rate = breakdown.vat_rate
    quote.vat_total = breakdown.vat_total
    quote.final_total = breakdown.final_total
    quote.margin_total = breakdown.margin_total
    quote.rule_version = breakdown.rule_version
    quote.formula_version = breakdown.xlsx_formula_version or breakdown.formula_version
    quote.status = "needs_approval" if breakdown.approval_required else "calculated"

    snapshot = CalculationSnapshot(
        quote_id=quote.id,
        input_snapshot={
            "labour": [l.model_dump(mode="json") for l in labour],
            "materials": [m.model_dump(mode="json") for m in materials],
            "charges": charges.model_dump(mode="json") if charges else None,
        },
        rule_snapshot=rule_to_dict(matched.rule) if matched else {},
        output_snapshot=breakdown.model_dump(mode="json"),
        calculated_by=user_id,
    )
    db.add(snapshot)
    db.flush()
    return breakdown
