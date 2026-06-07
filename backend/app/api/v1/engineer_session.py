from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import ValidationError as PydanticValidationError

from app.auth.dependencies import AuthenticatedUser, require_roles
from app.core.exceptions import AppError, success_response
from app.core.security import UserRole
from app.db.session import DbSession
from app.schemas.engineer_session import EngineerSiteVisitUpdate
from app.schemas.quote_job_assignment import EngineerAssignedJobRead
from app.services.engineer_session_service import get_engineer_session, update_engineer_site_visit
from app.services.quote_job_assignment_service import list_assigned_jobs_for_engineer

router = APIRouter(prefix="/engineer", tags=["engineer"])


@router.get("/jobs/assigned")
def list_engineer_assigned_jobs(
    db: DbSession,
    _user: AuthenticatedUser = Depends(require_roles(UserRole.ENGINEER)),
):
    items = list_assigned_jobs_for_engineer(db, _user)
    return success_response(
        [EngineerAssignedJobRead.model_validate(item).model_dump(mode="json") for item in items],
        meta={"total": len(items)},
    )


def _require_session_token(
    x_session_token: str | None = Header(default=None, alias="X-Session-Token"),
) -> str:
    if not x_session_token:
        raise HTTPException(status_code=401, detail="Missing session token")
    return x_session_token


@router.get("/sessions/{session_id}")
def read_engineer_session(
    session_id: UUID,
    db: DbSession,
    _user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN, UserRole.ENGINEER)),
    session_token: str = Depends(_require_session_token),
):
    try:
        result = get_engineer_session(db, session_id=session_id, session_token=session_token)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return success_response(result)


@router.put("/sessions/{session_id}/site-visit")
def save_engineer_site_visit(
    session_id: UUID,
    payload: EngineerSiteVisitUpdate,
    db: DbSession,
    _user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN, UserRole.ENGINEER)),
    session_token: str = Depends(_require_session_token),
):
    try:
        payload.model_validate_duration()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PydanticValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    try:
        result = update_engineer_site_visit(
            db,
            session_id=session_id,
            session_token=session_token,
            payload=payload,
        )
        db.commit()
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return success_response(result)
