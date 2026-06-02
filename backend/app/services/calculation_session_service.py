from datetime import datetime, timezone
from decimal import Decimal
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
    CombineWorkNotesResponse,
    DashboardQuoteItem,
    DashboardQuotesResponse,
    DashboardWorkItem,
    ReopenQuoteResponse,
    ResolvedRuleInfo,
    SessionUiState,
    SkillGroupBreakdown,
    Step1Snapshot,
    Step2Snapshot,
    UpdateCalculationSessionRequest,
    WorkBlockSnapshot,
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
    build_resolved_rule_info,
    client_has_trade_rate_rule,
    collect_work_skills,
    get_session_by_token,
    resolve_skill_trade,
    session_eworks_client_fee_pct,
    try_resolve_rate_rule,
    skills_are_uniform,
    work_skill_name,
)
from app.services.eworks_questionnaire_service import (
    build_internal_notes_context,
    format_links_and_quantity,
    work_block_to_step2_snapshot,
)
from app.services.idempotency_service import check_idempotency, hash_payload, store_idempotency
from app.engines.rules_engine import find_active_rule


def _eworks_preview_request(
    db: Session,
    *,
    session: CalculationSession,
    step1: Step1Snapshot,
    trade_id: UUID,
    labour_items: list,
    material_items: list,
    charges,
    internal_notes_context,
) -> CalculationPreviewRequest:
    kwargs: dict = {
        "client_id": session.client_id,
        "trade_id": trade_id,
        "labour_items": labour_items,
        "material_items": material_items,
        "charges": charges,
        "internal_notes_context": internal_notes_context,
    }
    if not client_has_trade_rate_rule(db, session.client_id, trade_id):
        kwargs["calculation_client_name"] = step1.client_name
        eworks_fee = session_eworks_client_fee_pct(session)
        kwargs["client_fee_pct_override"] = eworks_fee if eworks_fee is not None else Decimal("0")
    return CalculationPreviewRequest(**kwargs)


