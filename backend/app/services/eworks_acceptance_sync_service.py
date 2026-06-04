from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.calculation_session import CalculationSession
from app.schemas.eworks_link import Step1Snapshot
from app.services.audit_helpers import record_audit
from app.services.eworks_quote_api_service import (
    EworksQuoteApiError,
    build_custom_field_payload,
    redact_sync_record,
    update_quote_custom_field,
)
from app.services.quote_acceptance_helpers import is_quote_accepted

logger = logging.getLogger(__name__)

SYNC_PENDING = "pending"
SYNC_SUCCESS = "success"
SYNC_FAILED = "failed"
SYNC_SKIPPED = "skipped"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def resolve_eworks_quote_id(session: CalculationSession) -> int | None:
    """Resolve numeric eWorks quote ID from session snapshots."""
    step1 = session.step1_snapshot or {}
    payload = session.payload_snapshot or {}

    for source in (payload, step1):
        for key in ("eworks_quote_id", "quote_id", "id"):
            raw = source.get(key)
            if raw is None:
                continue
            try:
                numeric = int(str(raw).strip())
                if numeric > 0:
                    return numeric
            except (TypeError, ValueError):
                continue

    quote_number = str(step1.get("quote_number") or payload.get("quote_number") or "").strip()
    if not quote_number:
        return None

    if quote_number.upper().startswith("Q"):
        suffix = quote_number[1:].strip()
        if suffix.isdigit():
            return int(suffix)

    if quote_number.isdigit():
        return int(quote_number)

    return None


def _public_quote_url(session: CalculationSession) -> str | None:
    if not session.public_quote_token:
        return None
    frontend = (settings.frontend_url or "").rstrip("/")
    if not frontend:
        return f"/client/quote/{session.public_quote_token}"
    return f"{frontend}/client/quote/{session.public_quote_token}"


def build_acceptance_sync_text(session: CalculationSession) -> str:
    step1 = Step1Snapshot.model_validate(session.step1_snapshot)
    lines = [
        "Quote accepted in Optimal Estimate.",
        f"Quote Ref: {step1.quote_number}",
    ]
    if session.client_accepted_at:
        lines.append(f"Accepted At: {session.client_accepted_at.isoformat()}")
    if session.client_acceptance_name or session.client_acceptance_email:
        name = session.client_acceptance_name or "Client"
        if session.client_acceptance_email:
            lines.append(f"Accepted By: {name} <{session.client_acceptance_email}>")
        else:
            lines.append(f"Accepted By: {name}")
    if session.client_acceptance_notes:
        lines.append(f"Notes: {session.client_acceptance_notes.strip()}")
    public_url = _public_quote_url(session)
    if public_url:
        lines.append(f"Public Client Quote Link: {public_url}")
    return "\n".join(lines)


def _increment_attempts(session: CalculationSession) -> None:
    session.eworks_acceptance_sync_attempts = int(session.eworks_acceptance_sync_attempts or 0) + 1


def _mark_skipped(session: CalculationSession, message: str, *, payload: dict | None = None) -> str:
    _increment_attempts(session)
    session.eworks_acceptance_sync_status = SYNC_SKIPPED
    session.eworks_acceptance_sync_error = message
    session.eworks_acceptance_last_payload = redact_sync_record(payload) if payload else None
    session.eworks_acceptance_last_response = None
    return SYNC_SKIPPED


def _mark_failed(session: CalculationSession, message: str, *, payload: dict | None = None, response: Any = None) -> str:
    _increment_attempts(session)
    session.eworks_acceptance_sync_status = SYNC_FAILED
    session.eworks_acceptance_sync_error = _sanitize_error_message(message)
    session.eworks_acceptance_last_payload = redact_sync_record(payload) if payload else None
    session.eworks_acceptance_last_response = (
        redact_sync_record(response) if isinstance(response, (dict, list)) else None
    )
    return SYNC_FAILED


def _mark_success(session: CalculationSession, *, payload: dict, response: dict) -> str:
    now = _utcnow()
    _increment_attempts(session)
    session.eworks_acceptance_sync_status = SYNC_SUCCESS
    session.eworks_acceptance_synced_at = now
    session.eworks_acceptance_sync_error = None
    session.eworks_acceptance_last_payload = redact_sync_record(payload)
    session.eworks_acceptance_last_response = redact_sync_record(response)
    return SYNC_SUCCESS


