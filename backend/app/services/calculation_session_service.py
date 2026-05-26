from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppError
from app.models.calculation_session import CalculationSession
from app.schemas.calculation import CalculationBreakdown, CalculationPreviewRequest
from app.schemas.eworks_link import (
    AggregatedQuoteSummary,
    CalculateSessionResponse,
    CalculationSessionRead,
    ResolvedRuleInfo,
    SessionUiState,
    SkillGroupBreakdown,
    Step1Snapshot,
    Step2Snapshot,
    UpdateCalculationSessionRequest,
    WorkBreakdownResult,
    aggregate_work_charges,
    step2_to_calculation_inputs,
)
from app.services.calculation_aggregate_service import (
    aggregate_work_blocks,
    aggregated_quote_summary,
    build_combined_calculation_inputs,
    build_combined_internal_notes_context,
    build_combined_material_inputs,
    build_skill_group_labour_inputs,
    group_works_by_skill,
)
from app.services.calculation_service import preview_calculation
from app.services.calculation_view_service import (
    build_client_view_from_session,
    build_internal_notes_from_breakdown,
    build_internal_view_from_session,
)
from app.services.eworks_link_service import (
    collect_work_skills,
    get_session_by_token,
    resolve_skill_trade,
    skills_are_uniform,
)
from app.services.eworks_questionnaire_service import build_internal_notes_context, work_block_to_step2_snapshot
from app.services.idempotency_service import check_idempotency, hash_payload, store_idempotency
from app.engines.rules_engine import find_active_rule


def _resolved_from_session(session: CalculationSession, rule) -> ResolvedRuleInfo:
    return ResolvedRuleInfo(
        client_id=session.client_id,
        trade_id=session.trade_id,
        rule_id=session.rate_rule_id,
        rule_version=rule.version if rule else "",
        formula_source=rule.formula_source if rule else "",
        xlsx_client_name=rule.xlsx_client_name if rule else None,
        xlsx_trade_name=rule.xlsx_trade_name if rule else None,
    )


def _validate_work_block(step2: Step2Snapshot, work_index: int) -> None:
    if not step2.works:
        raise AppError("WORKS_REQUIRED", "At least one work block is required", 400)
    if work_index < 0 or work_index >= len(step2.works):
        raise AppError("WORK_INDEX_INVALID", "Invalid work index", 400)
    block = step2.works[work_index]
    work_step2 = work_block_to_step2_snapshot(block, trade_name="")
    if not block.scope or not block.scope.strip():
        raise AppError("SCOPE_REQUIRED", f"Scope of works is required for work {work_index + 1}", 400)
    if not work_step2.time_frame and work_step2.hours <= 0 and work_step2.days <= 0:
        raise AppError("TIMEFRAME_REQUIRED", f"Time frame is required for work {work_index + 1}", 400)
    if block.engineers_required and block.engineers_needed < 1:
        raise AppError("ENGINEERS_REQUIRED", f"Engineers needed must be at least 1 for work {work_index + 1}", 400)


def _session_ui_state(session: CalculationSession) -> SessionUiState | None:
    if not session.ui_state:
        return None
    return SessionUiState.model_validate(session.ui_state)


