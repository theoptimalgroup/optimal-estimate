"""Background runner for eWorks sync jobs (survives client disconnect)."""

from __future__ import annotations

import logging
import threading
import uuid
from typing import Any

from app.core.exceptions import AppError
from app.db.session import SessionLocal
from app.models.eworks_sync import EworksSyncRun
from app.services.audit_helpers import record_audit
from app.services.eworks_sync_lock_service import (
    SYNC_LOCK_ACTIVE_MESSAGE,
    release_sync_lock,
    touch_sync_lock_heartbeat,
    try_acquire_sync_lock,
)
from app.services.eworks_sync_run_state import (
    clear_stale_running_sync_locks,
    fail_sync_run,
    update_sync_run_progress,
)
from app.services.eworks_sync_service import (
    _start_run,
    sync_all_eworks,
    sync_customers_from_eworks,
    sync_jobs_from_eworks,
    sync_quotes_from_eworks,
    sync_quotes_incremental_recent,
)

logger = logging.getLogger(__name__)

_UNEXPECTED_EXIT_MESSAGE = "Sync ended without completing (unexpected worker exit)."


def _parse_user_id(user_id: str | uuid.UUID | None) -> uuid.UUID | None:
    if user_id is None:
        return None
    if isinstance(user_id, uuid.UUID):
        return user_id
    try:
        return uuid.UUID(str(user_id))
    except ValueError:
        return None


def _audit_action_for_type(sync_type: str, phase: str) -> str:
    if sync_type == "all":
        if phase == "started":
            return "eworks_all_sync_started"
        if phase == "completed":
            return "eworks_all_sync_completed"
        return "eworks_all_sync_failed"
    if sync_type == "jobs":
        return f"eworks_jobs_sync_{phase}"
    if sync_type == "customers":
        return f"eworks_customers_sync_{phase}"
    if sync_type == "products":
        return f"eworks_products_sync_{phase}"
    if sync_type == "appointments":
        return f"eworks_appointments_sync_{phase}"
    return f"eworks_quotes_sync_{phase}"


def get_running_sync_run(db) -> EworksSyncRun | None:
    return (
        db.query(EworksSyncRun)
        .filter(EworksSyncRun.status == "running")
        .order_by(EworksSyncRun.started_at.desc())
        .first()
    )


def _progress_with_lock(db, run: EworksSyncRun, sync_type: str, **kwargs) -> None:
    touch_sync_lock_heartbeat(db, sync_type, commit=False)
    update_sync_run_progress(db, run, **kwargs)


def schedule_eworks_sync(
    db,
    *,
    sync_type: str,
    filters: dict[str, Any] | None,
    user_id: str | uuid.UUID | None,
    actor_email: str | None = None,
    source: str = "manual",
    locked_by: str | None = None,
    check_global_running: bool = True,
) -> EworksSyncRun:
    """Create a sync run record and execute sync in a background thread.

    check_global_running=False skips the global running-sync guard so that
    an incremental quotes sync can proceed even while another sync type runs.
    """
    if sync_type not in {"quotes", "jobs", "customers", "all"}:
        raise AppError("INVALID_SYNC_TYPE", f"Unsupported sync type: {sync_type}", 400)

    clear_stale_running_sync_locks(db)

    if check_global_running:
        existing = get_running_sync_run(db)
        if existing is not None:
            raise AppError("SYNC_ALREADY_RUNNING", SYNC_LOCK_ACTIVE_MESSAGE, 409)

    lock = try_acquire_sync_lock(db, sync_type, locked_by=locked_by)
    if lock is None:
        raise AppError("SYNC_ALREADY_RUNNING", SYNC_LOCK_ACTIVE_MESSAGE, 409)

    parsed_user_id = _parse_user_id(user_id)
    run = _start_run(db, sync_type=sync_type, user_id=parsed_user_id)
    run.metadata_ = {"filters": filters or {}, "phase": "queued", "source": source}
    db.flush()

    run_id = run.id
    db.commit()

    record_audit(
        db,
        actor=None,
        action=_audit_action_for_type(sync_type, "started"),
        entity_type="eworks_sync",
        entity_id=str(run_id),
        metadata={"filters": filters or {}, "actor_email": actor_email},
    )
    db.commit()

    thread = threading.Thread(
        target=_run_sync_worker,
        args=(run_id, sync_type, filters or {}, parsed_user_id, actor_email),
        daemon=True,
        name=f"eworks-sync-{sync_type}-{run_id}",
    )
    thread.start()
    logger.info("Scheduled background eWorks sync run_id=%s type=%s", run_id, sync_type)
    return run


def _run_job_appointment_backfill(db, run: EworksSyncRun | None = None) -> None:
    from app.services.eworks_job_detail_sync_service import backfill_job_appointments_from_details

    if run is not None:
        _progress_with_lock(db, run, "jobs", phase="appointments_backfill", commit=True)
    backfill_job_appointments_from_details(db)


