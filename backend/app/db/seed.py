"""Seed initial users and master data."""

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.core.security import UserRole, get_password_hash
from app.db.session import SessionLocal
from app.models.client import Client
from app.models.rate_rule import RateRule
from app.models.trade import Trade
from app.models.user import User


def _get_or_create_client(db, name: str, billing_email: str) -> Client:
    client = db.scalar(select(Client).where(Client.name == name))
    if client:
        return client
    client = Client(name=name, billing_email=billing_email, default_vat_rate=Decimal("20.00"))
    db.add(client)
    db.flush()
    return client


def _get_or_create_trade(db, name: str, description: str) -> Trade:
    trade = db.scalar(select(Trade).where(Trade.name == name))
    if trade:
        return trade
    trade = Trade(name=name, description=description)
    db.add(trade)
    db.flush()
    return trade


def _add_rule_if_missing(db, *, client_id, trade_id, version: str, **kwargs) -> None:
    existing = db.scalar(
        select(RateRule).where(
            RateRule.client_id == client_id,
            RateRule.trade_id == trade_id,
            RateRule.version == version,
        )
    )
    if existing:
        return
    db.add(RateRule(client_id=client_id, trade_id=trade_id, version=version, **kwargs))


def _deactivate_legacy_rules(db) -> None:
    legacy_versions = {"global-1.0.0", "1.0.0"}
    for rule in db.scalars(select(RateRule).where(RateRule.version.in_(legacy_versions))).all():
        rule.is_active = False


def seed() -> None:
    db = SessionLocal()
    try:
        if not db.scalar(select(User).where(User.email == "admin@optimal.example")):
            users = [
                User(email="admin@optimal.example", full_name="Admin User", password_hash=get_password_hash("admin12345"), role=UserRole.ADMIN.value),
                User(email="estimator@optimal.example", full_name="Estimator User", password_hash=get_password_hash("estimate12345"), role=UserRole.ESTIMATOR.value),
                User(email="manager@optimal.example", full_name="Manager User", password_hash=get_password_hash("manager12345"), role=UserRole.MANAGER.value),
                User(email="engineer@optimal.example", full_name="Engineer User", password_hash=get_password_hash("engineer12345"), role=UserRole.ENGINEER.value),
            ]
            db.add_all(users)
            db.flush()
            print("Users seeded.")

        atkinson = _get_or_create_client(db, "Atkinson McLeod", "billing@atkinsonmcleod.example")
        oliver = _get_or_create_client(db, "Oliver Jaques", "billing@oliverjaques.example")
        napier = _get_or_create_client(db, "Napier Watt", "billing@napierwatt.example")

        multi_trader = _get_or_create_trade(db, "Multi-trader", "General multi-trade works")
        carpenter = _get_or_create_trade(db, "Carpenter", "Carpentry and joinery")
        _get_or_create_trade(db, "Doors, Windows & Locks", "Door, window and lock works")
        _get_or_create_trade(db, "Drains & Blockages", "Drainage and blockage clearance")
        _get_or_create_trade(db, "Electrician", "Electrical repairs and installations")
        _get_or_create_trade(db, "Fencing & Decking", "Fencing and decking works")
        _get_or_create_trade(db, "Flooring (Carpet, Laminate, Vinyl Etc)", "Flooring works")
        _get_or_create_trade(db, "Gardening", "Gardening and landscaping")
        _get_or_create_trade(db, "Gas Safe", "Gas safe registered works")
        _get_or_create_trade(db, "Painter & Decorator", "Painting and decorating")
        _get_or_create_trade(db, "Paths & Patios", "Paths and patio works")
        _get_or_create_trade(db, "Plasterer & Tiller", "Plastering and tiling works")
        _get_or_create_trade(db, "Plumber", "Plumbing works")
        _get_or_create_trade(db, "Roofer", "Roofing works")
        _get_or_create_trade(db, "Scaffolder", "Scaffolding works")
        _get_or_create_trade(db, "Specialist Subby", "Specialist subcontractor works")
        _get_or_create_trade(db, "Steel Worker", "Steel and metalwork")

        common = dict(
            minimum_hours=Decimal("1.0"),
            material_markup_type="percentage",
            vat_rate=Decimal("20.00"),
            active_from=date(2024, 1, 1),
            is_active=True,
        )

        _add_rule_if_missing(
            db,
            client_id=atkinson.id,
            trade_id=multi_trader.id,
            version="am-multi-1.0",
            hourly_rate=Decimal("72.00"),
            half_day_rate=Decimal("270.00"),
            day_rate=Decimal("500.00"),
            minimum_charge=Decimal("72.00"),
            material_markup_value=Decimal("15.00"),
            approval_threshold=Decimal("5000.00"),
            minimum_margin_percentage=Decimal("10.00"),
            **common,
        )
        _add_rule_if_missing(
            db,
            client_id=atkinson.id,
            trade_id=carpenter.id,
            version="am-carpenter-1.0",
            hourly_rate=Decimal("68.00"),
            half_day_rate=Decimal("255.00"),
            day_rate=Decimal("480.00"),
            minimum_charge=Decimal("68.00"),
            material_markup_value=Decimal("18.00"),
            approval_threshold=Decimal("4000.00"),
            minimum_margin_percentage=Decimal("12.00"),
            **common,
        )
        _add_rule_if_missing(
            db,
            client_id=oliver.id,
            trade_id=multi_trader.id,
            version="oj-multi-1.0",
            hourly_rate=Decimal("70.00"),
            half_day_rate=Decimal("260.00"),
            day_rate=Decimal("490.00"),
            minimum_charge=Decimal("70.00"),
            material_markup_value=Decimal("15.00"),
            approval_threshold=Decimal("4500.00"),
            minimum_margin_percentage=Decimal("10.00"),
            **common,
        )
        _add_rule_if_missing(
            db,
            client_id=None,
            trade_id=None,
            version="global-fallback-1.0",
            hourly_rate=Decimal("65.00"),
            half_day_rate=Decimal("240.00"),
            day_rate=Decimal("450.00"),
            minimum_charge=Decimal("65.00"),
            material_markup_value=Decimal("10.00"),
            approval_threshold=Decimal("3000.00"),
            **common,
        )

        _deactivate_legacy_rules(db)

        db.commit()
        print("Seed data created successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
