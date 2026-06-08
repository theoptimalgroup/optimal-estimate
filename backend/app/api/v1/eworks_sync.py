"""Admin-only endpoints for triggering and viewing eWorks Quote/Job sync.

Read-only from eWorks: no records are written back to eWorks.
Sync jobs run in background threads so they continue if the client navigates away.
"""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import cast, or_, String, and_

from app.auth.dependencies import CurrentUser, require_roles
from app.core.exceptions import AppError, success_response
from app.core.security import UserRole
from app.db.session import DbSession
from app.models.eworks_sync import EworksAttachment, EworksCustomer, EworksJob, EworksQuote, EworksSyncRun
from app.models.product import Product
from app.schemas.quote_assignment import AssignmentCreate, AssignmentRead
from app.schemas.eworks_sync_api import (
    EworksActiveSyncRun,
    EworksAttachmentDetailRead,
    EworksAttachmentSafeRead,
    EworksBackgroundSyncConfigRead,
    EworksBackgroundSyncLastRunRead,
    EworksCustomerRead,
    EworksJobRead,
    EworksJobAppointmentBackfillRead,
    EworksJobSafeDetailRead,
    EworksQuoteDetailRead,
    EworksQuoteRead,
    EworksQuoteSafeDetailRead,
    EworksSyncRequest,
    EworksSyncLockRead,
    EworksSyncRunRead,
    EworksSyncStartResponse,
    EworksSyncStatusResponse,
)
from app.services.eworks_sync_runner import get_running_sync_run, schedule_eworks_sync
from app.services.background_sync_scheduler import (
    build_background_sync_config,
    get_last_background_sync_run,
    get_last_successful_sync_runs,
    serialize_background_sync_run,
)
from app.services.eworks_sync_lock_service import (
    get_active_sync_locks,
    has_stale_running_locks,
    serialize_sync_lock,
)
from app.services.eworks_sync_run_state import clear_stale_running_sync_locks, fail_sync_run
from app.services.eworks_attachment_sync_service import (
    list_attachments_for_parent,
    serialize_attachment_admin,
    serialize_attachment_safe,
)
from app.services.eworks_safe_detail_service import (
    build_job_safe_detail,
    build_quote_safe_detail,
    serialize_quote_list_item,
)
from app.services.quote_assignment_service import create_assignment, list_assignments_for_quote

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/eworks-sync", tags=["eworks-sync"])

AdminOnly = Annotated[CurrentUser, Depends(require_roles(UserRole.ADMIN))]
ManagerWrite = Annotated[CurrentUser, Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))]
StaffRead = Annotated[CurrentUser, Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.ESTIMATOR))]


def _build_filters(req: EworksSyncRequest) -> dict:
    from app.services.eworks_sync_service import resolve_sync_filters

    base = {
        "date_from": req.date_from,
        "date_to": req.date_to,
        "status": req.status,
        "page_limit": req.page_limit,
    }
    return resolve_sync_filters(base, full=req.full)


def _parse_optional_int(value: str | None) -> int | None:
    if not value or not str(value).strip():
        return None
    try:
        return int(str(value).strip())
    except ValueError:
        return None


def _apply_quote_search(q, search: str | None):
    if not search:
        return q
    pattern = f"%{search.strip()}%"
    numeric = _parse_optional_int(search)
    clauses = [
        EworksQuote.quote_ref.ilike(pattern),
        EworksQuote.customer_name.ilike(pattern),
        EworksQuote.description.ilike(pattern),
        EworksQuote.status_name.ilike(pattern),
    ]
    if numeric is not None:
        clauses.append(EworksQuote.eworks_quote_id == numeric)
    clauses.append(EworksQuote.status.ilike(pattern))
    clauses.append(cast(EworksQuote.tags, String).ilike(pattern))
    return q.filter(or_(*clauses))


