"""Shared Call Back dashboard HTTP handlers."""

from __future__ import annotations

from app.db.session import DbSession
from app.schemas.call_back_dashboard import CallBackDashboardRead
from app.services.call_back_dashboard_service import get_call_back_dashboard


def fetch_call_back_dashboard_payload(db: DbSession, *, search: str | None = None) -> dict:
    """Build the Call Back dashboard response payload (single source of truth)."""
    data = get_call_back_dashboard(db, search=search)
    return CallBackDashboardRead.model_validate(data).model_dump()
