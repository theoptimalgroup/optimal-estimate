from uuid import UUID

from sqlalchemy.orm import Session

from app.adapters.pdf_renderer import render_eworks_estimate_document
from app.core.exceptions import AppError
from app.schemas.eworks_link import Step1Snapshot, Step2Snapshot
from app.services.calculation_session_service import calculate_session
from app.services.calculation_view_service import build_client_view_from_session
from app.services.eworks_link_service import get_session_by_token
from app.services.eworks_pdf_context_service import build_eworks_estimate_pdf_context
from app.services.eworks_questionnaire_service import work_block_to_step2_snapshot


def render_session_quote_pdf(
    db: Session,
    *,
    session_id: UUID,
    session_token: str,
    is_draft: bool = False,
) -> tuple[bytes, str, str]:
    session = get_session_by_token(db, session_id, session_token)
    if not session.step2_snapshot:
        raise AppError("STEP2_REQUIRED", "Estimator inputs are required before generating PDF", 400)

    step1 = Step1Snapshot.model_validate(session.step1_snapshot)
    step2_data = Step2Snapshot.model_validate(session.step2_snapshot)
    result = calculate_session(
        db=db,
        session_id=session_id,
        session_token=session_token,
        step2=None,
    )
    primary_step2 = work_block_to_step2_snapshot(step2_data.works[0], trade_name=step1.trade_name)
    combined_scope = "\n\n".join(
        block.scope.strip() for block in step2_data.works if block.scope and block.scope.strip()
    )
    primary_step2 = primary_step2.model_copy(update={"scope": combined_scope})
    client_view = build_client_view_from_session(session, result.breakdown, step1, primary_step2)
    context = build_eworks_estimate_pdf_context(
        step1=step1,
        step2=step2_data,
        breakdown=result.breakdown,
        client_view=client_view,
    )
    context["quote_number"] = step1.quote_number
    return render_eworks_estimate_document(context, is_draft=is_draft)
