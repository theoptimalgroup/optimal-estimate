from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.trade import Trade


def normalize_trade_name(name: str) -> str:
    return " ".join(name.strip().split())


def trade_search_filter(search: str | None):
    if not search or not search.strip():
        return None
    term = f"%{search.strip().lower()}%"
    return or_(
        func.lower(Trade.name).like(term),
        func.lower(Trade.description).like(term),
    )


def get_or_create_trade_for_import(db: Session, name: str, *, source_label: str) -> tuple[Trade, bool]:
    normalized = normalize_trade_name(name)
    trade = db.scalar(select(Trade).where(Trade.name == normalized))
    if trade:
        return trade, False
    trade = Trade(name=normalized, description=f"Imported from {source_label}")
    db.add(trade)
    db.flush()
    return trade, True
