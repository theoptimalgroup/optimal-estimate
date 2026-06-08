from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.rate_rule import RateRule

DEFAULT_XLSX_CLIENT_NAME = "DEFAULT"


@dataclass
class MatchedRule:
    rule: RateRule
    match_type: str


def _active_rules_query(quote_date: date, *, formula_source: str | None = None):
    clauses = [
        RateRule.is_active.is_(True),
        RateRule.active_from <= quote_date,
        or_(RateRule.active_to.is_(None), RateRule.active_to >= quote_date),
    ]
    if formula_source is not None:
        clauses.append(RateRule.formula_source == formula_source)
    return select(RateRule).where(*clauses)


def _default_xlsx_client_id(db: Session) -> UUID | None:
    from app.services.client_service import find_client_by_name_or_alias

    client = find_client_by_name_or_alias(db, DEFAULT_XLSX_CLIENT_NAME)
    return client.id if client else None


def find_active_xlsx_rule(
    db: Session,
    client_id: UUID | None,
    trade_id: UUID | None,
    quote_date: date | None = None,
) -> MatchedRule | None:
    """Resolve an active XLSX rule: exact client, DEFAULT client, then global trade."""
    if trade_id is None:
        return None

    quote_date = quote_date or date.today()
    candidates = db.scalars(_active_rules_query(quote_date, formula_source="xlsx")).all()
    default_client_id = _default_xlsx_client_id(db)

    priority_checks = [
        ("exact_client_trade", lambda r: client_id is not None and r.client_id == client_id and r.trade_id == trade_id),
        (
            "default_named_client_trade",
            lambda r: default_client_id is not None and r.client_id == default_client_id and r.trade_id == trade_id,
        ),
        ("global_trade", lambda r: r.client_id is None and r.trade_id == trade_id),
    ]

    for match_type, predicate in priority_checks:
        for rule in candidates:
            if predicate(rule):
                return MatchedRule(rule=rule, match_type=match_type)
    return None


def has_exact_client_trade_xlsx_rule(
    db: Session,
    client_id: UUID | None,
    trade_id: UUID | None,
    quote_date: date | None = None,
) -> bool:
    if client_id is None or trade_id is None:
        return False
    matched = find_active_xlsx_rule(db, client_id, trade_id, quote_date)
    return matched is not None and matched.match_type == "exact_client_trade"


def xlsx_fallback_warning(matched_rule: MatchedRule) -> str | None:
    if matched_rule.match_type == "exact_client_trade":
        return None
    trade_name = matched_rule.rule.xlsx_trade_name or "trade"
    return f"Exact client rate rule not found. Used default XLSX {trade_name} rule."


def resolve_calculation_rule(
    db: Session,
    client_id: UUID | None,
    trade_id: UUID | None,
    quote_date: date | None = None,
) -> MatchedRule | None:
    """Prefer XLSX trade rules (with DEFAULT/global fallback); otherwise simplified rules."""
    xlsx_matched = find_active_xlsx_rule(db, client_id, trade_id, quote_date)
    if xlsx_matched is not None:
        return xlsx_matched
    return find_active_rule(db, client_id, trade_id, quote_date)


def find_active_rule(
    db: Session,
    client_id: UUID | None,
    trade_id: UUID | None,
    quote_date: date | None = None,
) -> MatchedRule | None:
    quote_date = quote_date or date.today()
    candidates = db.scalars(
        select(RateRule).where(
            RateRule.is_active.is_(True),
            RateRule.active_from <= quote_date,
            or_(RateRule.active_to.is_(None), RateRule.active_to >= quote_date),
        )
    ).all()

    priority_checks = [
        ("exact_client_trade", lambda r: r.client_id == client_id and r.trade_id == trade_id),
        ("client_default_trade", lambda r: r.client_id == client_id and r.trade_id is None),
        ("default_client_trade", lambda r: r.client_id is None and r.trade_id == trade_id),
        ("global_default", lambda r: r.client_id is None and r.trade_id is None),
    ]

    for match_type, predicate in priority_checks:
        for rule in candidates:
            if predicate(rule):
                return MatchedRule(rule=rule, match_type=match_type)
    return None


def rule_to_dict(rule: RateRule) -> dict:
    return {
        "id": str(rule.id),
        "client_id": str(rule.client_id) if rule.client_id else None,
        "trade_id": str(rule.trade_id) if rule.trade_id else None,
        "version": rule.version,
        "hourly_rate": float(rule.hourly_rate) if rule.hourly_rate is not None else None,
        "half_day_rate": float(rule.half_day_rate) if rule.half_day_rate is not None else None,
        "day_rate": float(rule.day_rate) if rule.day_rate is not None else None,
        "minimum_hours": float(rule.minimum_hours) if rule.minimum_hours is not None else None,
        "minimum_charge": float(rule.minimum_charge) if rule.minimum_charge is not None else None,
        "material_markup_type": rule.material_markup_type,
        "material_markup_value": float(rule.material_markup_value),
        "vat_rate": float(rule.vat_rate),
        "approval_threshold": float(rule.approval_threshold) if rule.approval_threshold is not None else None,
        "minimum_margin_percentage": float(rule.minimum_margin_percentage)
        if rule.minimum_margin_percentage is not None
        else None,
        "rounding_rule": rule.rounding_rule,
        "active_from": rule.active_from.isoformat(),
        "active_to": rule.active_to.isoformat() if rule.active_to else None,
        "formula_source": rule.formula_source,
        "client_fee_pct": float(rule.client_fee_pct),
        "hourly_overhead_pct": float(rule.hourly_overhead_pct),
        "daily_overhead_pct": float(rule.daily_overhead_pct),
        "daily_overhead_long_job_pct": float(rule.daily_overhead_long_job_pct),
        "direct_hourly_cost": float(rule.direct_hourly_cost) if rule.direct_hourly_cost is not None else None,
        "direct_daily_cost": float(rule.direct_daily_cost) if rule.direct_daily_cost is not None else None,
        "labourer_hourly_cost": float(rule.labourer_hourly_cost),
        "labourer_daily_cost": float(rule.labourer_daily_cost),
        "material_charge_denominator": float(rule.material_charge_denominator),
        "parking_charge_denominator": float(rule.parking_charge_denominator),
        "congestion_charge_denominator": float(rule.congestion_charge_denominator),
        "mround_increment": float(rule.mround_increment),
        "oj_uplift_pct": float(rule.oj_uplift_pct),
        "nhs_overhead_uplift_pct": float(rule.nhs_overhead_uplift_pct),
        "eaf_flat_fee": float(rule.eaf_flat_fee),
        "internal_notes_template": rule.internal_notes_template,
        "xlsx_client_name": rule.xlsx_client_name,
        "xlsx_trade_name": rule.xlsx_trade_name,
    }