def _apply_job_search(q, search: str | None):
    if not search:
        return q
    pattern = f"%{search.strip()}%"
    numeric = _parse_optional_int(search)
    clauses = [
        EworksJob.job_ref.ilike(pattern),
        EworksJob.customer_name.ilike(pattern),
        EworksJob.description.ilike(pattern),
        EworksJob.status_name.ilike(pattern),
    ]
    if numeric is not None:
        clauses.append(EworksJob.eworks_job_id == numeric)
        clauses.append(EworksJob.eworks_quote_id == numeric)
    clauses.append(EworksJob.status.ilike(pattern))
    clauses.append(cast(EworksJob.tags, String).ilike(pattern))
    return q.filter(or_(*clauses))


def _apply_status_filter(q, status: str | None, status_col, status_name_col, raw_payload_col=None):
    if not status or not str(status).strip():
        return q
    value = str(status).strip()
    pattern = f"%{value}%"
    clauses = [
        status_col == value,
        status_col.ilike(pattern),
        status_name_col == value,
        status_name_col.ilike(pattern),
    ]
    if raw_payload_col is not None:
        raw = cast(raw_payload_col, String)
        clauses.extend(
            [
                raw.ilike(f'%"status": {value}%'),
                raw.ilike(f'%"status": "{value}"%'),
                raw.ilike(f'%"Status": {value}%'),
                raw.ilike(f'%"Status": "{value}"%'),
                raw.ilike(f'%"id": {value}%'),
                raw.ilike(f'%"id": "{value}"%'),
            ]
        )
    return q.filter(or_(*clauses))


def _serialize_tags(tags: list | None) -> list[str]:
    from app.services.manager_dashboard_service import _parse_tags_value

    return _parse_tags_value(tags)


def _apply_tag_filter(q, tag: str | None, tags_col, raw_payload_col=None):
    from app.services.manager_dashboard_service import is_awaiting_supplier_tag, is_ready_to_send_tag

    if not tag or not str(tag).strip():
        return q
    tag_text = str(tag).strip()
    pattern = f"%{tag_text}%"
    clauses: list = [cast(tags_col, String).ilike(pattern)]

    if is_awaiting_supplier_tag(tag_text):
        clauses.append(cast(tags_col, String).ilike("%awaiting supplier%"))
    elif is_ready_to_send_tag(tag_text):
        clauses.append(
            and_(
                cast(tags_col, String).ilike("%ready to send%"),
                or_(cast(tags_col, String).ilike("%quote%"), cast(tags_col, String).ilike("%quotes%")),
            )
        )

    if raw_payload_col is not None:
        raw = cast(raw_payload_col, String)
        if is_awaiting_supplier_tag(tag_text):
            clauses.append(raw.ilike("%awaiting supplier%"))
        elif is_ready_to_send_tag(tag_text):
            clauses.append(
                and_(
                    raw.ilike("%ready to send%"),
                    or_(raw.ilike("%quote%"), raw.ilike("%quotes%")),
                )
            )
        else:
            for key in ("tags", "tag_names", "labels", "categories"):
                clauses.append(raw.ilike(f'%"{key}"%{pattern[1:-1]}%'))
            clauses.append(raw.ilike(pattern))
    return q.filter(or_(*clauses))


def _serialize_run(run: EworksSyncRun) -> dict:
    metadata = run.metadata_ or {}
    return EworksSyncRunRead(
        id=str(run.id),
        sync_type=run.sync_type,
        status=run.status,
        started_at=str(run.started_at) if run.started_at else None,
        finished_at=str(run.finished_at) if run.finished_at else None,
        fetched_count=run.fetched_count,
        created_count=run.created_count,
        updated_count=run.updated_count,
        failed_count=run.failed_count,
        error_message=run.error_message,
        metadata=metadata,
    ).model_dump()


