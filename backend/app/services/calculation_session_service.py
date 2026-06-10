from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.utils.html_text import html_to_plain_text, prepare_pdf_rich_text
from app.utils.work_label import format_work_label
from app.core.config import settings
from app.core.exceptions import AppError
from app.models.calculation_session import CalculationSession
from app.schemas.calculation import CalculationBreakdown, CalculationPreviewRequest, ChargeInput
from app.schemas.dashboard_quote_groups import (
    DashboardQuoteGroupAssignmentItem,
    DashboardQuoteGroupAssignmentSubmissionRow,
    DashboardQuoteGroupAssignmentSummary,
    DashboardQuoteGroupDetailItem,
    DashboardQuoteGroupDetailResponse,
    DashboardQuoteGroupItem,
    DashboardQuoteGroupSessionDetailItem,
    DashboardQuoteGroupSessionItem,
    DashboardQuoteGroupVersionItem,
    DashboardQuoteGroupsResponse,
    DashboardSelectedEstimateDecision,
)
from app.schemas.eworks_link import (
    AggregatedQuoteSummary,
    CalculateSessionResponse,
    CalculationSessionRead,
    CombineWorkNotesResponse,
    DashboardQuoteItem,
    DashboardQuoteSummaryBreakdown,
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
    quote_additional_charge_lines,
    flatten_supplier_links,
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
    _uses_fallback_xlsx_fee,
    build_resolved_rule_info,
    client_has_trade_rate_rule,
    collect_work_skills,
    get_session_by_token,
    resolve_skill_trade,
    session_eworks_client_fee_pct,
    try_resolve_xlsx_rate_rule,
    skills_are_uniform,
    work_skill_name,
)
from app.services.eworks_questionnaire_service import (
    build_internal_notes_context,
    format_links_and_quantity,
    work_block_to_step2_snapshot,
)
from app.services.idempotency_service import check_idempotency, hash_payload, store_idempotency
from app.services.calculation_session_revision_service import (
    assert_session_editable,
    apply_submitter_to_session,
    complete_revision_submit,
    list_session_version_history,
)
from app.services.quote_acceptance_helpers import staff_acceptance_from_session
from app.engines.rules_engine import resolve_calculation_rule


def build_calculation_session_read(db: Session, session: CalculationSession) -> CalculationSessionRead:
    from app.services.quote_work_snapshot_service import resolve_shared_step2_for_session

    step1 = Step1Snapshot.model_validate(session.step1_snapshot)
    step2, shared_step2 = resolve_shared_step2_for_session(db, session)
    return CalculationSessionRead(
        session_id=session.id,
        step1=step1,
        step2=step2,
        shared_step2=shared_step2,
        resolved=_resolved_from_session(db, session),
        expires_at=session.expires_at,
        ui_state=_session_ui_state(session),
        status=session.status,
        locked=session.locked,
        revision_in_progress=session.revision_in_progress,
        active_revision_reason=session.active_revision_reason,
        current_version_number=session.current_version_number,
    )


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
    matched = try_resolve_xlsx_rate_rule(db, session.client_id, session.trade_id) if session.client_id and session.trade_id else None
    rule = db.get(RateRule, session.rate_rule_id) if session.rate_rule_id else None
    if rule is None and matched is not None:
        rule = matched.rule
    client = db.get(Client, session.client_id)
    trade = db.get(Trade, session.trade_id)
    if client is None or trade is None:
        raise AppError("SESSION_INVALID", "Calculation session is missing client or trade", 500)
    return build_resolved_rule_info(
        client,
        trade,
        rule,
        link_client_name=step1.client_name,
        eworks_client_fee_pct=session_eworks_client_fee_pct(session) if _uses_fallback_xlsx_fee(matched) else None,
    )


def _work_block_has_product_context(block: WorkBlockSnapshot) -> bool:
    if block.is_custom_scope:
        return bool((block.custom_title or "").strip())
    return (
        block.selected_product_id is not None
        or block.eworks_item_id is not None
        or bool((block.product_name or "").strip())
    )


def _merge_incoming_work_block_with_shared(
    incoming: WorkBlockSnapshot,
    shared: WorkBlockSnapshot | None,
) -> WorkBlockSnapshot:
    if shared is None or _work_block_has_product_context(incoming) or not _work_block_has_product_context(shared):
        return incoming
    updates: dict = {
        "selected_product_id": shared.selected_product_id,
        "is_custom_scope": shared.is_custom_scope,
        "custom_title": shared.custom_title,
        "eworks_item_id": shared.eworks_item_id,
        "product_name": shared.product_name,
        "product_code": shared.product_code,
        "product_quantity": shared.product_quantity,
        "product_unit_price": shared.product_unit_price,
        "product_total_price": shared.product_total_price,
        "scope_from_product": shared.scope_from_product,
    }
    if not (incoming.scope or "").strip():
        updates["scope"] = shared.scope
    return incoming.model_copy(update=updates)


def _merge_incoming_step2_with_shared(
    incoming: Step2Snapshot,
    shared: Step2Snapshot | None,
) -> Step2Snapshot:
    if shared is None or not shared.works:
        return incoming
    if not incoming.works:
        return incoming
    merged_works = [
        _merge_incoming_work_block_with_shared(
            block,
            shared.works[index] if index < len(shared.works) else None,
        )
        for index, block in enumerate(incoming.works)
    ]
    return incoming.model_copy(update={"works": merged_works})


def _validate_work_block(step2: Step2Snapshot, work_index: int) -> None:
    if not step2.works:
        raise AppError("WORKS_REQUIRED", "At least one work block is required", 400)
    if work_index < 0 or work_index >= len(step2.works):
        raise AppError("WORK_INDEX_INVALID", "Invalid work index", 400)
    block = step2.works[work_index]
    work_step2 = work_block_to_step2_snapshot(block, trade_name="")
    has_product = _work_block_has_product_context(block) and not block.is_custom_scope
    if block.is_custom_scope:
        if not (block.custom_title and block.custom_title.strip()):
            raise AppError(
                "CUSTOM_TITLE_REQUIRED",
                f"Custom product/scope title is required for work {work_index + 1}",
                400,
            )
        if not block.scope or not block.scope.strip():
            raise AppError("SCOPE_REQUIRED", f"Scope of works is required for work {work_index + 1}", 400)
    elif not has_product:
        raise AppError(
            "PRODUCT_OR_CUSTOM_REQUIRED",
            f"Select a product or add custom scope for work {work_index + 1}",
            400,
        )
    elif not block.scope or not block.scope.strip():
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


def _dashboard_quote_summary_breakdown(breakdown: dict) -> DashboardQuoteSummaryBreakdown | None:
    if breakdown.get("final_total") is None:
        return None
    labour_subtotal, materials_subtotal = _work_subtotals_from_breakdown(breakdown)
    works_subtotal = (labour_subtotal or Decimal("0")) + (materials_subtotal or Decimal("0"))
    charge_lines = breakdown.get("charges") or []
    additional_charges = sum(
        (Decimal(str(line["total"])) for line in charge_lines if line.get("total") is not None),
        Decimal("0"),
    )
    vat_total = breakdown.get("vat_total")
    if vat_total is None:
        return None
    return DashboardQuoteSummaryBreakdown(
        works_subtotal=works_subtotal,
        additional_charges=additional_charges,
        vat_total=Decimal(str(vat_total)),
        final_total=Decimal(str(breakdown["final_total"])),
    )


