from uuid import UUID

from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.rate_rule import RateRule
from app.models.trade import Trade
from app.schemas.trade_admin import TradeDetailRead, TradeListRead
from app.services.trade_service import normalize_trade_name, trade_search_filter


def _products_count_for_trade(db: Session, trade: Trade) -> int:
    try:
        if "products" not in inspect(db.bind).get_table_names():
            return 0
        return (
            db.scalar(
                select(func.count()).select_from(Product).where(func.lower(Product.category) == trade.name.lower())
            )
            or 0
        )
    except Exception:
        return 0


def _trade_counts(db: Session, trade: Trade) -> tuple[int, int]:
    rate_rules_count = db.scalar(select(func.count()).select_from(RateRule).where(RateRule.trade_id == trade.id)) or 0
    products_count = _products_count_for_trade(db, trade)
    return rate_rules_count, products_count


def _trade_to_read(db: Session, trade: Trade) -> TradeListRead:
    rate_rules_count, products_count = _trade_counts(db, trade)
    return TradeListRead(
        id=trade.id,
        name=trade.name,
        description=trade.description,
        is_active=trade.is_active,
        rate_rules_count=rate_rules_count,
        products_count=products_count,
        created_at=trade.created_at,
        updated_at=trade.updated_at,
    )


def list_trades_admin(
    db: Session,
    *,
    search: str | None = None,
    active: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[TradeListRead], int]:
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)

    query = select(Trade)
    search_filter = trade_search_filter(search)
    if search_filter is not None:
        query = query.where(search_filter)
    if active is not None:
        query = query.where(Trade.is_active.is_(active))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    trades = db.scalars(query.order_by(Trade.name).offset(offset).limit(limit)).all()
    return [_trade_to_read(db, trade) for trade in trades], total


def get_trade_detail(db: Session, trade_id: UUID) -> TradeDetailRead | None:
    trade = db.get(Trade, trade_id)
    if trade is None:
        return None
    return TradeDetailRead.model_validate(_trade_to_read(db, trade).model_dump())


def update_trade(
    db: Session,
    trade_id: UUID,
    *,
    name: str | None = None,
    description: str | None = None,
    is_active: bool | None = None,
) -> TradeDetailRead | None:
    trade = db.get(Trade, trade_id)
    if trade is None:
        return None

    if name is not None:
        trimmed = normalize_trade_name(name)
        if not trimmed:
            raise ValueError("Trade name is required")
        trade.name = trimmed

    if description is not None:
        trade.description = description.strip() or None

    if is_active is not None:
        trade.is_active = is_active

    db.flush()
    return get_trade_detail(db, trade_id)
