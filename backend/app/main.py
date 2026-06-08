from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import AppError, error_response
from app.core.logging import configure_application_insights, configure_logging


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    configure_application_insights()

    from app.db.session import SessionLocal
    from app.services.background_sync_scheduler import (
        should_start_scheduler,
        start_background_sync_scheduler,
        stop_background_sync_scheduler,
    )
    from app.services.eworks_sync_run_state import clear_stale_running_sync_locks

    import logging

    startup_logger = logging.getLogger(__name__)

    if settings.is_dev_auth:
        if settings.dev_auth_enabled:
            startup_logger.info("Dev auth enabled for %s", settings.dev_user_email)
        else:
            startup_logger.warning(
                "AUTH_PROVIDER=dev but DEV_AUTH_ENABLED=false; GET /auth/me will return 401 without a token"
            )
    elif settings.is_azure_auth:
        startup_logger.info("Azure auth enabled (tenant=%s)", settings.azure_tenant_id)

    if settings.run_background_worker:
        startup_logger.info("Starting in background worker mode")
    else:
        startup_logger.info("Starting in API mode (background scheduler disabled)")

    db = SessionLocal()
    try:
        cleared = clear_stale_running_sync_locks(db)
        if cleared:
            startup_logger.info("Cleared %s stale eWorks sync run(s) on startup", cleared)
    except Exception:
        startup_logger.exception("Failed to recover stale eWorks sync runs on startup")
    finally:
        db.close()

    start_background_sync_scheduler()
    yield
    stop_background_sync_scheduler()


app = FastAPI(title="Optimal Estimate Calculator API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content=error_response(exc.code, exc.message, exc.details))


@app.get("/health")
def health():
    from app.db.session import SessionLocal
    from app.services.background_sync_scheduler import is_scheduler_running, should_start_scheduler

    database_ok = False
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            database_ok = True
        finally:
            db.close()
    except Exception:
        database_ok = False

    scheduler_expected = should_start_scheduler()
    scheduler_running = is_scheduler_running() if settings.run_background_worker else False
    scheduler_ok = (not scheduler_expected) or scheduler_running

    status = "ok" if database_ok and scheduler_ok else "degraded"

    return {
        "status": status,
        "environment": settings.environment,
        "storage_backend": settings.storage_backend,
        "run_seed": settings.effective_run_seed,
        "frontend_url": settings.frontend_url or settings.cors_origin_list[0] if settings.cors_origin_list else None,
        "database_ok": database_ok,
        "background_worker_mode": settings.run_background_worker,
        "background_sync_enabled": settings.eworks_background_sync_enabled,
        "scheduler_expected": scheduler_expected,
        "scheduler_running": scheduler_running,
    }


app.include_router(api_router, prefix=settings.api_v1_prefix)
