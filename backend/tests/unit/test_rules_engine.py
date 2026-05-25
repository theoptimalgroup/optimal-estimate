from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.engines.approval_engine import build_calculation_breakdown, evaluate_approval_requirements
from app.engines.rules_engine import find_active_rule
from app.models.client import Client
from app.models.rate_rule import RateRule
from app.models.trade import Trade
from app.schemas.calculation import LabourInput


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    for model in (Client, Trade, RateRule):
        model.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    client = Client(name="Test Client", default_vat_rate=Decimal("20"))
    trade = Trade(name="Plumbing")
    session.add_all([client, trade])
    session.flush()
    rule = RateRule(
        client_id=client.id,
        trade_id=trade.id,
        version="1.0",
        hourly_rate=Decimal("75"),
        half_day_rate=Decimal("280"),
        day_rate=Decimal("520"),
        minimum_hours=Decimal("1"),
        minimum_charge=Decimal("75"),
        approval_threshold=Decimal("1000"),
        minimum_margin_percentage=Decimal("10"),
        active_from=date(2024, 1, 1),
        is_active=True,
    )
    session.add(rule)
    session.commit()
    yield session
    session.close()


def test_find_exact_client_trade_rule(db_session):
    client = db_session.query(Client).first()
    trade = db_session.query(Trade).first()
    matched = find_active_rule(db_session, client.id, trade.id, date.today())
    assert matched is not None
    assert matched.match_type == "exact_client_trade"


def test_approval_required_for_high_quote_value():
    rule = RateRule(approval_threshold=Decimal("500"))
    required, reasons = evaluate_approval_requirements(
        final_total=Decimal("600"),
        rule=rule,
        manual_override=False,
        margin_percentage=None,
        rule_found=True,
        other_charge=Decimal("0"),
        other_charge_reason=None,
    )
    assert required is True
    assert any("threshold" in r for r in reasons)


def test_approval_required_for_manual_override():
    required, reasons = evaluate_approval_requirements(
        final_total=Decimal("100"),
        rule=None,
        manual_override=True,
        margin_percentage=None,
        rule_found=True,
        other_charge=Decimal("0"),
        other_charge_reason=None,
    )
    assert required is True


def test_no_rate_rule_found_returns_warning(db_session):
    breakdown = build_calculation_breakdown(
        labour_items=[LabourInput(labour_type="hourly", number_of_engineers=1, hours_on_site=Decimal("2"))],
        material_items=[],
        charges=None,
        matched_rule=None,
        formula_version="1.0.0",
    )
    assert "RATE_RULE_NOT_FOUND" in breakdown.warnings
