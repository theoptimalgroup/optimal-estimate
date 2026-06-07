"""Unit tests for eWorks quote assignments."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import UserRole, get_password_hash
from app.db.session import get_db
from app.main import app
from app.models.calculation_session import CalculationSession
from app.models.calculation_session_version import CalculationSessionVersion
from app.models.client import Client
from app.models.client_alias import ClientAlias
from app.models.eworks_sync import EworksQuote
from app.models.quote_assignment import EworksQuoteAssignment
from app.models.rate_rule import RateRule
from app.models.support import AuditLog
from app.models.trade import Trade
from app.models.user import User


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
        Client.__table__,
        ClientAlias.__table__,
        Trade.__table__,
        RateRule.__table__,
        CalculationSession.__table__,
        CalculationSessionVersion.__table__,
        EworksQuote.__table__,
        EworksQuoteAssignment.__table__,
    ]:
        table.create(engine)

    Session = sessionmaker(bind=engine)
    session = Session()
    now = datetime.now(timezone.utc)

    users = {
        "admin": User(
            id=uuid.uuid4(),
            email="admin@optimal.example",
            full_name="Admin",
            password_hash=get_password_hash("admin12345"),
            role=UserRole.ADMIN.value,
            is_active=True,
            created_at=now,
            updated_at=now,
        ),
        "manager": User(
            id=uuid.uuid4(),
            email="manager@optimal.example",
            full_name="Manager",
            password_hash=get_password_hash("manager12345"),
            role=UserRole.MANAGER.value,
            is_active=True,
            created_at=now,
            updated_at=now,
        ),
        "estimator": User(
            id=uuid.uuid4(),
            email="estimator@optimal.example",
            full_name="Estimator",
            password_hash=get_password_hash("est12345"),
            role=UserRole.ESTIMATOR.value,
            is_active=True,
            created_at=now,
            updated_at=now,
        ),
        "estimator2": User(
            id=uuid.uuid4(),
            email="estimator2@optimal.example",
            full_name="Estimator Two",
            password_hash=get_password_hash("est22345"),
            role=UserRole.ESTIMATOR.value,
            is_active=True,
            created_at=now,
            updated_at=now,
        ),
        "engineer": User(
            id=uuid.uuid4(),
            email="engineer@optimal.example",
            full_name="Engineer",
            password_hash=get_password_hash("eng12345"),
            role=UserRole.ENGINEER.value,
            is_active=True,
            created_at=now,
            updated_at=now,
        ),
        "client": User(
            id=uuid.uuid4(),
            email="client@optimal.example",
            full_name="Client",
            password_hash=get_password_hash("client12345"),
            role=UserRole.CLIENT.value,
            is_active=True,
            created_at=now,
            updated_at=now,
        ),
    }
    session.add_all(users.values())
    trade = Trade(id=uuid.uuid4(), name="Carpenter", is_active=True, created_at=now, updated_at=now)
    session.add(trade)
    session.commit()
    session.users = users  # type: ignore[attr-defined]
    session.trade = trade  # type: ignore[attr-defined]
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
        "estimator": "estimator@optimal.example",
        "estimator2": "estimator2@optimal.example",
        "engineer": "engineer@optimal.example",
        "client": "client@optimal.example",
    }
    mock_settings.auth_provider = "dev"
    mock_settings.dev_auth_enabled = True
    mock_settings.dev_user_id = f"dev-{role}-1"
    mock_settings.dev_user_email = email_map[role]
    mock_settings.dev_user_name = f"{role.title()} User"
    mock_settings.dev_user_role = role
    mock_settings.dev_user_is_active = True
    mock_settings.dev_auth_auto_create_user = False


def _add_trade_default_rate_rule(session) -> RateRule:
    trade = session.trade  # type: ignore[attr-defined]
    rule = RateRule(
        client_id=None,
        trade_id=trade.id,
        formula_source="xlsx",
        version="trade-default-carpenter",
        hourly_rate=Decimal("95"),
        day_rate=Decimal("239.40"),
        direct_hourly_cost=Decimal("30"),
        direct_daily_cost=Decimal("239.40"),
        client_fee_pct=Decimal("0.15"),
        hourly_overhead_pct=Decimal("0.30"),
        daily_overhead_pct=Decimal("0.20"),
        daily_overhead_long_job_pct=Decimal("0.15"),
        labourer_hourly_cost=Decimal("18.75"),
        labourer_daily_cost=Decimal("150"),
        material_charge_denominator=Decimal("0.20"),
        parking_charge_denominator=Decimal("0.20"),
        congestion_charge_denominator=Decimal("0.20"),
        mround_increment=Decimal("5"),
        oj_uplift_pct=Decimal("10"),
        nhs_overhead_uplift_pct=Decimal("15"),
        eaf_flat_fee=Decimal("1"),
        xlsx_client_name="Trade default",
        xlsx_trade_name="Carpenter",
        material_markup_type="percentage",
        material_markup_value=Decimal("20"),
        vat_rate=Decimal("20"),
        active_from=date(2024, 1, 1),
        is_active=True,
    )
    session.add(rule)
    session.commit()
    return rule


def _minimal_step2() -> dict:
    return {
        "works": [
            {
                "scope": "Install socket",
                "selected_product_id": None,
                "product_name": "Socket install",
                "product_code": None,
                "labour_hours": 2,
                "materials": [],
                "attachments": [],
            }
        ],
        "congestion_required": True,
        "congestion_amount": 18,
    }


def _submit_assignment_estimate(api_client, assignment_id: int, *, role: str) -> tuple[str, str]:
    start = api_client.post(f"/api/v1/quote-assignments/{assignment_id}/start-estimate")
    assert start.status_code == 200, start.text
    session_id = start.json()["data"]["session_id"]
    token = start.json()["data"]["session_token"]
    submit = api_client.post(
        f"/api/v1/calculation-session/{session_id}/submit",
        headers={"X-Session-Token": token},
        json={"step2": _minimal_step2()},
    )
    assert submit.status_code == 200, submit.text
    return session_id, token


def _add_quote(session, *, quote_id: int = 9001, quote_ref: str = "Q-9001") -> EworksQuote:
    quote = EworksQuote(
        eworks_quote_id=quote_id,
        quote_ref=quote_ref,
        customer_name="ACME Ltd",
        description="Rewire",
        quote_date="2026-01-01",
        expiry_date="2026-04-01",
        raw_payload={"site_address": "10 High Street", "secret_token": "hidden"},
    )
    session.add(quote)
    session.commit()
    session.refresh(quote)
    return quote


@patch("app.auth.dependencies.settings")
def test_manager_can_list_assignees(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    resp = api_client.get("/api/v1/quote-assignments/assignees")
    assert resp.status_code == 200
    emails = {item["email"] for item in resp.json()["data"]}
    assert "estimator@optimal.example" in emails
    assert "engineer@optimal.example" in emails
    assert "manager@optimal.example" not in emails
    assert "client@optimal.example" not in emails


@patch("app.auth.dependencies.settings")
def test_assignees_endpoint_returns_estimator_engineer_only(mock_settings, api_client):
    _patch_dev_user(mock_settings, role="manager")
    resp = api_client.get("/api/v1/quote-assignments/assignees")
    roles = {item["role"] for item in resp.json()["data"]}
    assert roles <= {"estimator", "engineer"}
    assert "password_hash" not in resp.text


@patch("app.auth.dependencies.settings")
def test_manager_can_assign_quote_to_registered_estimator(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    quote = _add_quote(db_session)
    estimator = db_session.users["estimator"]  # type: ignore[attr-defined]

    resp = api_client.post(
        f"/api/v1/eworks-sync/quotes/{quote.id}/assignments",
        json={
            "assignment_type": "estimator",
            "assignee_kind": "registered",
            "assigned_user_id": str(estimator.id),
            "notes": "Please estimate",
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["assignment_type"] == "estimator"
    assert data["assignee_kind"] == "registered"
    assert data["assigned_user_email"] == estimator.email
    assert data["status"] == "assigned"


@patch("app.auth.dependencies.settings")
def test_manager_can_assign_quote_to_registered_engineer(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    quote = _add_quote(db_session, quote_id=9002, quote_ref="Q-9002")
    engineer = db_session.users["engineer"]  # type: ignore[attr-defined]

    resp = api_client.post(
        f"/api/v1/eworks-sync/quotes/{quote.id}/assignments",
        json={
            "assignment_type": "engineer",
            "assignee_kind": "registered",
            "assigned_user_id": str(engineer.id),
        },
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["assignment_type"] == "engineer"


@patch("app.auth.dependencies.settings")
def test_manager_cannot_assign_to_admin_or_client(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    quote = _add_quote(db_session, quote_id=9003, quote_ref="Q-9003")
    admin = db_session.users["admin"]  # type: ignore[attr-defined]
    client = db_session.users["client"]  # type: ignore[attr-defined]

    admin_resp = api_client.post(
        f"/api/v1/eworks-sync/quotes/{quote.id}/assignments",
        json={
            "assignment_type": "estimator",
            "assignee_kind": "registered",
            "assigned_user_id": str(admin.id),
        },
    )
    assert admin_resp.status_code == 400

    client_resp = api_client.post(
        f"/api/v1/eworks-sync/quotes/{quote.id}/assignments",
        json={
            "assignment_type": "estimator",
            "assignee_kind": "registered",
            "assigned_user_id": str(client.id),
        },
    )
    assert client_resp.status_code == 400


@patch("app.auth.dependencies.settings")
def test_external_assignment_generates_token(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    quote = _add_quote(db_session, quote_id=9004, quote_ref="Q-9004")

    resp = api_client.post(
        f"/api/v1/eworks-sync/quotes/{quote.id}/assignments",
        json={
            "assignment_type": "estimator",
            "assignee_kind": "external",
            "assigned_user_name": "External Estimator",
            "assigned_user_email": "external@example.com",
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["assignment_token"]
    assert data["assignment_link"].startswith("/assignment/")


@patch("app.auth.dependencies.settings")
def test_public_token_fetch_works(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    quote = _add_quote(db_session, quote_id=9005, quote_ref="Q-9005")
    create_resp = api_client.post(
        f"/api/v1/eworks-sync/quotes/{quote.id}/assignments",
        json={
            "assignment_type": "engineer",
            "assignee_kind": "external",
            "assigned_user_name": "Site Engineer",
            "assigned_user_email": "site@example.com",
        },
    )
    token = create_resp.json()["data"]["assignment_token"]

    public_resp = api_client.get(f"/api/v1/quote-assignments/public/{token}")
    assert public_resp.status_code == 200
    body = public_resp.json()["data"]
    assert body["quote_ref"] == "Q-9005"
    assert body["customer_name"] == "ACME Ltd"
    assert "raw_payload" not in public_resp.text
    assert "secret_token" not in public_resp.text


@patch("app.auth.dependencies.settings")
def test_revoked_token_returns_410(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    quote = _add_quote(db_session, quote_id=9006, quote_ref="Q-9006")
    create_resp = api_client.post(
        f"/api/v1/eworks-sync/quotes/{quote.id}/assignments",
        json={
            "assignment_type": "estimator",
            "assignee_kind": "external",
            "assigned_user_name": "External",
        },
    )
    assignment_id = create_resp.json()["data"]["id"]
    token = create_resp.json()["data"]["assignment_token"]

    revoke_resp = api_client.post(f"/api/v1/quote-assignments/{assignment_id}/revoke")
    assert revoke_resp.status_code == 200

    public_resp = api_client.get(f"/api/v1/quote-assignments/public/{token}")
    assert public_resp.status_code == 410


@patch("app.auth.dependencies.settings")
def test_estimator_sees_own_assignments(mock_settings, api_client, db_session):
    quote = _add_quote(db_session, quote_id=9007, quote_ref="Q-9007")
    estimator = db_session.users["estimator"]  # type: ignore[attr-defined]

    _patch_dev_user(mock_settings, role="manager")
    api_client.post(
        f"/api/v1/eworks-sync/quotes/{quote.id}/assignments",
        json={
            "assignment_type": "estimator",
            "assignee_kind": "registered",
            "assigned_user_id": str(estimator.id),
        },
    )

    _patch_dev_user(mock_settings, role="estimator")
    resp = api_client.get("/api/v1/quote-assignments/my")
    assert resp.status_code == 200
    items = resp.json()["data"]
    assert len(items) == 1
    assert items[0]["quote_ref"] == "Q-9007"
    assert items[0]["quote_summary"]["customer_name"] == "ACME Ltd"
    assert "raw_payload" not in resp.text


@patch("app.auth.dependencies.settings")
def test_engineer_sees_own_assignments(mock_settings, api_client, db_session):
    quote = _add_quote(db_session, quote_id=9008, quote_ref="Q-9008")
    engineer = db_session.users["engineer"]  # type: ignore[attr-defined]

    _patch_dev_user(mock_settings, role="manager")
    api_client.post(
        f"/api/v1/eworks-sync/quotes/{quote.id}/assignments",
        json={
            "assignment_type": "engineer",
            "assignee_kind": "registered",
            "assigned_user_id": str(engineer.id),
        },
    )

    _patch_dev_user(mock_settings, role="engineer")
    resp = api_client.get("/api/v1/quote-assignments/my")
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1
    assert resp.json()["data"][0]["assignment_type"] == "engineer"


@patch("app.auth.dependencies.settings")
def test_estimator_does_not_see_other_users_assignment(mock_settings, api_client, db_session):
    quote = _add_quote(db_session, quote_id=9009, quote_ref="Q-9009")
    estimator2 = db_session.users["estimator2"]  # type: ignore[attr-defined]

    _patch_dev_user(mock_settings, role="manager")
    api_client.post(
        f"/api/v1/eworks-sync/quotes/{quote.id}/assignments",
        json={
            "assignment_type": "estimator",
            "assignee_kind": "registered",
            "assigned_user_id": str(estimator2.id),
        },
    )

    _patch_dev_user(mock_settings, role="estimator")
    resp = api_client.get("/api/v1/quote-assignments/my")
    assert resp.status_code == 200
    assert resp.json()["data"] == []


@patch("app.auth.dependencies.settings")
def test_engineer_and_client_cannot_create_assignment(mock_settings, api_client, db_session):
    quote = _add_quote(db_session, quote_id=9010, quote_ref="Q-9010")
    estimator = db_session.users["estimator"]  # type: ignore[attr-defined]
    payload = {
        "assignment_type": "estimator",
        "assignee_kind": "registered",
        "assigned_user_id": str(estimator.id),
    }

    _patch_dev_user(mock_settings, role="engineer")
    engineer_resp = api_client.post(
        f"/api/v1/eworks-sync/quotes/{quote.id}/assignments",
        json=payload,
    )
    assert engineer_resp.status_code == 403

    _patch_dev_user(mock_settings, role="client")
    client_resp = api_client.post(
        f"/api/v1/eworks-sync/quotes/{quote.id}/assignments",
        json=payload,
    )
    assert client_resp.status_code == 403


@patch("app.auth.dependencies.settings")
def test_assignment_responses_exclude_raw_payload_and_secrets(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    quote = _add_quote(db_session, quote_id=9011, quote_ref="Q-9011")
    estimator = db_session.users["estimator"]  # type: ignore[attr-defined]

    create_resp = api_client.post(
        f"/api/v1/eworks-sync/quotes/{quote.id}/assignments",
        json={
            "assignment_type": "estimator",
            "assignee_kind": "registered",
            "assigned_user_id": str(estimator.id),
        },
    )
    assert "raw_payload" not in create_resp.text
    assert "secret_token" not in create_resp.text

    list_resp = api_client.get(f"/api/v1/eworks-sync/quotes/{quote.id}/assignments")
    assert "raw_payload" not in list_resp.text
    assert "secret_token" not in list_resp.text


@patch("app.auth.dependencies.settings")
def test_audit_log_created_without_assignment_token(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    quote = _add_quote(db_session, quote_id=9012, quote_ref="Q-9012")

    resp = api_client.post(
        f"/api/v1/eworks-sync/quotes/{quote.id}/assignments",
        json={
            "assignment_type": "estimator",
            "assignee_kind": "external",
            "assigned_user_name": "External Estimator",
            "assigned_user_email": "external@example.com",
        },
    )
    token = resp.json()["data"]["assignment_token"]

    logs = db_session.scalars(
        select(AuditLog).where(AuditLog.action == "quote_assignment_created")
    ).all()
    assert len(logs) == 1
    log = logs[0]
    metadata = (log.new_value or {}).get("_metadata") or {}
    after_payload = {k: v for k, v in (log.new_value or {}).items() if k != "_metadata"}
    assert metadata.get("assigned_user_email") == "external@example.com"
    assert "assignment_token" not in metadata
    assert "assignment_token" not in after_payload
    assert token not in str(log.new_value)
    assert token not in str(log.old_value)


@patch("app.auth.dependencies.settings")
def test_expired_public_token_returns_410(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    quote = _add_quote(db_session, quote_id=9013, quote_ref="Q-9013")
    create_resp = api_client.post(
        f"/api/v1/eworks-sync/quotes/{quote.id}/assignments",
        json={
            "assignment_type": "estimator",
            "assignee_kind": "external",
            "assigned_user_name": "Expired User",
        },
    )
    assignment_id = create_resp.json()["data"]["id"]
    token = create_resp.json()["data"]["assignment_token"]

    row = db_session.get(EworksQuoteAssignment, assignment_id)
    row.assignment_token_expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    db_session.commit()

    public_resp = api_client.get(f"/api/v1/quote-assignments/public/{token}")
    assert public_resp.status_code == 410


@patch("app.auth.dependencies.settings")
def test_estimator_can_start_own_estimator_assignment(mock_settings, api_client, db_session):
    quote = _add_quote(db_session, quote_id=9201, quote_ref="Q-9201")
    estimator = db_session.users["estimator"]  # type: ignore[attr-defined]

    _patch_dev_user(mock_settings, role="manager")
    create_resp = api_client.post(
        f"/api/v1/eworks-sync/quotes/{quote.id}/assignments",
        json={
            "assignment_type": "estimator",
            "assignee_kind": "registered",
            "assigned_user_id": str(estimator.id),
        },
    )
    assignment_id = create_resp.json()["data"]["id"]

    _patch_dev_user(mock_settings, role="estimator")
    start_resp = api_client.post(f"/api/v1/quote-assignments/{assignment_id}/start-estimate")
    assert start_resp.status_code == 200
    data = start_resp.json()["data"]
    assert data["session_id"]
    assert data["session_token"]
    assert data["resume_url"].startswith("/eworks/calculate?session_id=")
    assert "token=" in data["resume_url"]
    assert data["quote_ref"] == "Q-9201"
    assert "raw_payload" not in start_resp.text

    row = db_session.get(EworksQuoteAssignment, assignment_id)
    assert row.calculation_session_id is not None
    assert row.status == "in_progress"


@patch("app.auth.dependencies.settings")
def test_engineer_can_start_own_engineer_assignment(mock_settings, api_client, db_session):
    quote = _add_quote(db_session, quote_id=9202, quote_ref="Q-9202")
    engineer = db_session.users["engineer"]  # type: ignore[attr-defined]

    _patch_dev_user(mock_settings, role="manager")
    create_resp = api_client.post(
        f"/api/v1/eworks-sync/quotes/{quote.id}/assignments",
        json={
            "assignment_type": "engineer",
            "assignee_kind": "registered",
            "assigned_user_id": str(engineer.id),
        },
    )
    assignment_id = create_resp.json()["data"]["id"]

    _patch_dev_user(mock_settings, role="engineer")
    start_resp = api_client.post(f"/api/v1/quote-assignments/{assignment_id}/start-estimate")
    assert start_resp.status_code == 200


@patch("app.auth.dependencies.settings")
def test_estimator_cannot_start_another_users_assignment(mock_settings, api_client, db_session):
    quote = _add_quote(db_session, quote_id=9203, quote_ref="Q-9203")
    estimator2 = db_session.users["estimator2"]  # type: ignore[attr-defined]

    _patch_dev_user(mock_settings, role="manager")
    create_resp = api_client.post(
        f"/api/v1/eworks-sync/quotes/{quote.id}/assignments",
        json={
            "assignment_type": "estimator",
            "assignee_kind": "registered",
            "assigned_user_id": str(estimator2.id),
        },
    )
    assignment_id = create_resp.json()["data"]["id"]

    _patch_dev_user(mock_settings, role="estimator")
    start_resp = api_client.post(f"/api/v1/quote-assignments/{assignment_id}/start-estimate")
    assert start_resp.status_code == 403


@patch("app.auth.dependencies.settings")
def test_engineer_cannot_start_estimator_assignment(mock_settings, api_client, db_session):
    quote = _add_quote(db_session, quote_id=9204, quote_ref="Q-9204")
    estimator = db_session.users["estimator"]  # type: ignore[attr-defined]

    _patch_dev_user(mock_settings, role="manager")
    create_resp = api_client.post(
        f"/api/v1/eworks-sync/quotes/{quote.id}/assignments",
        json={
            "assignment_type": "estimator",
            "assignee_kind": "registered",
            "assigned_user_id": str(estimator.id),
        },
    )
    assignment_id = create_resp.json()["data"]["id"]

    _patch_dev_user(mock_settings, role="engineer")
    start_resp = api_client.post(f"/api/v1/quote-assignments/{assignment_id}/start-estimate")
    assert start_resp.status_code == 403


@patch("app.auth.dependencies.settings")
def test_manager_and_client_blocked_from_start_estimate(mock_settings, api_client, db_session):
    quote = _add_quote(db_session, quote_id=9205, quote_ref="Q-9205")
    estimator = db_session.users["estimator"]  # type: ignore[attr-defined]

    _patch_dev_user(mock_settings, role="manager")
    create_resp = api_client.post(
        f"/api/v1/eworks-sync/quotes/{quote.id}/assignments",
        json={
            "assignment_type": "estimator",
            "assignee_kind": "registered",
            "assigned_user_id": str(estimator.id),
        },
    )
    assignment_id = create_resp.json()["data"]["id"]

    manager_start = api_client.post(f"/api/v1/quote-assignments/{assignment_id}/start-estimate")
    assert manager_start.status_code == 403

    _patch_dev_user(mock_settings, role="client")
    client_start = api_client.post(f"/api/v1/quote-assignments/{assignment_id}/start-estimate")
    assert client_start.status_code == 403


@patch("app.auth.dependencies.settings")
def test_second_start_returns_same_session(mock_settings, api_client, db_session):
    quote = _add_quote(db_session, quote_id=9206, quote_ref="Q-9206")
    estimator = db_session.users["estimator"]  # type: ignore[attr-defined]

    _patch_dev_user(mock_settings, role="manager")
    create_resp = api_client.post(
        f"/api/v1/eworks-sync/quotes/{quote.id}/assignments",
        json={
            "assignment_type": "estimator",
            "assignee_kind": "registered",
            "assigned_user_id": str(estimator.id),
        },
    )
    assignment_id = create_resp.json()["data"]["id"]

    _patch_dev_user(mock_settings, role="estimator")
    first = api_client.post(f"/api/v1/quote-assignments/{assignment_id}/start-estimate").json()["data"]
    second = api_client.post(f"/api/v1/quote-assignments/{assignment_id}/start-estimate").json()["data"]
    assert first["session_id"] == second["session_id"]
    assert first["session_token"] == second["session_token"]
    assert db_session.query(CalculationSession).count() == 1


@patch("app.auth.dependencies.settings")
def test_list_my_assignments_excludes_session_token(mock_settings, api_client, db_session):
    quote = _add_quote(db_session, quote_id=9207, quote_ref="Q-9207")
    estimator = db_session.users["estimator"]  # type: ignore[attr-defined]

    _patch_dev_user(mock_settings, role="manager")
    create_resp = api_client.post(
        f"/api/v1/eworks-sync/quotes/{quote.id}/assignments",
        json={
            "assignment_type": "estimator",
            "assignee_kind": "registered",
            "assigned_user_id": str(estimator.id),
        },
    )
    assignment_id = create_resp.json()["data"]["id"]

    _patch_dev_user(mock_settings, role="estimator")
    api_client.post(f"/api/v1/quote-assignments/{assignment_id}/start-estimate")
    list_resp = api_client.get("/api/v1/quote-assignments/my")
    assert list_resp.status_code == 200
    item = list_resp.json()["data"][0]
    assert item["has_calculation_session"] is True
    assert item["calculation_session_id"]
    assert item["can_start_estimate"] is True
    assert "session_token" not in list_resp.text


@patch("app.auth.dependencies.settings")
def test_start_estimate_audit_created_without_token(mock_settings, api_client, db_session):
    quote = _add_quote(db_session, quote_id=9208, quote_ref="Q-9208")
    estimator = db_session.users["estimator"]  # type: ignore[attr-defined]

    _patch_dev_user(mock_settings, role="manager")
    create_resp = api_client.post(
        f"/api/v1/eworks-sync/quotes/{quote.id}/assignments",
        json={
            "assignment_type": "estimator",
            "assignee_kind": "registered",
            "assigned_user_id": str(estimator.id),
        },
    )
    assignment_id = create_resp.json()["data"]["id"]

    _patch_dev_user(mock_settings, role="estimator")
    start_resp = api_client.post(f"/api/v1/quote-assignments/{assignment_id}/start-estimate")
    token = start_resp.json()["data"]["session_token"]

    logs = db_session.scalars(select(AuditLog).where(AuditLog.action == "quote_assignment_started")).all()
    assert len(logs) == 1
    assert token not in str(logs[0].new_value)
    metadata = (logs[0].new_value or {}).get("_metadata") or {}
    assert metadata.get("quote_ref") == "Q-9208"


@patch("app.auth.dependencies.settings")
def test_public_external_assignment_can_start_estimate(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    quote = _add_quote(db_session, quote_id=9301, quote_ref="Q-9301")
    create_resp = api_client.post(
        f"/api/v1/eworks-sync/quotes/{quote.id}/assignments",
        json={
            "assignment_type": "estimator",
            "assignee_kind": "external",
            "assigned_user_name": "External Estimator",
            "assigned_user_email": "external@example.com",
        },
    )
    token = create_resp.json()["data"]["assignment_token"]
    assignment_id = create_resp.json()["data"]["id"]

    start_resp = api_client.post(f"/api/v1/quote-assignments/public/{token}/start-estimate")
    assert start_resp.status_code == 200
    data = start_resp.json()["data"]
    assert data["session_id"]
    assert data["session_token"]
    assert data["resume_url"].startswith("/eworks/calculate?session_id=")
    assert "token=" in data["resume_url"]
    assert data["assignment_id"] == assignment_id
    assert data["quote_ref"] == "Q-9301"
    assert "raw_payload" not in start_resp.text
    assert "secret_token" not in start_resp.text

    row = db_session.get(EworksQuoteAssignment, assignment_id)
    assert row.calculation_session_id is not None
    assert row.status == "in_progress"


def test_public_start_invalid_token_returns_404(api_client):
    resp = api_client.post("/api/v1/quote-assignments/public/not-a-real-token/start-estimate")
    assert resp.status_code == 404


@patch("app.auth.dependencies.settings")
def test_public_start_revoked_token_returns_410(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    quote = _add_quote(db_session, quote_id=9302, quote_ref="Q-9302")
    create_resp = api_client.post(
        f"/api/v1/eworks-sync/quotes/{quote.id}/assignments",
        json={
            "assignment_type": "estimator",
            "assignee_kind": "external",
            "assigned_user_name": "Revoked User",
        },
    )
    assignment_id = create_resp.json()["data"]["id"]
    token = create_resp.json()["data"]["assignment_token"]

    api_client.post(f"/api/v1/quote-assignments/{assignment_id}/revoke")
    resp = api_client.post(f"/api/v1/quote-assignments/public/{token}/start-estimate")
    assert resp.status_code == 410


@patch("app.auth.dependencies.settings")
def test_public_start_expired_token_returns_410(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    quote = _add_quote(db_session, quote_id=9303, quote_ref="Q-9303")
    create_resp = api_client.post(
        f"/api/v1/eworks-sync/quotes/{quote.id}/assignments",
        json={
            "assignment_type": "estimator",
            "assignee_kind": "external",
            "assigned_user_name": "Expired User",
        },
    )
    assignment_id = create_resp.json()["data"]["id"]
    token = create_resp.json()["data"]["assignment_token"]

    row = db_session.get(EworksQuoteAssignment, assignment_id)
    row.assignment_token_expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    db_session.commit()

    resp = api_client.post(f"/api/v1/quote-assignments/public/{token}/start-estimate")
    assert resp.status_code == 410


@patch("app.auth.dependencies.settings")
def test_public_start_cancelled_assignment_returns_410(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    quote = _add_quote(db_session, quote_id=9304, quote_ref="Q-9304")
    create_resp = api_client.post(
        f"/api/v1/eworks-sync/quotes/{quote.id}/assignments",
        json={
            "assignment_type": "estimator",
            "assignee_kind": "external",
            "assigned_user_name": "Cancelled User",
        },
    )
    assignment_id = create_resp.json()["data"]["id"]
    token = create_resp.json()["data"]["assignment_token"]

    row = db_session.get(EworksQuoteAssignment, assignment_id)
    row.status = "cancelled"
    db_session.commit()

    resp = api_client.post(f"/api/v1/quote-assignments/public/{token}/start-estimate")
    assert resp.status_code == 410


@patch("app.auth.dependencies.settings")
def test_registered_assignment_cannot_use_public_start_endpoint(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    quote = _add_quote(db_session, quote_id=9305, quote_ref="Q-9305")
    estimator = db_session.users["estimator"]  # type: ignore[attr-defined]
    create_resp = api_client.post(
        f"/api/v1/eworks-sync/quotes/{quote.id}/assignments",
        json={
            "assignment_type": "estimator",
            "assignee_kind": "registered",
            "assigned_user_id": str(estimator.id),
        },
    )
    assignment_id = create_resp.json()["data"]["id"]
    row = db_session.get(EworksQuoteAssignment, assignment_id)
    row.assignment_token = "registered-token-should-not-work"
    row.assignment_token_created_at = datetime.now(timezone.utc)
    row.assignment_token_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    db_session.commit()

    resp = api_client.post("/api/v1/quote-assignments/public/registered-token-should-not-work/start-estimate")
    assert resp.status_code == 403


@patch("app.auth.dependencies.settings")
def test_public_second_start_returns_same_session(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    quote = _add_quote(db_session, quote_id=9306, quote_ref="Q-9306")
    create_resp = api_client.post(
        f"/api/v1/eworks-sync/quotes/{quote.id}/assignments",
        json={
            "assignment_type": "estimator",
            "assignee_kind": "external",
            "assigned_user_name": "External Estimator",
        },
    )
    token = create_resp.json()["data"]["assignment_token"]

    first = api_client.post(f"/api/v1/quote-assignments/public/{token}/start-estimate").json()["data"]
    second = api_client.post(f"/api/v1/quote-assignments/public/{token}/start-estimate").json()["data"]
    assert first["session_id"] == second["session_id"]
    assert first["session_token"] == second["session_token"]
    assert db_session.query(CalculationSession).count() == 1


@patch("app.auth.dependencies.settings")
def test_public_start_audit_created_without_tokens(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    quote = _add_quote(db_session, quote_id=9307, quote_ref="Q-9307")
    create_resp = api_client.post(
        f"/api/v1/eworks-sync/quotes/{quote.id}/assignments",
        json={
            "assignment_type": "estimator",
            "assignee_kind": "external",
            "assigned_user_name": "External Estimator",
            "assigned_user_email": "external@example.com",
        },
    )
    token = create_resp.json()["data"]["assignment_token"]

    start_resp = api_client.post(f"/api/v1/quote-assignments/public/{token}/start-estimate")
    session_token = start_resp.json()["data"]["session_token"]

    logs = db_session.scalars(
        select(AuditLog).where(AuditLog.action == "quote_assignment_public_started")
    ).all()
    assert len(logs) == 1
    log_text = str(logs[0].new_value)
    metadata = (logs[0].new_value or {}).get("_metadata") or {}
    assert token not in log_text
    assert session_token not in log_text
    assert token not in str(metadata)
    assert session_token not in str(metadata)
    assert metadata.get("assignee_kind") == "external"
    assert metadata.get("assigned_user_email") == "external@example.com"
    assert metadata.get("quote_ref") == "Q-9307"


@patch("app.auth.dependencies.settings")
def test_engineer_submit_updates_assignment_status(mock_settings, api_client, db_session):
    _add_trade_default_rate_rule(db_session)
    quote = _add_quote(db_session, quote_id=9401, quote_ref="Q22122")
    engineer = db_session.users["engineer"]  # type: ignore[attr-defined]

    _patch_dev_user(mock_settings, role="manager")
    create_resp = api_client.post(
        f"/api/v1/eworks-sync/quotes/{quote.id}/assignments",
        json={
            "assignment_type": "engineer",
            "assignee_kind": "registered",
            "assigned_user_id": str(engineer.id),
        },
    )
    assignment_id = create_resp.json()["data"]["id"]

    _patch_dev_user(mock_settings, role="engineer")
    _submit_assignment_estimate(api_client, assignment_id, role="engineer")
    db_session.expire_all()

    row = db_session.get(EworksQuoteAssignment, assignment_id)
    assert row is not None
    assert row.status == "submitted"

    list_resp = api_client.get("/api/v1/quote-assignments/my")
    assert list_resp.status_code == 200
    item = next(i for i in list_resp.json()["data"] if i["id"] == assignment_id)
    assert item["status"] == "submitted"
    assert item["submitted_at"]
    assert item["can_view_submission"] is True
    assert "session_token" not in list_resp.text

    logs = db_session.scalars(select(AuditLog).where(AuditLog.action == "quote_assignment_submitted")).all()
    assert len(logs) == 1


@patch("app.auth.dependencies.settings")
def test_estimator_submit_updates_assignment_status(mock_settings, api_client, db_session):
    _add_trade_default_rate_rule(db_session)
    quote = _add_quote(db_session, quote_id=9402, quote_ref="Q-9402")
    estimator = db_session.users["estimator"]  # type: ignore[attr-defined]

    _patch_dev_user(mock_settings, role="manager")
    create_resp = api_client.post(
        f"/api/v1/eworks-sync/quotes/{quote.id}/assignments",
        json={
            "assignment_type": "estimator",
            "assignee_kind": "registered",
            "assigned_user_id": str(estimator.id),
        },
    )
    assignment_id = create_resp.json()["data"]["id"]

    _patch_dev_user(mock_settings, role="estimator")
    _submit_assignment_estimate(api_client, assignment_id, role="estimator")
    db_session.expire_all()

    row = db_session.get(EworksQuoteAssignment, assignment_id)
    assert row is not None
    assert row.status == "submitted"
