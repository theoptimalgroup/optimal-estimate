"""Sync run lifecycle helpers: progress updates and stale running-lock recovery."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.eworks_sync import EworksSyncRun
from app.services.eworks_sync_lock_service import clear_stale_sync_locks

logger = logging.getLogger(__name__)

STALE_SYNC_TIMEOUT_MESSAGE = "Marked failed automatically after stale sync timeout"
_PROGRESS_COMMIT_EVERY = 100


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _running_timeout_minutes() -> int:
    return max(1, int(settings.eworks_sync_running_timeout_minutes))


def _normalize_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def is_running_lock_stale(run: EworksSyncRun, *, now: datetime | None = None) -> bool:
    """True when a running sync row has exceeded the configured running timeout."""
    if run.status != "running" or run.finished_at is not None:
        return False

    now = now or _utcnow()
    metadata = run.metadata_ or {}
    heartbeat_raw = metadata.get("last_heartbeat_at")
    if heartbeat_raw:
        try:
            heartbeat = datetime.fromisoformat(str(heartbeat_raw))
            heartbeat = _normalize_utc(heartbeat)
            if heartbeat is not None and now - heartbeat > timedelta(minutes=_running_timeout_minutes()):
                return True
        except ValueError:
            pass

    started_at = _normalize_utc(run.started_at)
    if started_at is None:
        return True

    return now - started_at > timedelta(minutes=_running_timeout_minutes())


def fail_sync_run(
    db: Session,
    run: EworksSyncRun,
    *,
    error_message: str,
    phase: str = "failed",
    commit: bool = True,
) -> None:
    """Mark a running sync row as failed with finished_at set."""
    if run.status != "running":
        return

    now = _utcnow()
    run.status = "failed"
    run.finished_at = now
    run.error_message = error_message
    run.metadata_ = {
        **(run.metadata_ or {}),
        "phase": phase,
        "failed_at": now.isoformat(),
    }
    db.flush()
    if commit:
        db.commit()


def clear_stale_running_sync_locks(db: Session) -> int:
    """Mark stale running sync rows as failed so new syncs can start."""
    clear_stale_sync_locks(db)
    now = _utcnow()
    running = db.query(EworksSyncRun).filter(EworksSyncRun.status == "running").all()
    cleared = 0

    for run in running:
        if not is_running_lock_stale(run, now=now):
            continue

        fail_sync_run(
            db,
            run,
            error_message=STALE_SYNC_TIMEOUT_MESSAGE,
            phase="failed",
            commit=False,
        )
        run.metadata_ = {
            **(run.metadata_ or {}),
            "recovered_at": now.isoformat(),
            "recovery_reason": STALE_SYNC_TIMEOUT_MESSAGE,
        }
        cleared += 1
        logger.warning(
            "Cleared stale eWorks sync lock run_id=%s type=%s started_at=%s",
            run.id,
            run.sync_type,
            run.started_at,
        )

    if cleared:
        db.commit()
    return cleared


# Backwards-compatible alias used by API status endpoint.
def recover_stale_sync_runs(db: Session, *, on_startup: bool = False) -> int:
    del on_startup
    return clear_stale_running_sync_locks(db)


def update_sync_run_progress(
    db: Session,
    run: EworksSyncRun,
    *,
    phase: str | None = None,
    fetched: int | None = None,
    created: int | None = None,
    updated: int | None = None,
    failed: int | None = None,
    commit: bool = True,
) -> None:
    """Persist in-progress counts so the admin UI can show activity."""
    metadata = dict(run.metadata_ or {})
    metadata["last_heartbeat_at"] = _utcnow().isoformat()
    if phase is not None:
        metadata["phase"] = phase

    if fetched is not None:
        run.fetched_count = fetched
    if created is not None:
        run.created_count = created
    if updated is not None:
        run.updated_count = updated
    if failed is not None:
        run.failed_count = failed

    run.metadata_ = metadata
    db.flush()
    if commit:
        db.commit()
