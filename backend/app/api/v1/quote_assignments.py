"""Quote assignment APIs for synced eWorks quotes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth.dependencies import AuthenticatedUser, require_roles
from app.core.exceptions import success_response
from app.core.security import UserRole
from app.db.session import DbSession
from app.schemas.quote_assignment import (
    AssigneeUserRead,
    AssignmentCreate,
    AssignmentPublicRead,
    AssignmentPublicSubmit,
    AssignmentRead,
    AssignmentStartEstimateRead,
    AssignmentUpdateStatus,
)
from app.services.quote_assignment_service import (
    build_public_assignment_read,
    get_assignment_by_token,
    list_assignable_users,
    list_assignments_for_user,
    revoke_assignment,
    start_assignment_estimate,
    start_public_assignment_estimate,
    submit_public_assignment,
    update_assignment_status,
)

router = APIRouter(prefix="/quote-assignments", tags=["quote-assignments"])


@router.get("/assignees")
def list_assignees(
    db: DbSession,
    _user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
):
    items = list_assignable_users(db)
    return success_response([AssigneeUserRead.model_validate(item).model_dump() for item in items])


@router.get("/my")
def list_my_assignments(
    db: DbSession,
    user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN, UserRole.ESTIMATOR, UserRole.ENGINEER)),
):
    items = list_assignments_for_user(db, user)
    return success_response(
        [AssignmentRead.model_validate(item).model_dump() for item in items],
        meta={"total": len(items)},
    )


@router.post("/{assignment_id}/start-estimate")
def start_assignment_estimate_endpoint(
    assignment_id: int,
    db: DbSession,
    user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN, UserRole.ESTIMATOR, UserRole.ENGINEER)),
):
    data = start_assignment_estimate(db, assignment_id, user)
    data.pop("created", None)
    return success_response(AssignmentStartEstimateRead.model_validate(data).model_dump())


@router.post("/{assignment_id}/revoke")
def revoke_assignment_endpoint(
    assignment_id: int,
    db: DbSession,
    user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
):
    data = revoke_assignment(db, assignment_id, user)
    return success_response(AssignmentRead.model_validate(data).model_dump())


@router.patch("/{assignment_id}/status")
def update_assignment_status_endpoint(
    assignment_id: int,
    body: AssignmentUpdateStatus,
    db: DbSession,
    user: AuthenticatedUser = Depends(
        require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.ESTIMATOR, UserRole.ENGINEER)
    ),
):
    data = update_assignment_status(db, assignment_id, body.status, user)
    return success_response(AssignmentRead.model_validate(data).model_dump())


@router.get("/public/{assignment_token}")
def get_public_assignment(assignment_token: str, db: DbSession):
    row = get_assignment_by_token(db, assignment_token)
    data = build_public_assignment_read(db, row)
    return success_response(AssignmentPublicRead.model_validate(data).model_dump())


@router.post("/public/{assignment_token}/submit")
def submit_public_assignment_endpoint(
    assignment_token: str,
    body: AssignmentPublicSubmit,
    db: DbSession,
):
    data = submit_public_assignment(db, assignment_token, body.notes)
    return success_response(AssignmentPublicRead.model_validate(data).model_dump())


@router.post("/public/{assignment_token}/start-estimate")
def start_public_assignment_estimate_endpoint(assignment_token: str, db: DbSession):
    data = start_public_assignment_estimate(db, assignment_token)
    return success_response(AssignmentStartEstimateRead.model_validate(data).model_dump())
