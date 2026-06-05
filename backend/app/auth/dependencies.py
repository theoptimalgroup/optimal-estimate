import logging
from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.providers.azure import validate_azure_access_token
from app.auth.resolution import resolve_azure_authenticated_user, resolve_dev_authenticated_user
from app.auth.types import AuthenticatedUser
from app.core.config import settings
from app.core.security import UserRole
from app.db.session import DbSession

logger = logging.getLogger(__name__)
_bearer = HTTPBearer(auto_error=False)

DASHBOARD_ALLOWED_ROLES = frozenset({UserRole.ADMIN, UserRole.MANAGER, UserRole.ESTIMATOR})
DASHBOARD_BLOCKED_ROLES = frozenset({UserRole.ENGINEER, UserRole.CLIENT})


def _resolve_azure_user(
    db: DbSession,
    credentials: HTTPAuthorizationCredentials | None,
) -> AuthenticatedUser:
    if credentials is None or not credentials.credentials:
        logger.warning("Azure auth: no Bearer token in request")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token_prefix = credentials.credentials[:20] if credentials.credentials else "EMPTY"
    logger.info("Azure auth: validating token prefix=%s...", token_prefix)
    try:
        claims = validate_azure_access_token(credentials.credentials, settings)
    except HTTPException as exc:
        logger.warning("Azure auth: token validation failed detail=%s", exc.detail)
        raise
    return resolve_azure_authenticated_user(db, claims)


def get_current_user(
    db: DbSession,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AuthenticatedUser:
    if settings.auth_provider == "azure":
        return _resolve_azure_user(db, credentials)
    return resolve_dev_authenticated_user(db, settings)


def try_get_optional_current_user(
    db: DbSession,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AuthenticatedUser | None:
    """Resolve authenticated user when provider credentials are present; else None."""
    if settings.auth_provider == "azure":
        if credentials is None or not credentials.credentials:
            return None
        try:
            return _resolve_azure_user(db, credentials)
        except HTTPException:
            return None

    if not settings.dev_auth_enabled:
        return None
    return resolve_dev_authenticated_user(db, settings)


def _is_valid_dashboard_password(password: str | None) -> bool:
    return bool(password and password == settings.dashboard_password)


@dataclass(frozen=True)
class DashboardAccess:
    method: Literal["user", "password"]
    user: AuthenticatedUser | None = None


@dataclass(frozen=True)
class ProductSyncAccess:
    method: Literal["user", "password"]
    user: AuthenticatedUser | None = None


def require_dashboard_access(
    user: Annotated[AuthenticatedUser | None, Depends(try_get_optional_current_user)],
    x_dashboard_password: str | None = Header(default=None, alias="X-Dashboard-Password"),
) -> DashboardAccess:
    """Allow staff roles via dev/Bearer auth, or legacy X-Dashboard-Password fallback."""
    if user is not None:
        if user.role in DASHBOARD_ALLOWED_ROLES:
            return DashboardAccess(method="user", user=user)
        if user.role in DASHBOARD_BLOCKED_ROLES:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    if _is_valid_dashboard_password(x_dashboard_password):
        return DashboardAccess(method="password")

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid dashboard password")


def require_product_sync_access(
    user: Annotated[AuthenticatedUser | None, Depends(try_get_optional_current_user)],
    x_dashboard_password: str | None = Header(default=None, alias="X-Dashboard-Password"),
) -> ProductSyncAccess:
    """Allow admin via dev/Bearer auth, or legacy X-Dashboard-Password fallback."""
    if user is not None:
        if user.role == UserRole.ADMIN:
            return ProductSyncAccess(method="user", user=user)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    if _is_valid_dashboard_password(x_dashboard_password):
        return ProductSyncAccess(method="password")

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid dashboard password")


def require_roles(*allowed_roles: UserRole):
    allowed = set(allowed_roles)

    def dependency(user: Annotated[AuthenticatedUser, Depends(get_current_user)]) -> AuthenticatedUser:
        if user.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return dependency


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
