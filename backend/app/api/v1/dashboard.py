from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import Response

from app.core.config import settings
from app.core.exceptions import AppError, success_response
from app.db.session import DbSession
from app.schemas.eworks_link import (
    CombinedPdfRequest,
    CombineWorkNotesRequest,
    CombineWorkNotesResponse,
    DashboardQuotesResponse,
    ReopenQuoteResponse,
)
from app.services.calculation_session_service import (
    combine_selected_work_internal_notes,
    list_submitted_quotes,
    reopen_submitted_session,
    render_combined_works_pdf,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _require_dashboard_password(
    x_dashboard_password: str | None = Header(default=None, alias="X-Dashboard-Password"),
) -> None:
    if not x_dashboard_password or x_dashboard_password != settings.dashboard_password:
        raise HTTPException(status_code=401, detail="Invalid dashboard password")


@router.get("/quotes")
def get_submitted_quotes(db: DbSession, _auth=Depends(_require_dashboard_password)):
    result = list_submitted_quotes(db)
    return success_response(DashboardQuotesResponse.model_validate(result))


@router.post("/quotes/{session_id}/reopen")
def reopen_quote(session_id: UUID, db: DbSession, _auth=Depends(_require_dashboard_password)):
    try:
        result = reopen_submitted_session(db, session_id=session_id)
        db.commit()
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return success_response(ReopenQuoteResponse.model_validate(result))


@router.post("/quotes/{session_id}/combine-notes")
def combine_work_notes(
    session_id: UUID,
    payload: CombineWorkNotesRequest,
    db: DbSession,
    _auth=Depends(_require_dashboard_password),
):
    try:
        result = combine_selected_work_internal_notes(
            db,
            session_id=session_id,
            work_indexes=payload.work_indexes,
        )
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return success_response(CombineWorkNotesResponse.model_validate(result))


@router.post("/quotes/{session_id}/combined-pdf")
def download_combined_pdf(
    session_id: UUID,
    payload: CombinedPdfRequest,
    db: DbSession,
    _auth=Depends(_require_dashboard_password),
):
    try:
        content, file_name, media_type = render_combined_works_pdf(
            db,
            session_id=session_id,
            work_indexes=payload.work_indexes,
            view_type=payload.view_type,
        )
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )
