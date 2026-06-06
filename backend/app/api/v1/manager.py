from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.dependencies import AuthenticatedUser, require_roles
from app.core.exceptions import AppError, success_response
from app.core.security import UserRole
from app.db.session import DbSession
from app.schemas.manager_dashboard import ManagerDashboardRead
from app.schemas.quote_job_assignment import AssignQuoteJobRequest, AssignQuoteJobResponse
from app.services.manager_dashboard_service import get_manager_dashboard
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
    """Record manager decision to assign the job to a selected submitted estimate."""
    try:
        decision = assign_quote_job(db, quote_ref=quote_ref, payload=body, actor=user)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return success_response(AssignQuoteJobResponse(decision=decision).model_dump(mode="json"))
