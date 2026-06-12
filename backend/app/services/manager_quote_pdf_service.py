from __future__ import annotations

from typing import Literal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.calculation_session import CalculationSession
from app.schemas.eworks_link import Step1Snapshot, Step2Snapshot
from app.services.calculation_session_pdf_service import render_session_quote_pdf
from app.services.calculation_session_service import render_combined_works_pdf
from app.services.pdf_calculation_context_service import build_pdf_calculation_context
from app.services.eworks_pdf_context_service import build_all_trades_pdf_context
from app.services.pdf_estimator_identity_service import resolve_estimated_by_for_pdf

ManagerQuotePdfView = Literal["client", "internal", "combined", "all-trades"]


def _require_submitted_session(db: Session, session_id: UUID) -> CalculationSession:
    session = db.get(CalculationSession, session_id)
    if session is None:
        raise AppError("SESSION_NOT_FOUND", "Quote session not found", 404)
    if session.status != "submitted":
        raise AppError("SESSION_NOT_SUBMITTED", "PDF is only available for submitted quotes", 409)
    if not session.step2_snapshot:
        raise AppError("STEP2_REQUIRED", "No saved work data for this quote", 400)
    return session


def _all_work_indexes(session: CalculationSession) -> list[int]:
    step2 = Step2Snapshot.model_validate(session.step2_snapshot)
    if not step2.works:
        raise AppError("WORKS_REQUIRED", "No works found for this quote", 400)
    return list(range(len(step2.works)))


def render_all_trades_quote_pdf(
    db: Session,
    *,
    session: CalculationSession,
    version_number: int | None = None,
    current_user=None,
) -> tuple[bytes, str, str]:
    from app.adapters.pdf_renderer import render_all_trades_document

    pdf_ctx = build_pdf_calculation_context(
        db,
        session,
        allow_recalculate=False,
        version_number=version_number,
        view_type="all-trades",
    )
    if not pdf_ctx.step2.works:
        raise AppError("WORKS_REQUIRED", "No works found for this quote", 400)

    breakdown = pdf_ctx.breakdown.model_dump(mode="json")
    work_breakdowns = [item.model_dump(mode="json") for item in pdf_ctx.work_breakdowns]
    try:
        estimated_by_name = resolve_estimated_by_for_pdf(db, session, pdf_ctx.step1, current_user=current_user)
        context = build_all_trades_pdf_context(
            db=db,
            step1=pdf_ctx.step1,
            step2=pdf_ctx.step2,
            breakdown=breakdown,
            work_breakdowns=work_breakdowns,
            estimated_by_name=estimated_by_name,
        )
    except ValueError as exc:
        raise AppError("CALCULATION_REQUIRED", str(exc), 400) from exc

    return render_all_trades_document(context)


def render_manager_quote_pdf(
    db: Session,
    *,
    session_id: UUID,
    view: ManagerQuotePdfView,
    version_number: int | None = None,
    current_user=None,
) -> tuple[bytes, str, str]:
    session = _require_submitted_session(db, session_id)
    original_step1 = dict(session.step1_snapshot or {})
    original_step2 = dict(session.step2_snapshot) if session.step2_snapshot else None
    original_ui_state = dict(session.ui_state) if isinstance(session.ui_state, dict) else session.ui_state
    try:
        if version_number is not None:
            from app.services.calculation_session_revision_service import (
                apply_version_snapshot_to_session,
                get_session_version,
            )

            version = get_session_version(db, session_id=session_id, version_number=version_number)
            apply_version_snapshot_to_session(db, version)
        if view == "combined":
            return render_session_quote_pdf(
                db,
                session_id=session_id,
                session_token=session.session_token,
                read_only=True,
                current_user=current_user,
            )
        if view == "all-trades":
            return render_all_trades_quote_pdf(
                db,
                session=session,
                version_number=version_number,
                current_user=current_user,
            )
        view_type = "client" if view == "client" else "optimal"
        return render_combined_works_pdf(
            db,
            session_id=session_id,
            work_indexes=_all_work_indexes(session),
            view_type=view_type,
            version_number=version_number,
            current_user=current_user,
        )
    finally:
        session.step1_snapshot = original_step1
        session.step2_snapshot = original_step2
        session.ui_state = original_ui_state
