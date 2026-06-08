"""Database-backed locks for eWorks sync coordination."""

from __future__ import annotations

import logging
import os
import socket
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.eworks_sync import EworksSyncLock

logger = logging.getLogger(__name__)

SYNC_LOCK_ACTIVE_MESSAGE = "A sync is already running. Try again shortly."
STALE_LOCK_MESSAGE = "Released stale eWorks sync lock after timeout"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def lock_timeout_minutes() -> int:
    return max(1, int(settings.eworks_sync_lock_timeout_minutes))


def lock_heartbeat_seconds() -> int:
    return max(15, int(settings.eworks_sync_lock_heartbeat_seconds))


def get_worker_id() -> str:
    host = socket.gethostname()
    pid = os.getpid()
    worker = "worker" if settings.run_background_worker else "api"
    return f"{worker}:{host}:{pid}"


def is_sync_lock_stale(lock: EworksSyncLock, *, now: datetime | None = None) -> bool:
    if lock.status != "running":
        return False

    now = now or _utcnow()
    heartbeat = _normalize_utc(lock.heartbeat_at)
    expires = _normalize_utc(lock.expires_at)
    started = _normalize_utc(lock.started_at)

    if expires is not None and now >= expires:
        return True
    if heartbeat is not None and now - heartbeat > timedelta(minutes=lock_timeout_minutes()):
        return True
    if heartbeat is None and started is not None and now - started > timedelta(minutes=lock_timeout_minutes()):
        return True
    return False


def _get_lock_row(db: Session, sync_type: str) -> EworksSyncLock | None:
    return db.query(EworksSyncLock).filter(EworksSyncLock.sync_type == sync_type).first()


def clear_stale_sync_locks(db: Session, *, sync_type: str | None = None) -> int:
    """Mark stale running locks as failed so new syncs can start."""
    now = _utcnow()
    query = db.query(EworksSyncLock).filter(EworksSyncLock.status == "running")
    if sync_type is not None:
        query = query.filter(EworksSyncLock.sync_type == sync_type)

    cleared = 0
    for lock in query.all():
        if not is_sync_lock_stale(lock, now=now):
            continue
        lock.status = "failed"
        lock.updated_at = now
        cleared += 1
        logger.warning(
            "Cleared stale eWorks sync lock type=%s locked_by=%s heartbeat_at=%s",
            lock.sync_type,
            lock.locked_by,
            lock.heartbeat_at,
        )

    if cleared:
        db.commit()
    return cleared


def try_acquire_sync_lock(db: Session, sync_type: str, *, locked_by: str | None = None) -> EworksSyncLock | None:
    """Acquire a sync lock or return None when another fresh lock exists."""
    clear_stale_sync_locks(db, sync_type=sync_type)

    existing = _get_lock_row(db, sync_type)
    if existing is not None and existing.status == "running" and not is_sync_lock_stale(existing):
        return None

    now = _utcnow()
    expires = now + timedelta(minutes=lock_timeout_minutes())
    owner = locked_by or get_worker_id()

    if existing is None:
        lock = EworksSyncLock(
            sync_type=sync_type,
            locked_by=owner,
            status="running",
            started_at=now,
            heartbeat_at=now,
            expires_at=expires,
        )
        db.add(lock)
    else:
        existing.locked_by = owner
        existing.status = "running"
        existing.started_at = now
        existing.heartbeat_at = now
        existing.expires_at = expires
        existing.updated_at = now
        lock = existing

    db.flush()
    db.commit()
    db.refresh(lock)
    return lock


def touch_sync_lock_heartbeat(db: Session, sync_type: str, *, commit: bool = True) -> None:
    lock = _get_lock_row(db, sync_type)
    if lock is None or lock.status != "running":
        return

    now = _utcnow()
    lock.heartbeat_at = now
    lock.expires_at = now + timedelta(minutes=lock_timeout_minutes())
    lock.updated_at = now
    db.flush()
    if commit:
        db.commit()


def release_sync_lock(
    db: Session,
    sync_type: str,
    *,
    status: str = "success",
    commit: bool = True,
) -> None:
    lock = _get_lock_row(db, sync_type)
    if lock is None:
        return

    now = _utcnow()
    lock.status = status
    lock.heartbeat_at = now
    lock.updated_at = now
    db.flush()
    if commit:
        db.commit()


def get_active_sync_locks(db: Session) -> list[EworksSyncLock]:
    clear_stale_sync_locks(db)
    return (
        db.query(EworksSyncLock)
        .filter(EworksSyncLock.status == "running")
        .order_by(EworksSyncLock.started_at.desc())
        .all()
    )


def has_stale_running_locks(db: Session) -> bool:
    """True when any running lock row is stale (before recovery clears it)."""
    now = _utcnow()
    for lock in db.query(EworksSyncLock).filter(EworksSyncLock.status == "running").all():
        if is_sync_lock_stale(lock, now=now):
            return True
    return False


def serialize_sync_lock(lock: EworksSyncLock) -> dict:
    return {
        "sync_type": lock.sync_type,
        "locked_by": lock.locked_by,
        "status": lock.status,
        "started_at": lock.started_at.isoformat() if lock.started_at else None,
        "heartbeat_at": lock.heartbeat_at.isoformat() if lock.heartbeat_at else None,
        "expires_at": lock.expires_at.isoformat() if lock.expires_at else None,
        "is_stale": is_sync_lock_stale(lock),
    }
