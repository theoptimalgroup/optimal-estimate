"""Unit tests for client public quote API."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import UserRole, get_password_hash
from app.db.session import get_db
from app.main import app
from app.models.calculation_session import CalculationSession
from app.models.support import AuditLog
from app.models.user import User
from app.schemas.calculation import CalculationBreakdown, LineBreakdown
from app.services.client_quote_service import create_or_get_public_link


def _patch_dev_user(mock_settings, *, role: str, email: str = "staff@optimal.example", enabled: bool = True):
    mock_settings.dev_auth_enabled = enabled
    mock_settings.dev_user_id = "dev-user-1"
    mock_settings.dev_user_email = email
    mock_settings.dev_user_name = "Staff User"
    mock_settings.dev_user_role = role
    mock_settings.dev_user_is_active = True
    mock_settings.dev_auth_auto_create_user = False


def _step1_snapshot() -> dict:
    return {
        "quote_number": "Q-CLIENT-1",
        "job_number": "JOB-001",
        "client_name": "Atkinson McLeod",
        "trade_name": "Painter",
        "property_address": "1 Test Street",
        "quote_description": "Repaint hallway",
    }


def _breakdown() -> CalculationBreakdown:
    return CalculationBreakdown(
        labour=[LineBreakdown(label="Labour", formula="day", total=Decimal("800"))],
        materials=[LineBreakdown(label="Materials", formula="qty", total=Decimal("200"))],
        charges=[LineBreakdown(label="Parking", formula="fixed", total=Decimal("50"))],
        subtotal=Decimal("1050"),
        vat_rate=Decimal("20"),
        vat_total=Decimal("210"),
        final_total=Decimal("1260"),
        formula_version="1.0.0",
        profit_gbp=Decimal("300"),
        profit_pct=Decimal("25"),
        internal_notes="secret internal note",
        denominator_used=Decimal("0.7"),
        formula_source="xlsx",
    )


def _create_public_link(session, submitted_id):
    from app.schemas.eworks_link import Step1Snapshot, Step2Snapshot

    with patch("app.services.client_quote_service._get_breakdown_and_works") as mock_breakdown:
        mock_breakdown.return_value = (
            _breakdown(),
            Step1Snapshot.model_validate(_step1_snapshot()),
            Step2Snapshot.model_validate({"works": [{"scope": "Paint hallway", "product_name": "Painting"}]}),
            [],
        )
        link = create_or_get_public_link(session, submitted_id)
        session.commit()
    return link


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for model in (User, CalculationSession, AuditLog):
        model.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    now = datetime.now(timezone.utc)
    session.add(
        User(
            id=uuid4(),
            email="manager@optimal.example",
            full_name="Manager User",
            password_hash=get_password_hash("manager12345"),
            role=UserRole.MANAGER.value,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    )
    submitted_id = uuid4()
    session.add(
        CalculationSession(
            id=submitted_id,
            session_token="session-token-secret-value",
            source="test",
            payload_snapshot={},
            step1_snapshot=_step1_snapshot(),
            step2_snapshot={"works": [{"scope": "Paint hallway", "product_name": "Painting"}]},
            ui_state={
                "last_result": {
                    "breakdown": _breakdown().model_dump(mode="json"),
                    "work_breakdowns": [{"work_index": 0, "breakdown": {"final_total": "1260"}}],
                    "internal_notes": "secret",
                }
            },
            expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
            status="submitted",
            submitted_at=now,
        )
    )
    session.commit()
    yield session, submitted_id
    session.close()


@pytest.fixture()
def client_quotes_client(db_session):
    session, _ = db_session

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@patch("app.auth.dependencies.settings")
def test_manager_can_create_public_link(mock_settings, client_quotes_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    _, submitted_id = db_session
    response = client_quotes_client.post(f"/api/v1/client-quotes/{submitted_id}/public-link")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["public_url"].startswith("/client/quote/")
    assert body["public_token"]
    assert body["public_token"] != "session-token-secret-value"


@patch("app.auth.dependencies.settings")
@patch("app.services.client_quote_service._get_breakdown_and_works")
def test_public_token_can_fetch_quote_without_auth(mock_breakdown, mock_settings, client_quotes_client, db_session):
    from app.schemas.eworks_link import Step1Snapshot, Step2Snapshot

    session, submitted_id = db_session
    mock_breakdown.return_value = (
        _breakdown(),
        Step1Snapshot.model_validate(_step1_snapshot()),
        Step2Snapshot.model_validate({"works": [{"scope": "Paint hallway", "product_name": "Painting"}]}),
        [],
    )
    link = create_or_get_public_link(session, submitted_id)
    session.commit()

    response = client_quotes_client.get(f"/api/v1/client-quotes/public/{link.public_token}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["quote_ref"] == "Q-CLIENT-1"
    assert data["acceptance"]["accepted"] is False
    text = response.text.lower()
    assert "session_token" not in text
    assert "session-token-secret-value" not in text
    assert "internal_notes" not in text
    assert "profit" not in text
    assert "margin" not in text
    assert "denominator" not in text
    assert "formula_source" not in text


@patch("app.auth.dependencies.settings")
def test_invalid_token_returns_404(mock_settings, client_quotes_client):
    _patch_dev_user(mock_settings, role="manager")
    response = client_quotes_client.get("/api/v1/client-quotes/public/invalid-token-value")
    assert response.status_code == 404


@patch("app.auth.dependencies.settings")
@pytest.mark.parametrize("role", ["engineer", "client"])
def test_engineer_and_client_blocked_from_creating_link(mock_settings, client_quotes_client, db_session, role):
    _patch_dev_user(mock_settings, role=role)
    _, submitted_id = db_session
    response = client_quotes_client.post(f"/api/v1/client-quotes/{submitted_id}/public-link")
    assert response.status_code == 403


@patch("app.auth.dependencies.settings")
def test_estimator_can_create_public_link(mock_settings, client_quotes_client, db_session):
    _patch_dev_user(mock_settings, role="estimator")
    _, submitted_id = db_session
    response = client_quotes_client.post(f"/api/v1/client-quotes/{submitted_id}/public-link")
    assert response.status_code == 200


@patch("app.services.client_quote_service._get_breakdown_and_works")
def test_revoked_token_returns_410(mock_breakdown, client_quotes_client, db_session):
    from app.schemas.eworks_link import Step1Snapshot, Step2Snapshot

    session, submitted_id = db_session
    mock_breakdown.return_value = (
        _breakdown(),
        Step1Snapshot.model_validate(_step1_snapshot()),
        Step2Snapshot.model_validate({"works": []}),
        [],
    )
    link = create_or_get_public_link(session, submitted_id)
    row = session.get(CalculationSession, submitted_id)
    row.public_quote_token_revoked_at = datetime.now(timezone.utc)
    session.commit()

    response = client_quotes_client.get(f"/api/v1/client-quotes/public/{link.public_token}")
    assert response.status_code == 410


@patch("app.auth.dependencies.settings")
def test_admin_can_create_public_link(mock_settings, client_quotes_client, db_session):
    _patch_dev_user(mock_settings, role="admin")
    _, submitted_id = db_session
    response = client_quotes_client.post(f"/api/v1/client-quotes/{submitted_id}/public-link")
    assert response.status_code == 200


@patch("app.auth.dependencies.settings")
def test_unauthenticated_can_fetch_public_quote(mock_settings, client_quotes_client, db_session):
    mock_settings.dev_auth_enabled = False
    session, submitted_id = db_session
    with patch("app.services.client_quote_service._get_breakdown_and_works") as mock_breakdown:
        from app.schemas.eworks_link import Step1Snapshot, Step2Snapshot

        mock_breakdown.return_value = (
            _breakdown(),
            Step1Snapshot.model_validate(_step1_snapshot()),
            Step2Snapshot.model_validate({"works": [{"scope": "Paint hallway", "product_name": "Painting"}]}),
            [],
        )
        link = create_or_get_public_link(session, submitted_id)
        session.commit()
        response = client_quotes_client.get(f"/api/v1/client-quotes/public/{link.public_token}")
    assert response.status_code == 200


@patch("app.services.client_quote_service._get_breakdown_and_works")
def test_public_accept_succeeds_with_valid_token(mock_breakdown, client_quotes_client, db_session):
    session, submitted_id = db_session
    link = _create_public_link(session, submitted_id)

    response = client_quotes_client.post(
        f"/api/v1/client-quotes/public/{link.public_token}/accept",
        json={"name": "Jane Client", "email": "client@example.com", "notes": "Please proceed"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["accepted"] is True
    assert data["already_accepted"] is False
    assert data["quote_ref"] == "Q-CLIENT-1"
    assert data["accepted_at"]

    text = response.text.lower()
    assert "session_token" not in text
    assert "profit" not in text
    assert "internal_notes" not in text

    row = session.get(CalculationSession, submitted_id)
    assert row.client_acceptance_name == "Jane Client"
    assert row.client_acceptance_email == "client@example.com"
    assert row.client_acceptance_notes == "Please proceed"
    assert row.client_accepted_at is not None


@patch("app.services.client_quote_service._get_breakdown_and_works")
def test_public_accept_invalid_token_returns_404(mock_breakdown, client_quotes_client):
    response = client_quotes_client.post(
        "/api/v1/client-quotes/public/invalid-token-value/accept",
        json={"name": "Jane Client", "email": "client@example.com"},
    )
    assert response.status_code == 404


@patch("app.services.client_quote_service._get_breakdown_and_works")
def test_public_accept_revoked_token_returns_410(mock_breakdown, client_quotes_client, db_session):
    session, submitted_id = db_session
    link = _create_public_link(session, submitted_id)
    row = session.get(CalculationSession, submitted_id)
    row.public_quote_token_revoked_at = datetime.now(timezone.utc)
    session.commit()

    response = client_quotes_client.post(
        f"/api/v1/client-quotes/public/{link.public_token}/accept",
        json={"name": "Jane Client", "email": "client@example.com"},
    )
    assert response.status_code == 410


@patch("app.services.client_quote_service._get_breakdown_and_works")
def test_public_accept_expired_token_returns_410(mock_breakdown, client_quotes_client, db_session):
    session, submitted_id = db_session
    link = _create_public_link(session, submitted_id)
    row = session.get(CalculationSession, submitted_id)
    row.public_quote_expires_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
    session.commit()

    response = client_quotes_client.post(
        f"/api/v1/client-quotes/public/{link.public_token}/accept",
        json={"name": "Jane Client", "email": "client@example.com"},
    )
    assert response.status_code == 410


@patch("app.services.client_quote_service._get_breakdown_and_works")
def test_public_accept_missing_name_or_email_returns_validation_error(mock_breakdown, client_quotes_client, db_session):
    session, submitted_id = db_session
    link = _create_public_link(session, submitted_id)

    missing_name = client_quotes_client.post(
        f"/api/v1/client-quotes/public/{link.public_token}/accept",
        json={"email": "client@example.com"},
    )
    assert missing_name.status_code == 422

    missing_email = client_quotes_client.post(
        f"/api/v1/client-quotes/public/{link.public_token}/accept",
        json={"name": "Jane Client"},
    )
    assert missing_email.status_code == 422

    invalid_email = client_quotes_client.post(
        f"/api/v1/client-quotes/public/{link.public_token}/accept",
        json={"name": "Jane Client", "email": "not-an-email"},
    )
    assert invalid_email.status_code == 422


@patch("app.services.client_quote_service._get_breakdown_and_works")
def test_public_accept_already_accepted_returns_safe_response(mock_breakdown, client_quotes_client, db_session):
    session, submitted_id = db_session
    link = _create_public_link(session, submitted_id)

    first = client_quotes_client.post(
        f"/api/v1/client-quotes/public/{link.public_token}/accept",
        json={"name": "Jane Client", "email": "client@example.com"},
    )
    assert first.status_code == 200

    second = client_quotes_client.post(
        f"/api/v1/client-quotes/public/{link.public_token}/accept",
        json={"name": "Other Person", "email": "other@example.com"},
    )
    assert second.status_code == 200
    data = second.json()["data"]
    assert data["accepted"] is True
    assert data["already_accepted"] is True

    row = session.get(CalculationSession, submitted_id)
    assert row.client_acceptance_email == "client@example.com"


@patch("app.services.client_quote_service._get_breakdown_and_works")
def test_public_accept_creates_audit_log(mock_breakdown, client_quotes_client, db_session):
    session, submitted_id = db_session
    link = _create_public_link(session, submitted_id)

    response = client_quotes_client.post(
        f"/api/v1/client-quotes/public/{link.public_token}/accept",
        json={"name": "Jane Client", "email": "client@example.com"},
    )
    assert response.status_code == 200

    logs = session.scalars(select(AuditLog).where(AuditLog.action == "client_quote_accepted")).all()
    assert len(logs) == 1
    log = logs[0]
    assert log.entity_id == submitted_id
    assert log.new_value["_metadata"]["quote_ref"] == "Q-CLIENT-1"
    assert log.new_value["_metadata"]["client_acceptance_email"] == "client@example.com"
    assert log.new_value["_metadata"]["public_link"] is True
    assert link.public_token not in str(log.new_value)


@patch("app.auth.dependencies.settings")
@patch("app.services.calculation_session_service._dashboard_last_result")
def test_manager_review_includes_acceptance_status(mock_last_result, mock_settings, client_quotes_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    session, submitted_id = db_session
    now = datetime.now(timezone.utc)
    row = session.get(CalculationSession, submitted_id)
    row.client_accepted_at = now
    row.client_acceptance_name = "Jane Client"
    row.client_acceptance_email = "client@example.com"
    row.client_acceptance_notes = "Ready to start"
    session.commit()

    mock_last_result.return_value = {
        "breakdown": _breakdown().model_dump(mode="json"),
        "work_breakdowns": [],
    }

    response = client_quotes_client.get("/api/v1/dashboard/quotes")
    assert response.status_code == 200
    quotes = response.json()["data"]["quotes"]
    assert len(quotes) == 1
    acceptance = quotes[0]["acceptance"]
    assert acceptance["accepted"] is True
    assert acceptance["name"] == "Jane Client"
    assert acceptance["email"] == "client@example.com"
    assert acceptance["notes"] == "Ready to start"


@patch("app.auth.dependencies.settings")
@patch("app.services.estimator_service._extract_final_total")
def test_estimator_quote_detail_includes_acceptance_status(mock_total, mock_settings, client_quotes_client, db_session):
    _patch_dev_user(mock_settings, role="estimator")
    session, submitted_id = db_session
    now = datetime.now(timezone.utc)
    row = session.get(CalculationSession, submitted_id)
    row.client_accepted_at = now
    row.client_acceptance_name = "Jane Client"
    row.client_acceptance_email = "client@example.com"
    session.commit()
    mock_total.return_value = Decimal("1260")

    response = client_quotes_client.get(f"/api/v1/estimator/quotes/{submitted_id}")
    assert response.status_code == 200
    acceptance = response.json()["data"]["acceptance"]
    assert acceptance["accepted"] is True
    assert acceptance["name"] == "Jane Client"
