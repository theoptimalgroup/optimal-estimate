from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.support import AuditLog
from app.models.user import User

REDACTED = "***REDACTED***"

SENSITIVE_KEY_PATTERN = re.compile(
    r"(password|password_hash|token|session_token|api_key|secret|authorization|dashboard_password)",
    re.IGNORECASE,
)


def _json_safe(data: Any) -> Any:
    if isinstance(data, dict):
        return {key: _json_safe(value) for key, value in data.items()}
    if isinstance(data, list):
        return [_json_safe(item) for item in data]
    if isinstance(data, (datetime, date)):
        return data.isoformat()
    if isinstance(data, Decimal):
        return str(data)
    if isinstance(data, UUID):
        return str(data)
    return data


def redact_sensitive_fields(data: Any) -> Any:
    if isinstance(data, dict):
        redacted: dict[str, Any] = {}
        for key, value in data.items():
            if SENSITIVE_KEY_PATTERN.search(str(key)):
                redacted[key] = REDACTED
            else:
                redacted[key] = redact_sensitive_fields(value)
        return redacted
    if isinstance(data, list):
        return [redact_sensitive_fields(item) for item in data]
    return data


def _parse_actor_user_id(actor_user_id: str | UUID | None) -> UUID | None:
    if actor_user_id is None:
        return None
    if isinstance(actor_user_id, UUID):
        return actor_user_id
    try:
        return UUID(str(actor_user_id))
    except ValueError:
        return None


def _normalize_entity_id(entity_id: UUID | str | int | None) -> tuple[UUID | None, dict[str, Any]]:
    metadata: dict[str, Any] = {}
    if entity_id is None:
        return None, metadata
    if isinstance(entity_id, UUID):
        return entity_id, metadata
    try:
        return UUID(str(entity_id)), metadata
    except ValueError:
        metadata["entity_ref"] = str(entity_id)
        return None, metadata


def _build_summary(action: str, entity_type: str, entity_id: UUID | None, metadata: dict[str, Any]) -> str:
    ref = str(entity_id) if entity_id else metadata.get("entity_ref")
    if ref:
        return f"{action} on {entity_type} {ref}"
    return f"{action} on {entity_type}"


def _split_stored_values(new_value: dict | None) -> tuple[dict | None, dict | None]:
    if not new_value:
        return None, None
    if "_metadata" in new_value:
        payload = {k: v for k, v in new_value.items() if k != "_metadata"}
        metadata = new_value.get("_metadata")
        return payload or None, metadata if isinstance(metadata, dict) else None
    return new_value, None


def create_audit_log(
    db: Session,
    *,
    actor_user_id: str | UUID | None = None,
    actor_email: str | None = None,
    action: str,
    entity_type: str,
    entity_id: UUID | str | int | None = None,
    before: dict | None = None,
    after: dict | None = None,
    metadata: dict | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    entity_uuid, entity_meta = _normalize_entity_id(entity_id)
    combined_meta = {**entity_meta, **(metadata or {})}
    if actor_email:
        combined_meta.setdefault("actor_email", actor_email)

    redacted_before = redact_sensitive_fields(_json_safe(before)) if before is not None else None
    redacted_after = redact_sensitive_fields(_json_safe(after)) if after is not None else None

    stored_new = dict(redacted_after or {})
    if combined_meta:
        stored_new["_metadata"] = redact_sensitive_fields(_json_safe(combined_meta))

    entry = AuditLog(
        user_id=_parse_actor_user_id(actor_user_id),
        action=action,
        entity_type=entity_type,
        entity_id=entity_uuid,
        old_value=redacted_before,
        new_value=stored_new or ({"_metadata": redact_sensitive_fields(_json_safe(combined_meta))} if combined_meta else None),
        ip_address=ip_address,
    )
    db.add(entry)
    db.flush()
    return entry


def _audit_to_list_item(log: AuditLog, actor_email: str | None) -> dict[str, Any]:
    _, metadata = _split_stored_values(log.new_value)
    entity_ref = str(log.entity_id) if log.entity_id else (metadata or {}).get("entity_ref")
    email = actor_email or (metadata or {}).get("actor_email")
    return {
        "id": log.id,
        "actor_user_id": log.user_id,
        "actor_email": email,
        "action": log.action,
        "entity_type": log.entity_type,
        "entity_id": entity_ref,
        "summary": _build_summary(log.action, log.entity_type, log.entity_id, metadata or {}),
        "ip_address": log.ip_address,
        "created_at": log.created_at,
    }


def _audit_to_detail(log: AuditLog, actor_email: str | None) -> dict[str, Any]:
    after_payload, metadata = _split_stored_values(log.new_value)
    base = _audit_to_list_item(log, actor_email)
    return {
        **base,
        "metadata": metadata,
        "before_snapshot": log.old_value,
        "after_snapshot": after_payload,
    }


def _base_query():
    return select(AuditLog, User.email).outerjoin(User, AuditLog.user_id == User.id)


def list_audit_logs(
    db: Session,
    *,
    search: str | None = None,
    actor_email: str | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)

    query = _base_query()

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                AuditLog.action.ilike(term),
                AuditLog.entity_type.ilike(term),
                User.email.ilike(term),
            )
        )

    if actor_email and actor_email.strip():
        query = query.where(User.email.ilike(f"%{actor_email.strip()}%"))

    if action:
        query = query.where(AuditLog.action == action)

    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)

    if entity_id:
        try:
            query = query.where(AuditLog.entity_id == UUID(entity_id))
        except ValueError:
            query = query.where(AuditLog.id.is_(None))  # no match for invalid UUID filter

    if date_from is not None:
        query = query.where(AuditLog.created_at >= date_from)

    if date_to is not None:
        query = query.where(AuditLog.created_at <= date_to)

    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query) or 0

    rows = db.execute(query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)).all()
    items = [_audit_to_list_item(log, email) for log, email in rows]
    return items, total


def get_audit_log(db: Session, audit_log_id: UUID) -> dict[str, Any] | None:
    row = db.execute(
        _base_query().where(AuditLog.id == audit_log_id)
    ).first()
    if row is None:
        return None
    log, email = row
    return _audit_to_detail(log, email)
