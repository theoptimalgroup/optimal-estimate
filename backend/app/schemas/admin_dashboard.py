from __future__ import annotations

from pydantic import BaseModel

from app.schemas.manager_dashboard import ManagerDashboardRead


class AdminDashboardStats(BaseModel):
    users: int
    products: int
    audit_logs: int
    eworks_api_enabled: bool
    database_reachable: bool


class AdminDashboardRead(ManagerDashboardRead):
    admin_stats: AdminDashboardStats
