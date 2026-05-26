"""Lambert/Lamberts alias handling and XLSX import tests."""

from __future__ import annotations

import sys
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if not (PROJECT_ROOT / "scripts").is_dir():
    PROJECT_ROOT = Path(__file__).resolve().parents[2].parent
if not (PROJECT_ROOT / "scripts").is_dir() and Path("/workspace/scripts").is_dir():
    PROJECT_ROOT = Path("/workspace")
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from import_quote_calculator_rules import import_rules
from app.core.security import UserRole, get_password_hash
from app.db.session import get_db
from app.main import app
from app.models.client import Client
from app.models.client_alias import ClientAlias
from app.models.rate_rule import RateRule
from app.models.trade import Trade
from app.models.user import User
from app.services.client_service import (
    ensure_client_alias,
    find_client_by_name_or_alias,
    get_or_create_client_for_import,
)
from tests.test_db import make_test_session

XLSX_PATH = PROJECT_ROOT / "docs" / "1.7 MASTER HELPER.xlsx"


@pytest.fixture()
def lambert_api_client():
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


class TestMigrationAndSchema:
    def test_rate_rule_xlsx_columns_exist(self):
        session, engine = make_test_session()
        try:
            inspector = inspect(engine)
            columns = {column["name"] for column in inspector.get_columns("rate_rules")}
            assert "client_fee_pct" in columns
            assert "formula_source" in columns
            assert "xlsx_client_name" in columns
        finally:
            session.close()

    def test_client_aliases_table_exists(self):
        session, engine = make_test_session()
        try:
            inspector = inspect(engine)
            assert "client_aliases" in inspector.get_table_names()
        finally:
            session.close()


class TestClientAliasResolution:
    def test_import_creates_lamberts_with_lambert_alias(self):
        session, _ = make_test_session()
        try:
            client, created, alias_added = get_or_create_client_for_import(session, "Lambert Chartered Surveyors")
            session.commit()

            assert created is True
            assert client.name == "Lamberts Chartered Surveyors"
            alias = session.scalar(
                select(ClientAlias).where(ClientAlias.alias_name == "Lambert Chartered Surveyors")
            )
            assert alias is not None
            assert alias.client_id == client.id

            resolved = find_client_by_name_or_alias(session, "Lambert Chartered Surveyors")
            assert resolved is not None
            assert resolved.id == client.id
            assert resolved.name == "Lamberts Chartered Surveyors"
        finally:
            session.close()

    def test_canonical_name_does_not_create_duplicate_alias(self):
        session, _ = make_test_session()
        try:
            client, _, _ = get_or_create_client_for_import(session, "Lamberts Chartered Surveyors")
            ensure_client_alias(session, client, "Lambert Chartered Surveyors")
            session.commit()

            aliases = session.scalars(select(ClientAlias).where(ClientAlias.client_id == client.id)).all()
            assert len(aliases) == 1
            assert aliases[0].alias_name == "Lambert Chartered Surveyors"
        finally:
            session.close()


@pytest.mark.skipif(not XLSX_PATH.exists(), reason="Master helper workbook missing")
class TestLambertPilotImport:
    def test_dry_run_lambert_pilot_is_16_rules(self):
        stats = import_rules(dry_run=True, client_filter="Lambert")
        assert stats["clients"] == 1
        assert stats["trades"] == 16
        assert stats["rules_would_create"] == 16

    def test_live_import_creates_16_xlsx_rules_with_client_id(self, lambert_api_client):
        _, session, _ = lambert_api_client
        stats = import_rules(dry_run=False, client_filter="Lambert", overwrite=True, db=session)
        session.commit()
        session.expire_all()

        assert stats["rules_created"] == 16

        client = session.scalar(select(Client).where(Client.name == "Lamberts Chartered Surveyors"))
        assert client is not None

        rules = session.scalars(
            select(RateRule).where(RateRule.client_id == client.id, RateRule.formula_source == "xlsx")
        ).all()
        assert len(rules) == 16
        assert all(rule.client_id is not None for rule in rules)
        assert all(rule.xlsx_client_name == "Lambert Chartered Surveyors" for rule in rules)
