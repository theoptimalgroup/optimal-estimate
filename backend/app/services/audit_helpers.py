"""Helpers for recording audit events from API endpoints."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.dependencies import DashboardAccess
from app.auth.types import AuthenticatedUser
from app.services.audit_log_service import create_audit_log

logger = logging.getLogger(__name__)


def snapshot_model(model: Any, *, exclude: set[str] | None = None) -> dict[str, Any]:
    excluded = exclude or set()
    data: dict[str, Any] = {}
    for column in model.__table__.columns:
        key = column.name
        if key in excluded:
            continue
        value = getattr(model, key)
        if isinstance(value, UUID):
            data[key] = str(value)
        else:
            data[key] = value
    return data


def record_audit(
    db: Session,
    *,
    actor: AuthenticatedUser | None,
    action: str,
    entity_type: str,
    entity_id: UUID | str | int | None,
    before: dict | None = None,
    after: dict | None = None,
    metadata: dict | None = None,
    ip_address: str | None = None,
) -> None:
    try:
        with db.begin_nested():
            create_audit_log(
                db,
                actor_user_id=actor.id if actor else None,
                actor_email=actor.email if actor else None,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                before=before,
                after=after,
                metadata=metadata,
                ip_address=ip_address,
            )
    except Exception:
        logger.exception("Failed to write audit log for action=%s entity_type=%s", action, entity_type)


def record_dashboard_audit(
    db: Session,
    *,
    access: DashboardAccess,
    action: str,
    entity_type: str,
    entity_id: UUID | str | int | None,
    before: dict | None = None,
    after: dict | None = None,
    metadata: dict | None = None,
) -> None:
    actor = access.user
    meta = dict(metadata or {})
    if access.method == "password":
        meta.setdefault("auth_method", "dashboard_password")
        meta.setdefault("actor_email", "dashboard-password")
    try:
        with db.begin_nested():
            create_audit_log(
                db,
                actor_user_id=actor.id if actor else None,
                actor_email=actor.email if actor else meta.get("actor_email"),
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                before=before,
                after=after,
                metadata=meta,
            )
    except Exception:
        logger.exception("Failed to write dashboard audit log for action=%s", action)
