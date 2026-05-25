"""Idempotency key storage and replay for retriable mutations."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.support import IdempotencyKey


def hash_payload(payload: dict | str | None) -> str:
    if payload is None:
        return hashlib.sha256(b"").hexdigest()
    if isinstance(payload, str):
        raw = payload.encode("utf-8")
    else:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def session_idempotency_key(source: str, quote_number: str, job_number: str) -> str:
    return f"eworks.session.{source}.{quote_number}.{job_number}"


@dataclass(frozen=True)
class IdempotencyReplay:
    payload: dict
    status_code: int


def lookup_idempotency(db: Session, key: str) -> IdempotencyKey | None:
    record = db.scalar(select(IdempotencyKey).where(IdempotencyKey.key == key))
    if record is None:
        return None
    if record.expires_at is not None:
        expires = record.expires_at if record.expires_at.tzinfo else record.expires_at.replace(tzinfo=timezone.utc)
        if expires <= datetime.now(timezone.utc):
            return None
    return record


def check_idempotency(db: Session, *, key: str, request_hash: str) -> IdempotencyReplay | None:
    record = lookup_idempotency(db, key)
    if record is None:
        return None
    if record.request_hash != request_hash:
        raise AppError(
            "IDEMPOTENCY_CONFLICT",
            "Idempotency key reused with a different request body",
            409,
        )
    if record.response_payload is None:
        return None
    return IdempotencyReplay(payload=record.response_payload, status_code=record.status_code or 200)


def store_idempotency(
    db: Session,
    *,
    key: str,
    request_hash: str,
    response_payload: dict,
    status_code: int = 200,
    expires_at: datetime | None = None,
) -> IdempotencyKey:
    record = lookup_idempotency(db, key)
    if record is None:
        record = IdempotencyKey(
            key=key,
            request_hash=request_hash,
            response_payload=response_payload,
            status_code=status_code,
            expires_at=expires_at,
        )
        db.add(record)
    else:
        record.request_hash = request_hash
        record.response_payload = response_payload
        record.status_code = status_code
        record.expires_at = expires_at
    db.flush()
    return record