def _serialize_active_run(run: EworksSyncRun | None) -> EworksActiveSyncRun | None:
    if run is None:
        return None
    metadata = run.metadata_ or {}
    return EworksActiveSyncRun(
        run_id=str(run.id),
        sync_type=run.sync_type,
        started_at=str(run.started_at) if run.started_at else None,
        phase=metadata.get("phase"),
    )


def _start_background_sync(db: DbSession, actor: AdminOnly, sync_type: str, req: EworksSyncRequest) -> dict:
    try:
        run = schedule_eworks_sync(
            db,
            sync_type=sync_type,
            filters=_build_filters(req),
            user_id=actor.id,
            actor_email=actor.email,
        )
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return success_response(
        EworksSyncStartResponse(
            run_id=str(run.id),
            sync_type=sync_type,
            status="running",
            message="Sync started in background. Poll /eworks-sync/runs/{run_id} for progress.",
        ).model_dump()
    )


# ---------------------------------------------------------------------------
# Sync trigger endpoints (admin only, background)
# ---------------------------------------------------------------------------

@router.post("/quotes")
def trigger_quotes_sync(
    db: DbSession,
    actor: AdminOnly,
    req: EworksSyncRequest = EworksSyncRequest(),
):
    """Start background sync of eWorks Quotes into local DB (admin only, read-only from eWorks)."""
    return _start_background_sync(db, actor, "quotes", req)


@router.post("/jobs")
def trigger_jobs_sync(
    db: DbSession,
    actor: AdminOnly,
    req: EworksSyncRequest = EworksSyncRequest(),
):
    """Start background sync of eWorks Jobs into local DB (admin only, read-only from eWorks)."""
    return _start_background_sync(db, actor, "jobs", req)


@router.post("/jobs/backfill-appointments")
def backfill_job_appointments(
    db: DbSession,
    actor: AdminOnly,
    limit: int | None = Query(default=None, ge=1, le=5000),
):
    """Fetch eWorks Job detail for synced jobs and backfill appointment rows (admin only)."""
    from app.core.config import settings as cfg
    from app.services.eworks_job_detail_sync_service import backfill_job_appointments_from_details

    if not cfg.eworks_api_enabled:
        raise HTTPException(status_code=503, detail="eWorks API is disabled")

    effective_limit = limit
    if effective_limit is None and cfg.eworks_sync_job_details_limit_per_run is not None:
        effective_limit = cfg.eworks_sync_job_details_limit_per_run

    summary = backfill_job_appointments_from_details(db, limit=effective_limit)
    return success_response(EworksJobAppointmentBackfillRead.model_validate(summary.__dict__).model_dump())


@router.post("/quotes/backfill-attachments")
def backfill_quote_attachments(
    db: DbSession,
    actor: AdminOnly,
    limit: int | None = Query(default=None, ge=1, le=5000),
):
    """Fetch eWorks quote attachments for synced quotes and upsert local rows (admin only)."""
    from app.core.config import settings as cfg
    from app.schemas.eworks_sync_api import EworksQuoteAttachmentBackfillRead
    from app.services.eworks_quote_attachment_sync_service import backfill_quote_attachments_from_eworks

    if not cfg.eworks_api_enabled:
        raise HTTPException(status_code=503, detail="eWorks API is disabled")

    summary = backfill_quote_attachments_from_eworks(db, limit=limit)
    return success_response(EworksQuoteAttachmentBackfillRead.model_validate(summary.__dict__).model_dump())


@router.post("/customers")
def trigger_customers_sync(
    db: DbSession,
    actor: AdminOnly,
    req: EworksSyncRequest = EworksSyncRequest(),
):
    """Start background sync of eWorks Customers into local DB (admin only, read-only from eWorks)."""
    return _start_background_sync(db, actor, "customers", req)


@router.post("/all")
def trigger_all_sync(
    db: DbSession,
    actor: AdminOnly,
    req: EworksSyncRequest = EworksSyncRequest(),
):
    """Start background sync of eWorks Customers, Quotes, and Jobs (admin only, read-only from eWorks)."""
    return _start_background_sync(db, actor, "all", req)


