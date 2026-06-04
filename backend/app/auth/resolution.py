"""Resolve dev-authenticated users from the database with env fallback."""

from __future__ import annotations

import secrets

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.types import AuthenticatedUser
from app.core.config import Settings, settings
from app.core.security import UserRole, get_password_hash
from app.models.user import User


def parse_user_role(role_value: str) -> UserRole:
    try:
        return UserRole(role_value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication configuration",
        ) from exc


def lookup_user_by_email(db: Session, email: str) -> User | None:
    normalized = email.strip().lower()
    if not normalized:
        return None
    return db.scalar(select(User).where(func.lower(User.email) == normalized))


def _db_user_to_authenticated(user: User, *, auth_provider: str = "dev") -> AuthenticatedUser:
    return AuthenticatedUser(
        id=str(user.id),
        email=user.email,
        name=user.full_name,
        role=parse_user_role(user.role),
        is_active=user.is_active,
        auth_provider=auth_provider,
    )


def _env_user_to_authenticated(config: Settings) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=config.dev_user_id,
        email=config.dev_user_email,
        name=config.dev_user_name,
        role=parse_user_role(config.dev_user_role),
        is_active=config.dev_user_is_active,
        auth_provider="dev",
    )


def _auto_create_dev_user(db: Session, config: Settings) -> User:
    user = User(
        email=config.dev_user_email.strip(),
        full_name=config.dev_user_name,
        password_hash=get_password_hash(secrets.token_urlsafe(32)),
        role=parse_user_role(config.dev_user_role).value,
        is_active=True,
    )
    db.add(user)
    db.flush()
    db.commit()
    db.refresh(user)
    return user


def resolve_db_user_by_email(
    db: Session,
    email: str,
    *,
    auth_provider: str,
    not_registered_detail: str = "User not registered",
) -> AuthenticatedUser:
    """Map an identity email to a registered users-table row (case-insensitive)."""
    db_user = lookup_user_by_email(db, email)
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=not_registered_detail)

    user = _db_user_to_authenticated(db_user, auth_provider=auth_provider)
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
    return user


def resolve_azure_authenticated_user(db: Session, claims) -> AuthenticatedUser:
    """Map validated Azure token claims to a DB-backed AuthenticatedUser."""
    from app.auth.providers.azure import AzureTokenClaims

    if not isinstance(claims, AzureTokenClaims):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    return resolve_db_user_by_email(
        db,
        claims.email,
        auth_provider="azure",
        not_registered_detail="User not registered",
    )


def resolve_dev_authenticated_user(db: Session, config: Settings | None = None) -> AuthenticatedUser:
    """Resolve the current dev user: DB match by email, optional auto-create, then env fallback."""
    config = config or settings

    if not config.dev_auth_enabled:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    db_user = lookup_user_by_email(db, config.dev_user_email)
    if db_user is not None:
        user = _db_user_to_authenticated(db_user, auth_provider="dev")
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
        return user

    if config.dev_auth_auto_create_user:
        db_user = _auto_create_dev_user(db, config)
        return _db_user_to_authenticated(db_user, auth_provider="dev")

    user = _env_user_to_authenticated(config)
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
    return user