def _run_sync_worker(
    run_id: uuid.UUID,
    sync_type: str,
    filters: dict[str, Any],
    user_id: uuid.UUID | None,
    actor_email: str | None,
) -> None:
    db = SessionLocal()
    run: EworksSyncRun | None = None
    lock_status = "success"
    try:
        run = db.get(EworksSyncRun, run_id)
        if run is None:
            logger.error("Background sync run %s not found", run_id)
            lock_status = "failed"
            return

        run.metadata_ = {**(run.metadata_ or {}), "phase": "running"}
        _progress_with_lock(db, run, sync_type, phase="running", commit=True)

        if sync_type == "quotes":
            mode = (filters or {}).get("mode", "full")
            if mode == "incremental_recent":
                summary, _ = sync_quotes_incremental_recent(
                    db,
                    window_minutes=int((filters or {}).get("recent_window_minutes", 60)),
                    timeout_seconds=int((filters or {}).get("timeout_seconds", 120)),
                    user_id=user_id,
                    run=run,
                )
            else:
                summary, _ = sync_quotes_from_eworks(db, filters=filters, user_id=user_id, run=run)
            db.commit()
            record_audit(
                db,
                actor=None,
                action=_audit_action_for_type("quotes", "completed"),
                entity_type="eworks_sync",
                entity_id=str(run_id),
                metadata={
                    "fetched": summary.fetched,
                    "created": summary.created,
                    "updated": summary.updated,
                    "failed": summary.failed,
                    "actor_email": actor_email,
                },
            )
            db.commit()
            return

        if sync_type == "customers":
            summary, _ = sync_customers_from_eworks(db, filters=filters, user_id=user_id, run=run)
            db.commit()
            record_audit(
                db,
                actor=None,
                action=_audit_action_for_type("customers", "completed"),
                entity_type="eworks_sync",
                entity_id=str(run_id),
                metadata={
                    "fetched": summary.fetched,
                    "created": summary.created,
                    "updated": summary.updated,
                    "failed": summary.failed,
                    "actor_email": actor_email,
                },
            )
            db.commit()
            return

        if sync_type == "jobs":
            summary, _ = sync_jobs_from_eworks(db, filters=filters, user_id=user_id, run=run)
            db.commit()
            try:
                _run_job_appointment_backfill(db, run)
                db.commit()
            except Exception:
                logger.exception("Job appointment backfill failed after jobs sync run_id=%s", run_id)
                db.rollback()
            record_audit(
                db,
                actor=None,
                action=_audit_action_for_type("jobs", "completed"),
                entity_type="eworks_sync",
                entity_id=str(run_id),
                metadata={
                    "fetched": summary.fetched,
                    "created": summary.created,
                    "updated": summary.updated,
                    "failed": summary.failed,
                    "actor_email": actor_email,
                },
            )
            db.commit()
            return

        result = sync_all_eworks(db, filters=filters, user_id=user_id, run=run)
        db.commit()
        try:
            _run_job_appointment_backfill(db, run)
            db.commit()
        except Exception:
            logger.exception("Job appointment backfill failed after all sync run_id=%s", run_id)
            db.rollback()
        record_audit(
            db,
            actor=None,
            action=_audit_action_for_type("all", "completed"),
            entity_type="eworks_sync",
            entity_id=str(run_id),
            metadata={
                "customers_fetched": result.customers.fetched,
                "quotes_fetched": result.quotes.fetched,
                "jobs_fetched": result.jobs.fetched,
                "errors": result.errors,
                "actor_email": actor_email,
            },
        )
        db.commit()
    except Exception as exc:
        lock_status = "failed"
        logger.exception("Background eWorks sync failed run_id=%s type=%s", run_id, sync_type)
        db.rollback()
        try:
            run = db.get(EworksSyncRun, run_id)
            if run is not None:
                fail_sync_run(db, run, error_message=str(exc), commit=True)
            record_audit(
                db,
                actor=None,
                action=_audit_action_for_type(sync_type, "failed"),
                entity_type="eworks_sync",
                entity_id=str(run_id),
                metadata={"error": str(exc), "actor_email": actor_email},
            )
            db.commit()
        except Exception:
            logger.exception("Failed to mark background sync run as failed run_id=%s", run_id)
            db.rollback()
    finally:
        try:
            run = db.get(EworksSyncRun, run_id)
            if run is not None and run.status == "running":
                fail_sync_run(db, run, error_message=_UNEXPECTED_EXIT_MESSAGE, commit=True)
                lock_status = "failed"
            release_sync_lock(db, sync_type, status=lock_status, commit=True)
        except Exception:
            logger.exception("Failed to finalize background sync run run_id=%s", run_id)
            db.rollback()
        db.close()