def _dashboard_last_result(db: Session, session: CalculationSession) -> dict | None:
    from app.services.pdf_calculation_context_service import (
        resolve_session_calculation_result,
        session_blocks_recalculation,
    )

    try:
        last_result, _ = resolve_session_calculation_result(
            db,
            session,
            allow_recalculate=not session_blocks_recalculation(session),
        )
        return last_result
    except AppError:
        return None


def update_session_step2(
    db: Session,
    *,
    session_id: UUID,
    session_token: str,
    payload: UpdateCalculationSessionRequest,
    idempotency_key: str | None = None,
) -> CalculationSessionRead:
    from app.services.quote_work_snapshot_service import (
        normalize_shared_work_blocks,
        save_shared_step2,
        sync_session_step2_from_shared,
    )

    request_body = payload.model_dump(mode="json", exclude_none=True)
    if idempotency_key:
        replay = check_idempotency(db, key=idempotency_key, request_hash=hash_payload(request_body))
        if replay is not None:
            return CalculationSessionRead.model_validate(replay.payload)

    session = get_session_by_token(db, session_id, session_token)
    assert_session_editable(session)
    if payload.step2 is not None:
        from app.services.quote_work_snapshot_service import resolve_shared_step2_for_session

        shared_step2, _ = resolve_shared_step2_for_session(db, session)
        merged_step2 = normalize_shared_work_blocks(
            _merge_incoming_step2_with_shared(payload.step2, shared_step2)
        )
        save_shared_step2(db, session, merged_step2)
        sync_session_step2_from_shared(db, session, merged_step2)
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
    result = build_calculation_session_read(db, session)
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
    actor=None,
):
    from app.schemas.eworks_link import Step2Snapshot
    from app.services.quote_work_attachment_service import save_quote_work_attachment

    session = get_session_by_token(db, session_id, session_token)
    assert_session_editable(session)
    attachment = await save_quote_work_attachment(
        db,
        session=session,
        upload=upload,
        work_index=work_index,
        actor=actor,
    )
    from app.services.quote_work_snapshot_service import normalize_shared_work_blocks

    step2 = Step2Snapshot.model_validate(session.step2_snapshot) if session.step2_snapshot else Step2Snapshot()
    if not step2.works:
        step2 = Step2Snapshot.model_validate({"scope": step2.scope, **step2.model_dump()})
    step2 = normalize_shared_work_blocks(step2)
    _validate_work_block(step2, work_index)
    block = step2.works[work_index]
    if not any(item.id == attachment.id for item in block.attachments):
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
    from app.services.quote_work_attachment_service import resolve_attachment_meta

    meta, _, _ = resolve_attachment_meta(db, session_id, attachment_id)
    return meta


async def delete_session_attachment(
    db: Session,
    *,
    session_id: UUID,
    session_token: str,
    attachment_id: str,
    actor=None,
) -> None:
    from app.schemas.eworks_link import Step2Snapshot
    from app.services.quote_work_attachment_service import delete_quote_work_attachment, get_quote_attachment_row

    session = get_session_by_token(db, session_id, session_token)
    assert_session_editable(session)

    row = get_quote_attachment_row(db, attachment_id)
    if row is not None:
        await delete_quote_work_attachment(db, attachment_id=attachment_id, session=session, actor=actor)
    elif session.step2_snapshot:
        step2 = Step2Snapshot.model_validate(session.step2_snapshot)
        work_index, attachment = _find_attachment_in_step2(step2, attachment_id)
        if attachment is None:
            raise AppError("ATTACHMENT_NOT_FOUND", "Attachment not found", 404)
        from app.services.eworks_attachment_service import delete_stored_attachment

        await delete_stored_attachment(session_id, attachment.stored_name)
        if work_index is not None:
            block = step2.works[work_index]
            block.attachments = [item for item in block.attachments if item.id != attachment_id]
            step2.works[work_index] = block
        else:
            step2.attachments = [item for item in step2.attachments if item.id != attachment_id]
        session.step2_snapshot = step2.model_dump(mode="json")
    else:
        raise AppError("ATTACHMENT_NOT_FOUND", "Attachment not found", 404)

    if session.step2_snapshot:
        step2 = Step2Snapshot.model_validate(session.step2_snapshot)
        changed = False
        for index, block in enumerate(step2.works):
            filtered = [item for item in block.attachments if item.id != attachment_id]
            if len(filtered) != len(block.attachments):
                step2.works[index] = block.model_copy(update={"attachments": filtered})
                changed = True
        if step2.attachments:
            filtered_root = [item for item in step2.attachments if item.id != attachment_id]
            if len(filtered_root) != len(step2.attachments):
                step2.attachments = filtered_root
                changed = True
        if changed:
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
    cost_to_optimal_labour = Decimal("0")
    cost_to_optimal_materials = Decimal("0")
    has_cost_to_optimal = False
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
        if bd.cost_to_optimal_labour is not None:
            cost_to_optimal_labour += bd.cost_to_optimal_labour
            has_cost_to_optimal = True
        if bd.cost_to_optimal_materials is not None:
            cost_to_optimal_materials += bd.cost_to_optimal_materials
            has_cost_to_optimal = True
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
        cost_to_optimal_labour=cost_to_optimal_labour if has_cost_to_optimal else None,
        cost_to_optimal_materials=cost_to_optimal_materials if has_cost_to_optimal else None,
    )


