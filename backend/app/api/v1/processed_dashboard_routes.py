"""Shared Sales Pipeline processed-dashboard HTTP handlers."""

from __future__ import annotations

from app.db.session import DbSession
from app.schemas.processed_dashboard import ProcessedDashboardRead
from app.services.processed_dashboard_service import get_processed_dashboard


def fetch_processed_dashboard_payload(db: DbSession, *, search: str | None = None) -> dict:
    """Build the processed dashboard response payload (single source of truth)."""
    data = get_processed_dashboard(db, search=search)
    return ProcessedDashboardRead.model_validate(data).model_dump()