def update_session_step2(
    db: Session,
    *,
    session_id: UUID,
    session_token: str,
    payload: UpdateCalculationSessionRequest,
    idempotency_key: str | None = None,
) -> CalculationSessionRead:
    request_body = payload.model_dump(mode="json", exclude_none=True)
    if idempotency_key:
        replay = check_idempotency(db, key=idempotency_key, request_hash=hash_payload(request_body))
        if replay is not None:
            return CalculationSessionRead.model_validate(replay.payload)

    session = get_session_by_token(db, session_id, session_token)
    if payload.step2 is not None:
        session.step2_snapshot = payload.step2.model_dump(mode="json")
    if payload.ui_state is not None:
        session.ui_state = payload.ui_state.model_dump(mode="json")
    if payload.step2 is None and payload.ui_state is None:
        raise AppError("EMPTY_UPDATE", "Nothing to update", 400)
    db.flush()
    from app.models.rate_rule import RateRule

    rule = db.get(RateRule, session.rate_rule_id)
    step1 = Step1Snapshot.model_validate(session.step1_snapshot)
    step2 = Step2Snapshot.model_validate(session.step2_snapshot) if session.step2_snapshot else None
    result = CalculationSessionRead(
        session_id=session.id,
        step1=step1,
        step2=step2,
        resolved=_resolved_from_session(session, rule),
        expires_at=session.expires_at,
        ui_state=_session_ui_state(session),
    )
    if idempotency_key:
        store_idempotency(
            db,
            key=idempotency_key,
            request_hash=hash_payload(request_body),
            response_payload=result.model_dump(mode="json"),
            expires_at=session.expires_at,
        )
    return result


async def add_session_attachment(
    db: Session,
    *,
    session_id: UUID,
    session_token: str,
    upload,
    work_index: int = 0,
):
    from app.schemas.eworks_link import SessionAttachmentMeta, Step2Snapshot
    from app.services.eworks_attachment_service import save_session_attachment

    session = get_session_by_token(db, session_id, session_token)
    attachment = await save_session_attachment(session_id, upload)
    step2 = Step2Snapshot.model_validate(session.step2_snapshot) if session.step2_snapshot else Step2Snapshot()
    if not step2.works:
        step2 = Step2Snapshot.model_validate({"scope": step2.scope, **step2.model_dump()})
    _validate_work_block(step2, work_index)
    block = step2.works[work_index]
    block.attachments = [*block.attachments, attachment]
    step2.works[work_index] = block
    session.step2_snapshot = step2.model_dump(mode="json")
    db.flush()
    return attachment


def _merge_skill_group_breakdowns(
    groups: list[SkillGroupBreakdown],
    *,
    vat_rate,
    formula_version: str,
    formula_source: str | None = None,
    xlsx_formula_version: str | None = None,
):
    """Merge per-skill-group breakdowns into a single combined CalculationBreakdown."""
    from decimal import Decimal
    from app.engines.calculation_engine import calculate_vat, round_money
    from app.schemas.calculation import CalculationBreakdown, LineBreakdown

    labour_lines: list[LineBreakdown] = []
    labour_charge = Decimal("0")
    direct_labour_cost = Decimal("0")
    profit_gbp = Decimal("0")
    materials_lines: list[LineBreakdown] = []
    charges_lines: list[LineBreakdown] = []
    materials_charge = Decimal("0")
    passthrough = Decimal("0")
    internal_notes_parts: list[str] = []

    for group in groups:
        bd = group.breakdown
        for line in bd.labour:
            labour_lines.append(LineBreakdown(label=f"{group.skill}: {line.label}", formula=line.formula, total=line.total))
        if bd.labour_charge_to_client:
            labour_charge += bd.labour_charge_to_client
        if bd.direct_labour_cost:
            direct_labour_cost += bd.direct_labour_cost
        if bd.profit_gbp:
            profit_gbp += bd.profit_gbp
        for line in bd.materials:
            materials_lines.append(line)
        if bd.materials_parking_cc_charge:
            materials_charge += bd.materials_parking_cc_charge
        for line in bd.charges:
            charges_lines.append(line)
            passthrough += line.total
        if bd.internal_notes:
            internal_notes_parts.append(f"--- {group.skill} ---\n{bd.internal_notes}")

    subtotal = round_money(labour_charge + materials_charge + passthrough)
    vat_total = calculate_vat(subtotal, vat_rate)
    final_total = round_money(subtotal + vat_total)

    return CalculationBreakdown(
        labour=labour_lines,
        materials=materials_lines,
        charges=charges_lines,
        subtotal=subtotal,
        vat_rate=vat_rate,
        vat_total=vat_total,
        final_total=final_total,
        formula_version=formula_version,
        formula_source=formula_source,
        xlsx_formula_version=xlsx_formula_version,
        direct_labour_cost=direct_labour_cost or None,
        labour_charge_to_client=labour_charge or None,
        materials_parking_cc_charge=materials_charge or None,
        profit_gbp=profit_gbp or None,
        internal_notes="\n\n".join(internal_notes_parts) if internal_notes_parts else None,
    )


