"""Unit tests for eWorks Customer sync and customer-name enrichment."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import UserRole, get_password_hash
from app.db.session import get_db
from app.main import app
from app.models.calculation_session import CalculationSession
from app.models.eworks_sync import EworksCustomer, EworksJob, EworksQuote, EworksSyncRun
from app.models.support import AuditLog
from app.models.trade import Trade
from app.models.user import User
from app.services.eworks_sync_service import (
    enrich_customer_name_on_fields,
    enrich_existing_quotes_customer_names,
    extract_customer_name_from_customer_record,
    sync_customers_from_eworks,
)
from app.services.quote_assignment_service import _resolve_quote_customer_name


SAMPLE_CUSTOMER = {
    "id": 501,
    "company_name": "Bright Sparks Ltd",
    "full_name": "Jane Bright",
    "email": "jane@brightsparks.example",
    "phone": "01234567890",
}


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in [
        User.__table__,
        AuditLog.__table__,
        Trade.__table__,
        CalculationSession.__table__,
        EworksCustomer.__table__,
        EworksQuote.__table__,
        EworksJob.__table__,
        EworksSyncRun.__table__,
    ]:
        table.create(engine)

    Session = sessionmaker(bind=engine)
    session = Session()
    now = datetime.now(timezone.utc)

    admin = User(
        id=uuid.uuid4(),
        email="admin@optimal.example",
        full_name="Admin",
        password_hash=get_password_hash("admin12345"),
        role=UserRole.ADMIN.value,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    manager = User(
        id=uuid.uuid4(),
        email="manager@optimal.example",
        full_name="Manager",
        password_hash=get_password_hash("manager12345"),
        role=UserRole.MANAGER.value,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    engineer = User(
        id=uuid.uuid4(),
        email="engineer@optimal.example",
        full_name="Engineer",
        password_hash=get_password_hash("eng12345"),
        role=UserRole.ENGINEER.value,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    session.add_all([admin, manager, engineer])
    trade = Trade(id=uuid.uuid4(), name="Electrician", is_active=True, created_at=now, updated_at=now)
    session.add(trade)
    session.commit()
    yield session
    session.close()


@pytest.fixture()
def api_client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def _patch_dev_user(mock_settings, *, role: str):
    email_map = {
        "admin": "admin@optimal.example",
        "manager": "manager@optimal.example",
        "engineer": "engineer@optimal.example",
    }
    mock_settings.auth_provider = "dev"
    mock_settings.dev_auth_enabled = True
    mock_settings.dev_user_id = f"dev-{role}-1"
    mock_settings.dev_user_email = email_map[role]
    mock_settings.dev_user_name = f"{role.title()} User"
    mock_settings.dev_user_role = role
    mock_settings.dev_user_is_active = True
    mock_settings.dev_auth_auto_create_user = False


def test_extract_customer_name_from_customer_record():
    assert extract_customer_name_from_customer_record(SAMPLE_CUSTOMER) == "Jane Bright"
    assert extract_customer_name_from_customer_record({"id": 1, "company_name": "Company Only"}) == "Company Only"
    assert extract_customer_name_from_customer_record({"id": 1, "display_name": "Display Co"}) == "Display Co"
    assert extract_customer_name_from_customer_record({"id": 1, "name": "Named Co"}) == "Named Co"


@patch("app.services.eworks_sync_service.fetch_all_customers")
def test_sync_customers_upserts_records(mock_fetch, db_session):
    mock_fetch.return_value = [SAMPLE_CUSTOMER, {**SAMPLE_CUSTOMER, "id": 502, "company_name": "Other Co"}]

    summary, _ = sync_customers_from_eworks(db_session)
    db_session.commit()

    assert summary.fetched == 2
    assert summary.created == 2
    assert summary.failed == 0

    rows = db_session.query(EworksCustomer).order_by(EworksCustomer.eworks_customer_id).all()
    assert len(rows) == 2
    assert rows[0].eworks_customer_id == 501
    assert rows[0].customer_name == "Jane Bright"
    assert rows[0].email == "jane@brightsparks.example"
    assert rows[0].raw_payload["id"] == 501


@patch("app.services.eworks_sync_service.fetch_all_customers")
def test_sync_customers_updates_existing(mock_fetch, db_session):
    db_session.add(
        EworksCustomer(
            eworks_customer_id=501,
            customer_name="Old Name",
            raw_payload={"id": 501},
        )
    )
    db_session.commit()
    mock_fetch.return_value = [SAMPLE_CUSTOMER]

    summary, _ = sync_customers_from_eworks(db_session)
    db_session.commit()

    assert summary.created == 0
    assert summary.updated == 1
    row = db_session.query(EworksCustomer).filter(EworksCustomer.eworks_customer_id == 501).one()
    assert row.customer_name == "Jane Bright"


def test_enrich_customer_name_on_fields_from_local_customer(db_session):
    db_session.add(
        EworksCustomer(
            eworks_customer_id=777,
            customer_name="Synced Customer Ltd",
            raw_payload={"id": 777},
        )
    )
    db_session.commit()

    fields = {"customer_id": 777, "customer_name": None}
    enrich_customer_name_on_fields(db_session, fields)
    assert fields["customer_name"] == "Synced Customer Ltd"


def test_enrich_existing_quotes_customer_names_backfills(db_session):
    db_session.add(
        EworksCustomer(
            eworks_customer_id=888,
            customer_name="Backfill Customer",
            raw_payload={"id": 888},
        )
    )
    db_session.add(
        EworksQuote(
            eworks_quote_id=1001,
            quote_ref="Q-1001",
            customer_id=888,
            customer_name=None,
        )
    )
    db_session.commit()

    updated = enrich_existing_quotes_customer_names(db_session)
    db_session.commit()

    assert updated == 1
    quote = db_session.query(EworksQuote).filter(EworksQuote.eworks_quote_id == 1001).one()
    assert quote.customer_name == "Backfill Customer"


@patch("app.services.eworks_sync_service.fetch_all_customers")
def test_sync_customers_backfills_quote_names(mock_fetch, db_session):
    db_session.add(
        EworksQuote(
            eworks_quote_id=2002,
            quote_ref="Q-2002",
            customer_id=501,
            customer_name=None,
        )
    )
    db_session.commit()
    mock_fetch.return_value = [SAMPLE_CUSTOMER]

    sync_customers_from_eworks(db_session)
    db_session.commit()

    quote = db_session.query(EworksQuote).filter(EworksQuote.eworks_quote_id == 2002).one()
    assert quote.customer_name == "Jane Bright"


def test_resolve_quote_customer_name_prefers_quote_then_lookup(db_session):
    db_session.add(
        EworksCustomer(
            eworks_customer_id=999,
            customer_name="Lookup Name",
            raw_payload={"id": 999},
        )
    )
    quote_with_name = EworksQuote(
        eworks_quote_id=1,
        customer_id=999,
        customer_name="Direct Name",
    )
    quote_lookup = EworksQuote(
        eworks_quote_id=2,
        customer_id=999,
        customer_name=None,
    )
    quote_unknown = EworksQuote(
        eworks_quote_id=3,
        customer_id=None,
        customer_name=None,
    )

    assert _resolve_quote_customer_name(db_session, quote_with_name) == "Direct Name"
    assert _resolve_quote_customer_name(db_session, quote_lookup) == "Lookup Name"
    assert _resolve_quote_customer_name(db_session, quote_unknown) == "Unknown Customer"


@patch("app.api.v1.eworks_sync.schedule_eworks_sync")
@patch("app.auth.dependencies.settings")
def test_admin_can_trigger_customers_sync(mock_settings, mock_schedule, api_client):
    _patch_dev_user(mock_settings, role="admin")
    run = EworksSyncRun(id=uuid.uuid4(), sync_type="customers", status="running")
    mock_schedule.return_value = run
    resp = api_client.post("/api/v1/eworks-sync/customers", json={})
    mock_schedule.assert_called_once()
    assert resp.status_code == 200
    assert resp.json()["data"]["sync_type"] == "customers"


@patch("app.auth.dependencies.settings")
def test_manager_blocked_from_customers_sync(mock_settings, api_client):
    _patch_dev_user(mock_settings, role="manager")
    resp = api_client.post("/api/v1/eworks-sync/customers", json={})
    assert resp.status_code == 403


@patch("app.auth.dependencies.settings")
def test_engineer_blocked_from_customers_sync(mock_settings, api_client):
    _patch_dev_user(mock_settings, role="engineer")
    resp = api_client.post("/api/v1/eworks-sync/customers", json={})
    assert resp.status_code == 403


@patch("app.auth.dependencies.settings")
def test_admin_can_list_customers_without_raw_payload(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    db_session.add(
        EworksCustomer(
            eworks_customer_id=501,
            customer_name="Bright Sparks Ltd",
            email="jane@brightsparks.example",
            phone="01234567890",
            raw_payload={"id": 501, "secret": "hidden"},
        )
    )
    db_session.commit()

    resp = api_client.get("/api/v1/eworks-sync/customers")
    assert resp.status_code == 200
    item = resp.json()["data"]["items"][0]
    assert item["customer_name"] == "Bright Sparks Ltd"
    assert "raw_payload" not in item


@patch("app.auth.dependencies.settings")
def test_manager_blocked_from_customers_list(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    db_session.add(EworksCustomer(eworks_customer_id=1, raw_payload={"id": 1}))
    db_session.commit()
    resp = api_client.get("/api/v1/eworks-sync/customers")
    assert resp.status_code == 403


@patch("app.auth.dependencies.settings")
def test_status_includes_customers_count(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    db_session.add(EworksCustomer(eworks_customer_id=10, customer_name="Test Co", raw_payload={"id": 10}))
    db_session.commit()

    resp = api_client.get("/api/v1/eworks-sync/status")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["customers_count"] >= 1
    assert "last_customers_sync" in data
    assert "raw_payload" not in resp.text
