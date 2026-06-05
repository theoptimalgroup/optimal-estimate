"""Admin-only endpoints for triggering and viewing eWorks Quote/Job sync.

Read-only from eWorks: no records are written back to eWorks.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.dependencies import CurrentUser, require_roles
from app.core.exceptions import AppError, success_response
from app.core.security import UserRole
from app.db.session import DbSession
from app.models.eworks_sync import EworksJob, EworksQuote, EworksSyncRun
from app.schemas.eworks_sync_api import (
    EworksJobRead,
    EworksQuoteDetailRead,
    EworksQuoteRead,
    EworksSyncRequest,
    EworksSyncRunRead,
    EworksSyncStatusResponse,
)
from app.services.audit_helpers import record_audit
from app.services.eworks_sync_service import (
    sync_all_eworks,
    sync_jobs_from_eworks,
    sync_quotes_from_eworks,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/eworks-sync", tags=["eworks-sync"])

AdminOnly = Annotated[CurrentUser, Depends(require_roles(UserRole.ADMIN))]
StaffRead = Annotated[CurrentUser, Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.ESTIMATOR))]


def _build_filters(req: EworksSyncRequest) -> dict:
    return {
        "date_from": req.date_from,
        "date_to": req.date_to,
        "status": req.status,
        "page_limit": req.page_limit,
    }


# ---------------------------------------------------------------------------
# Sync trigger endpoints (admin only)
# ---------------------------------------------------------------------------

@router.post("/quotes")
def trigger_quotes_sync(
    db: DbSession,
    actor: AdminOnly,
    req: EworksSyncRequest = EworksSyncRequest(),
):
    """Fetch all eWorks Quotes and upsert into local DB (admin only, read-only from eWorks)."""
    record_audit(
        db,
        actor=actor,
        action="eworks_quotes_sync_started",
        entity_type="eworks_sync",
        entity_id=None,
        metadata={"filters": req.model_dump(exclude_none=True)},
    )
    try:
        summary, run = sync_quotes_from_eworks(db, filters=_build_filters(req), user_id=actor.id)
        db.commit()
    except AppError as exc:
        db.rollback()
        record_audit(db, actor=actor, action="eworks_quotes_sync_failed", entity_type="eworks_sync", entity_id=None, metadata={"error": exc.message})
        db.commit()
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except Exception as exc:
        db.rollback()
        record_audit(db, actor=actor, action="eworks_quotes_sync_failed", entity_type="eworks_sync", entity_id=None, metadata={"error": str(exc)})
        db.commit()
        raise HTTPException(status_code=500, detail="Quotes sync failed") from exc

    record_audit(
        db,
        actor=actor,
        action="eworks_quotes_sync_completed",
        entity_type="eworks_sync",
        entity_id=str(run.id),
        metadata={
            "fetched": summary.fetched,
            "created": summary.created,
            "updated": summary.updated,
            "failed": summary.failed,
        },
    )
    db.commit()
    return success_response({"summary": summary.model_dump(), "run_id": str(run.id)})


@router.post("/jobs")
def trigger_jobs_sync(
    db: DbSession,
    actor: AdminOnly,
    req: EworksSyncRequest = EworksSyncRequest(),
):
    """Fetch all eWorks Jobs and upsert into local DB (admin only, read-only from eWorks)."""
    record_audit(
        db,
        actor=actor,
        action="eworks_jobs_sync_started",
        entity_type="eworks_sync",
        entity_id=None,
        metadata={"filters": req.model_dump(exclude_none=True)},
    )
    try:
        summary, run = sync_jobs_from_eworks(db, filters=_build_filters(req), user_id=actor.id)
        db.commit()
    except AppError as exc:
        db.rollback()
        record_audit(db, actor=actor, action="eworks_jobs_sync_failed", entity_type="eworks_sync", entity_id=None, metadata={"error": exc.message})
        db.commit()
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except Exception as exc:
        db.rollback()
        record_audit(db, actor=actor, action="eworks_jobs_sync_failed", entity_type="eworks_sync", entity_id=None, metadata={"error": str(exc)})
        db.commit()
        raise HTTPException(status_code=500, detail="Jobs sync failed") from exc

    record_audit(
        db,
        actor=actor,
        action="eworks_jobs_sync_completed",
        entity_type="eworks_sync",
        entity_id=str(run.id),
        metadata={
            "fetched": summary.fetched,
            "created": summary.created,
            "updated": summary.updated,
            "failed": summary.failed,
        },
    )
    db.commit()
    return success_response({"summary": summary.model_dump(), "run_id": str(run.id)})


@router.post("/all")
def trigger_all_sync(
    db: DbSession,
    actor: AdminOnly,
    req: EworksSyncRequest = EworksSyncRequest(),
):
    """Fetch all eWorks Quotes and Jobs and upsert both (admin only, read-only from eWorks)."""
    record_audit(
        db,
        actor=actor,
        action="eworks_all_sync_started",
        entity_type="eworks_sync",
        entity_id=None,
        metadata={"filters": req.model_dump(exclude_none=True)},
    )
    try:
        result = sync_all_eworks(db, filters=_build_filters(req), user_id=actor.id)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Sync all failed") from exc

    record_audit(
        db,
        actor=actor,
        action="eworks_all_sync_completed",
        entity_type="eworks_sync",
        entity_id=None,
        metadata={
            "quotes_fetched": result.quotes.fetched,
            "jobs_fetched": result.jobs.fetched,
            "errors": result.errors,
        },
    )
    db.commit()
    return success_response(result.model_dump())


# ---------------------------------------------------------------------------
# Status endpoint
# ---------------------------------------------------------------------------

@router.get("/status")
def get_sync_status(db: DbSession, actor: AdminOnly):
    """Return counts and last sync timestamps for local eWorks data (admin only)."""
    from app.core.config import settings as cfg

    quotes_count = db.query(EworksQuote).count()
    jobs_count = db.query(EworksJob).count()

    last_q = (
        db.query(EworksQuote.synced_at)
        .order_by(EworksQuote.synced_at.desc())
        .first()
    )
    last_j = (
        db.query(EworksJob.synced_at)
        .order_by(EworksJob.synced_at.desc())
        .first()
    )

    return success_response(
        EworksSyncStatusResponse(
            quotes_count=quotes_count,
            jobs_count=jobs_count,
            last_quotes_sync=str(last_q[0]) if last_q else None,
            last_jobs_sync=str(last_j[0]) if last_j else None,
            eworks_api_enabled=bool(cfg.eworks_api_enabled),
        ).model_dump()
    )


# ---------------------------------------------------------------------------
# Sync runs history
# ---------------------------------------------------------------------------

@router.get("/runs")
def list_sync_runs(
    db: DbSession,
    actor: AdminOnly,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Return recent sync run history (admin only)."""
    runs = (
        db.query(EworksSyncRun)
        .order_by(EworksSyncRun.started_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    total = db.query(EworksSyncRun).count()
    return success_response({
        "items": [
            EworksSyncRunRead(
                id=str(r.id),
                sync_type=r.sync_type,
                status=r.status,
                started_at=str(r.started_at) if r.started_at else None,
                finished_at=str(r.finished_at) if r.finished_at else None,
                fetched_count=r.fetched_count,
                created_count=r.created_count,
                updated_count=r.updated_count,
                failed_count=r.failed_count,
                error_message=r.error_message,
            ).model_dump()
            for r in runs
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    })


# ---------------------------------------------------------------------------
# Local data read endpoints (admin/manager/estimator)
# ---------------------------------------------------------------------------

@router.get("/quotes")
def list_quotes(
    db: DbSession,
    actor: StaffRead,
    search: str | None = Query(default=None),
    customer_id: int | None = Query(default=None),
    customer_name: str | None = Query(default=None),
    status: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    """List locally-synced eWorks Quotes with pagination and filtering."""
    q = db.query(EworksQuote)

    if search:
        pattern = f"%{search}%"
        q = q.filter(
            EworksQuote.quote_ref.ilike(pattern)
            | EworksQuote.customer_name.ilike(pattern)
            | EworksQuote.description.ilike(pattern)
        )
    if customer_id is not None:
        q = q.filter(EworksQuote.customer_id == customer_id)
    if customer_name:
        q = q.filter(EworksQuote.customer_name.ilike(f"%{customer_name}%"))
    if status:
        q = q.filter(EworksQuote.status == status)
    if date_from:
        q = q.filter(EworksQuote.quote_date >= date_from)
    if date_to:
        q = q.filter(EworksQuote.quote_date <= date_to)

    total = q.count()
    rows = q.order_by(EworksQuote.eworks_quote_id.desc()).offset(offset).limit(limit).all()

    return success_response({
        "items": [
            EworksQuoteRead(
                id=r.id,
                eworks_quote_id=r.eworks_quote_id,
                quote_ref=r.quote_ref,
                customer_id=r.customer_id,
                customer_name=r.customer_name,
                status=r.status,
                status_name=r.status_name,
                quote_date=r.quote_date,
                expiry_date=r.expiry_date,
                description=r.description,
                customer_ref=r.customer_ref,
                po_ref=r.po_ref,
                wo_ref=r.wo_ref,
                subtotal=float(r.subtotal) if r.subtotal is not None else None,
                vat=float(r.vat) if r.vat is not None else None,
                total=float(r.total) if r.total is not None else None,
                synced_at=str(r.synced_at) if r.synced_at else None,
            ).model_dump()
            for r in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    })


@router.get("/quotes/{quote_id}")
def get_quote_detail(db: DbSession, quote_id: int, actor: AdminOnly):
    """Return full detail including raw_payload for a locally-synced Quote (admin only)."""
    row = db.query(EworksQuote).filter(EworksQuote.id == quote_id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Quote not found")
    return success_response(
        EworksQuoteDetailRead(
            id=row.id,
            eworks_quote_id=row.eworks_quote_id,
            quote_ref=row.quote_ref,
            customer_id=row.customer_id,
            customer_name=row.customer_name,
            status=row.status,
            status_name=row.status_name,
            quote_date=row.quote_date,
            expiry_date=row.expiry_date,
            description=row.description,
            customer_ref=row.customer_ref,
            po_ref=row.po_ref,
            wo_ref=row.wo_ref,
            subtotal=float(row.subtotal) if row.subtotal is not None else None,
            vat=float(row.vat) if row.vat is not None else None,
            total=float(row.total) if row.total is not None else None,
            synced_at=str(row.synced_at) if row.synced_at else None,
            notes=row.notes,
            customer_notes=row.customer_notes,
            terms=row.terms,
            project_id=row.project_id,
            raw_payload=row.raw_payload,
        ).model_dump()
    )


@router.get("/jobs")
def list_jobs(
    db: DbSession,
    actor: StaffRead,
    search: str | None = Query(default=None),
    customer_id: int | None = Query(default=None),
    customer_name: str | None = Query(default=None),
    status: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    """List locally-synced eWorks Jobs with pagination and filtering."""
    q = db.query(EworksJob)

    if search:
        pattern = f"%{search}%"
        q = q.filter(
            EworksJob.job_ref.ilike(pattern)
            | EworksJob.customer_name.ilike(pattern)
            | EworksJob.description.ilike(pattern)
        )
    if customer_id is not None:
        q = q.filter(EworksJob.customer_id == customer_id)
    if customer_name:
        q = q.filter(EworksJob.customer_name.ilike(f"%{customer_name}%"))
    if status:
        q = q.filter(EworksJob.status == status)
    if date_from:
        q = q.filter(EworksJob.job_date >= date_from)
    if date_to:
        q = q.filter(EworksJob.job_date <= date_to)

    total = q.count()
    rows = q.order_by(EworksJob.eworks_job_id.desc()).offset(offset).limit(limit).all()

    return success_response({
        "items": [
            EworksJobRead(
                id=r.id,
                eworks_job_id=r.eworks_job_id,
                job_ref=r.job_ref,
                eworks_quote_id=r.eworks_quote_id,
                customer_id=r.customer_id,
                customer_name=r.customer_name,
                status=r.status,
                status_name=r.status_name,
                job_date=r.job_date,
                description=r.description,
                address=r.address,
                subtotal=float(r.subtotal) if r.subtotal is not None else None,
                vat=float(r.vat) if r.vat is not None else None,
                total=float(r.total) if r.total is not None else None,
                synced_at=str(r.synced_at) if r.synced_at else None,
            ).model_dump()
            for r in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    })


@router.get("/jobs/{job_id}")
def get_job_detail(db: DbSession, job_id: int, actor: AdminOnly):
    """Return full detail including raw_payload for a locally-synced Job (admin only)."""
    row = db.query(EworksJob).filter(EworksJob.id == job_id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return success_response({
        "id": row.id,
        "eworks_job_id": row.eworks_job_id,
        "job_ref": row.job_ref,
        "eworks_quote_id": row.eworks_quote_id,
        "customer_id": row.customer_id,
        "customer_name": row.customer_name,
        "status": row.status,
        "status_name": row.status_name,
        "job_date": row.job_date,
        "description": row.description,
        "notes": row.notes,
        "address": row.address,
        "subtotal": float(row.subtotal) if row.subtotal is not None else None,
        "vat": float(row.vat) if row.vat is not None else None,
        "total": float(row.total) if row.total is not None else None,
        "synced_at": str(row.synced_at) if row.synced_at else None,
        "raw_payload": row.raw_payload,
    })
