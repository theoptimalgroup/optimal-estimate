from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import AuthenticatedUser, require_roles
from app.core.exceptions import success_response
from app.core.security import UserRole
from app.db.session import DbSession
from app.schemas.manager_dashboard import ManagerDashboardRead
from app.services.manager_dashboard_service import get_manager_dashboard

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
