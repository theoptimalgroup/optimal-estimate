"""Unit tests for eWorks acceptance sync."""

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
from app.services.eworks_acceptance_sync_service import (
    SYNC_FAILED,
    SYNC_SKIPPED,
    SYNC_SUCCESS,
    build_acceptance_sync_text,
    resolve_eworks_quote_id,
    sync_quote_acceptance_to_eworks,
)
from app.services.eworks_quote_api_service import redact_sync_record


def _patch_dev_user(mock_settings, *, role: str, email: str = "staff@optimal.example", enabled: bool = True):
    mock_settings.dev_auth_enabled = enabled
    mock_settings.dev_user_id = "dev-user-1"
    mock_settings.dev_user_email = email
    mock_settings.dev_user_name = "Staff User"
    mock_settings.dev_user_role = role
    mock_settings.dev_user_is_active = True
    mock_settings.dev_auth_auto_create_user = False


def _step1_snapshot(*, quote_number: str = "Q21863") -> dict:
    return {
        "quote_number": quote_number,
        "job_number": "JOB-001",
        "client_name": "Atkinson McLeod",
        "trade_name": "Painter",
        "property_address": "1 Test Street",
    }


def _breakdown() -> CalculationBreakdown:
    return CalculationBreakdown(
        labour=[LineBreakdown(label="Labour", formula="day", total=Decimal("800"))],
        materials=[LineBreakdown(label="Materials", formula="qty", total=Decimal("200"))],
        charges=[],
        subtotal=Decimal("1000"),
        vat_rate=Decimal("20"),
        vat_total=Decimal("200"),
        final_total=Decimal("1200"),
        formula_version="1.0.0",
    )


def _accepted_session(session: CalculationSession) -> None:
    now = datetime.now(timezone.utc)
    session.client_accepted_at = now
    session.client_acceptance_name = "Jane Client"
    session.client_acceptance_email = "client@example.com"
    session.client_acceptance_notes = "Ready to proceed"
    session.public_quote_token = "public-token-value"
    session.status = "submitted"
    session.submitted_at = now


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
    row = CalculationSession(
        id=submitted_id,
        session_token="session-token-secret-value",
        source="test",
        payload_snapshot={"quote_number": "Q21863"},
        step1_snapshot=_step1_snapshot(),
        step2_snapshot={"works": []},
        ui_state={"last_result": {"breakdown": _breakdown().model_dump(mode="json")}},
        expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
        status="submitted",
        submitted_at=now,
    )
    _accepted_session(row)
    session.add(row)
    session.commit()
    yield session, submitted_id
    session.close()


@pytest.fixture()
def sync_client(db_session):
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


def test_resolve_eworks_quote_id_from_q_prefix():
    session = CalculationSession(
        id=uuid4(),
        session_token="token",
        source="test",
        payload_snapshot={},
        step1_snapshot=_step1_snapshot(quote_number="Q21863"),
        expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
    )
    assert resolve_eworks_quote_id(session) == 21863


def test_resolve_eworks_quote_id_from_numeric():
    session = CalculationSession(
        id=uuid4(),
        session_token="token",
        source="test",
        payload_snapshot={},
        step1_snapshot=_step1_snapshot(quote_number="21863"),
        expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
    )
    assert resolve_eworks_quote_id(session) == 21863


def test_build_acceptance_sync_text_excludes_secrets():
    session = CalculationSession(
        id=uuid4(),
        session_token="session-token-secret-value",
        source="test",
        payload_snapshot={},
        step1_snapshot=_step1_snapshot(),
        expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
        public_quote_token="public-token-secret",
    )
    _accepted_session(session)
    text = build_acceptance_sync_text(session)
    assert "session-token-secret-value" not in text
    assert "Jane Client" in text
    assert "Q21863" in text


def test_redact_sync_record_removes_sensitive_keys():
    payload = {
        "cf_data": {"txtar_45": "accepted"},
        "api_key": "secret-key",
        "session_token": "abc",
    }
    redacted = redact_sync_record(payload)
    assert redacted["api_key"] == "***REDACTED***"
    assert redacted["session_token"] == "***REDACTED***"


@patch("app.services.eworks_acceptance_sync_service.settings")
def test_sync_skipped_when_disabled(mock_settings, db_session):
    session, submitted_id = db_session
    mock_settings.eworks_acceptance_sync_enabled = False
    mock_settings.eworks_acceptance_sync_mode = "custom_field"

    row = session.get(CalculationSession, submitted_id)
    status = sync_quote_acceptance_to_eworks(session, row)
    assert status == SYNC_SKIPPED
    assert row.eworks_acceptance_sync_error == "Acceptance sync disabled"