# ---------------------------------------------------------------------------
# Status endpoint
# ---------------------------------------------------------------------------

@router.get("/status")
def get_sync_status(db: DbSession, actor: AdminOnly):
    """Return counts, last sync timestamps, and any active background sync."""
    from app.core.config import settings as cfg

    clear_stale_running_sync_locks(db)
    quotes_count = db.query(EworksQuote).count()
    jobs_count = db.query(EworksJob).count()
    customers_count = db.query(EworksCustomer).count()
    products_count = db.query(Product).count()

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
    last_c = (
        db.query(EworksCustomer.synced_at)
        .order_by(EworksCustomer.synced_at.desc())
        .first()
    )
    last_p = (
        db.query(Product.updated_at)
        .order_by(Product.updated_at.desc())
        .first()
    )
    active = get_running_sync_run(db)
    background_config = build_background_sync_config()
    last_background = serialize_background_sync_run(get_last_background_sync_run(db))
    active_locks = [EworksSyncLockRead(**serialize_sync_lock(lock)) for lock in get_active_sync_locks(db)]
    stale_warning = has_stale_running_locks(db)
    last_successful_raw = get_last_successful_sync_runs(db)
    last_successful = {
        key: EworksBackgroundSyncLastRunRead(**value) if value else None
        for key, value in last_successful_raw.items()
    }

    return success_response(
        EworksSyncStatusResponse(
            quotes_count=quotes_count,
            jobs_count=jobs_count,
            customers_count=customers_count,
            products_count=products_count,
            last_quotes_sync=str(last_q[0]) if last_q else None,
            last_jobs_sync=str(last_j[0]) if last_j else None,
            last_customers_sync=str(last_c[0]) if last_c else None,
            last_products_sync=str(last_p[0]) if last_p else None,
            eworks_api_enabled=bool(cfg.eworks_api_enabled),
            active_sync=_serialize_active_run(active),
            background_sync=EworksBackgroundSyncConfigRead(**background_config),
            last_background_sync=(
                EworksBackgroundSyncLastRunRead(**last_background) if last_background else None
            ),
            active_sync_locks=active_locks,
            stale_lock_warning=stale_warning,
            last_successful_syncs=last_successful,
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
        "items": [_serialize_run(r) for r in runs],
        "total": total,
        "limit": limit,
        "offset": offset,
    })


@router.get("/runs/{run_id}")
def get_sync_run(db: DbSession, run_id: UUID, actor: AdminOnly):
    """Return a single sync run for progress polling (admin only)."""
    run = db.query(EworksSyncRun).filter(EworksSyncRun.id == run_id).one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Sync run not found")
    return success_response(_serialize_run(run))


