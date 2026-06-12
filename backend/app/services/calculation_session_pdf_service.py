from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.pdf_renderer import render_eworks_estimate_document
from app.core.exceptions import AppError
from app.models.calculation_session import CalculationSession
from app.schemas.calculation import CalculationBreakdown
from app.schemas.eworks_link import (
    Step1Snapshot,
    Step2Snapshot,
)
from app.services.pdf_calculation_context_service import build_pdf_calculation_context
from app.services.calculation_view_service import build_client_view_from_session
from app.services.eworks_link_service import get_session_by_token
from app.auth.types import AuthenticatedUser
from app.services.eworks_pdf_context_service import build_eworks_estimate_pdf_context
from app.services.eworks_questionnaire_service import work_block_to_step2_snapshot
from app.services.pdf_estimator_identity_service import resolve_estimated_by_for_pdf


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




def render_session_quote_pdf(
    db: Session,
    *,
    session_id: UUID,
    session_token: str,
    is_draft: bool = False,
    read_only: bool = False,
    show_internal_notes: bool = True,
    current_user: AuthenticatedUser | None = None,
) -> tuple[bytes, str, str]:
    session = _load_session_for_pdf(
        db,
        session_id=session_id,
        session_token=session_token,
        read_only=read_only,
    )
    if not session.step2_snapshot:
        raise AppError("STEP2_REQUIRED", "Estimator inputs are required before generating PDF", 400)

    pdf_ctx = build_pdf_calculation_context(
        db,
        session,
        allow_recalculate=not read_only,
        session_id=session_id,
        session_token=session_token,
        view_type="combined" if not is_draft else "draft",
    )
    step1 = pdf_ctx.step1
    step2_data = pdf_ctx.step2
    breakdown = pdf_ctx.breakdown
    work_breakdowns = pdf_ctx.work_breakdowns
    aggregated_summary = pdf_ctx.aggregated_summary
    internal_notes = pdf_ctx.internal_notes
    primary_step2 = work_block_to_step2_snapshot(step2_data.works[0], trade_name=step1.trade_name)
    combined_scope = "\n\n".join(
        block.scope.strip() for block in step2_data.works if block.scope and block.scope.strip()
    )
    primary_step2 = primary_step2.model_copy(update={"scope": combined_scope})
    client_view = build_client_view_from_session(session, breakdown, step1, primary_step2)
    estimated_by_name = resolve_estimated_by_for_pdf(db, session, step1, current_user=current_user)
    context = build_eworks_estimate_pdf_context(
        step1=step1,
        step2=step2_data,
        breakdown=breakdown,
        client_view=client_view,
        work_breakdowns=work_breakdowns,
        aggregated_summary=aggregated_summary,
        internal_notes=internal_notes,
        show_internal_notes=show_internal_notes,
        estimated_by_name=estimated_by_name,
    )
    context["quote_number"] = step1.quote_number
    return render_eworks_estimate_document(context, is_draft=is_draft)
