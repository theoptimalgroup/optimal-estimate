from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.dependencies import AuthenticatedUser, require_roles
from app.core.exceptions import success_response
from app.core.security import UserRole
from app.db.session import DbSession
from app.schemas.estimator import (
    EstimatorClientRead,
    EstimatorDashboardRead,
    EstimatorProductRead,
    EstimatorQuoteDetailRead,
    EstimatorQuoteRow,
    EstimatorResumeRead,
)
from app.services.estimator_service import (
    get_estimator_dashboard,
    get_estimator_quote,
    get_estimator_resume,
    list_estimator_approvals,
    list_estimator_clients,
    list_estimator_products,
    list_estimator_quotes,
)

router = APIRouter(prefix="/estimator", tags=["estimator"])


@router.get("/dashboard")
def get_estimator_dashboard_endpoint(
    db: DbSession,
    _user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN, UserRole.ESTIMATOR)),
):
    dashboard = get_estimator_dashboard(db)
    return success_response(EstimatorDashboardRead.model_validate(dashboard))


@router.get("/quotes")
def list_estimator_quotes_endpoint(
    db: DbSession,
    search: str | None = Query(None),
    status: str | None = Query(None),
    client_id: UUID | None = Query(None),
    trade_id: UUID | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN, UserRole.ESTIMATOR)),
):
    items, total = list_estimator_quotes(
        db,
        search=search,
        status=status,
        client_id=client_id,
        trade_id=trade_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return success_response(
        [EstimatorQuoteRow.model_validate(item) for item in items],
        meta={"total": total, "limit": limit, "offset": offset},
    )


@router.get("/quotes/{session_id}")
def get_estimator_quote_endpoint(
    session_id: UUID,
    db: DbSession,
    _user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN, UserRole.ESTIMATOR)),
):
    quote = get_estimator_quote(db, session_id)
    if quote is None:
        raise HTTPException(status_code=404, detail="Quote not found")
    return success_response(EstimatorQuoteDetailRead.model_validate(quote))


@router.post("/quotes/{session_id}/resume")
def resume_estimator_quote_endpoint(
    session_id: UUID,
    db: DbSession,
    _user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN, UserRole.ESTIMATOR)),
):
    resume = get_estimator_resume(db, session_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Quote cannot be resumed")
    return success_response(EstimatorResumeRead.model_validate(resume))


@router.get("/approvals")
def list_estimator_approvals_endpoint(
    db: DbSession,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN, UserRole.ESTIMATOR)),
):
    items, total = list_estimator_approvals(db, limit=limit, offset=offset)
    return success_response(
        [EstimatorQuoteRow.model_validate(item) for item in items],
        meta={"total": total, "limit": limit, "offset": offset},
    )


@router.get("/clients")
def list_estimator_clients_endpoint(
    db: DbSession,
    _user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN, UserRole.ESTIMATOR)),
):
    clients = list_estimator_clients(db)
    return success_response([EstimatorClientRead.model_validate(item) for item in clients])


@router.get("/products")
def list_estimator_products_endpoint(
    db: DbSession,
    search: str | None = Query(None),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN, UserRole.ESTIMATOR)),
):
    items, total = list_estimator_products(db, search=search, limit=limit, offset=offset)
    return success_response(
        [EstimatorProductRead.model_validate(item) for item in items],
        meta={"total": total, "limit": limit, "offset": offset},
    )
