from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.pdf_renderer import render_eworks_estimate_document
from app.core.exceptions import AppError
from app.models.calculation_session import CalculationSession
from app.schemas.calculation import CalculationBreakdown
from app.schemas.eworks_link import (
    AggregatedQuoteSummary,
    Step1Snapshot,
    Step2Snapshot,
    WorkBreakdownResult,
)
from app.services.calculation_session_service import (
    _session_ui_state,
    calculate_session,
)
from app.services.calculation_view_service import build_client_view_from_session
from app.services.eworks_link_service import get_session_by_token
from app.services.eworks_pdf_context_service import build_eworks_estimate_pdf_context
from app.services.eworks_questionnaire_service import work_block_to_step2_snapshot


def _load_session_for_pdf(
    db: Session,
    *,
    session_id: UUID,
    session_token: str,
    read_only: bool,
) -> CalculationSession:
    if read_only:
        session = db.scalar(
            select(CalculationSession).where(
                CalculationSession.id == session_id,
                CalculationSession.session_token == session_token,
            )
        )
        if session is None:
            raise AppError("SESSION_NOT_FOUND", "Calculation session not found", 404)
        return session
    return get_session_by_token(db, session_id, session_token)


def _resolve_pdf_calculation_payload(
    db: Session,
    *,
    session: CalculationSession,
    session_id: UUID,
    session_token: str,
    read_only: bool,
) -> tuple[
    CalculationBreakdown,
    list[WorkBreakdownResult],
    AggregatedQuoteSummary | None,
    str | None,
]:
    ui_state = _session_ui_state(session)
    last_result = ui_state.last_result if ui_state else None
    if isinstance(last_result, dict) and last_result.get("breakdown") and last_result.get("work_breakdowns"):
        breakdown = CalculationBreakdown.model_validate(last_result["breakdown"])
        work_breakdowns = [
            WorkBreakdownResult.model_validate(item) for item in last_result.get("work_breakdowns") or []
        ]
        aggregated_summary = None
        if last_result.get("aggregated_summary"):
            aggregated_summary = AggregatedQuoteSummary.model_validate(last_result["aggregated_summary"])
        internal_notes = last_result.get("internal_notes") or breakdown.internal_notes
        return breakdown, work_breakdowns, aggregated_summary, internal_notes

    if read_only or session.status == "submitted" or session.locked:
        raise AppError("CALCULATION_REQUIRED", "No calculation result available for this quote", 400)

    result = calculate_session(
        db,
        session_id=session_id,
        session_token=session_token,
        step2=None,
    )
    return (
        result.breakdown,
        result.work_breakdowns,
        result.aggregated_summary,
        result.internal_notes or result.breakdown.internal_notes,
    )


def render_session_quote_pdf(
    db: Session,
    *,
    session_id: UUID,
    session_token: str,
    is_draft: bool = False,
    read_only: bool = False,
) -> tuple[bytes, str, str]:
    session = _load_session_for_pdf(
        db,
        session_id=session_id,
        session_token=session_token,
        read_only=read_only,
    )
    if not session.step2_snapshot:
        raise AppError("STEP2_REQUIRED", "Estimator inputs are required before generating PDF", 400)

    step1 = Step1Snapshot.model_validate(session.step1_snapshot)
    step2_data = Step2Snapshot.model_validate(session.step2_snapshot)
    breakdown, work_breakdowns, aggregated_summary, internal_notes = _resolve_pdf_calculation_payload(
        db,
        session=session,
        session_id=session_id,
        session_token=session_token,
        read_only=read_only,
    )
    primary_step2 = work_block_to_step2_snapshot(step2_data.works[0], trade_name=step1.trade_name)
    combined_scope = "\n\n".join(
        block.scope.strip() for block in step2_data.works if block.scope and block.scope.strip()
    )
    primary_step2 = primary_step2.model_copy(update={"scope": combined_scope})
    client_view = build_client_view_from_session(session, breakdown, step1, primary_step2)
    context = build_eworks_estimate_pdf_context(
        step1=step1,
        step2=step2_data,
        breakdown=breakdown,
        client_view=client_view,
        work_breakdowns=work_breakdowns,
        aggregated_summary=aggregated_summary,
        internal_notes=internal_notes,
    )
    context["quote_number"] = step1.quote_number
    return render_eworks_estimate_document(context, is_draft=is_draft)