@router.post("/runs/{run_id}/cancel")
def cancel_sync_run(db: DbSession, run_id: UUID, actor: AdminOnly):
    """Mark a stuck background sync as failed so a new sync can start (admin only)."""
    from datetime import datetime, timezone

    run = db.query(EworksSyncRun).filter(EworksSyncRun.id == run_id).one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Sync run not found")
    if run.status != "running":
        raise HTTPException(status_code=400, detail="Sync run is not active")

    now = datetime.now(timezone.utc)
    run.status = "failed"
    run.finished_at = now
    run.error_message = "Sync cancelled by admin."
    run.metadata_ = {
        **(run.metadata_ or {}),
        "phase": "cancelled",
        "cancelled_at": now.isoformat(),
        "cancelled_by": actor.email,
    }
    db.commit()
    return success_response(_serialize_run(run))


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
    tag: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    """List locally-synced eWorks Quotes with pagination and filtering."""
    q = db.query(EworksQuote)

    q = _apply_quote_search(q, search)
    if customer_id is not None:
        q = q.filter(EworksQuote.customer_id == customer_id)
    if customer_name:
        q = q.filter(EworksQuote.customer_name.ilike(f"%{customer_name.strip()}%"))
    q = _apply_status_filter(q, status, EworksQuote.status, EworksQuote.status_name, EworksQuote.raw_payload)
    q = _apply_tag_filter(q, tag, EworksQuote.tags, EworksQuote.raw_payload)
    if date_from:
        q = q.filter(EworksQuote.quote_date >= date_from)
    if date_to:
        q = q.filter(EworksQuote.quote_date <= date_to)

    total = q.count()
    rows = q.order_by(EworksQuote.eworks_quote_id.desc()).offset(offset).limit(limit).all()

    return success_response({
        "items": [serialize_quote_list_item(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    })


@router.get("/quotes/{quote_id}/safe")
def get_quote_safe_detail(db: DbSession, quote_id: int, actor: StaffRead):
    """Return grouped manager-safe quote detail without raw_payload (admin/manager/estimator)."""
    row = db.query(EworksQuote).filter(EworksQuote.id == quote_id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Quote not found")
    return success_response(
        EworksQuoteSafeDetailRead.model_validate(build_quote_safe_detail(db, row)).model_dump()
    )


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
            tags=_serialize_tags(row.tags),
            synced_at=str(row.synced_at) if row.synced_at else None,
            notes=row.notes,
            customer_notes=row.customer_notes,
            terms=row.terms,
            project_id=row.project_id,
            raw_payload=row.raw_payload,
        ).model_dump()
    )


@router.get("/customers")
def list_customers(
    db: DbSession,
    actor: AdminOnly,
    search: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    """List locally-synced eWorks Customers (admin only; no raw_payload)."""
    q = db.query(EworksCustomer)
    if search:
        pattern = f"%{search.strip()}%"
        numeric = _parse_optional_int(search)
        clauses = [
            EworksCustomer.customer_name.ilike(pattern),
            EworksCustomer.full_name.ilike(pattern),
            EworksCustomer.company_name.ilike(pattern),
            EworksCustomer.email.ilike(pattern),
            EworksCustomer.phone.ilike(pattern),
        ]
        if numeric is not None:
            clauses.append(EworksCustomer.eworks_customer_id == numeric)
        q = q.filter(or_(*clauses))

    total = q.count()
    rows = q.order_by(EworksCustomer.eworks_customer_id.desc()).offset(offset).limit(limit).all()

    return success_response({
        "items": [
            EworksCustomerRead(
                id=r.id,
                eworks_customer_id=r.eworks_customer_id,
                customer_name=r.customer_name,
                full_name=r.full_name,
                company_name=r.company_name,
                email=r.email,
                phone=r.phone,
                billing_email=r.billing_email,
                address_1=r.address_1,
                address_2=r.address_2,
                city=r.city,
                county=r.county,
                postcode=r.postcode,
                synced_at=str(r.synced_at) if r.synced_at else None,
            ).model_dump()
            for r in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    })


@router.get("/jobs")
def list_jobs(
    db: DbSession,
    actor: StaffRead,
    search: str | None = Query(default=None),
    customer_id: int | None = Query(default=None),
    customer_name: str | None = Query(default=None),
    status: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    """List locally-synced eWorks Jobs with pagination and filtering."""
    q = db.query(EworksJob)

    q = _apply_job_search(q, search)
    if customer_id is not None:
        q = q.filter(EworksJob.customer_id == customer_id)
    if customer_name:
        q = q.filter(EworksJob.customer_name.ilike(f"%{customer_name.strip()}%"))
    q = _apply_status_filter(q, status, EworksJob.status, EworksJob.status_name, EworksJob.raw_payload)
    q = _apply_tag_filter(q, tag, EworksJob.tags, EworksJob.raw_payload)
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
                tags=_serialize_tags(r.tags),
                total_appointments=r.total_appointments,
                completed_appointments=r.completed_appointments,
                detail_synced_at=str(r.detail_synced_at) if r.detail_synced_at else None,
                synced_at=str(r.synced_at) if r.synced_at else None,
            ).model_dump()
            for r in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    })


@router.get("/jobs/{job_id}/safe")
def get_job_safe_detail(db: DbSession, job_id: int, actor: StaffRead):
    """Return grouped manager-safe job detail without raw_payload (admin/manager/estimator)."""
    row = db.query(EworksJob).filter(EworksJob.id == job_id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return success_response(
        EworksJobSafeDetailRead.model_validate(build_job_safe_detail(db, row)).model_dump()
    )


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


@router.get("/quotes/{quote_id}/attachments")
def list_quote_attachments(db: DbSession, quote_id: int, actor: StaffRead):
    """List safe attachment metadata for a locally-synced quote."""
    row = db.query(EworksQuote).filter(EworksQuote.id == quote_id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Quote not found")
    attachments = list_attachments_for_parent(
        db,
        parent_type="quote",
        parent_local_id=row.id,
        parent_eworks_id=row.eworks_quote_id,
    )
    return success_response(
        {
            "items": [
                EworksAttachmentSafeRead.model_validate(serialize_attachment_safe(item)).model_dump()
                for item in attachments
            ],
            "total": len(attachments),
        }
    )


@router.get("/jobs/{job_id}/attachments")
def list_job_attachments(db: DbSession, job_id: int, actor: StaffRead):
    """List safe attachment metadata for a locally-synced job."""
    row = db.query(EworksJob).filter(EworksJob.id == job_id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    attachments = list_attachments_for_parent(
        db,
        parent_type="job",
        parent_local_id=row.id,
        parent_eworks_id=row.eworks_job_id,
    )
    return success_response(
        {
            "items": [
                EworksAttachmentSafeRead.model_validate(serialize_attachment_safe(item)).model_dump()
                for item in attachments
            ],
            "total": len(attachments),
        }
    )


@router.get("/attachments/{attachment_id}")
def get_attachment_detail(db: DbSession, attachment_id: int, actor: AdminOnly):
    """Return attachment detail including raw_payload (admin only)."""
    row = db.query(EworksAttachment).filter(EworksAttachment.id == attachment_id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return success_response(
        EworksAttachmentDetailRead.model_validate(serialize_attachment_admin(row)).model_dump()
    )


@router.get("/attachments/{attachment_id}/download")
def download_attachment(db: DbSession, attachment_id: int, actor: StaffRead):
    """On-demand attachment download (disabled by default until eWorks endpoint is confirmed)."""
    from app.core.config import settings

    row = db.query(EworksAttachment).filter(EworksAttachment.id == attachment_id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Attachment not found")
    if not settings.eworks_sync_attachment_files_enabled:
        raise HTTPException(
            status_code=503,
            detail="Attachment file download is disabled (EWORKS_SYNC_ATTACHMENT_FILES_ENABLED=false)",
        )
    raise HTTPException(status_code=501, detail="Attachment download endpoint not configured")


@router.get("/quotes/{quote_id}/assignments")
def list_quote_assignments(db: DbSession, quote_id: int, actor: ManagerWrite):
    """List assignments for a locally-synced quote (admin/manager)."""
    items = list_assignments_for_quote(db, quote_id)
    return success_response(
        {
            "items": [AssignmentRead.model_validate(item).model_dump() for item in items],
            "total": len(items),
        }
    )


@router.post("/quotes/{quote_id}/assignments")
def create_quote_assignment(db: DbSession, quote_id: int, body: AssignmentCreate, actor: ManagerWrite):
    """Assign a synced quote to a registered or external estimator/engineer."""
    data = create_assignment(
        db,
        quote_id=quote_id,
        payload=body.model_dump(mode="json"),
        current_user=actor,
    )
    return success_response(AssignmentRead.model_validate(data).model_dump())
