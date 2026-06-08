"""Sync eWorks quote/job attachment metadata from payload (read-only; no file download by default)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.eworks_sync import EworksAttachment

logger = logging.getLogger(__name__)

ATTACHMENT_FIELD_KEYS = (
    "attachments",
    "Attachments",
    "files",
    "Files",
    "documents",
    "Documents",
    "photos",
    "Photos",
    "uploads",
    "quote_attachments",
    "quote_documents",
    "uploaded_files",
    "job_attachments",
)

_ATTACHMENT_KEY_LOOKUP = {key.lower() for key in ATTACHMENT_FIELD_KEYS}

_SENSITIVE_URL_PARTS = (
    "api_key",
    "token",
    "access_token",
    "session_token",
    "authorization",
    "signature",
    "sig=",
    "password",
)


def _safe_int(val: Any) -> int | None:
    if val is None:
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _safe_str(val: Any, max_len: int | None = None) -> str | None:
    if val is None:
        return None
    text = str(val).strip() or None
    if text and max_len:
        text = text[:max_len]
    return text


def _attachment_identity(raw: dict[str, Any]) -> str | None:
    for key in ("id", "attachment_id", "file_id", "document_id", "upload_id"):
        value = raw.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def find_attachment_like_keys(raw_payload: dict[str, Any]) -> list[str]:
    """Return payload keys that contain attachment-like lists (for debug-safe logging)."""
    found: list[str] = []
    for key, value in raw_payload.items():
        if str(key).lower() not in _ATTACHMENT_KEY_LOOKUP:
            continue
        if isinstance(value, list) and value:
            found.append(str(key))
    return found


def payload_has_embedded_attachments(raw_payload: dict[str, Any] | None) -> bool:
    if not raw_payload or not isinstance(raw_payload, dict):
        return False
    return bool(find_attachment_like_keys(raw_payload))


def _extract_attachment_items(raw_payload: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for key in ATTACHMENT_FIELD_KEYS:
        value = raw_payload.get(key)
        if not isinstance(value, list):
            continue
        for entry in value:
            if not isinstance(entry, dict):
                continue
            identity = _attachment_identity(entry) or _safe_str(
                entry.get("filename") or entry.get("file_name") or entry.get("name")
            )
            dedupe_key = f"{identity}:{entry.get('size') or entry.get('size_bytes')}"
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            items.append(entry)
    return items


def _normalize_attachment_fields(
    raw: dict[str, Any],
    *,
    parent_type: str,
    parent_eworks_id: int,
    parent_local_id: int | None,
) -> dict[str, Any]:
    uploaded_by = raw.get("uploaded_by")
    if isinstance(uploaded_by, dict):
        uploaded_by = uploaded_by.get("name") or uploaded_by.get("full_name") or uploaded_by.get("email")

    return {
        "eworks_attachment_id": _attachment_identity(raw),
        "parent_type": parent_type,
        "parent_eworks_id": parent_eworks_id,
        "parent_local_id": parent_local_id,
        "filename": _safe_str(
            raw.get("filename") or raw.get("file_name") or raw.get("name") or raw.get("title"),
            500,
        ),
        "mime_type": _safe_str(
            raw.get("mime_type") or raw.get("content_type") or raw.get("type"),
            200,
        ),
        "size_bytes": _safe_int(raw.get("size_bytes") or raw.get("size") or raw.get("file_size")),
        "description": _safe_str(raw.get("description") or raw.get("notes")),
        "created_on": _safe_str(
            raw.get("created_on") or raw.get("created_at") or raw.get("uploaded_at") or raw.get("date"),
            30,
        ),
        "uploaded_by": _safe_str(uploaded_by, 200),
        "download_endpoint": _safe_str(
            raw.get("download_endpoint")
            or raw.get("download_url")
            or raw.get("url")
            or raw.get("href")
            or raw.get("path"),
            1000,
        ),
        "raw_payload": raw,
    }


def _upsert_key(row: EworksAttachment) -> tuple[str, int, str]:
    return (
        row.parent_type,
        row.parent_eworks_id,
        row.eworks_attachment_id or (row.filename or f"row-{row.id}"),
    )


def sync_parent_attachment_items(
    db: Session,
    *,
    parent_type: str,
    parent_eworks_id: int,
    parent_local_id: int | None,
    items: list[dict[str, Any]],
) -> tuple[int, int]:
    """Upsert attachment metadata from a list of attachment records. Returns (created, updated)."""
    if not settings.eworks_sync_attachments_enabled:
        return 0, 0
    if not items:
        return 0, 0

    now = datetime.now(timezone.utc)
    existing_rows = (
        db.query(EworksAttachment)
        .filter(
            EworksAttachment.parent_type == parent_type,
            EworksAttachment.parent_eworks_id == parent_eworks_id,
        )
        .all()
    )
    existing_by_key = {_upsert_key(row): row for row in existing_rows}
    seen_keys: set[tuple[str, int, str]] = set()
    created = 0
    updated = 0

    for item in items:
        if not isinstance(item, dict):
            continue
        fields = _normalize_attachment_fields(
            item,
            parent_type=parent_type,
            parent_eworks_id=parent_eworks_id,
            parent_local_id=parent_local_id,
        )
        if not fields["filename"] and not fields["eworks_attachment_id"]:
            continue

        key = (
            parent_type,
            parent_eworks_id,
            fields["eworks_attachment_id"] or fields["filename"] or "",
        )
        seen_keys.add(key)
        fields["synced_at"] = now

        existing = existing_by_key.get(key)
        if existing is None:
            db.add(EworksAttachment(**fields))
            created += 1
        else:
            for field_name, value in fields.items():
                if field_name in {"local_storage_path", "downloaded_at"}:
                    continue
                setattr(existing, field_name, value)
            existing.synced_at = now
            updated += 1

    for key, row in existing_by_key.items():
        if key not in seen_keys:
            db.delete(row)

    db.flush()
    return created, updated


def sync_parent_attachments(
    db: Session,
    *,
    parent_type: str,
    parent_eworks_id: int,
    parent_local_id: int | None,
    raw_payload: dict[str, Any] | None,
) -> int:
    """Extract and upsert attachment metadata for one quote/job. Returns count synced."""
    if not raw_payload or not isinstance(raw_payload, dict):
        return 0

    items = _extract_attachment_items(raw_payload)
    if not items:
        return 0

    created, updated = sync_parent_attachment_items(
        db,
        parent_type=parent_type,
        parent_eworks_id=parent_eworks_id,
        parent_local_id=parent_local_id,
        items=items,
    )
    return created + updated


def sync_parent_attachments_detailed(
    db: Session,
    *,
    parent_type: str,
    parent_eworks_id: int,
    parent_local_id: int | None,
    raw_payload: dict[str, Any] | None,
) -> tuple[int, int]:
    """Extract and upsert attachment metadata. Returns (created, updated)."""
    if not raw_payload or not isinstance(raw_payload, dict):
        return 0, 0

    items = _extract_attachment_items(raw_payload)
    if not items:
        return 0, 0

    return sync_parent_attachment_items(
        db,
        parent_type=parent_type,
        parent_eworks_id=parent_eworks_id,
        parent_local_id=parent_local_id,
        items=items,
    )


def _url_contains_secrets(url: str | None) -> bool:
    if not url:
        return False
    lower = url.lower()
    return any(part in lower for part in _SENSITIVE_URL_PARTS)


def serialize_attachment_safe(row: EworksAttachment) -> dict[str, Any]:
    """Return manager-safe attachment metadata (no raw payload or sensitive URLs)."""
    return {
        "id": row.id,
        "filename": row.filename,
        "mime_type": row.mime_type,
        "size_bytes": row.size_bytes,
        "description": row.description,
        "uploaded_by": row.uploaded_by,
        "created_on": row.created_on,
        "synced_at": str(row.synced_at) if row.synced_at else None,
    }


def serialize_attachment_admin(row: EworksAttachment) -> dict[str, Any]:
    """Return admin attachment detail including raw_payload."""
    data = serialize_attachment_safe(row)
    data.update(
        {
            "eworks_attachment_id": row.eworks_attachment_id,
            "parent_type": row.parent_type,
            "parent_eworks_id": row.parent_eworks_id,
            "parent_local_id": row.parent_local_id,
            "download_endpoint": row.download_endpoint,
            "local_storage_path": row.local_storage_path,
            "downloaded_at": str(row.downloaded_at) if row.downloaded_at else None,
            "raw_payload": row.raw_payload,
        }
    )
    return data


def list_attachments_for_parent(
    db: Session,
    *,
    parent_type: str,
    parent_local_id: int | None = None,
    parent_eworks_id: int | None = None,
) -> list[EworksAttachment]:
    from sqlalchemy import or_

    query = db.query(EworksAttachment).filter(EworksAttachment.parent_type == parent_type)
    if parent_local_id is not None and parent_eworks_id is not None:
        query = query.filter(
            or_(
                EworksAttachment.parent_local_id == parent_local_id,
                EworksAttachment.parent_eworks_id == parent_eworks_id,
            )
        )
    elif parent_local_id is not None:
        query = query.filter(EworksAttachment.parent_local_id == parent_local_id)
    elif parent_eworks_id is not None:
        query = query.filter(EworksAttachment.parent_eworks_id == parent_eworks_id)
    else:
        return []

    return query.order_by(EworksAttachment.filename.asc(), EworksAttachment.id.asc()).all()
