from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.auth.dependencies import AuthenticatedUser, require_roles
from app.core.exceptions import AppError, success_response
from app.core.security import UserRole
from app.db.session import DbSession
from app.schemas.manager_dashboard import ManagerDashboardRead
from app.schemas.quote_job_assignment import AssignQuoteJobRequest, AssignQuoteJobResponse
from app.services.audit_helpers import record_audit
from app.services.manager_dashboard_service import get_manager_dashboard
from app.services.manager_quote_pdf_service import render_manager_quote_pdf
from app.services.quote_job_assignment_service import assign_quote_job

router = APIRouter(prefix="/manager", tags=["manager"])


@router.get("/dashboard")
def get_manager_dashboard_endpoint(
    db: DbSession,
    limit_per_category: int = Query(default=10, ge=1, le=50),
    _user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
):
    """Return synced eWorks quote categories for the manager dashboard (local DB only)."""
    data = get_manager_dashboard(db, limit_per_category=limit_per_category)
    return success_response(ManagerDashboardRead.model_validate(data).model_dump())


@router.post("/quotes/{quote_ref}/assign-job")
def assign_quote_job_endpoint(
    quote_ref: str,
    body: AssignQuoteJobRequest,
    db: DbSession,
    user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
):
    """Record manager decision to select a submitted estimate (not an eWorks job assignment)."""
    try:
        decision = assign_quote_job(db, quote_ref=quote_ref, payload=body, actor=user)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return success_response(AssignQuoteJobResponse(decision=decision).model_dump(mode="json"))


@router.get("/quotes/{session_id}/pdf/{view}")
def download_manager_quote_pdf(
    session_id: UUID,
    view: Literal["client", "internal", "combined", "all-trades"],
    db: DbSession,
    user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
    version: int | None = Query(default=None, ge=1),
):
    """Download client, internal, combined, or all-trades PDF for a submitted quote session."""
    try:
        content, file_name, media_type = render_manager_quote_pdf(
            db,
            session_id=session_id,
            view=view,
            version_number=version,
        )
        record_audit(
            db,
            actor=user,
            action="manager_quote_pdf_downloaded",
            entity_type="calculation_session",
            entity_id=session_id,
            metadata={"file_name": file_name, "view": view, "version": version},
        )
        db.commit()
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )
