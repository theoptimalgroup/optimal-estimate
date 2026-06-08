"""APScheduler-based background eWorks sync (customers, quotes, jobs, products).

Scheduler starts only when both EWORKS_BACKGROUND_SYNC_ENABLED and RUN_BACKGROUND_WORKER are true.
"""

from __future__ import annotations

import logging
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.core.exceptions import AppError
from app.db.session import SessionLocal
from app.models.eworks_sync import EworksSyncRun
from app.services.eworks_product_sync_service import sync_products_from_eworks
from app.services.eworks_sync_lock_service import (
    SYNC_LOCK_ACTIVE_MESSAGE,
    get_worker_id,
    release_sync_lock,
    touch_sync_lock_heartbeat,
    try_acquire_sync_lock,
)
from app.services.eworks_sync_runner import get_running_sync_run, schedule_eworks_sync
from app.services.eworks_sync_run_state import clear_stale_running_sync_locks
from app.services.eworks_sync_service import resolve_sync_filters

logger = logging.getLogger(__name__)

_SKIP_RUNNING_MESSAGE = "Skipped background sync because another sync is running"

_scheduler: BackgroundScheduler | None = None


def should_start_scheduler() -> bool:
    return bool(settings.eworks_background_sync_enabled and settings.run_background_worker)


def build_background_sync_config() -> dict[str, Any]:
    """Safe, read-only background sync config for admin APIs."""
    return {
        "enabled": settings.eworks_background_sync_enabled,
        "worker_enabled": settings.run_background_worker,
        "scheduler_active": should_start_scheduler(),
        "customers_enabled": settings.eworks_background_customers_enabled,
        "quotes_enabled": settings.eworks_background_quotes_enabled,
        "jobs_enabled": settings.eworks_background_jobs_enabled,
        "products_enabled": settings.eworks_background_products_enabled,
        "attachments_enabled": settings.eworks_background_attachments_enabled,
        "customers_interval_minutes": max(1, int(settings.eworks_customers_sync_interval_minutes)),
        "quotes_interval_minutes": max(1, int(settings.eworks_quotes_sync_interval_minutes)),
        "jobs_interval_minutes": max(1, int(settings.eworks_jobs_sync_interval_minutes)),
        "products_interval_minutes": max(1, int(settings.eworks_products_sync_interval_minutes)),
        "lookback_days": max(1, int(settings.eworks_sync_lookback_days)),
        "running_timeout_minutes": max(1, int(settings.eworks_sync_running_timeout_minutes)),
        "lock_timeout_minutes": max(1, int(settings.eworks_sync_lock_timeout_minutes)),
        "lock_heartbeat_seconds": max(15, int(settings.eworks_sync_lock_heartbeat_seconds)),
    }


def _prepare_sync_session(db) -> bool:
    """Clear stale locks and return False when another sync is already running."""
    clear_stale_running_sync_locks(db)
    if get_running_sync_run(db) is not None:
        logger.info(_SKIP_RUNNING_MESSAGE)
        return False
    return True


def _background_sync_filters() -> dict[str, Any]:
    return resolve_sync_filters(full=False)


def _schedule_background_sync(sync_type: str) -> None:
    db = SessionLocal()
    try:
        if not _prepare_sync_session(db):
            return
        schedule_eworks_sync(
            db,
            sync_type=sync_type,
            filters=_background_sync_filters(),
            user_id=None,
            actor_email="background-scheduler",
            source="background",
            locked_by=get_worker_id(),
        )
        logger.info("Background %s sync scheduled", sync_type)
    except AppError as exc:
        if exc.code == "SYNC_ALREADY_RUNNING":
            logger.info(_SKIP_RUNNING_MESSAGE)
        else:
            logger.exception("Background %s sync failed to start: %s", sync_type, exc.message)
    except Exception:
        logger.exception("Background %s sync failed unexpectedly", sync_type)
    finally:
        db.close()


def run_background_customers_sync() -> None:
    if not settings.eworks_background_customers_enabled:
        return
    if not settings.eworks_api_enabled:
        logger.info("Skipped background customers sync: eWorks API disabled")
        return
    _schedule_background_sync("customers")


def run_background_quotes_sync() -> None:
    if not settings.eworks_background_quotes_enabled:
        return
    if not settings.eworks_api_enabled:
        logger.info("Skipped background quotes sync: eWorks API disabled")
        return
    _schedule_background_sync("quotes")


def run_background_jobs_sync() -> None:
    if not settings.eworks_background_jobs_enabled:
        return
    if not settings.eworks_api_enabled:
        logger.info("Skipped background jobs sync: eWorks API disabled")
        return
    _schedule_background_sync("jobs")


def run_background_products_sync() -> None:
    if not settings.eworks_background_products_enabled:
        return

    db = SessionLocal()
    lock_type = "products"
    try:
        if not _prepare_sync_session(db):
            return

        lock = try_acquire_sync_lock(db, lock_type, locked_by=get_worker_id())
        if lock is None:
            logger.info(_SKIP_RUNNING_MESSAGE)
            return

        touch_sync_lock_heartbeat(db, lock_type)
        summary = sync_products_from_eworks(db)
        db.commit()
        status = "success" if summary.failed == 0 else "partial"
        release_sync_lock(db, lock_type, status=status)
        logger.info(
            "Background product sync finished status=%s fetched=%s created=%s updated=%s skipped=%s failed=%s",
            status,
            summary.fetched,
            summary.created,
            summary.updated,
            summary.skipped,
            summary.failed,
        )
    except AppError as exc:
        db.rollback()
        release_sync_lock(db, lock_type, status="failed")
        logger.warning("Background product sync unavailable: %s", exc.message)
    except Exception:
        db.rollback()
        release_sync_lock(db, lock_type, status="failed")
        logger.exception("Background product sync failed unexpectedly")
    finally:
        db.close()


def get_last_background_sync_run(db, *, sync_type: str | None = None) -> EworksSyncRun | None:
    """Return the most recent background sync run (any terminal or running state)."""
    runs = (
        db.query(EworksSyncRun)
        .order_by(EworksSyncRun.started_at.desc())
        .limit(100)
        .all()
    )
    for run in runs:
        metadata = run.metadata_ or {}
        if metadata.get("source") != "background":
            continue
        if sync_type is not None and run.sync_type != sync_type:
            continue
        return run
    return None


def get_last_successful_background_sync_run(db, *, sync_type: str) -> EworksSyncRun | None:
    runs = (
        db.query(EworksSyncRun)
        .filter(EworksSyncRun.sync_type == sync_type, EworksSyncRun.status.in_(["success", "partial"]))
        .order_by(EworksSyncRun.started_at.desc())
        .limit(20)
        .all()
    )
    for run in runs:
        metadata = run.metadata_ or {}
        if metadata.get("source") == "background":
            return run
    return None


def get_last_successful_sync_runs(db) -> dict[str, dict[str, Any] | None]:
    result: dict[str, dict[str, Any] | None] = {}
    for sync_type in ("customers", "quotes", "jobs", "all"):
        run = get_last_successful_background_sync_run(db, sync_type=sync_type)
        result[sync_type] = serialize_background_sync_run(run)
    result["products"] = None
    return result


def serialize_background_sync_run(run: EworksSyncRun | None) -> dict[str, Any] | None:
    if run is None:
        return None
    metadata = run.metadata_ or {}
    return {
        "run_id": str(run.id),
        "sync_type": run.sync_type,
        "status": run.status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "source": metadata.get("source"),
        "phase": metadata.get("phase"),
        "fetched_count": run.fetched_count,
        "updated_count": run.updated_count,
        "failed_count": run.failed_count,
        "error_message": run.error_message,
    }


def start_background_sync_scheduler() -> None:
    global _scheduler

    if not should_start_scheduler():
        logger.info(
            "Background eWorks sync scheduler not started "
            "(enabled=%s, worker=%s)",
            settings.eworks_background_sync_enabled,
            settings.run_background_worker,
        )
        return

    if _scheduler is not None and _scheduler.running:
        return

    scheduler = BackgroundScheduler(timezone="UTC")

    if settings.eworks_background_customers_enabled:
        scheduler.add_job(
            run_background_customers_sync,
            IntervalTrigger(minutes=max(1, int(settings.eworks_customers_sync_interval_minutes))),
            id="eworks_background_customers_sync",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

    if settings.eworks_background_quotes_enabled:
        scheduler.add_job(
            run_background_quotes_sync,
            IntervalTrigger(minutes=max(1, int(settings.eworks_quotes_sync_interval_minutes))),
            id="eworks_background_quotes_sync",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

    if settings.eworks_background_jobs_enabled:
        scheduler.add_job(
            run_background_jobs_sync,
            IntervalTrigger(minutes=max(1, int(settings.eworks_jobs_sync_interval_minutes))),
            id="eworks_background_jobs_sync",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

    if settings.eworks_background_products_enabled:
        scheduler.add_job(
            run_background_products_sync,
            IntervalTrigger(minutes=max(1, int(settings.eworks_products_sync_interval_minutes))),
            id="eworks_background_products_sync",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

    scheduler.start()
    _scheduler = scheduler
    logger.info(
        "Background eWorks worker started "
        "(customers=%s every %sm, quotes=%s every %sm, jobs=%s every %sm, products=%s every %sm)",
        settings.eworks_background_customers_enabled,
        settings.eworks_customers_sync_interval_minutes,
        settings.eworks_background_quotes_enabled,
        settings.eworks_quotes_sync_interval_minutes,
        settings.eworks_background_jobs_enabled,
        settings.eworks_jobs_sync_interval_minutes,
        settings.eworks_background_products_enabled,
        settings.eworks_products_sync_interval_minutes,
    )


def stop_background_sync_scheduler() -> None:
    global _scheduler
    if _scheduler is None:
        return
    try:
        _scheduler.shutdown(wait=False)
        logger.info("Background eWorks sync scheduler stopped")
    except Exception:
        logger.exception("Failed to stop background eWorks sync scheduler")
    finally:
        _scheduler = None


def is_scheduler_running() -> bool:
    return _scheduler is not None and _scheduler.running
