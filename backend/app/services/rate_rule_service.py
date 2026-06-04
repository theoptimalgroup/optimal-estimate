from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.calculation_session import CalculationSession
from app.models.client import Client
from app.models.rate_rule import RateRule
from app.models.trade import Trade
from app.schemas.master_data import RateRuleRead
from app.schemas.rate_rule import RateRuleDetailRead, RateRuleListRead, RateRuleUsage


def _lookup_priority(rule: RateRule) -> str | None:
    if rule.client_id and rule.trade_id:
        return "exact_client_trade"
    if rule.client_id and rule.trade_id is None:
        return "client_default_trade"
    if rule.client_id is None and rule.trade_id:
        return "default_client_trade"
    if rule.client_id is None and rule.trade_id is None:
        return "global_default"
    return None


def _rule_to_list_read(rule: RateRule) -> RateRuleListRead:
    base = RateRuleRead.model_validate(rule)
    return RateRuleListRead(
        **base.model_dump(),
        client_name=rule.client.name if rule.client else None,
        trade_name=rule.trade.name if rule.trade else None,
    )


def _base_query():
    return (
        select(RateRule)
        .outerjoin(Client, RateRule.client_id == Client.id)
        .outerjoin(Trade, RateRule.trade_id == Trade.id)
        .options(joinedload(RateRule.client), joinedload(RateRule.trade))
    )


def _apply_filters(
    query,
    *,
    client_id: UUID | None,
    trade_id: UUID | None,
    client_name: str | None,
    trade_name: str | None,
    active: bool | None,
    formula_source: str | None,
):
    if client_id is not None:
        query = query.where(RateRule.client_id == client_id)
    if trade_id is not None:
        query = query.where(RateRule.trade_id == trade_id)
    if active is not None:
        query = query.where(RateRule.is_active.is_(active))
    if formula_source:
        query = query.where(RateRule.formula_source == formula_source)
    if client_name and client_name.strip():
        term = f"%{client_name.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(Client.name).like(term),
                func.lower(RateRule.xlsx_client_name).like(term),
            )
        )
    if trade_name and trade_name.strip():
        term = f"%{trade_name.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(Trade.name).like(term),
                func.lower(RateRule.xlsx_trade_name).like(term),
            )
        )
    return query


def list_rate_rules(
    db: Session,
    *,
    client_id: UUID | None = None,
    trade_id: UUID | None = None,
    client_name: str | None = None,
    trade_name: str | None = None,
    active: bool | None = None,
    formula_source: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[RateRuleListRead], int]:
    query = _apply_filters(
        _base_query(),
        client_id=client_id,
        trade_id=trade_id,
        client_name=client_name,
        trade_name=trade_name,
        active=active,
        formula_source=formula_source,
    )

    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    rules = db.scalars(
        query.order_by(Client.name.nulls_last(), Trade.name.nulls_last(), RateRule.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).unique().all()

    return [_rule_to_list_read(rule) for rule in rules], total


def get_rate_rule_detail(db: Session, rule_id: UUID) -> RateRuleDetailRead | None:
    rule = db.scalar(_base_query().where(RateRule.id == rule_id))
    if rule is None:
        return None

    quotes_using_version = (
        db.scalar(
            select(func.count())
            .select_from(CalculationSession)
            .where(CalculationSession.rate_rule_id == rule_id)
        )
        or 0
    )
    jobs_for_client = 0
    if rule.client_id is not None:
        jobs_for_client = (
            db.scalar(
                select(func.count())
                .select_from(CalculationSession)
                .where(CalculationSession.client_id == rule.client_id)
            )
            or 0
        )

    list_read = _rule_to_list_read(rule)
    return RateRuleDetailRead(
        **list_read.model_dump(),
        usage=RateRuleUsage(
            quotes_using_version=quotes_using_version,
            jobs_for_client=jobs_for_client,
            lookup_priority=_lookup_priority(rule),
        ),
    )


def update_rate_rule_status(db: Session, rule_id: UUID, is_active: bool) -> RateRuleDetailRead | None:
    rule = db.get(RateRule, rule_id)
    if rule is None:
        return None
    rule.is_active = is_active
    db.flush()
    return get_rate_rule_detail(db, rule_id)
