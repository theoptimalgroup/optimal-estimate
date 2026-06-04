from fastapi import APIRouter, Depends

from app.auth.dependencies import AuthenticatedUser, require_roles
from app.core.config import settings
from app.core.exceptions import success_response
from app.core.security import UserRole
from app.db.session import DbSession
from app.schemas.settings import SettingsRead, SettingsStatusRead
from app.services.settings_service import get_safe_settings, get_settings_status

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
def get_settings_endpoint(
    _user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN)),
):
    payload = get_safe_settings(settings)
    return success_response(SettingsRead.model_validate(payload))


@router.get("/status")
def get_settings_status_endpoint(
    db: DbSession,
    _user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN)),
):
    status = get_settings_status(db)
    return success_response(SettingsStatusRead.model_validate(status))
