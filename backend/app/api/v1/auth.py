import logging

from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import AuthenticatedUser, get_current_user
from app.auth.schemas import CurrentUserRead
from app.core.exceptions import success_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
def get_me(request: Request, user: AuthenticatedUser = Depends(get_current_user)):
    logger.debug("GET /auth/me auth_header=%s", request.headers.get("authorization", "MISSING")[:40])
    return success_response(
        CurrentUserRead(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role,
            is_active=user.is_active,
            auth_provider=user.auth_provider,
        )
    )