def calculate_session(
    db: Session,
    *,
    session_id: UUID,
    session_token: str,
    step2: Step2Snapshot | None = None,
    idempotency_key: str | None = None,
) -> CalculateSessionResponse:
    from app.services.quote_work_snapshot_service import (
        normalize_shared_work_blocks,
        resolve_shared_step2_for_session,
        save_shared_step2,
        sync_session_step2_from_shared,
    )

    request_body = {"step2": step2.model_dump(mode="json") if step2 else None}
    if idempotency_key:
        replay = check_idempotency(db, key=idempotency_key, request_hash=hash_payload(request_body))
        if replay is not None:
            return CalculateSessionResponse.model_validate(replay.payload)

    session = get_session_by_token(db, session_id, session_token)
    assert_session_editable(session)
    if step2 is not None:
        shared_step2, _ = resolve_shared_step2_for_session(db, session)
        step2_data = normalize_shared_work_blocks(_merge_incoming_step2_with_shared(step2, shared_step2))
        save_shared_step2(db, session, step2_data)
    else:
        step2_data, _ = resolve_shared_step2_for_session(db, session)
    step2_data = _merge_shared_quote_attachments(db, session, step2_data)
    if step2_data is not None:
        step2_data = normalize_shared_work_blocks(step2_data)
    if step2_data is None:
        raise AppError("STEP2_REQUIRED", "Estimator inputs are required before calculation", 400)
    sync_session_step2_from_shared(db, session, step2_data)
    step1 = Step1Snapshot.model_validate(session.step1_snapshot)
    if not step2_data.works:
        step2_data = Step2Snapshot.model_validate(step2_data.model_dump(mode="json"))

    for index in range(len(step2_data.works)):
        block = step2_data.works[index]
        if not block.findings and step1.findings_report:
            block = block.model_copy(update={"findings": step1.findings_report})
            step2_data.works[index] = block
        _validate_work_block(step2_data, index)

    charges = aggregate_work_charges(step1, step2_data.works, step2=step2_data)
    single_work = len(step2_data.works) == 1
    work_skills = collect_work_skills(step2_data.works, step1.trade_name)
    uniform_skills = skills_are_uniform(step2_data.works, step1.trade_name)

    matched = resolve_calculation_rule(db, session.client_id, session.trade_id, None)
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
        # Work breakdowns include labour and materials only; additional charges are quote-level.
        breakdown = preview_calculation(
            db,
            _eworks_preview_request(
                db,
                session=session,
                step1=step1,
                trade_id=work_trade.id,
                labour_items=labour,
                material_items=materials,
                charges=ChargeInput(),
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

    if single_work or uniform_skills:
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
        aggregated_summary_payload = (
            None
            if single_work
            else AggregatedQuoteSummary.model_validate(
                aggregated_quote_summary(aggregated, len(step2_data.works), skills=work_skills)
            )
        )
    else:
        from app.services.calculation_aggregate_service import build_mixed_skill_combined_breakdown

        breakdown, aggregated, _skills = build_mixed_skill_combined_breakdown(
            db,
            client_id=session.client_id,
            step1=step1,
            step2=step2_data,
            fallback_trade_name=step1.trade_name,
            charges=charges,
            vat_rate=vat_rate,
            formula_version=settings.formula_version,
            formula_source=formula_source,
            xlsx_formula_version=xlsx_formula_version,
        )
        skill_group_results = []
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
    merged = incoming.model_copy(update={"works": merged_works})
    if existing.attachments and not incoming.attachments:
        merged = merged.model_copy(update={"attachments": existing.attachments})
    return merged


def _merge_shared_quote_attachments(db: Session, session: CalculationSession, step2: Step2Snapshot | None) -> Step2Snapshot | None:
    if step2 is None:
        return None
    from app.services.quote_work_attachment_service import merge_shared_attachments_into_step2

    return merge_shared_attachments_into_step2(db, session, step2)


def submit_session(
    db: Session,
    *,
    session_id: UUID,
    session_token: str,
    step2: Step2Snapshot | None = None,
    idempotency_key: str | None = None,
) -> None:
    from app.services.quote_work_snapshot_service import resolve_shared_step2_for_session, save_shared_step2

    session = get_session_by_token(db, session_id, session_token)
    existing_step2 = Step2Snapshot.model_validate(session.step2_snapshot) if session.step2_snapshot else None
    if step2 is not None:
        shared_step2, _ = resolve_shared_step2_for_session(db, session)
        merged_step2 = _merge_incoming_step2_with_shared(step2, shared_step2)
        save_shared_step2(db, session, merged_step2)
    else:
        merged_step2, _ = resolve_shared_step2_for_session(db, session)
    merged_step2 = _merge_step2_attachments(existing_step2, merged_step2) if merged_step2 is not None else merged_step2
    merged_step2 = _merge_shared_quote_attachments(db, session, merged_step2)
    calculate_session(
        db,
        session_id=session_id,
        session_token=session_token,
        step2=merged_step2,
        idempotency_key=idempotency_key,
    )
    session = get_session_by_token(db, session_id, session_token)
    apply_submitter_to_session(db, session)
    session.status = "submitted"
    session.submitted_at = datetime.now(timezone.utc)
    complete_revision_submit(db, session)
    from app.services.quote_assignment_service import mark_linked_assignment_submitted

    mark_linked_assignment_submitted(db, session_id)
    db.flush()


def _resolve_work_product_fields(db: Session, block: WorkBlockSnapshot) -> tuple[str | None, str | None]:
    if block.is_custom_scope:
        title = (block.custom_title or block.product_name or "").strip() or None
        return title, None

    product_name = (block.product_name or "").strip() or None
    product_code = (block.product_code or "").strip() or None
    if product_name or block.selected_product_id is None:
        return product_name, product_code

    from app.models.product import Product

    product = db.get(Product, block.selected_product_id)
    if product is None:
        return product_name, product_code
    return product.product_name, product.product_code


def _build_dashboard_work_item(
    db: Session,
    *,
    index: int,
    block: WorkBlockSnapshot,
    labour_subtotal,
    materials_subtotal,
    work_internal_notes,
) -> DashboardWorkItem:
    product_name, product_code = _resolve_work_product_fields(db, block)
    return DashboardWorkItem(
        work_index=index,
        scope=block.scope,
        product_name=product_name,
        product_code=product_code,
        display_label=format_work_label(
            product_name=product_name,
            product_code=product_code,
            scope=block.scope,
            index=index,
            is_custom_scope=block.is_custom_scope,
            custom_title=block.custom_title,
        ),
        labour_subtotal=labour_subtotal,
        materials_subtotal=materials_subtotal,
        internal_notes=work_internal_notes,
        attachments=block.attachments,
        details=block,
    )


def _build_dashboard_quote_item_from_session(db: Session, session: CalculationSession) -> DashboardQuoteItem:
    from decimal import Decimal

    step1 = Step1Snapshot.model_validate(session.step1_snapshot)
    step2 = Step2Snapshot.model_validate(session.step2_snapshot) if session.step2_snapshot else Step2Snapshot()
    last_result = _dashboard_last_result(db, session)
    work_breakdowns = last_result.get("work_breakdowns", []) if last_result else []
    breakdown_map = {item["work_index"]: item for item in work_breakdowns}

    final_total = None
    internal_notes = None
    summary_breakdown = None
    if last_result:
        breakdown = last_result.get("breakdown") or {}
        if breakdown.get("final_total") is not None:
            final_total = Decimal(str(breakdown["final_total"]))
        internal_notes = last_result.get("internal_notes")
        summary_breakdown = _dashboard_quote_summary_breakdown(breakdown)

    works: list[DashboardWorkItem] = []
    for index, block in enumerate(step2.works):
        work_result = breakdown_map.get(index, {})
        work_bd = work_result.get("breakdown") or {}

        # For single-work quotes with XLSX formula, parking/CC are folded into the
        # combined materials bucket.  The per-work breakdown intentionally omits
        # quote-level charges (computed with an empty ChargeInput), so it reflects
        # only raw materials.  Use the combined (quote-level) breakdown to ensure
        # the work card subtotal matches the Quote Summary.
        if len(step2.works) == 1 and last_result:
            combined_bd = last_result.get("breakdown") or {}
            labour_subtotal, materials_subtotal = _work_subtotals_from_breakdown(combined_bd)
            if labour_subtotal is None and materials_subtotal is None:
                labour_subtotal, materials_subtotal = _work_subtotals_from_breakdown(work_bd)
        else:
            labour_subtotal, materials_subtotal = _work_subtotals_from_breakdown(work_bd)

        # For single-work quotes, the combined internal notes already include
        # quote-level parking/CC in the BUDGET line.  The per-work notes are built
        # without charges, so they would show Parking: £0.  Always prefer the
        # combined notes for single-work quotes so every display path is consistent.
        work_internal_notes = work_result.get("internal_notes")
        if len(step2.works) == 1:
            work_internal_notes = internal_notes or work_internal_notes
        works.append(
            _build_dashboard_work_item(
                db,
                index=index,
                block=block,
                labour_subtotal=labour_subtotal,
                materials_subtotal=materials_subtotal,
                work_internal_notes=work_internal_notes,
            )
        )

    return DashboardQuoteItem(
        session_id=session.id,
        session_token=session.session_token,
        quote_number=step1.quote_number,
        job_number=step1.job_number,
        client_name=step1.client_name,
        trade_name=step1.trade_name,
        submitted_at=session.submitted_at,
        final_total=final_total,
        internal_notes=internal_notes,
        additional_charges=quote_additional_charge_lines(step2),
        breakdown=summary_breakdown,
        works=works,
        acceptance=staff_acceptance_from_session(session),
        status=session.status,
        locked=session.locked,
        current_version_number=max(session.current_version_number, 1),
        revision_in_progress=session.revision_in_progress,
        active_revision_reason=session.active_revision_reason,
        can_revise=session.status == "submitted" and session.locked and not session.revision_in_progress,
        can_continue_revision=session.revision_in_progress and not session.locked,
    )


def get_submitted_quote_detail(
    db: Session,
    session_id: UUID,
    *,
    version_number: int | None = None,
) -> DashboardQuoteItem:
    from app.models.calculation_session import CalculationSession
    from app.services.calculation_session_revision_service import (
        apply_version_snapshot_to_session,
        get_session_version,
    )

    session = db.get(CalculationSession, session_id)
    if session is None:
        raise AppError("SESSION_NOT_FOUND", "Quote session not found", 404)
    if session.status not in {"submitted", "revision_in_progress"} or session.submitted_at is None:
        raise AppError("SESSION_NOT_SUBMITTED", "Quote is not submitted", 404)

    original_step1 = dict(session.step1_snapshot or {})
    original_step2 = dict(session.step2_snapshot) if session.step2_snapshot else None
    original_ui_state = dict(session.ui_state) if isinstance(session.ui_state, dict) else session.ui_state
    try:
        if version_number is not None:
            version = get_session_version(db, session_id=session_id, version_number=version_number)
            apply_version_snapshot_to_session(db, version)
        return _build_dashboard_quote_item_from_session(db, session)
    finally:
        session.step1_snapshot = original_step1
        session.step2_snapshot = original_step2
        session.ui_state = original_ui_state


def list_submitted_quotes(db: Session) -> DashboardQuotesResponse:
    from sqlalchemy import select

    from app.models.calculation_session import CalculationSession

    sessions = db.scalars(
        select(CalculationSession)
        .where(
            CalculationSession.status.in_(("submitted", "revision_in_progress")),
            CalculationSession.submitted_at.is_not(None),
        )
        .order_by(CalculationSession.submitted_at.desc())
    ).all()

    quotes: list[DashboardQuoteItem] = []
    for session in sessions:
        if not session.submitted_at:
            continue
        quotes.append(_build_dashboard_quote_item_from_session(db, session))

    return DashboardQuotesResponse(quotes=quotes)


def _reopened_session_ids(db: Session) -> set[UUID]:
    from sqlalchemy import select

    from app.models.support import AuditLog

    rows = db.scalars(select(AuditLog.entity_id).where(AuditLog.action == "quote_reopened")).all()
    return {row for row in rows if row is not None}


def _parse_eworks_quote_id(value) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _quote_group_identity(session: CalculationSession, step1: Step1Snapshot) -> tuple[str, str | None, int | None]:
    payload = session.payload_snapshot if isinstance(session.payload_snapshot, dict) else {}
    eworks_quote_id = _parse_eworks_quote_id(payload.get("eworks_quote_id"))
    if eworks_quote_id is None:
        eworks_quote_id = _parse_eworks_quote_id(step1.external_job_id)
    if eworks_quote_id is not None:
        quote_ref = (step1.quote_number or "").strip() or None
        return f"eworks_quote_id:{eworks_quote_id}", quote_ref, eworks_quote_id

    quote_ref = (step1.quote_number or "").strip() or None
    if quote_ref:
        return f"quote_ref:{quote_ref}", quote_ref, None

    return f"session_id:{session.id}", step1.quote_number or None, None


def _session_final_total(db: Session, session: CalculationSession) -> Decimal | None:
    last_result = _dashboard_last_result(db, session)
    if not last_result:
        return None
    breakdown = last_result.get("breakdown") or {}
    if breakdown.get("final_total") is None:
        return None
    return Decimal(str(breakdown["final_total"]))


def _build_quote_group_session_item(db: Session, session: CalculationSession) -> DashboardQuoteGroupSessionItem:
    step2 = Step2Snapshot.model_validate(session.step2_snapshot) if session.step2_snapshot else Step2Snapshot()
    acceptance = staff_acceptance_from_session(session)
    return DashboardQuoteGroupSessionItem(
        session_id=session.id,
        submitted_at=session.submitted_at,  # type: ignore[arg-type]
        final_total=_session_final_total(db, session),
        works_count=len(step2.works),
        status=session.status,
        accepted=acceptance.accepted,
        client_accepted_at=session.client_accepted_at,
        created_at=session.created_at,
        updated_at=session.updated_at,
        current_version_number=max(session.current_version_number, 1),
        revision_in_progress=session.revision_in_progress,
    )


def _build_quote_groups(db: Session, sessions: list[CalculationSession]) -> list[DashboardQuoteGroupItem]:
    reopened_ids = _reopened_session_ids(db)
    grouped: dict[str, dict] = {}

    for session in sessions:
        if not session.submitted_at:
            continue
        step1 = Step1Snapshot.model_validate(session.step1_snapshot)
        group_key, quote_ref, eworks_quote_id = _quote_group_identity(session, step1)
        session_item = _build_quote_group_session_item(db, session)

        bucket = grouped.get(group_key)
        if bucket is None:
            bucket = {
                "group_key": group_key,
                "quote_ref": quote_ref,
                "eworks_quote_id": eworks_quote_id,
                "client_name": step1.client_name,
                "trade_name": step1.trade_name,
                "sessions": [],
            }
            grouped[group_key] = bucket
        bucket["sessions"].append(session_item)

    groups: list[DashboardQuoteGroupItem] = []
    for bucket in grouped.values():
        sessions_sorted = sorted(
            bucket["sessions"],
            key=lambda item: item.submitted_at,
            reverse=True,
        )
        totals = [item.final_total for item in sessions_sorted if item.final_total is not None]
        latest = sessions_sorted[0]
        accepted_session = next((item for item in sessions_sorted if item.accepted), None)
        groups.append(
            DashboardQuoteGroupItem(
                group_key=bucket["group_key"],
                quote_ref=bucket["quote_ref"],
                eworks_quote_id=bucket["eworks_quote_id"],
                client_name=bucket["client_name"],
                trade_name=bucket["trade_name"],
                submission_count=len(sessions_sorted),
                latest_submitted_at=latest.submitted_at,
                latest_total=latest.final_total,
                highest_total=max(totals) if totals else None,
                lowest_total=min(totals) if totals else None,
                accepted=accepted_session.accepted if accepted_session else False,
                client_accepted_at=accepted_session.client_accepted_at if accepted_session else None,
                reopened_count=sum(1 for item in sessions_sorted if item.session_id in reopened_ids),
                latest_session_id=latest.session_id,
                sessions=sessions_sorted,
            )
        )

    groups.sort(key=lambda group: group.latest_submitted_at, reverse=True)
    return groups


def list_submitted_quote_groups(db: Session) -> DashboardQuoteGroupsResponse:
    from sqlalchemy import select

    sessions = db.scalars(
        select(CalculationSession)
        .where(
            CalculationSession.status.in_(("submitted", "revision_in_progress")),
            CalculationSession.submitted_at.is_not(None),
        )
        .order_by(CalculationSession.submitted_at.desc())
    ).all()
    return DashboardQuoteGroupsResponse(groups=_build_quote_groups(db, list(sessions)))


def get_submitted_quote_group_detail(
    db: Session,
    *,
    group_key: str | None = None,
    quote_ref: str | None = None,
    eworks_quote_id: int | None = None,
) -> DashboardQuoteGroupDetailResponse:
    groups = list_submitted_quote_groups(db).groups
    target: DashboardQuoteGroupItem | None = None

    if group_key:
        target = next((group for group in groups if group.group_key == group_key), None)
    elif eworks_quote_id is not None:
        target = next((group for group in groups if group.eworks_quote_id == eworks_quote_id), None)
    elif quote_ref:
        normalized = quote_ref.strip()
        target = next((group for group in groups if (group.quote_ref or "").strip() == normalized), None)

    if target is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Quote group not found")

    return DashboardQuoteGroupDetailResponse(group=_build_quote_group_detail(db, target))


def _derive_assignment_status(
    assignment_status: str,
    linked_session: CalculationSession | None,
) -> str:
    if assignment_status == "cancelled":
        return "cancelled"
    if (
        linked_session is not None
        and linked_session.submitted_at is not None
        and linked_session.status == "submitted"
    ):
        return "submitted"
    if linked_session is not None or assignment_status == "in_progress":
        return "in_progress"
    return "assigned"


def _list_assignments_for_quote_identity(
    db: Session,
    *,
    eworks_quote_id: int | None,
    quote_ref: str | None,
) -> list:
    from sqlalchemy import or_

    from app.models.quote_assignment import EworksQuoteAssignment

    filters = []
    if eworks_quote_id is not None:
        filters.append(EworksQuoteAssignment.eworks_quote_id == eworks_quote_id)
    normalized_ref = (quote_ref or "").strip()
    if normalized_ref:
        filters.append(EworksQuoteAssignment.quote_ref == normalized_ref)
    if not filters:
        return []

    return (
        db.query(EworksQuoteAssignment)
        .filter(or_(*filters))
        .order_by(EworksQuoteAssignment.assigned_at.desc(), EworksQuoteAssignment.id.desc())
        .all()
    )


def _load_linked_sessions(db: Session, session_ids: list[UUID]) -> dict[UUID, CalculationSession]:
    if not session_ids:
        return {}
    from sqlalchemy import select

    rows = db.scalars(select(CalculationSession).where(CalculationSession.id.in_(session_ids))).all()
    return {row.id: row for row in rows}


def _build_dashboard_assignment_items(
    db: Session,
    assignments: list,
) -> list[DashboardQuoteGroupAssignmentItem]:
    linked_session_ids = [
        row.calculation_session_id for row in assignments if row.calculation_session_id is not None
    ]
    linked_sessions = _load_linked_sessions(db, linked_session_ids)

    items: list[DashboardQuoteGroupAssignmentItem] = []
    for row in assignments:
        linked_session = linked_sessions.get(row.calculation_session_id) if row.calculation_session_id else None
        derived_status = _derive_assignment_status(row.status, linked_session)
        items.append(
            DashboardQuoteGroupAssignmentItem(
                id=row.id,
                assignment_type=row.assignment_type,
                assignee_kind=row.assignee_kind,
                assigned_user_id=row.assigned_user_id,
                assigned_user_name=row.assigned_user_name,
                assigned_user_email=row.assigned_user_email,
                status=derived_status,
                assigned_at=row.assigned_at,
                started_at=linked_session.created_at if linked_session is not None else None,
                submitted_at=linked_session.submitted_at
                if linked_session is not None and linked_session.submitted_at is not None
                else None,
                calculation_session_id=row.calculation_session_id,
                has_submission=derived_status == "submitted",
            )
        )
    return items


def _build_assignment_summary(
    assignments: list[DashboardQuoteGroupAssignmentItem],
) -> DashboardQuoteGroupAssignmentSummary:
    summary = DashboardQuoteGroupAssignmentSummary(total_assignments=len(assignments))
    for item in assignments:
        if item.assignment_type == "estimator":
            summary.estimator_assignments += 1
        elif item.assignment_type == "engineer":
            summary.engineer_assignments += 1

        if item.status == "assigned":
            summary.pending_assignments += 1
        elif item.status == "in_progress":
            summary.in_progress_assignments += 1
        elif item.status == "submitted":
            summary.submitted_assignments += 1
        elif item.status == "cancelled":
            summary.cancelled_assignments += 1
    return summary


def _derive_group_review_status(
    group: DashboardQuoteGroupItem,
    assignment_summary: DashboardQuoteGroupAssignmentSummary,
) -> str:
    if group.accepted or group.client_accepted_at is not None:
        return "accepted"
    if group.submission_count > 0:
        return "ready_for_review"
    if assignment_summary.in_progress_assignments > 0:
        return "in_progress"
    if assignment_summary.pending_assignments > 0:
        return "pending"
    return "pending"


def _resolve_session_submitter(
    db: Session,
    session: CalculationSession | None,
    *,
    assignments_by_session_id: dict[UUID, object],
    assignments_by_id: dict[int, object],
) -> tuple[UUID | None, str, str | None, str | None]:
    if session is None:
        return None, "Unknown submitter", None, None

    assignment = assignments_by_session_id.get(session.id)
    if assignment is None:
        payload = session.payload_snapshot if isinstance(session.payload_snapshot, dict) else {}
        payload_assignment_id = payload.get("assignment_id")
        if payload_assignment_id is not None:
            try:
                assignment = assignments_by_id.get(int(payload_assignment_id))
            except (TypeError, ValueError):
                assignment = None

    from app.services.quote_assignment_service import resolve_session_submitter_identity

    identity = resolve_session_submitter_identity(db, session, assignment=assignment)
    name = identity["submitted_by_name"]
    role = identity["submitted_by_role"]
    return identity["submitted_by_user_id"], name, identity["submitted_by_email"], role


def _assignee_display_name(
    *,
    assigned_user_name: str | None,
    assigned_user_email: str | None,
) -> str:
    name = (assigned_user_name or "").strip()
    if name:
        return name
    email = (assigned_user_email or "").strip()
    if email:
        return email
    return "Unassigned"


def _can_select_estimate_row(
    *,
    assignment_status: str,
    linked_session_id: UUID | None,
    assignee_name: str,
) -> bool:
    if assignment_status != "submitted" or linked_session_id is None:
        return False
    normalized_name = (assignee_name or "").strip().lower()
    return normalized_name not in {"", "unknown", "unassigned"}


def _dashboard_version_items(
    db: Session,
    session_id: UUID,
    *,
    submitted_by_role: str | None = None,
) -> list[DashboardQuoteGroupVersionItem]:
    history = list_session_version_history(db, session_id)
    return [
        DashboardQuoteGroupVersionItem(
            version_number=version.version_number,
            submitted_at=version.submitted_at,
            submitted_by_name=version.submitted_by_name,
            submitted_by_email=version.submitted_by_email,
            submitted_by_role=submitted_by_role,
            revision_reason=version.revision_reason,
            final_total=version.final_total,
            status=version.status,
            is_current=version.is_current,
        )
        for version in sorted(history.versions, key=lambda item: item.version_number, reverse=True)
    ]


def _enrich_assignment_submission_row(
    db: Session,
    row: DashboardQuoteGroupAssignmentSubmissionRow,
    *,
    raw_sessions_by_id: dict[UUID, CalculationSession],
    assigned_session_id: UUID | None,
) -> DashboardQuoteGroupAssignmentSubmissionRow:
    updates: dict = {
        "can_select_estimate": _can_select_estimate_row(
            assignment_status=row.assignment_status,
            linked_session_id=row.linked_session_id,
            assignee_name=row.assignee_name,
        ),
        "is_selected_estimate": assigned_session_id is not None and row.linked_session_id == assigned_session_id,
    }
    if row.linked_session_id is not None:
        raw_session = raw_sessions_by_id.get(row.linked_session_id)
        if raw_session is not None:
            from app.services.quote_job_assignment_service import _session_comparison_summary

            updates["comparison_summary"] = _session_comparison_summary(db, raw_session)
        versions = _dashboard_version_items(
            db,
            row.linked_session_id,
            submitted_by_role=row.submitted_by_role,
        )
        updates["versions"] = versions
        updates["version_count"] = len(versions)
        updates["current_version_number"] = (
            next((item.version_number for item in versions if item.is_current), None)
            or (versions[0].version_number if versions else None)
        )
    return row.model_copy(update=updates)


def _build_assignment_submission_rows(
    db: Session,
    group: DashboardQuoteGroupItem,
    assignments: list[DashboardQuoteGroupAssignmentItem],
    detail_sessions: list[DashboardQuoteGroupSessionDetailItem],
    *,
    raw_sessions_by_id: dict[UUID, CalculationSession],
    selected_estimate_decision: DashboardSelectedEstimateDecision | None = None,
) -> list[DashboardQuoteGroupAssignmentSubmissionRow]:
    sessions_by_id = {item.session_id: item for item in detail_sessions}
    linked_session_ids: set[UUID] = set()
    assigned_session_id = (
        selected_estimate_decision.selected_session_id if selected_estimate_decision is not None else None
    )

    rows: list[DashboardQuoteGroupAssignmentSubmissionRow] = []
    for assignment in assignments:
        session = (
            sessions_by_id.get(assignment.calculation_session_id)
            if assignment.calculation_session_id is not None
            else None
        )
        if assignment.calculation_session_id is not None:
            linked_session_ids.add(assignment.calculation_session_id)

        is_submitted = assignment.status == "submitted"
        linked_session_id = assignment.calculation_session_id
        if is_submitted and session is not None:
            linked_session_id = session.session_id

        rows.append(
            _enrich_assignment_submission_row(
                db,
                DashboardQuoteGroupAssignmentSubmissionRow(
                    assignment_id=assignment.id,
                    assignment_type=assignment.assignment_type,
                    assignee_kind=assignment.assignee_kind,
                    assignee_name=_assignee_display_name(
                        assigned_user_name=assignment.assigned_user_name,
                        assigned_user_email=assignment.assigned_user_email,
                    ),
                    assignee_email=assignment.assigned_user_email,
                    assignment_status=assignment.status,
                    assigned_at=assignment.assigned_at,
                    started_at=assignment.started_at,
                    submitted_at=session.submitted_at if session is not None else assignment.submitted_at,
                    linked_session_id=linked_session_id,
                    submitted_by_name=session.submitted_by_name if session is not None else None,
                    submitted_by_email=session.submitted_by_email if session is not None else None,
                    submitted_by_role=session.submitted_by_role if session is not None else None,
                    final_total=session.final_total if session is not None else None,
                    works_count=session.works_count if session is not None else None,
                    can_view_details=is_submitted and linked_session_id is not None,
                    can_reopen=is_submitted and linked_session_id is not None,
                ),
                raw_sessions_by_id=raw_sessions_by_id,
                assigned_session_id=assigned_session_id,
            )
        )

    for session in detail_sessions:
        if session.session_id in linked_session_ids:
            continue
        raw_session = raw_sessions_by_id.get(session.session_id)
        from app.services.quote_assignment_service import (
            _is_unknown_submitter_name,
            resolve_session_submitter_identity,
        )

        identity = (
            resolve_session_submitter_identity(db, raw_session)
            if raw_session is not None
            else {
                "submitted_by_name": session.submitted_by_name,
                "submitted_by_email": session.submitted_by_email,
                "submitted_by_role": session.submitted_by_role,
                "assignment_type": "unknown",
                "assignee_kind": "unknown",
                "assignment_source": None,
            }
        )

        display_name = _assignee_display_name(
            assigned_user_name=identity.get("submitted_by_name"),
            assigned_user_email=identity.get("submitted_by_email"),
        )
        if display_name == "Unassigned" or _is_unknown_submitter_name(display_name):
            display_name = "Unknown"
        rows.append(
            _enrich_assignment_submission_row(
                db,
                DashboardQuoteGroupAssignmentSubmissionRow(
                    assignment_id=None,
                    assignment_type=identity.get("assignment_type") or "unknown",
                    assignee_kind=identity.get("assignee_kind") or "unknown",
                    assignee_name=display_name,
                    assignee_email=identity.get("submitted_by_email") or session.submitted_by_email,
                    assignment_status="submitted",
                    assigned_at=None,
                    started_at=None,
                    submitted_at=session.submitted_at,
                    linked_session_id=session.session_id,
                    submitted_by_name=identity.get("submitted_by_name") or session.submitted_by_name,
                    submitted_by_email=identity.get("submitted_by_email") or session.submitted_by_email,
                    submitted_by_role=identity.get("submitted_by_role") or session.submitted_by_role,
                    assignment_source=identity.get("assignment_source"),
                    final_total=session.final_total,
                    works_count=session.works_count,
                    can_view_details=True,
                    can_reopen=True,
                ),
                raw_sessions_by_id=raw_sessions_by_id,
                assigned_session_id=assigned_session_id,
            )
        )

    latest_submitted_at: datetime | None = None
    latest_row_indexes: list[int] = []
    for index, row in enumerate(rows):
        if row.submitted_at is None:
            continue
        if latest_submitted_at is None or row.submitted_at > latest_submitted_at:
            latest_submitted_at = row.submitted_at
            latest_row_indexes = [index]
        elif row.submitted_at == latest_submitted_at:
            latest_row_indexes.append(index)

    if len(latest_row_indexes) == 1:
        row = rows[latest_row_indexes[0]]
        rows[latest_row_indexes[0]] = _enrich_assignment_submission_row(
            db,
            row.model_copy(update={"is_latest": True}),
            raw_sessions_by_id=raw_sessions_by_id,
            assigned_session_id=assigned_session_id,
        )
    elif len(latest_row_indexes) > 1:
        preferred_index = next(
            (index for index in latest_row_indexes if rows[index].linked_session_id == group.latest_session_id),
            latest_row_indexes[0],
        )
        row = rows[preferred_index]
        rows[preferred_index] = _enrich_assignment_submission_row(
            db,
            row.model_copy(update={"is_latest": True}),
            raw_sessions_by_id=raw_sessions_by_id,
            assigned_session_id=assigned_session_id,
        )

    def _row_sort_key(row: DashboardQuoteGroupAssignmentSubmissionRow) -> tuple:
        submitted_rank = row.submitted_at.timestamp() if row.submitted_at is not None else float("-inf")
        assigned_rank = row.assigned_at.timestamp() if row.assigned_at is not None else float("-inf")
        return (-submitted_rank, -assigned_rank, row.assignment_id or 0)

    rows.sort(key=_row_sort_key)
    return rows


def _build_quote_group_detail(
    db: Session,
    group: DashboardQuoteGroupItem,
) -> DashboardQuoteGroupDetailItem:
    raw_assignments = _list_assignments_for_quote_identity(
        db,
        eworks_quote_id=group.eworks_quote_id,
        quote_ref=group.quote_ref,
    )
    assignments = _build_dashboard_assignment_items(db, raw_assignments)
    assignment_summary = _build_assignment_summary(assignments)
    review_status = _derive_group_review_status(group, assignment_summary)

    assignments_by_session_id = {
        row.calculation_session_id: row for row in raw_assignments if row.calculation_session_id is not None
    }
    assignments_by_id = {row.id: row for row in raw_assignments}

    session_ids = [item.session_id for item in group.sessions]
    sessions_by_id = _load_linked_sessions(db, session_ids)

    from app.services.selected_estimate_decision_service import (
        build_dashboard_selected_estimate_decision,
        get_selected_estimate_for_quote,
    )

    selected_estimate_row = get_selected_estimate_for_quote(
        db,
        quote_ref=group.quote_ref,
        eworks_quote_id=group.eworks_quote_id,
    )
    selected_estimate_decision = build_dashboard_selected_estimate_decision(db, selected_estimate_row)

    detail_sessions: list[DashboardQuoteGroupSessionDetailItem] = []
    for item in group.sessions:
        session = sessions_by_id.get(item.session_id)
        submitter_id, submitter_name, submitter_email, submitter_role = _resolve_session_submitter(
            db,
            session,
            assignments_by_session_id=assignments_by_session_id,
            assignments_by_id=assignments_by_id,
        )
        detail_sessions.append(
            DashboardQuoteGroupSessionDetailItem(
                **item.model_dump(),
                submitted_by_user_id=submitter_id,
                submitted_by_name=submitter_name,
                submitted_by_email=submitter_email,
                submitted_by_role=submitter_role,
                is_latest=item.session_id == group.latest_session_id,
                version_history=[
                    DashboardQuoteGroupVersionItem(
                        version_number=version.version_number,
                        submitted_at=version.submitted_at,
                        submitted_by_name=version.submitted_by_name,
                        submitted_by_email=version.submitted_by_email,
                        submitted_by_role=submitter_role,
                        revision_reason=version.revision_reason,
                        final_total=version.final_total,
                        status=version.status,
                        is_current=version.is_current,
                    )
                    for version in list_session_version_history(db, item.session_id).versions
                ],
            )
        )

    return DashboardQuoteGroupDetailItem(
        **group.model_dump(exclude={"sessions"}),
        review_status=review_status,
        assignment_summary=assignment_summary,
        assignments=assignments,
        sessions=detail_sessions,
        assignment_submissions=_build_assignment_submission_rows(
            db,
            group,
            assignments,
            detail_sessions,
            raw_sessions_by_id=sessions_by_id,
            selected_estimate_decision=selected_estimate_decision,
        ),
        selected_estimate_decision=selected_estimate_decision,
    )


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
        work_charges = ChargeInput()
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
    work_charges = ChargeInput()
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
    internal_notes_text: str | None = None,
) -> dict:
    material_rows = [*flatten_supplier_links(block.materials_to_order), *block.shelf_materials_rows]
    materials_link = format_links_and_quantity(material_rows)
    labour_charge = breakdown.labour_charge_to_client or Decimal("0")
    materials_charge = breakdown.materials_parking_cc_charge or Decimal("0")
    client_price = breakdown.subtotal

    # material_cost = cost-to-Optimal for materials (actual cost, NOT the charge to client).
    # The materials lines in an XLSX breakdown represent charge amounts (e.g. £265), so summing
    # them here would give the wrong number.  Use the stored cost field when available.
    if breakdown.cost_to_optimal_materials is not None:
        material_cost = breakdown.cost_to_optimal_materials
    elif breakdown.profit_gbp is not None:
        # Derive: total optimal cost = subtotal − profit; subtract direct labour for the split.
        total_optimal = client_price - breakdown.profit_gbp
        material_cost = total_optimal - (breakdown.direct_labour_cost or Decimal("0"))
    else:
        # Last resort (legacy breakdowns without profit): sum the materials charge lines.
        material_cost = sum((line.total for line in breakdown.materials), Decimal("0"))

    # labour_cost_to_optimal = full cost-to-Optimal for labour (incl. overhead & fee share).
    if breakdown.cost_to_optimal_labour is not None:
        labour_cost_to_optimal = breakdown.cost_to_optimal_labour
    else:
        labour_cost_to_optimal = breakdown.direct_labour_cost or Decimal("0")

    optimal_cost = labour_cost_to_optimal + material_cost
    profit_gbp = breakdown.profit_gbp if breakdown.profit_gbp is not None else (client_price - optimal_cost)
    margin_pct = breakdown.profit_pct
    if margin_pct is None and client_price > 0:
        margin_pct = (profit_gbp / client_price) * Decimal("100")

    scope_text = html_to_plain_text(block.scope or "").strip()
    description = scope_text.split("\n", 1)[0].strip() if scope_text else html_to_plain_text(step1.original_job_description or "").strip() or "Work item"
    findings = html_to_plain_text(block.findings or step1.findings_report or "").strip()
    notes_exclusions = html_to_plain_text(block.other_notes or "").strip()
    if internal_notes_text is None:
        resolved_internal_notes = (breakdown.internal_notes or "").strip()
    else:
        resolved_internal_notes = internal_notes_text.strip()

    return {
        "index": display_index,
        "description": description,
        "description_html": prepare_pdf_rich_text(block.scope or description),
        "findings": findings,
        "findings_html": prepare_pdf_rich_text(block.findings or step1.findings_report or ""),
        "scope": scope_text,
        "scope_html": prepare_pdf_rich_text(block.scope or ""),
        "notes_exclusions": notes_exclusions,
        "notes_exclusions_html": prepare_pdf_rich_text(block.other_notes or ""),
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
        "internal_notes": resolved_internal_notes,
        "internal_notes_html": prepare_pdf_rich_text(resolved_internal_notes),
        "_subtotal": client_price,
        "_vat_total": breakdown.vat_total,
        "_grand_total": breakdown.final_total,
        "_material_cost": material_cost,
        "_labour_charge": labour_charge,
        "_materials_charge": materials_charge,
        "_optimal_cost": optimal_cost,
        "_profit_gbp": profit_gbp,
    }


def render_combined_all_trades_pdf(
    db: Session,
    *,
    session_id: UUID,
    work_indexes: list[int],
) -> tuple[bytes, str, str]:
    from app.adapters.pdf_renderer import render_all_trades_document
    from app.services.eworks_pdf_context_service import build_all_trades_pdf_context
    from app.services.pdf_calculation_context_service import (
        build_pdf_calculation_context,
        session_blocks_recalculation,
    )

    session = db.get(CalculationSession, session_id)
    if session is None:
        raise AppError("SESSION_NOT_FOUND", "Quote session not found", 404)

    pdf_ctx = build_pdf_calculation_context(
        db,
        session,
        allow_recalculate=not session_blocks_recalculation(session),
        view_type="all_trades",
    )
    if not pdf_ctx.step2.works:
        raise AppError("WORKS_REQUIRED", "No works found for this quote", 400)

    unique_indexes = sorted({index for index in work_indexes})
    for index in unique_indexes:
        if index < 0 or index >= len(pdf_ctx.step2.works):
            raise AppError("WORK_INDEX_INVALID", f"Invalid work index: {index}", 400)

    all_work_indexes = set(range(len(pdf_ctx.step2.works)))
    filtered_indexes = unique_indexes if set(unique_indexes) != all_work_indexes else None

    breakdown = pdf_ctx.breakdown.model_dump(mode="json")
    work_breakdowns = [item.model_dump(mode="json") for item in pdf_ctx.work_breakdowns]
    try:
        context = build_all_trades_pdf_context(
            db=db,
            step1=pdf_ctx.step1,
            step2=pdf_ctx.step2,
            breakdown=breakdown,
            work_breakdowns=work_breakdowns,
            work_indexes=filtered_indexes,
        )
    except ValueError as exc:
        raise AppError("CALCULATION_REQUIRED", str(exc), 400) from exc

    return render_all_trades_document(context)


def render_combined_works_pdf(
    db: Session,
    *,
    session_id: UUID,
    work_indexes: list[int],
    view_type: str,
    version_number: int | None = None,
) -> tuple[bytes, str, str]:
    from app.adapters.pdf_renderer import render_combined_works_document
    from app.services.pdf_calculation_context_service import (
        build_pdf_calculation_context,
        build_work_internal_calculation_note,
        quote_level_totals_for_works,
        session_blocks_recalculation,
        work_breakdown_map,
    )

    session = db.get(CalculationSession, session_id)
    if session is None:
        raise AppError("SESSION_NOT_FOUND", "Quote session not found", 404)
    if view_type == "all_trades":
        return render_combined_all_trades_pdf(
            db,
            session_id=session_id,
            work_indexes=work_indexes,
        )
    if view_type not in {"client", "optimal"}:
        raise AppError("VIEW_TYPE_INVALID", "view_type must be 'client', 'optimal', or 'all_trades'", 400)

    pdf_ctx = build_pdf_calculation_context(
        db,
        session,
        allow_recalculate=not session_blocks_recalculation(session),
        version_number=version_number,
        view_type=view_type,
    )
    step1 = pdf_ctx.step1
    step2 = pdf_ctx.step2
    breakdown = pdf_ctx.breakdown
    if not step2.works:
        raise AppError("WORKS_REQUIRED", "No works found for this quote", 400)

    unique_indexes = sorted({index for index in work_indexes})
    for index in unique_indexes:
        if index < 0 or index >= len(step2.works):
            raise AppError("WORK_INDEX_INVALID", f"Invalid work index: {index}", 400)

    breakdown_by_work = work_breakdown_map(pdf_ctx.work_breakdowns)
    items: list[dict] = []
    total_material_cost = Decimal("0")
    total_labour_charge = Decimal("0")
    total_materials_charge = Decimal("0")
    total_optimal_cost = Decimal("0")
    total_profit = Decimal("0")

    for position, index in enumerate(unique_indexes, start=1):
        block = step2.works[index]
        work_result = breakdown_by_work.get(index)
        if work_result is None:
            raise AppError("CALCULATION_REQUIRED", f"No cached breakdown for work {index + 1}", 400)
        resolved_notes = None
        if view_type != "client":
            resolved_notes = build_work_internal_calculation_note(
                work_index=index,
                work_block=block,
                work_result=work_result,
                quote_internal_notes=pdf_ctx.internal_notes,
                quote_breakdown=breakdown,
                work_count=len(step2.works),
            )
        # For single-work XLSX quotes, parking/CC charges are folded into the
        # combined materials bucket. The per-work breakdown is computed with an
        # empty ChargeInput, so it reflects only raw materials (e.g. £140) and
        # gives the wrong subtotal/quoted-price. Use the combined (quote-level)
        # breakdown for all item rows when there is only one work, because
        # combined == per-work for labour but correctly includes parking/CC.
        effective_breakdown = pdf_ctx.breakdown if len(step2.works) == 1 else work_result.breakdown
        row = _work_item_row(
            display_index=position,
            block=block,
            step1=step1,
            breakdown=effective_breakdown,
            internal_notes_text=resolved_notes or "",
        )
        item = {key: value for key, value in row.items() if not key.startswith("_")}
        if view_type == "client":
            item.pop("internal_notes", None)
            item.pop("internal_notes_html", None)
        items.append(item)
        total_material_cost += row["_material_cost"]
        total_labour_charge += row["_labour_charge"]
        total_materials_charge += row["_materials_charge"]
        total_optimal_cost += row["_optimal_cost"]
        total_profit += row["_profit_gbp"]

    all_work_indexes = set(range(len(step2.works)))
    subtotal, vat_total, grand_total = quote_level_totals_for_works(
        breakdown=breakdown,
        work_breakdowns=pdf_ctx.work_breakdowns,
        work_indexes=unique_indexes,
        all_work_indexes=all_work_indexes,
    )
    all_works_selected = set(unique_indexes) == all_work_indexes and len(unique_indexes) == len(all_work_indexes)
    if all_works_selected and breakdown.profit_gbp is not None:
        total_profit = breakdown.profit_gbp
    overall_margin = (total_profit / subtotal * Decimal("100")) if subtotal > 0 else Decimal("0")
    generated_at = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")

    report_notes = _build_report_notes(step1)
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
        "report_notes": report_notes,
        "report_notes_html": prepare_pdf_rich_text(report_notes),
        "subtotal": _format_gbp(subtotal),
        "vat_total": _format_gbp(vat_total),
        "grand_total": _format_gbp(grand_total),
        "generated_at": generated_at,
        "items": items,
        "cost_summary": {
            "material_cost": _format_gbp(total_material_cost),
            "labour_charge": _format_gbp(
                breakdown.labour_charge_to_client if all_works_selected and breakdown.labour_charge_to_client else total_labour_charge
            ),
            "materials_charge": _format_gbp(
                breakdown.materials_parking_cc_charge
                if all_works_selected and breakdown.materials_parking_cc_charge
                else total_materials_charge
            ),
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
    session.locked = False
    session.revision_in_progress = False
    session.active_revision_reason = None
    session.ui_state = {
        "current_step": 1,
        "max_reachable_step": 1,
        "last_result": None,
    }
    db.flush()
    return ReopenQuoteResponse(session_id=session.id, session_token=session.session_token)
