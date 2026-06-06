from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.auth.dependencies import DashboardAccess, require_dashboard_access
from app.core.exceptions import AppError, success_response
from app.db.session import DbSession
from app.schemas.eworks_link import (
    CombinedPdfRequest,
    CombineWorkNotesRequest,
    CombineWorkNotesResponse,
    DashboardQuotesResponse,
    ReopenQuoteResponse,
)
from app.services.audit_helpers import record_dashboard_audit
from app.services.calculation_session_service import (
    combine_selected_work_internal_notes,
    get_submitted_quote_group_detail,
    list_submitted_quote_groups,
    list_submitted_quotes,
    reopen_submitted_session,
    render_combined_works_pdf,
)
from app.schemas.dashboard_quote_groups import (
    DashboardQuoteGroupDetailResponse,
    DashboardQuoteGroupsResponse,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/quotes")
def get_submitted_quotes(db: DbSession, _auth=Depends(require_dashboard_access)):
    result = list_submitted_quotes(db)
    return success_response(DashboardQuotesResponse.model_validate(result))


@router.get("/quote-groups")
def get_submitted_quote_groups(db: DbSession, _auth=Depends(require_dashboard_access)):
    result = list_submitted_quote_groups(db)
    return success_response(
        DashboardQuoteGroupsResponse.model_validate(result).model_dump(mode="json"),
        meta={"total": len(result.groups)},
    )


@router.get("/quote-groups/detail")
def get_submitted_quote_group_detail_endpoint(
    db: DbSession,
    _auth=Depends(require_dashboard_access),
    group_key: str | None = Query(default=None),
    quote_ref: str | None = Query(default=None),
    eworks_quote_id: int | None = Query(default=None),
):
    if not group_key and not quote_ref and eworks_quote_id is None:
        raise HTTPException(status_code=400, detail="group_key, quote_ref, or eworks_quote_id is required")
    result = get_submitted_quote_group_detail(
        db,
        group_key=group_key,
        quote_ref=quote_ref,
        eworks_quote_id=eworks_quote_id,
    )
    return success_response(DashboardQuoteGroupDetailResponse.model_validate(result).model_dump(mode="json"))


@router.post("/quotes/{session_id}/reopen")
def reopen_quote(session_id: UUID, db: DbSession, auth: DashboardAccess = Depends(require_dashboard_access)):
    try:
        result = reopen_submitted_session(db, session_id=session_id)
        record_dashboard_audit(
            db,
            access=auth,
            action="quote_reopened",
            entity_type="calculation_session",
            entity_id=session_id,
            after={"status": "in_progress"},
        )
        db.commit()
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return success_response(ReopenQuoteResponse.model_validate(result))


@router.post("/quotes/{session_id}/combine-notes")
def combine_work_notes(
    session_id: UUID,
    payload: CombineWorkNotesRequest,
    db: DbSession,
    _auth=Depends(require_dashboard_access),
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
    auth: DashboardAccess = Depends(require_dashboard_access),
):
    try:
        content, file_name, media_type = render_combined_works_pdf(
            db,
            session_id=session_id,
            work_indexes=payload.work_indexes,
            view_type=payload.view_type,
        )
        record_dashboard_audit(
            db,
            access=auth,
            action="combined_pdf_generated",
            entity_type="calculation_session",
            entity_id=session_id,
            metadata={"file_name": file_name, "view_type": payload.view_type, "work_indexes": payload.work_indexes},
        )
        db.commit()
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )
