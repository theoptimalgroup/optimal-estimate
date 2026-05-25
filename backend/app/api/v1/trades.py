from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from app.core.deps import DbSession
from app.core.exceptions import success_response
from app.models.trade import Trade
from app.schemas.master_data import TradeRead
from app.services.trade_service import trade_search_filter

router = APIRouter(prefix="/trades", tags=["trades"])


@router.get("")
def list_trades(
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Filter by trade name or description"),
    is_active: bool | None = None,
):
    query = select(Trade)
    search_filter = trade_search_filter(search)
    if search_filter is not None:
        query = query.where(search_filter)
    if is_active is not None:
        query = query.where(Trade.is_active.is_(is_active))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    trades = db.scalars(query.order_by(Trade.name).offset((page - 1) * page_size).limit(page_size)).all()
    return success_response(
        [TradeRead.model_validate(t) for t in trades],
        meta={"page": page, "page_size": page_size, "total": total, "total_pages": (total + page_size - 1) // page_size},
    )


@router.get("/{trade_id}")
def get_trade(trade_id: UUID, db: DbSession):
    trade = db.get(Trade, trade_id)
    if trade is None:
        raise HTTPException(status_code=404, detail="Trade not found")
    return success_response(TradeRead.model_validate(trade))
