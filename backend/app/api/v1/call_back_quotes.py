from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import AuthenticatedUser, require_roles
from app.core.exceptions import AppError, success_response
from app.core.security import UserRole
from app.db.session import DbSession
from app.schemas.call_back_dashboard import CallBackTrackingPatch, CallBackTrackingRead
from app.services.call_back_dashboard_service import patch_call_back_tracking, tracking_row_to_read

router = APIRouter(prefix="/call-back-quotes", tags=["call-back-quotes"])


@router.patch("/{quote_id}/tracking")
def patch_call_back_quote_tracking(
    quote_id: int,
    body: CallBackTrackingPatch,
    db: DbSession,
    user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
):
    """Update local call-back tracking fields (never writes to eWorks)."""
    try:
        row = patch_call_back_tracking(db, quote_id, body, user)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return success_response(CallBackTrackingRead.model_validate(tracking_row_to_read(row)).model_dump())