@patch("app.services.eworks_acceptance_sync_service.settings")
def test_sync_failed_when_eworks_raises(mock_settings, db_session):
    session, submitted_id = db_session
    mock_settings.eworks_acceptance_sync_enabled = True
    mock_settings.eworks_acceptance_sync_mode = "custom_field"
    mock_settings.eworks_api_enabled = True
    mock_settings.eworks_acceptance_custom_field_key = "txtar_45"
    mock_settings.frontend_url = "http://localhost:3000"

    row = session.get(CalculationSession, submitted_id)
    with patch(
        "app.services.eworks_acceptance_sync_service.update_quote_custom_field",
        side_effect=Exception("eWorks unavailable"),
    ):
        status = sync_quote_acceptance_to_eworks(session, row)

    assert status == SYNC_FAILED
    assert "eWorks unavailable" in (row.eworks_acceptance_sync_error or "")
    assert row.client_accepted_at is not None
    assert "session-token-secret-value" not in (row.eworks_acceptance_sync_error or "")


@patch("app.services.eworks_acceptance_sync_service.settings")
def test_sync_success_updates_status(mock_settings, db_session):
    session, submitted_id = db_session
    mock_settings.eworks_acceptance_sync_enabled = True
    mock_settings.eworks_acceptance_sync_mode = "custom_field"
    mock_settings.eworks_api_enabled = True
    mock_settings.eworks_acceptance_custom_field_key = "txtar_45"
    mock_settings.frontend_url = None

    row = session.get(CalculationSession, submitted_id)
    with patch(
        "app.services.eworks_acceptance_sync_service.update_quote_custom_field",
        return_value={"status": 1},
    ):
        status = sync_quote_acceptance_to_eworks(session, row)

    assert status == SYNC_SUCCESS
    assert row.eworks_acceptance_synced_at is not None
    assert row.eworks_acceptance_sync_error is None
    assert row.eworks_acceptance_last_payload is not None
    assert "api_key" not in str(row.eworks_acceptance_last_payload)


@patch("app.services.eworks_acceptance_sync_service.settings")
def test_repeat_sync_not_triggered_when_already_success(mock_settings, db_session):
    session, submitted_id = db_session
    mock_settings.eworks_acceptance_sync_enabled = True
    mock_settings.eworks_acceptance_sync_mode = "custom_field"

    row = session.get(CalculationSession, submitted_id)
    row.eworks_acceptance_sync_status = SYNC_SUCCESS
    session.commit()

    with patch("app.services.eworks_acceptance_sync_service.update_quote_custom_field") as mock_update:
        status = sync_quote_acceptance_to_eworks(session, row)
        mock_update.assert_not_called()
    assert status == SYNC_SUCCESS