def _resolved_from_session(db: Session, session: CalculationSession) -> ResolvedRuleInfo:
    from app.models.client import Client
    from app.models.rate_rule import RateRule
    from app.models.trade import Trade

    step1 = Step1Snapshot.model_validate(session.step1_snapshot)
    rule = db.get(RateRule, session.rate_rule_id) if session.rate_rule_id else None
    if rule is None and session.client_id and session.trade_id:
        rule = try_resolve_rate_rule(db, session.client_id, session.trade_id)
    client = db.get(Client, session.client_id)
    trade = db.get(Trade, session.trade_id)
    if client is None or trade is None:
        raise AppError("SESSION_INVALID", "Calculation session is missing client or trade", 500)
    return build_resolved_rule_info(
        client,
        trade,
        rule,
        link_client_name=step1.client_name,
        eworks_client_fee_pct=session_eworks_client_fee_pct(session) if rule is None else None,
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


def _work_subtotals_from_breakdown(breakdown: dict):
    from decimal import Decimal

    labour_lines = breakdown.get("labour") or []
    materials_lines = breakdown.get("materials") or []
    labour_subtotal = sum(Decimal(str(line["total"])) for line in labour_lines) if labour_lines else None
    materials_subtotal = sum(Decimal(str(line["total"])) for line in materials_lines) if materials_lines else None
    if labour_subtotal is None and breakdown.get("labour_charge_to_client") is not None:
        labour_subtotal = Decimal(str(breakdown["labour_charge_to_client"]))
    if materials_subtotal is None and breakdown.get("materials_parking_cc_charge") is not None:
        materials_subtotal = Decimal(str(breakdown["materials_parking_cc_charge"]))
    return labour_subtotal, materials_subtotal


def _dashboard_last_result(db: Session, session: CalculationSession) -> dict | None:
    ui_state = _session_ui_state(session)
    last_result = ui_state.last_result if ui_state else None
    if isinstance(last_result, dict):
        breakdown = last_result.get("breakdown") or {}
        if last_result.get("work_breakdowns") and breakdown.get("final_total") is not None:
            return last_result
    if not session.step2_snapshot:
        return None
    calc = calculate_session(db, session_id=session.id, session_token=session.session_token, step2=None)
    return calc.model_dump(mode="json")


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
        if session.status == "submitted":
            raise AppError("SESSION_SUBMITTED", "Cannot update questionnaire after submission", 409)
        session.step2_snapshot = payload.step2.model_dump(mode="json")
    if payload.findings_report is not None:
        current_step1 = dict(session.step1_snapshot or {})
        current_step1["findings_report"] = payload.findings_report
        session.step1_snapshot = current_step1
    if payload.ui_state is not None:
        existing_ui_state = _session_ui_state(session)
        merged_ui_state = payload.ui_state.model_dump(mode="json")
        if existing_ui_state and existing_ui_state.last_result is not None and merged_ui_state.get("last_result") is None:
            merged_ui_state["last_result"] = existing_ui_state.last_result
        session.ui_state = merged_ui_state
    if payload.step2 is None and payload.ui_state is None and payload.findings_report is None:
        raise AppError("EMPTY_UPDATE", "Nothing to update", 400)
    db.flush()
    step1 = Step1Snapshot.model_validate(session.step1_snapshot)
    step2 = Step2Snapshot.model_validate(session.step2_snapshot) if session.step2_snapshot else None
    result = CalculationSessionRead(
        session_id=session.id,
        step1=step1,
        step2=step2,
        resolved=_resolved_from_session(db, session),
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


def _find_attachment_in_step2(step2: Step2Snapshot, attachment_id: str):
    from app.schemas.eworks_link import SessionAttachmentMeta

    for work_index, block in enumerate(step2.works):
        for attachment in block.attachments:
            if attachment.id == attachment_id:
                return work_index, attachment
    for attachment in step2.attachments:
        if attachment.id == attachment_id:
            return None, SessionAttachmentMeta.model_validate(attachment)
    return None, None


def get_session_attachment_meta(db: Session, session_id: UUID, attachment_id: str):
    from app.schemas.eworks_link import SessionAttachmentMeta, Step2Snapshot

    session = db.get(CalculationSession, session_id)
    if not session or not session.step2_snapshot:
        raise AppError("ATTACHMENT_NOT_FOUND", "Attachment not found", 404)
    step2 = Step2Snapshot.model_validate(session.step2_snapshot)
    _, attachment = _find_attachment_in_step2(step2, attachment_id)
    if attachment is None:
        raise AppError("ATTACHMENT_NOT_FOUND", "Attachment not found", 404)
    return SessionAttachmentMeta.model_validate(attachment)


async def delete_session_attachment(
    db: Session,
    *,
    session_id: UUID,
    session_token: str,
    attachment_id: str,
) -> None:
    from app.schemas.eworks_link import Step2Snapshot
    from app.services.eworks_attachment_service import delete_stored_attachment

    session = get_session_by_token(db, session_id, session_token)
    if not session.step2_snapshot:
        raise AppError("ATTACHMENT_NOT_FOUND", "Attachment not found", 404)

    step2 = Step2Snapshot.model_validate(session.step2_snapshot)
    work_index, attachment = _find_attachment_in_step2(step2, attachment_id)
    if attachment is None:
        raise AppError("ATTACHMENT_NOT_FOUND", "Attachment not found", 404)

    await delete_stored_attachment(session_id, attachment.stored_name)

    if work_index is not None:
        block = step2.works[work_index]
        block.attachments = [item for item in block.attachments if item.id != attachment_id]
        step2.works[work_index] = block
    else:
        step2.attachments = [item for item in step2.attachments if item.id != attachment_id]

    session.step2_snapshot = step2.model_dump(mode="json")
    db.flush()


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
            _eworks_preview_request(
                db,
                session=session,
                step1=step1,
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
            _eworks_preview_request(
                db,
                session=session,
                step1=step1,
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
                _eworks_preview_request(
                    db,
                    session=session,
                    step1=step1,
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


def _merge_step2_attachments(existing: Step2Snapshot | None, incoming: Step2Snapshot) -> Step2Snapshot:
    if not existing or not existing.works:
        return incoming
    merged_works = []
    for index, block in enumerate(incoming.works):
        if index < len(existing.works) and existing.works[index].attachments and not block.attachments:
            block = block.model_copy(update={"attachments": existing.works[index].attachments})
        merged_works.append(block)
    return incoming.model_copy(update={"works": merged_works})


def submit_session(
    db: Session,
    *,
    session_id: UUID,
    session_token: str,
    step2: Step2Snapshot | None = None,
    idempotency_key: str | None = None,
) -> None:
    session = get_session_by_token(db, session_id, session_token)
    existing_step2 = Step2Snapshot.model_validate(session.step2_snapshot) if session.step2_snapshot else None
    merged_step2 = _merge_step2_attachments(existing_step2, step2) if step2 is not None else step2
    calculate_session(
        db,
        session_id=session_id,
        session_token=session_token,
        step2=merged_step2,
        idempotency_key=idempotency_key,
    )
    session = get_session_by_token(db, session_id, session_token)
    session.status = "submitted"
    session.submitted_at = datetime.now(timezone.utc)
    db.flush()


def list_submitted_quotes(db: Session) -> DashboardQuotesResponse:
    from decimal import Decimal

    from sqlalchemy import select

    from app.models.calculation_session import CalculationSession

    sessions = db.scalars(
        select(CalculationSession)
        .where(CalculationSession.status == "submitted")
        .order_by(CalculationSession.submitted_at.desc())
    ).all()

    quotes: list[DashboardQuoteItem] = []
    for session in sessions:
        if not session.submitted_at:
            continue
        step1 = Step1Snapshot.model_validate(session.step1_snapshot)
        step2 = Step2Snapshot.model_validate(session.step2_snapshot) if session.step2_snapshot else Step2Snapshot()
        last_result = _dashboard_last_result(db, session)
        work_breakdowns = last_result.get("work_breakdowns", []) if last_result else []
        breakdown_map = {item["work_index"]: item for item in work_breakdowns}

        final_total = None
        internal_notes = None
        if last_result:
            breakdown = last_result.get("breakdown") or {}
            if breakdown.get("final_total") is not None:
                final_total = Decimal(str(breakdown["final_total"]))
            internal_notes = last_result.get("internal_notes")

        works: list[DashboardWorkItem] = []
        for index, block in enumerate(step2.works):
            work_result = breakdown_map.get(index, {})
            breakdown = work_result.get("breakdown") or {}
            labour_subtotal, materials_subtotal = _work_subtotals_from_breakdown(breakdown)
            work_internal_notes = work_result.get("internal_notes")
            if not work_internal_notes and len(step2.works) == 1:
                work_internal_notes = internal_notes
            works.append(
                DashboardWorkItem(
                    work_index=index,
                    scope=block.scope,
                    labour_subtotal=labour_subtotal,
                    materials_subtotal=materials_subtotal,
                    internal_notes=work_internal_notes,
                    attachments=block.attachments,
                    details=block,
                )
            )

        quotes.append(
            DashboardQuoteItem(
                session_id=session.id,
                session_token=session.session_token,
                quote_number=step1.quote_number,
                job_number=step1.job_number,
                client_name=step1.client_name,
                trade_name=step1.trade_name,
                submitted_at=session.submitted_at,
                final_total=final_total,
                internal_notes=internal_notes,
                works=works,
            )
        )

    return DashboardQuotesResponse(quotes=quotes)


def _preview_internal_notes_for_works(
    db: Session,
    *,
    session: CalculationSession,
    step1: Step1Snapshot,
    blocks: list[WorkBlockSnapshot],
    skill: str,
) -> str:
    trade = resolve_skill_trade(db, skill, fallback_trade_name=step1.trade_name)
    if len(blocks) == 1:
        block = blocks[0]
        work_step2 = work_block_to_step2_snapshot(block, trade_name=step1.trade_name)
        labour, materials, _ = step2_to_calculation_inputs(
            step1,
            work_step2,
            trade_id=trade.id,
            include_charges=False,
        )
        work_charges = aggregate_work_charges(step1, [block])
        breakdown = preview_calculation(
            db,
            _eworks_preview_request(
                db,
                session=session,
                step1=step1,
                trade_id=trade.id,
                labour_items=labour,
                material_items=materials,
                charges=work_charges,
                internal_notes_context=build_internal_notes_context(step1, block),
            ),
        )
        return breakdown.internal_notes or ""

    labour, materials, combined_charges, _ = build_combined_calculation_inputs(
        step1,
        Step2Snapshot(works=blocks),
        trade_id=trade.id,
    )
    breakdown = preview_calculation(
        db,
        _eworks_preview_request(
            db,
            session=session,
            step1=step1,
            trade_id=trade.id,
            labour_items=labour,
            material_items=materials,
            charges=combined_charges,
            internal_notes_context=build_combined_internal_notes_context(step1, blocks),
        ),
    )
    return breakdown.internal_notes or ""


def combine_selected_work_internal_notes(
    db: Session,
    *,
    session_id: UUID,
    work_indexes: list[int],
) -> CombineWorkNotesResponse:
    from app.models.calculation_session import CalculationSession

    session = db.get(CalculationSession, session_id)
    if session is None:
        raise AppError("SESSION_NOT_FOUND", "Quote session not found", 404)
    if not session.step2_snapshot:
        raise AppError("STEP2_REQUIRED", "No saved work data for this quote", 400)

    step1 = Step1Snapshot.model_validate(session.step1_snapshot)
    step2 = Step2Snapshot.model_validate(session.step2_snapshot)
    if not step2.works:
        raise AppError("WORKS_REQUIRED", "No works found for this quote", 400)

    unique_indexes = sorted({index for index in work_indexes})
    selected: list[tuple[int, WorkBlockSnapshot]] = []
    for index in unique_indexes:
        if index < 0 or index >= len(step2.works):
            raise AppError("WORK_INDEX_INVALID", f"Invalid work index: {index}", 400)
        selected.append((index, step2.works[index]))

    skill_to_items: dict[str, list[tuple[int, WorkBlockSnapshot]]] = {}
    skill_order: list[str] = []
    for index, block in selected:
        skill = work_skill_name(block, step1.trade_name)
        if skill not in skill_to_items:
            skill_to_items[skill] = []
            skill_order.append(skill)
        skill_to_items[skill].append((index, block))

    distinct_skills = len(skill_order)
    sections: list[tuple[int, str]] = []
    for skill in skill_order:
        items = skill_to_items[skill]
        blocks = [block for _, block in items]
        indexes = [index for index, _ in items]
        sort_key = min(indexes)
        notes = _preview_internal_notes_for_works(
            db,
            session=session,
            step1=step1,
            blocks=blocks,
            skill=skill,
        )
        note_text = notes or "(no internal notes)"
        if len(blocks) > 1 or distinct_skills == 1:
            sections.append((sort_key, note_text))
        else:
            sections.append((sort_key, f"Work {indexes[0] + 1}:\n{note_text}"))

    sections.sort(key=lambda item: item[0])
    header = f"Quote {step1.quote_number} · Job {step1.job_number} — {step1.client_name}"
    body = "\n\n".join(section for _, section in sections)
    return CombineWorkNotesResponse(
        quote_number=step1.quote_number,
        job_number=step1.job_number,
        client_name=step1.client_name,
        internal_notes=f"{header}\n\n{body}",
    )


def _format_gbp(value: Decimal | float | int | None) -> str:
    amount = Decimal(str(value or 0)).quantize(Decimal("0.01"))
    return f"£{amount:,.2f}"


def _format_pct(value: Decimal | float | int | None) -> str:
    amount = Decimal(str(value or 0)).quantize(Decimal("0.01"))
    return f"{amount:,.2f}%"


def _format_property_manager(step1: Step1Snapshot) -> str:
    name = (step1.property_manager_name or "").strip()
    if not name:
        return "—"
    if "property manager" in name.lower():
        return name
    return f"{name} (Property Manager)"


def _build_report_notes(step1: Step1Snapshot) -> str:
    custom = (step1.findings_report or step1.quote_description or "").strip()
    if custom:
        return custom
    return (
        "We attended the above address to undertake a visual inspection for quoting purposes.\n\n"
        "We reviewed the reported observations and have prepared the following recommended scope of works.\n\n"
        "We would recommend that the following scope of works are undertaken."
    )


def _breakdown_for_work_block(
    db: Session,
    *,
    session: CalculationSession,
    step1: Step1Snapshot,
    block: WorkBlockSnapshot,
) -> CalculationBreakdown:
    skill = work_skill_name(block, step1.trade_name)
    trade = resolve_skill_trade(db, skill, fallback_trade_name=step1.trade_name)
    work_step2 = work_block_to_step2_snapshot(block, trade_name=step1.trade_name)
    labour, materials, _ = step2_to_calculation_inputs(
        step1,
        work_step2,
        trade_id=trade.id,
        include_charges=False,
    )
    work_charges = aggregate_work_charges(step1, [block])
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
            internal_notes_context=build_internal_notes_context(step1, block),
        ),
    )


def _work_item_row(
    *,
    display_index: int,
    block: WorkBlockSnapshot,
    step1: Step1Snapshot,
    breakdown: CalculationBreakdown,
) -> dict:
    material_rows = [*block.materials_to_order, *block.shelf_materials_rows]
    materials_link = format_links_and_quantity(material_rows)
    material_cost = sum((line.total for line in breakdown.materials), Decimal("0"))
    labour_charge = breakdown.labour_charge_to_client or Decimal("0")
    materials_charge = breakdown.materials_parking_cc_charge or Decimal("0")
    direct_labour = breakdown.direct_labour_cost or Decimal("0")
    client_price = breakdown.subtotal
    optimal_cost = direct_labour + material_cost
    profit_gbp = breakdown.profit_gbp if breakdown.profit_gbp is not None else (client_price - optimal_cost)
    margin_pct = breakdown.profit_pct
    if margin_pct is None and client_price > 0:
        margin_pct = (profit_gbp / client_price) * Decimal("100")

    scope_text = (block.scope or "").strip()
    description = scope_text.split("\n", 1)[0].strip() if scope_text else (step1.original_job_description or "Work item")
    findings = (block.findings or step1.findings_report or "").strip()
    notes_exclusions = (block.other_notes or "").strip()

    return {
        "index": display_index,
        "description": description,
        "findings": findings,
        "scope": scope_text,
        "notes_exclusions": notes_exclusions,
        "materials_link": materials_link,
        "qty": materials_link,
        "material_cost": _format_gbp(material_cost),
        "labour_charge": _format_gbp(labour_charge),
        "materials_charge": _format_gbp(materials_charge),
        "client_price": _format_gbp(client_price),
        "quoted_price": _format_gbp(client_price),
        "optimal_cost": _format_gbp(optimal_cost),
        "profit_gbp": _format_gbp(profit_gbp),
        "margin_pct": _format_pct(margin_pct),
        "internal_notes": (breakdown.internal_notes or "").strip(),
        "_subtotal": client_price,
        "_vat_total": breakdown.vat_total,
        "_grand_total": breakdown.final_total,
        "_material_cost": material_cost,
        "_labour_charge": labour_charge,
        "_materials_charge": materials_charge,
        "_optimal_cost": optimal_cost,
        "_profit_gbp": profit_gbp,
    }


def render_combined_works_pdf(
    db: Session,
    *,
    session_id: UUID,
    work_indexes: list[int],
    view_type: str,
) -> tuple[bytes, str, str]:
    from app.adapters.pdf_renderer import render_combined_works_document

    session = db.get(CalculationSession, session_id)
    if session is None:
        raise AppError("SESSION_NOT_FOUND", "Quote session not found", 404)
    if not session.step2_snapshot:
        raise AppError("STEP2_REQUIRED", "No saved work data for this quote", 400)
    if view_type not in {"client", "optimal"}:
        raise AppError("VIEW_TYPE_INVALID", "view_type must be 'client' or 'optimal'", 400)

    step1 = Step1Snapshot.model_validate(session.step1_snapshot)
    step2 = Step2Snapshot.model_validate(session.step2_snapshot)
    if not step2.works:
        raise AppError("WORKS_REQUIRED", "No works found for this quote", 400)

    unique_indexes = sorted({index for index in work_indexes})
    items: list[dict] = []
    subtotal = Decimal("0")
    vat_total = Decimal("0")
    grand_total = Decimal("0")
    total_material_cost = Decimal("0")
    total_labour_charge = Decimal("0")
    total_materials_charge = Decimal("0")
    total_optimal_cost = Decimal("0")
    total_profit = Decimal("0")

    for position, index in enumerate(unique_indexes, start=1):
        if index < 0 or index >= len(step2.works):
            raise AppError("WORK_INDEX_INVALID", f"Invalid work index: {index}", 400)
        block = step2.works[index]
        breakdown = _breakdown_for_work_block(db, session=session, step1=step1, block=block)
        row = _work_item_row(display_index=position, block=block, step1=step1, breakdown=breakdown)
        items.append({key: value for key, value in row.items() if not key.startswith("_")})
        subtotal += row["_subtotal"]
        vat_total += row["_vat_total"]
        grand_total += row["_grand_total"]
        total_material_cost += row["_material_cost"]
        total_labour_charge += row["_labour_charge"]
        total_materials_charge += row["_materials_charge"]
        total_optimal_cost += row["_optimal_cost"]
        total_profit += row["_profit_gbp"]

    overall_margin = (total_profit / subtotal * Decimal("100")) if subtotal > 0 else Decimal("0")
    generated_at = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")

    context = {
        "quote_number": step1.quote_number,
        "job_number": step1.job_number,
        "client_name": step1.client_name,
        "property_address": step1.property_address or "",
        "engineer_name": step1.engineer_name or "",
        "trade_name": step1.trade_name,
        "prepared_by": "The Optimal Group",
        "property_manager": _format_property_manager(step1),
        "total_items": len(items),
        "vat_label": "VAT + 20%",
        "document_title": "QUOTE SUMMARY" if view_type == "client" else "OPTIMAL QUOTE SUMMARY",
        "report_notes": _build_report_notes(step1),
        "subtotal": _format_gbp(subtotal),
        "vat_total": _format_gbp(vat_total),
        "grand_total": _format_gbp(grand_total),
        "generated_at": generated_at,
        "items": items,
        "cost_summary": {
            "material_cost": _format_gbp(total_material_cost),
            "labour_charge": _format_gbp(total_labour_charge),
            "materials_charge": _format_gbp(total_materials_charge),
            "client_price": _format_gbp(subtotal),
            "optimal_cost": _format_gbp(total_optimal_cost),
            "profit_gbp": _format_gbp(total_profit),
            "margin_pct": _format_pct(overall_margin),
        },
    }
    return render_combined_works_document(context, view_type=view_type)


def reopen_submitted_session(db: Session, *, session_id: UUID) -> ReopenQuoteResponse:
    session = db.get(CalculationSession, session_id)
    if session is None:
        raise AppError("SESSION_NOT_FOUND", "Quote session not found", 404)
    if session.status != "submitted":
        raise AppError("SESSION_NOT_SUBMITTED", "Only submitted quotes can be reopened for editing", 409)

    session.status = "in_progress"
    session.submitted_at = None
    session.ui_state = {
        "current_step": 1,
        "max_reachable_step": 1,
        "last_result": None,
    }
    db.flush()
    return ReopenQuoteResponse(session_id=session.id, session_token=session.session_token)
