from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.dependencies import AuthenticatedUser, require_roles
from app.core.exceptions import success_response
from app.core.security import UserRole
from app.db.session import DbSession
from app.models.user import User
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.audit_helpers import record_audit, snapshot_model
from app.services.user_service import create_user, get_user, list_users, update_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
def list_users_endpoint(
    db: DbSession,
    search: str | None = Query(None),
    role: UserRole | None = Query(None),
    active: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN)),
):
    users, total = list_users(
        db,
        search=search,
        role=role.value if role else None,
        active=active,
        limit=limit,
        offset=offset,
    )
    return success_response(users, meta={"total": total, "limit": limit, "offset": offset})


@router.post("")
def create_user_endpoint(
    body: UserCreate,
    db: DbSession,
    actor: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN)),
):
    try:
        user = create_user(
            db,
            email=str(body.email),
            name=body.name,
            role=body.role,
            is_active=body.is_active,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    record_audit(
        db,
        actor=actor,
        action="user_created",
        entity_type="user",
        entity_id=user.id,
        before=None,
        after=user.model_dump(mode="json"),
    )
    db.commit()
    return success_response(user)


@router.get("/{user_id}")
def get_user_endpoint(
    user_id: UUID,
    db: DbSession,
    _user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN)),
):
    user = get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return success_response(user)


@router.patch("/{user_id}")
def update_user_endpoint(
    user_id: UUID,
    body: UserUpdate,
    db: DbSession,
    actor: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN)),
):
    payload = body.model_dump(exclude_unset=True)
    if not payload:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        existing = db.get(User, user_id)
        before = snapshot_model(existing, exclude={"password_hash"}) if existing else None
        user = update_user(
            db,
            user_id,
            name=payload.get("name"),
            role=payload.get("role"),
            is_active=payload.get("is_active"),
            actor_email=actor.email,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    record_audit(
        db,
        actor=actor,
        action="user_updated",
        entity_type="user",
        entity_id=user_id,
        before=before,
        after=user.model_dump(mode="json"),
    )
    db.commit()
    return success_response(user)
