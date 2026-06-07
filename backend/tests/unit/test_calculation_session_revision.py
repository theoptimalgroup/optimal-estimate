"""Tests for self-service estimate revision and version history."""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import patch as mock_patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.session import get_db
from app.main import app
from app.models.calculation_session import CalculationSession
from app.models.calculation_session_version import CalculationSessionVersion
from app.models.client import Client
from app.models.client_alias import ClientAlias
from app.models.rate_rule import RateRule
from app.models.trade import Trade
from tests.integration.test_eworks_calculation_session import (
    TEST_SECRET,
    _alex_work_block,
    _base_payload,
    _make_lambert_carpenter_rule,
    make_signed_payload,
)
from tests.test_db import make_test_session


@pytest.fixture()
def revision_api_client(monkeypatch):
    monkeypatch.setattr(settings, "eworks_link_secret", TEST_SECRET)
    monkeypatch.setattr(settings, "eworks_link_sig_required", True)
    monkeypatch.setattr(settings, "dashboard_password", "revision-test-password")

    session, _ = make_test_session()
    client = Client(id=uuid.uuid4(), name="Lamberts Chartered Surveyors", default_vat_rate=Decimal("20"))
    alias = ClientAlias(id=uuid.uuid4(), client_id=client.id, alias_name="Lambert Chartered Surveyors")
    trade = Trade(id=uuid.uuid4(), name="Carpenter")
    rule = _make_lambert_carpenter_rule(client.id, trade.id)
    session.add_all([client, alias, trade, rule])
    session.commit()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client, session
    app.dependency_overrides.clear()
    session.close()


def _create_submitted_session(revision_api_client, *, scope: str = "Initial scope") -> tuple[str, str, object]:
    test_client, db_session = revision_api_client
    payload_b64, sig = make_signed_payload(_base_payload())
    created = test_client.post("/api/v1/calculation-session/from-link", json={"payload": payload_b64, "sig": sig})
    assert created.status_code == 200
    session_id = created.json()["data"]["session_id"]
    token = created.json()["data"]["session_token"]
    step2 = {"works": [_alex_work_block(scope=scope)], "congestion_required": True, "congestion_amount": 18}
    submit = test_client.post(
        f"/api/v1/calculation-session/{session_id}/submit",
        headers={"X-Session-Token": token},
        json={"step2": step2},
    )
    assert submit.status_code == 200
    db_session.expire_all()
    return session_id, token, db_session


def test_submitted_session_is_locked_with_version_one(revision_api_client):
    session_id, token, db_session = _create_submitted_session(revision_api_client)
    test_client, _ = revision_api_client
    session = db_session.get(CalculationSession, uuid.UUID(session_id))
    assert session is not None
    assert session.status == "submitted"
    assert session.locked is True
    assert session.current_version_number == 1

    versions = db_session.query(CalculationSessionVersion).filter_by(session_id=session.id).all()
    assert len(versions) == 1
    assert versions[0].version_number == 1
    assert versions[0].is_current is True
    assert versions[0].revision_reason is None

    patch_resp = test_client.patch(
        f"/api/v1/calculation-session/{session_id}",
        headers={"X-Session-Token": token},
        json={"step2": {"works": [_alex_work_block(scope="Blocked edit")]}},
    )
    assert patch_resp.status_code == 409


def test_revise_requires_reason(revision_api_client):
    session_id, token, _ = _create_submitted_session(revision_api_client)
    test_client, _ = revision_api_client
    response = test_client.post(
        f"/api/v1/calculation-session/{session_id}/revise",
        headers={"X-Session-Token": token},
        json={"reason": "   "},
    )
    assert response.status_code == 400