def calculate_session(
    db: Session,
    *,
    session_id: UUID,
    session_token: str,
    step2: Step2Snapshot | None = None,
    idempotency_key: str | None = None,
) -> CalculateSessionResponse:
    request_body = {"step2": step2.model_dump(mode="json") if step2 else None}
    if idempotency_key:
        replay = check_idempotency(db, key=idempotency_key, request_hash=hash_payload(request_body))
        if replay is not None:
            return CalculateSessionResponse.model_validate(replay.payload)

    session = get_session_by_token(db, session_id, session_token)
    if step2 is not None:
        session.step2_snapshot = step2.model_dump(mode="json")
    if not session.step2_snapshot:
        raise AppError("STEP2_REQUIRED", "Estimator inputs are required before calculation", 400)

    step1 = Step1Snapshot.model_validate(session.step1_snapshot)
    step2_data = Step2Snapshot.model_validate(session.step2_snapshot)
    if not step2_data.works:
        step2_data = Step2Snapshot.model_validate(session.step2_snapshot)

    for index in range(len(step2_data.works)):
        block = step2_data.works[index]
        if not block.findings and step1.findings_report:
            block = block.model_copy(update={"findings": step1.findings_report})
            step2_data.works[index] = block
        _validate_work_block(step2_data, index)

    charges = aggregate_work_charges(step1, step2_data.works)
    single_work = len(step2_data.works) == 1
    work_skills = collect_work_skills(step2_data.works, step1.trade_name)
    uniform_skills = skills_are_uniform(step2_data.works, step1.trade_name)

    matched = find_active_rule(db, session.client_id, session.trade_id, None)
    rule = matched.rule if matched else None
    from decimal import Decimal

    vat_rate = rule.vat_rate if rule else Decimal("20")
    formula_source = rule.formula_source if rule else None
    xlsx_formula_version = settings.xlsx_formula_version if rule and rule.formula_source == "xlsx" else None

    work_results: list[WorkBreakdownResult] = []
    for index, block in enumerate(step2_data.works):
        work_trade = resolve_skill_trade(db, block.skill_required, fallback_trade_name=step1.trade_name)
        work_step2 = work_block_to_step2_snapshot(block, trade_name=step1.trade_name)
        labour, materials, _ = step2_to_calculation_inputs(
            step1,
            work_step2,
            trade_id=work_trade.id,
            include_charges=False,
        )
        # Each work block uses its own charges so parking/CC set per-work appear in that work's breakdown.
        work_charges = aggregate_work_charges(step1, [block])
        breakdown = preview_calculation(
            db,
            CalculationPreviewRequest(
                client_id=session.client_id,
                trade_id=work_trade.id,
                labour_items=labour,
                material_items=materials,
                charges=work_charges,
                internal_notes_context=build_internal_notes_context(step1, block),
            ),
        )
        work_results.append(
            WorkBreakdownResult(
                work_index=index,
                scope=block.scope,
                breakdown=breakdown,
                internal_notes=breakdown.internal_notes,
            )
        )

    skill_group_results: list[SkillGroupBreakdown] = []

    if single_work:
        breakdown = work_results[0].breakdown
        aggregated_summary_payload: AggregatedQuoteSummary | None = None
    elif uniform_skills:
        combined_trade_id = resolve_skill_trade(db, work_skills[0], fallback_trade_name=step1.trade_name).id
        labour, materials, combined_charges, aggregated = build_combined_calculation_inputs(
            step1,
            step2_data,
            trade_id=combined_trade_id,
        )
        breakdown = preview_calculation(
            db,
            CalculationPreviewRequest(
                client_id=session.client_id,
                trade_id=combined_trade_id,
                labour_items=labour,
                material_items=materials,
                charges=combined_charges,
                internal_notes_context=build_combined_internal_notes_context(step1, step2_data.works),
            ),
        )
        aggregated_summary_payload = AggregatedQuoteSummary.model_validate(
            aggregated_quote_summary(aggregated, len(step2_data.works), skills=work_skills)
        )
    else:
        # Group works by skill — compute one combined breakdown per trade group.
        skill_group_results: list[SkillGroupBreakdown] = []
        for skill, group_works in group_works_by_skill(step2_data.works, step1.trade_name):
            trade = resolve_skill_trade(db, skill, fallback_trade_name=step1.trade_name)
            group_charges = aggregate_work_charges(step1, group_works)
            group_labour, _group_agg = build_skill_group_labour_inputs(group_works, trade_id=trade.id)
            group_materials = build_combined_material_inputs(step1, Step2Snapshot(works=group_works))
            group_breakdown = preview_calculation(
                db,
                CalculationPreviewRequest(
                    client_id=session.client_id,
                    trade_id=trade.id,
                    labour_items=group_labour,
                    material_items=group_materials,
                    charges=group_charges,
                    internal_notes_context=build_combined_internal_notes_context(step1, group_works),
                ),
            )
            skill_group_results.append(SkillGroupBreakdown(skill=skill, breakdown=group_breakdown))

        breakdown = _merge_skill_group_breakdowns(
            skill_group_results,
            vat_rate=vat_rate,
            formula_version=settings.formula_version,
            formula_source=formula_source,
            xlsx_formula_version=xlsx_formula_version,
        )
        aggregated = aggregate_work_blocks(step2_data.works)
        aggregated_summary_payload = AggregatedQuoteSummary.model_validate(
            aggregated_quote_summary(aggregated, len(step2_data.works), skills=work_skills)
        )

    primary_step2 = work_block_to_step2_snapshot(step2_data.works[0], trade_name=step1.trade_name)
    combined_scope = "\n\n".join(
        block.scope.strip() for block in step2_data.works if block.scope and block.scope.strip()
    )
    primary_step2 = primary_step2.model_copy(update={"scope": combined_scope})

    internal_view = build_internal_view_from_session(session, breakdown, primary_step2)
    internal_view["work_breakdowns"] = [
        {
            "work_index": item.work_index,
            "scope": item.scope,
            "breakdown": item.breakdown.model_dump(mode="json"),
            "internal_notes": item.internal_notes,
        }
        for item in work_results
    ]
    client_view = build_client_view_from_session(session, breakdown, step1, primary_step2)
    client_view["work_count"] = len(step2_data.works)
    notes = build_internal_notes_from_breakdown(session, breakdown)

    session.ui_state = SessionUiState(
        current_step=3,
        max_reachable_step=3,
        last_result=CalculateSessionResponse(
            breakdown=breakdown,
            work_breakdowns=work_results,
            aggregated_summary=aggregated_summary_payload,
            skill_group_breakdowns=skill_group_results,
            internal_view=internal_view,
            internal_notes=notes.get("internal_notes"),
            client_view=client_view,
        ).model_dump(mode="json"),
    ).model_dump(mode="json")
    db.flush()

    result = CalculateSessionResponse(
        breakdown=breakdown,
        work_breakdowns=work_results,
        aggregated_summary=aggregated_summary_payload,
        skill_group_breakdowns=skill_group_results,
        internal_view=internal_view,
        internal_notes=notes.get("internal_notes"),
        client_view=client_view,
    )
    if idempotency_key:
        store_idempotency(
            db,
            key=idempotency_key,
            request_hash=hash_payload(request_body),
            response_payload=result.model_dump(mode="json"),
            expires_at=session.expires_at,
        )
    return result
