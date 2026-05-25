"""Full XLSX import coverage: 158 clients, 16 trades, 2,528 rules."""

from __future__ import annotations

import sys
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from import_quote_calculator_rules import (
    EXPECTED_FULL_IMPORT_CLIENTS,
    EXPECTED_FULL_IMPORT_RULES,
    EXPECTED_FULL_IMPORT_TRADES,
    import_rules,
)
from app.core.security import UserRole, get_password_hash
from app.db.session import get_db
from app.engines.rules_engine import find_active_rule
from app.main import app
from app.models.client import Client
from app.models.rate_rule import RateRule
from app.models.trade import Trade
from app.models.user import User
from app.services.client_service import find_client_by_name_or_alias, get_or_create_client_for_import
from tests.test_db import make_test_session

XLSX_PATH = ROOT / "docs" / "1.7 MASTER HELPER.xlsx"


@pytest.fixture()
def full_import_api_client():
    session, _ = make_test_session()
    admin = User(
        id=uuid.uuid4(),
        email="admin@optimal.example",
        full_name="Admin",
        password_hash=get_password_hash("admin12345"),
        role=UserRole.ADMIN.value,
    )
    session.add(admin)
    session.commit()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client, session, admin
    app.dependency_overrides.clear()
    session.close()


@pytest.mark.skipif(not XLSX_PATH.exists(), reason="Master helper workbook missing")
class TestFullXlsxImport:
    def test_full_dry_run_counts(self):
        stats = import_rules(dry_run=True)
        assert stats["clients"] == EXPECTED_FULL_IMPORT_CLIENTS
        assert stats["trades"] == EXPECTED_FULL_IMPORT_TRADES
        assert stats["rules_would_create"] == EXPECTED_FULL_IMPORT_RULES

    def test_full_import_creates_clients_trades_and_rules(self, full_import_api_client):
        _, session, _ = full_import_api_client
        stats = import_rules(dry_run=False, overwrite=True, db=session)
        session.commit()
        session.expire_all()

        assert stats["rules_created"] == EXPECTED_FULL_IMPORT_RULES
        assert session.scalar(select(func.count()).select_from(Client)) == EXPECTED_FULL_IMPORT_CLIENTS
        assert session.scalar(select(func.count()).select_from(Trade)) == EXPECTED_FULL_IMPORT_TRADES

        xlsx_rules = session.scalars(select(RateRule).where(RateRule.formula_source == "xlsx")).all()
        assert len(xlsx_rules) == EXPECTED_FULL_IMPORT_RULES
        assert all(rule.client_id is not None for rule in xlsx_rules)
        assert all(rule.trade_id is not None for rule in xlsx_rules)

    def test_no_duplicate_clients_after_alias_normalization(self, full_import_api_client):
        _, session, _ = full_import_api_client
        import_rules(dry_run=False, overwrite=True, db=session)
        session.commit()

        lambert = session.scalar(select(Client).where(Client.name == "Lamberts Chartered Surveyors"))
        legacy = session.scalar(select(Client).where(Client.name == "Lambert Chartered Surveyors"))
        assert lambert is not None
        assert legacy is None

        total_clients = session.scalar(select(func.count()).select_from(Client))
        assert total_clients == EXPECTED_FULL_IMPORT_CLIENTS


class TestFullImportResolutionAndTradesApi:
    def test_client_alias_resolution_finds_lamberts(self, full_import_api_client):
        _, session, _ = full_import_api_client
        get_or_create_client_for_import(session, "Lambert Chartered Surveyors")
        session.commit()

        resolved = find_client_by_name_or_alias(session, "Lambert Chartered Surveyors")
        assert resolved is not None
        assert resolved.name == "Lamberts Chartered Surveyors"

    def test_active_rule_lookup_for_lambert_carpenter(self, full_import_api_client):
        _, session, _ = full_import_api_client
        client, _, _ = get_or_create_client_for_import(session, "Lambert Chartered Surveyors")
        trade = Trade(id=uuid.uuid4(), name="Carpenter")
        session.add_all(
            [
                trade,
                RateRule(
                    client_id=client.id,
                    trade_id=trade.id,
                    formula_source="xlsx",
                    version="full-import-search",
                    xlsx_client_name="Lambert Chartered Surveyors",
                    xlsx_trade_name="Carpenter",
                    hourly_rate=Decimal("95"),
                    material_markup_type="percentage",
                    material_markup_value=Decimal("20"),
                    vat_rate=Decimal("20"),
                    active_from=date(2024, 1, 1),
                    is_active=True,
                ),
            ]
        )
        session.commit()

        matched = find_active_rule(session, client.id, trade.id, date(2024, 6, 1))
        assert matched is not None
        assert matched.rule.formula_source == "xlsx"
        assert matched.rule.xlsx_client_name == "Lambert Chartered Surveyors"

    def test_trades_search_carpenter(self, full_import_api_client):
        test_client, session, _ = full_import_api_client
        session.add(Trade(id=uuid.uuid4(), name="Carpenter"))
        session.commit()

        body = test_client.get("/api/v1/trades?search=carpenter").json()
        assert body["meta"]["total"] >= 1
        assert any(item["name"] == "Carpenter" for item in body["data"])

    def test_trades_list_finds_carpenter(self, full_import_api_client):
        test_client, session, _ = full_import_api_client
        session.add(Trade(id=uuid.uuid4(), name="Carpenter"))
        session.commit()

        body = test_client.get("/api/v1/trades?search=carpenter&page_size=100").json()
        names = [item["name"] for item in body["data"]]
        assert "Carpenter" in names