def test_owner_can_start_revision_and_resubmit_new_version(revision_api_client):
    session_id, token, db_session = _create_submitted_session(revision_api_client, scope="Version one scope")
    test_client, _ = revision_api_client
    revise = test_client.post(
        f"/api/v1/calculation-session/{session_id}/revise",
        headers={"X-Session-Token": token},
        json={"reason": "Client requested scope change"},
    )
    assert revise.status_code == 200
    data = revise.json()["data"]
    assert data["revision_in_progress"] is True
    assert "session_token" not in data
    assert data["active_revision_reason"] == "Client requested scope change"

    db_session.expire_all()
    session = db_session.get(CalculationSession, uuid.UUID(session_id))
    assert session.revision_in_progress is True
    assert session.locked is False

    resubmit = test_client.post(
        f"/api/v1/calculation-session/{session_id}/submit",
        headers={"X-Session-Token": token},
        json={
            "step2": {
                "works": [_alex_work_block(scope="Version two scope")],
                "congestion_required": True,
                "congestion_amount": 18,
            }
        },
    )
    assert resubmit.status_code == 200
    submit_data = resubmit.json()["data"]
    assert submit_data["version_number"] == 2
    assert submit_data["revision"] is True

    db_session.expire_all()
    versions = (
        db_session.query(CalculationSessionVersion)
        .filter_by(session_id=uuid.UUID(session_id))
        .order_by(CalculationSessionVersion.version_number)
        .all()
    )
    assert len(versions) == 2
    assert versions[0].step2_snapshot["works"][0]["scope"] == "Version one scope"
    assert versions[1].step2_snapshot["works"][0]["scope"] == "Version two scope"
    assert versions[1].revision_reason == "Client requested scope change"
    assert versions[1].is_current is True
    assert versions[0].is_current is False


def test_non_owner_token_blocked_from_revision(revision_api_client):
    session_id, _token, _ = _create_submitted_session(revision_api_client)
    test_client, _ = revision_api_client
    other = test_client.post("/api/v1/calculation-session/dev-bootstrap")
    assert other.status_code == 200
    wrong_token = other.json()["data"]["session_token"]
    response = test_client.post(
        f"/api/v1/calculation-session/{session_id}/revise",
        headers={"X-Session-Token": wrong_token},
        json={"reason": "Should fail"},
    )
    assert response.status_code in {401, 403, 404}


def test_manager_can_view_version_history_without_tokens(revision_api_client):
    session_id, token, _ = _create_submitted_session(revision_api_client)
    test_client, _ = revision_api_client
    test_client.post(
        f"/api/v1/calculation-session/{session_id}/revise",
        headers={"X-Session-Token": token},
        json={"reason": "Updated materials"},
    )
    test_client.post(
        f"/api/v1/calculation-session/{session_id}/submit",
        headers={"X-Session-Token": token},
        json={
            "step2": {
                "works": [_alex_work_block(scope="Revised scope")],
                "congestion_required": True,
                "congestion_amount": 18,
            }
        },
    )

    response = test_client.get(
        f"/api/v1/dashboard/quotes/{session_id}/versions",
        headers={"X-Dashboard-Password": "revision-test-password"},
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["current_version_number"] == 2
    assert len(payload["versions"]) == 2
    assert "session_token" not in payload
    for version in payload["versions"]:
        assert "calculation_result" not in version
        assert "step1_snapshot" not in version
        if version["version_number"] == 2:
            assert version["revision_reason"] == "Updated materials"


def test_manager_pdf_service_applies_version_snapshot(revision_api_client):
    from unittest.mock import patch as mock_patch

    from app.services.manager_quote_pdf_service import render_manager_quote_pdf

    session_id, token, db_session = _create_submitted_session(revision_api_client, scope="Version one scope")
    test_client, _ = revision_api_client
    test_client.post(
        f"/api/v1/calculation-session/{session_id}/revise",
        headers={"X-Session-Token": token},
        json={"reason": "Pricing update"},
    )
    test_client.post(
        f"/api/v1/calculation-session/{session_id}/submit",
        headers={"X-Session-Token": token},
        json={
            "step2": {
                "works": [_alex_work_block(scope="Version two scope")],
                "congestion_required": True,
                "congestion_amount": 18,
            }
        },
    )

    versions = (
        db_session.query(CalculationSessionVersion)
        .filter_by(session_id=uuid.UUID(session_id))
        .order_by(CalculationSessionVersion.version_number)
        .all()
    )
    assert versions[0].step2_snapshot["works"][0]["scope"] == "Version one scope"

    with mock_patch("app.services.manager_quote_pdf_service.render_combined_works_pdf") as mock_render:
        mock_render.return_value = (b"%PDF", "quote.pdf", "application/pdf")
        content, file_name, media_type = render_manager_quote_pdf(
            db_session,
            session_id=uuid.UUID(session_id),
            view="client",
            version_number=1,
        )
    assert content == b"%PDF"
    assert file_name == "quote.pdf"
    assert media_type == "application/pdf"
    assert mock_render.called
    called_session = db_session.get(CalculationSession, uuid.UUID(session_id))
    assert called_session.step2_snapshot["works"][0]["scope"] == "Version two scope"
