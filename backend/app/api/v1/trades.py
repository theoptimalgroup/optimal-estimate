from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select

from app.auth.dependencies import AuthenticatedUser, require_roles
from app.core.exceptions import success_response
from app.core.security import UserRole
from app.db.session import DbSession
from app.models.trade import Trade
from app.schemas.master_data import TradeRead
from app.schemas.trade_admin import TradeAdminUpdate
from app.services.audit_helpers import record_audit
from app.services.trade_admin_service import get_trade_detail, list_trades_admin, update_trade
from app.services.trade_service import trade_search_filter

router = APIRouter(prefix="/trades", tags=["trades"])


@router.get("")
def list_trades(
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    limit: int | None = Query(None, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None, description="Filter by trade name or description"),
    is_active: bool | None = None,
    active: bool | None = Query(None, description="Alias for is_active (admin UI)"),
):
    active_filter = is_active if is_active is not None else active

    if limit is not None:
        trades, total = list_trades_admin(
            db,
            search=search,
            active=active_filter,
            limit=limit,
            offset=offset,
        )
        return success_response(trades, meta={"total": total, "limit": limit, "offset": offset})

    query = select(Trade)
    search_filter = trade_search_filter(search)
    if search_filter is not None:
        query = query.where(search_filter)
    if active_filter is not None:
        query = query.where(Trade.is_active.is_(active_filter))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    trades = db.scalars(query.order_by(Trade.name).offset((page - 1) * page_size).limit(page_size)).all()
    return success_response(
        [TradeRead.model_validate(t) for t in trades],
        meta={"page": page, "page_size": page_size, "total": total, "total_pages": (total + page_size - 1) // page_size},
    )


@router.get("/{trade_id}")
def get_trade(trade_id: UUID, db: DbSession, enriched: bool = Query(False)):
    if enriched:
        trade = get_trade_detail(db, trade_id)
    else:
        row = db.get(Trade, trade_id)
        trade = TradeRead.model_validate(row) if row else None
    if trade is None:
        raise HTTPException(status_code=404, detail="Trade not found")
    return success_response(trade)


@router.patch("/{trade_id}")
def update_trade_endpoint(
    trade_id: UUID,
    body: TradeAdminUpdate,
    db: DbSession,
    actor: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN)),
):
    payload = body.model_dump(exclude_unset=True)
    if not payload:
        raise HTTPException(status_code=400, detail="No fields to update")

    before_trade = get_trade_detail(db, trade_id)
    before = before_trade.model_dump(mode="json") if before_trade else None

    try:
        trade = update_trade(db, trade_id, **payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if trade is None:
        raise HTTPException(status_code=404, detail="Trade not found")

    record_audit(
        db,
        actor=actor,
        action="trade_updated",
        entity_type="trade",
        entity_id=trade_id,
        before=before,
        after=trade.model_dump(mode="json"),
    )
    db.commit()
    return success_response(trade)