def _sanitize_error_message(message: str) -> str:
    sanitized = message or "Unknown eWorks sync error"
    sanitized = re.sub(
        r"(api[_-]?key|session[_-]?token|password|secret|authorization)\s*[:=]\s*\S+",
        r"\1=***REDACTED***",
        sanitized,
        flags=re.IGNORECASE,
    )
    api_key = getattr(settings, "eworks_api_key", None)
    if isinstance(api_key, str) and api_key and api_key in sanitized:
        sanitized = sanitized.replace(api_key, "***REDACTED***")
    secret_key = getattr(settings, "secret_key", None)
    if isinstance(secret_key, str) and secret_key and secret_key in sanitized:
        sanitized = sanitized.replace(secret_key, "***REDACTED***")
    return sanitized[:2000]


def _should_attempt_sync(session: CalculationSession, *, force_retry: bool) -> bool:
    if not is_quote_accepted(session):
        return False
    if force_retry:
        return True
    status = session.eworks_acceptance_sync_status
    return status not in {SYNC_SUCCESS, SYNC_SKIPPED}


def sync_quote_acceptance_to_eworks(
    db: Session,
    session: CalculationSession,
    *,
    force_retry: bool = False,
    actor=None,
) -> str:
    """Attempt non-blocking eWorks acceptance sync. Never raises to callers."""
    if not _should_attempt_sync(session, force_retry=force_retry):
        return session.eworks_acceptance_sync_status or SYNC_SKIPPED

    session.eworks_acceptance_sync_status = SYNC_PENDING
    db.flush()

    if not settings.eworks_acceptance_sync_enabled:
        status = _mark_skipped(session, "Acceptance sync disabled")
        _record_sync_audit(db, session, status, actor=actor)
        db.commit()
        return status

    if settings.eworks_acceptance_sync_mode != "custom_field":
        status = _mark_skipped(session, "No safe eWorks write endpoint configured")
        _record_sync_audit(db, session, status, actor=actor)
        db.commit()
        return status

    if not settings.eworks_api_enabled:
        status = _mark_skipped(session, "eWorks API disabled")
        _record_sync_audit(db, session, status, actor=actor)
        db.commit()
        return status

    quote_id = resolve_eworks_quote_id(session)
    if quote_id is None:
        status = _mark_skipped(session, "Missing eWorks quote id")
        _record_sync_audit(db, session, status, actor=actor)
        db.commit()
        return status

    field_key = settings.eworks_acceptance_custom_field_key
    acceptance_text = build_acceptance_sync_text(session)
    payload = build_custom_field_payload(field_key, acceptance_text)

    try:
        response = update_quote_custom_field(quote_id, field_key, acceptance_text)
        status = _mark_success(session, payload=payload, response=response)
        _record_sync_audit(db, session, status, actor=actor, quote_id=quote_id)
        db.commit()
        return status
    except EworksQuoteApiError as exc:
        logger.warning(
            "eWorks acceptance sync failed for session=%s quote_id=%s: %s",
            session.id,
            quote_id,
            exc,
        )
        status = _mark_failed(session, str(exc), payload=payload)
        _record_sync_audit(db, session, status, actor=actor, quote_id=quote_id)
        db.commit()
        return status
    except Exception as exc:
        logger.exception("Unexpected eWorks acceptance sync failure for session=%s", session.id)
        status = _mark_failed(session, str(exc), payload=payload)
        _record_sync_audit(db, session, status, actor=actor, quote_id=quote_id)
        db.commit()
        return status


def retry_quote_acceptance_eworks_sync(
    db: Session,
    session_id: UUID,
    *,
    actor=None,
) -> CalculationSession:
    session = db.get(CalculationSession, session_id)
    if session is None:
        from app.core.exceptions import AppError

        raise AppError("SESSION_NOT_FOUND", "Quote session not found", 404)
    if not is_quote_accepted(session):
        from app.core.exceptions import AppError

        raise AppError("QUOTE_NOT_ACCEPTED", "Quote has not been accepted by the client", 400)

    sync_quote_acceptance_to_eworks(db, session, force_retry=True, actor=actor)
    db.refresh(session)
    return session


def _record_sync_audit(
    db: Session,
    session: CalculationSession,
    status: str,
    *,
    actor=None,
    quote_id: int | None = None,
) -> None:
    step1 = Step1Snapshot.model_validate(session.step1_snapshot)
    metadata: dict[str, Any] = {
        "quote_ref": step1.quote_number,
        "sync_status": status,
    }
    if quote_id is not None:
        metadata["eworks_quote_id"] = quote_id
    if session.eworks_acceptance_sync_error:
        metadata["error"] = _sanitize_error_message(session.eworks_acceptance_sync_error)

    if status == SYNC_SUCCESS:
        action = "eworks_acceptance_sync_success"
    elif status == SYNC_FAILED:
        action = "eworks_acceptance_sync_failed"
    else:
        action = "eworks_acceptance_sync_skipped"

    record_audit(
        db,
        actor=actor,
        action=action,
        entity_type="calculation_session",
        entity_id=session.id,
        metadata=metadata,
    )