@patch("app.services.client_quote_service._get_breakdown_and_works")
@patch("app.services.eworks_acceptance_sync_service.settings")
def test_client_accept_succeeds_when_sync_disabled(
    mock_settings, mock_breakdown, sync_client, db_session
):
    from app.schemas.eworks_link import Step1Snapshot, Step2Snapshot

    session, submitted_id = db_session
    row = session.get(CalculationSession, submitted_id)
    row.client_accepted_at = None
    row.client_acceptance_name = None
    row.client_acceptance_email = None
    session.commit()

    mock_settings.eworks_acceptance_sync_enabled = False
    mock_breakdown.return_value = (
        _breakdown(),
        Step1Snapshot.model_validate(_step1_snapshot()),
        Step2Snapshot.model_validate({"works": []}),
        [],
    )
    link = create_or_get_public_link(session, submitted_id)
    session.commit()

    response = sync_client.post(
        f"/api/v1/client-quotes/public/{link.public_token}/accept",
        json={"name": "Jane Client", "email": "client@example.com"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["accepted"] is True
    assert "eworks" not in response.text.lower()
    assert "sync_status" not in response.text.lower()

    row = session.get(CalculationSession, submitted_id)
    assert row.client_accepted_at is not None
    assert row.eworks_acceptance_sync_status == SYNC_SKIPPED


@patch("app.services.client_quote_service._get_breakdown_and_works")
@patch("app.services.eworks_acceptance_sync_service.settings")
def test_client_accept_succeeds_when_sync_raises(
    mock_settings, mock_breakdown, sync_client, db_session
):
    from app.schemas.eworks_link import Step1Snapshot, Step2Snapshot

    session, submitted_id = db_session
    row = session.get(CalculationSession, submitted_id)
    row.client_accepted_at = None
    row.client_acceptance_name = None
    row.client_acceptance_email = None
    session.commit()

    mock_settings.eworks_acceptance_sync_enabled = True
    mock_settings.eworks_acceptance_sync_mode = "custom_field"
    mock_settings.eworks_api_enabled = True
    mock_settings.eworks_acceptance_custom_field_key = "txtar_45"
    mock_settings.frontend_url = None
    mock_breakdown.return_value = (
        _breakdown(),
        Step1Snapshot.model_validate(_step1_snapshot()),
        Step2Snapshot.model_validate({"works": []}),
        [],
    )
    link = create_or_get_public_link(session, submitted_id)
    session.commit()

    with patch(
        "app.services.eworks_acceptance_sync_service.update_quote_custom_field",
        side_effect=Exception("eWorks down"),
    ):
        response = sync_client.post(
            f"/api/v1/client-quotes/public/{link.public_token}/accept",
            json={"name": "Jane Client", "email": "client@example.com"},
        )

    assert response.status_code == 200
    row = session.get(CalculationSession, submitted_id)
    assert row.client_accepted_at is not None
    assert row.eworks_acceptance_sync_status == SYNC_FAILED


@patch("app.auth.dependencies.settings")
def test_manager_can_retry_sync(mock_settings, sync_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    session, submitted_id = db_session
    row = session.get(CalculationSession, submitted_id)
    row.eworks_acceptance_sync_status = SYNC_FAILED
    row.eworks_acceptance_sync_error = "Previous failure"
    session.commit()

    with patch(
        "app.services.eworks_acceptance_sync_service.update_quote_custom_field",
        return_value={"status": 1},
    ), patch("app.services.eworks_acceptance_sync_service.settings") as sync_settings:
        sync_settings.eworks_acceptance_sync_enabled = True
        sync_settings.eworks_acceptance_sync_mode = "custom_field"
        sync_settings.eworks_api_enabled = True
        sync_settings.eworks_acceptance_custom_field_key = "txtar_45"
        sync_settings.frontend_url = None
        response = sync_client.post(f"/api/v1/client-quotes/{submitted_id}/sync-acceptance-eworks")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == SYNC_SUCCESS


@patch("app.auth.dependencies.settings")
@pytest.mark.parametrize("role", ["estimator", "engineer", "client"])
def test_non_manager_admin_blocked_from_retry(mock_settings, sync_client, db_session, role):
    _patch_dev_user(mock_settings, role=role)
    _, submitted_id = db_session
    response = sync_client.post(f"/api/v1/client-quotes/{submitted_id}/sync-acceptance-eworks")
    assert response.status_code == 403


@patch("app.auth.dependencies.settings")
def test_retry_blocked_when_quote_not_accepted(mock_settings, sync_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    session, submitted_id = db_session
    row = session.get(CalculationSession, submitted_id)
    row.client_accepted_at = None
    row.client_acceptance_name = None
    row.client_acceptance_email = None
    session.commit()

    response = sync_client.post(f"/api/v1/client-quotes/{submitted_id}/sync-acceptance-eworks")
    assert response.status_code == 400


@patch("app.auth.dependencies.settings")
@patch("app.services.calculation_session_service._dashboard_last_result")
def test_manager_review_includes_eworks_sync_status(mock_last_result, mock_settings, sync_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    session, submitted_id = db_session
    row = session.get(CalculationSession, submitted_id)
    row.eworks_acceptance_sync_status = SYNC_FAILED
    row.eworks_acceptance_sync_error = "eWorks unavailable"
    session.commit()

    mock_last_result.return_value = {
        "breakdown": _breakdown().model_dump(mode="json"),
        "work_breakdowns": [],
    }

    response = sync_client.get("/api/v1/dashboard/quotes")
    assert response.status_code == 200
    acceptance = response.json()["data"]["quotes"][0]["acceptance"]
    assert acceptance["eworks_sync"]["status"] == SYNC_FAILED
    assert acceptance["eworks_sync"]["error"] == "eWorks unavailable"
    assert "api_key" not in str(acceptance["eworks_sync"])


@patch("app.services.eworks_acceptance_sync_service.settings")
def test_sync_creates_audit_event_on_failure(mock_settings, db_session):
    session, submitted_id = db_session
    mock_settings.eworks_acceptance_sync_enabled = True
    mock_settings.eworks_acceptance_sync_mode = "custom_field"
    mock_settings.eworks_api_enabled = True
    mock_settings.eworks_acceptance_custom_field_key = "txtar_45"
    mock_settings.frontend_url = None

    row = session.get(CalculationSession, submitted_id)
    with patch(
        "app.services.eworks_acceptance_sync_service.update_quote_custom_field",
        side_effect=Exception("network error"),
    ):
        sync_quote_acceptance_to_eworks(session, row)

    logs = session.scalars(select(AuditLog).where(AuditLog.action == "eworks_acceptance_sync_failed")).all()
    assert len(logs) >= 1
    assert "session-token-secret-value" not in str(logs[0].new_value)
