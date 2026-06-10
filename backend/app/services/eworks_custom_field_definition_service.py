"""Sync and resolve eWorks CustomFields definitions for safe detail display."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppError
from app.models.eworks_sync import EworksCustomFieldDefinition, EworksQuote
from app.services.eworks_custom_fields_api_service import fetch_all_custom_field_definitions

logger = logging.getLogger(__name__)

_DEFINITION_REFRESH_HOURS = 24

KNOWN_QUOTE_FIELD_KEYS = frozenset(
    {"txt_9", "list_5", "list_8", "txt_43", "list_16", "list_28", "txtar_44"}
)


@dataclass(frozen=True)
class CustomFieldDefinitionView:
    field_key: str
    label: str
    field_type: str | None
    options: list[str] | None
    sections: list[str] | None


class CustomFieldDefinitionSyncSummary(BaseModel):
    fetched: int = 0
    created: int = 0
    updated: int = 0
    failed: int = 0


class CustomFieldDefinitionRead(BaseModel):
    id: int
    eworks_custom_field_id: int
    field_key: str
    label: str
    type: str | None = None
    section: str | None = None
    options: list[str] | None = None
    default_value: str | None = None
    synced_at: str | None = None


class CustomFieldDebugRow(BaseModel):
    field_key: str
    label: str
    type: str | None = None
    section: str | None = None
    value: str | None = None
    options: list[str] | None = None


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def infer_field_type_from_key(field_key: str) -> str | None:
    if field_key.startswith("list_"):
        return "LIST"
    if field_key.startswith("txtar_"):
        return "TEXTAREA"
    if field_key.startswith("txt_"):
        return "TEXT"
    return None


def parse_list_options(field_value: Any) -> list[str] | None:
    if not isinstance(field_value, str) or not field_value.strip():
        return None
    return [part.strip() for part in field_value.replace("\r\n", "\n").split("\n") if part.strip()]


def extract_custom_field_sections(allowed_sections: Any) -> list[str]:
    if not isinstance(allowed_sections, dict):
        return []
    settings_rows = allowed_sections.get("section_settings")
    if not isinstance(settings_rows, list):
        return []
    sections: list[str] = []
    for row in settings_rows:
        if not isinstance(row, dict):
            continue
        section = _as_str(row.get("section"))
        if section and section not in sections:
            sections.append(section)
    return sections


def parse_custom_field_definition(raw: dict[str, Any]) -> dict[str, Any] | None:
    field_key = _as_str(raw.get("field_key"))
    custom_field_id = raw.get("custom_field_id")
    if not field_key or custom_field_id is None:
        return None

    field_type = _as_str(raw.get("field_type")) or infer_field_type_from_key(field_key)
    options = parse_list_options(raw.get("field_value")) if field_type == "LIST" else None

    return {
        "eworks_custom_field_id": int(custom_field_id),
        "field_key": field_key,
        "field_label": _as_str(raw.get("field_label")),
        "field_type": field_type,
        "default_value": _as_str(raw.get("default_value")),
        "options": options,
        "sections": extract_custom_field_sections(raw.get("allowed_sections")),
        "status": raw.get("status"),
        "raw_payload": raw,
    }


def sync_custom_field_definitions(db: Session) -> CustomFieldDefinitionSyncSummary:
    """Fetch all CustomFields definitions from eWorks and upsert locally."""
    summary = CustomFieldDefinitionSyncSummary()
    synced_at = datetime.now(timezone.utc)

    try:
        records = fetch_all_custom_field_definitions()
    except AppError:
        raise
    except Exception as exc:
        logger.exception("Custom field definition sync failed")
        raise AppError("EWORKS_SYNC_FAILED", f"Custom field definition sync failed: {exc}", 502) from exc

    summary.fetched = len(records)
    existing_by_key = {
        row.field_key: row
        for row in db.query(EworksCustomFieldDefinition).all()
    }

    for raw in records:
        if not isinstance(raw, dict):
            summary.failed += 1
            continue
        parsed = parse_custom_field_definition(raw)
        if parsed is None:
            summary.failed += 1
            continue

        row = existing_by_key.get(parsed["field_key"])
        if row is None:
            row = EworksCustomFieldDefinition(
                eworks_custom_field_id=parsed["eworks_custom_field_id"],
                field_key=parsed["field_key"],
            )
            db.add(row)
            summary.created += 1
        else:
            summary.updated += 1

        row.eworks_custom_field_id = parsed["eworks_custom_field_id"]
        row.field_label = parsed["field_label"]
        row.field_type = parsed["field_type"]
        row.default_value = parsed["default_value"]
        row.options = parsed["options"]
        row.sections = parsed["sections"]
        row.status = parsed["status"]
        row.raw_payload = parsed["raw_payload"]
        row.synced_at = synced_at

    db.commit()
    logger.info(
        "Custom field definitions synced fetched=%s created=%s updated=%s failed=%s",
        summary.fetched,
        summary.created,
        summary.updated,
        summary.failed,
    )
    return summary


def _definitions_are_stale(db: Session) -> bool:
    count = db.query(EworksCustomFieldDefinition).count()
    if count == 0:
        return True
    latest = db.query(func.max(EworksCustomFieldDefinition.synced_at)).scalar()
    if latest is None:
        return True
    if latest.tzinfo is None:
        latest = latest.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - latest >= timedelta(hours=_DEFINITION_REFRESH_HOURS)


def ensure_custom_field_definitions(db: Session, *, force: bool = False) -> bool:
    """Sync definitions when missing or stale. Returns True when a sync ran."""
    if not settings.eworks_api_enabled:
        return False
    if not force and not _definitions_are_stale(db):
        return False
    sync_custom_field_definitions(db)
    return True


def definitions_lookup_map(db: Session) -> dict[str, CustomFieldDefinitionView]:
    rows = db.query(EworksCustomFieldDefinition).order_by(EworksCustomFieldDefinition.field_key.asc()).all()
    lookup: dict[str, CustomFieldDefinitionView] = {}
    for row in rows:
        lookup[row.field_key] = CustomFieldDefinitionView(
            field_key=row.field_key,
            label=row.field_label or row.field_key,
            field_type=row.field_type or infer_field_type_from_key(row.field_key),
            options=row.options if isinstance(row.options, list) else None,
            sections=row.sections if isinstance(row.sections, list) else None,
        )
    return lookup


def serialize_custom_field_definition(row: EworksCustomFieldDefinition) -> dict[str, Any]:
    sections = row.sections if isinstance(row.sections, list) else []
    return CustomFieldDefinitionRead(
        id=row.id,
        eworks_custom_field_id=row.eworks_custom_field_id,
        field_key=row.field_key,
        label=row.field_label or row.field_key,
        type=row.field_type or infer_field_type_from_key(row.field_key),
        section=", ".join(sections) if sections else None,
        options=row.options if isinstance(row.options, list) else None,
        default_value=row.default_value,
        synced_at=str(row.synced_at) if row.synced_at else None,
    ).model_dump()


def list_custom_field_definitions(
    db: Session,
    *,
    section: str | None = None,
    search: str | None = None,
) -> list[dict[str, Any]]:
    q = db.query(EworksCustomFieldDefinition).order_by(EworksCustomFieldDefinition.field_key.asc())
    rows = q.all()
    if section:
        normalized = section.strip().upper()
        rows = [
            row
            for row in rows
            if isinstance(row.sections, list) and normalized in [str(item).upper() for item in row.sections]
        ]
    if search:
        needle = search.strip().lower()
        rows = [
            row
            for row in rows
            if needle in (row.field_key or "").lower() or needle in (row.field_label or "").lower()
        ]
    return [serialize_custom_field_definition(row) for row in rows]


def _quote_cf_data(raw: dict[str, Any]) -> dict[str, Any]:
    for key in ("cf_data", "cfData"):
        source = raw.get(key)
        if isinstance(source, dict):
            return source
    return {}


def build_quote_custom_fields_debug(db: Session, quote: EworksQuote) -> list[dict[str, Any]]:
    """Admin debug rows: definition metadata merged with quote cf_data values."""
    ensure_custom_field_definitions(db)
    definitions = db.query(EworksCustomFieldDefinition).order_by(EworksCustomFieldDefinition.field_key.asc()).all()
    raw = quote.raw_payload if isinstance(quote.raw_payload, dict) else {}
    cf_data = _quote_cf_data(raw)

    rows: list[CustomFieldDebugRow] = []
    seen_keys: set[str] = set()

    for row in definitions:
        sections = row.sections if isinstance(row.sections, list) else []
        section_text = ", ".join(str(item) for item in sections) if sections else None
        applies_to_quote = not sections or "QUOTE" in [str(item).upper() for item in sections]
        if not applies_to_quote and row.field_key not in cf_data:
            continue

        value_raw = cf_data.get(row.field_key)
        value_text = None if value_raw in (None, "") else str(value_raw)
        field_type = row.field_type or infer_field_type_from_key(row.field_key)
        rows.append(
            CustomFieldDebugRow(
                field_key=row.field_key,
                label=row.field_label or row.field_key,
                type=field_type,
                section=section_text,
                value=value_text,
                options=row.options if field_type == "LIST" and isinstance(row.options, list) else None,
            )
        )
        seen_keys.add(row.field_key)

    for key, value_raw in cf_data.items():
        key_text = str(key)
        if key_text in seen_keys:
            continue
        value_text = None if value_raw in (None, "") else str(value_raw)
        field_type = infer_field_type_from_key(key_text)
        rows.append(
            CustomFieldDebugRow(
                field_key=key_text,
                label=key_text,
                type=field_type,
                section=None,
                value=value_text,
                options=None,
            )
        )

    rows.sort(key=lambda item: item.field_key)
    return [row.model_dump() for row in rows]
