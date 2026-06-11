from fastapi import APIRouter, Depends, Query

from app.api.v1.processed_dashboard_routes import fetch_processed_dashboard_payload
from app.auth.dependencies import AuthenticatedUser, require_roles
from app.core.config import settings
from app.core.exceptions import success_response
from app.core.security import UserRole
from app.db.session import DbSession
from app.schemas.admin_dashboard import AdminDashboardRead, AdminDashboardStats
from app.services.manager_dashboard_service import get_manager_dashboard
from app.services.settings_service import get_safe_settings, get_settings_status

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard")
def get_admin_dashboard_endpoint(
    db: DbSession,
    limit_per_category: int = Query(default=10, ge=1, le=50),
    search: str | None = Query(default=None, max_length=200),
    _user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN)),
):
    """Return synced eWorks quote categories for the admin dashboard (local DB only)."""
    data = get_manager_dashboard(
        db,
        limit_per_category=limit_per_category,
        search=search,
    )
    status = get_settings_status(db)
    safe_settings = get_safe_settings(settings)

    payload = {
        **data,
        "admin_stats": AdminDashboardStats(
            users=status.counts.users,
            products=status.counts.products,
            audit_logs=status.counts.audit_logs,
            eworks_api_enabled=safe_settings.eworks.api_enabled,
            database_reachable=status.database_reachable,
        ),
    }
    return success_response(AdminDashboardRead.model_validate(payload).model_dump())


@router.get("/processed-dashboard")
def get_admin_processed_dashboard_endpoint(
    db: DbSession,
    search: str | None = Query(default=None, max_length=200),
    _user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN)),
):
    """Return sales pipeline dashboard for processed eWorks quotes (local DB only)."""
    return success_response(fetch_processed_dashboard_payload(db, search=search))
