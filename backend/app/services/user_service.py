import secrets
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.auth.resolution import lookup_user_by_email
from app.core.config import settings
from app.core.security import UserRole, get_password_hash
from app.models.user import User
from app.schemas.user import UserRead


def _auth_provider_for_registered_user() -> str:
    return "azure" if settings.auth_provider == "azure" else "local"


def user_to_read(user: User, *, auth_provider: str | None = None) -> UserRead:
    return UserRead(
        id=user.id,
        email=user.email,
        name=user.full_name,
        role=UserRole(user.role),
        is_active=user.is_active,
        auth_provider=auth_provider or _auth_provider_for_registered_user(),
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def list_users(
    db: Session,
    *,
    search: str | None = None,
    role: str | None = None,
    active: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[UserRead], int]:
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)

    query = select(User)

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                User.email.ilike(term),
                User.full_name.ilike(term),
            )
        )

    if role:
        query = query.where(User.role == role)

    if active is not None:
        query = query.where(User.is_active.is_(active))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    users = db.scalars(query.order_by(User.full_name, User.email).offset(offset).limit(limit)).all()
    return [user_to_read(user) for user in users], total


def get_user(db: Session, user_id: UUID) -> UserRead | None:
    user = db.get(User, user_id)
    if user is None:
        return None
    return user_to_read(user)


def create_user(
    db: Session,
    *,
    email: str,
    name: str,
    role: UserRole,
    is_active: bool = True,
) -> UserRead:
    normalized_email = email.strip().lower()
    if not normalized_email:
        raise ValueError("Email is required")

    trimmed_name = name.strip()
    if not trimmed_name:
        raise ValueError("Name is required")

    if lookup_user_by_email(db, normalized_email) is not None:
        raise ValueError("A user with this email already exists")

    user = User(
        email=normalized_email,
        full_name=trimmed_name,
        password_hash=get_password_hash(secrets.token_urlsafe(32)),
        role=role.value,
        is_active=is_active,
    )
    db.add(user)
    db.flush()
    return user_to_read(user)


def update_user(
    db: Session,
    user_id: UUID,
    *,
    name: str | None = None,
    role: UserRole | None = None,
    is_active: bool | None = None,
    actor_email: str | None = None,
) -> UserRead | None:
    user = db.get(User, user_id)
    if user is None:
        return None

    if name is not None:
        trimmed = name.strip()
        if not trimmed:
            raise ValueError("Name is required")
        user.full_name = trimmed

    if role is not None:
        user.role = role.value

    if is_active is not None:
        if is_active is False and actor_email and user.email.lower() == actor_email.lower():
            raise ValueError("You cannot deactivate your own account")
        user.is_active = is_active

    db.flush()
    return user_to_read(user)
