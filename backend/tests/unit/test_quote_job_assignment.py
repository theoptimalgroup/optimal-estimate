"""Unit tests for manager quote job assignment."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.main import app
from app.models.calculation_session import CalculationSession
from app.models.calculation_session_version import CalculationSessionVersion
from app.models.client import Client
from app.models.client_alias import ClientAlias
from app.models.eworks_sync import EworksJob, EworksQuote
from app.models.quote_assignment import EworksQuoteAssignment
from app.models.quote_job_assignment import QuoteJobAssignment
from app.models.selected_estimate_decision import SelectedEstimateDecision
from app.models.support import AuditLog
from app.models.trade import Trade
from app.models.user import User


def _patch_dev_user(mock_settings, *, role: str, email: str | None = None):
    mock_settings.auth_provider = "dev"
    mock_settings.dev_auth_enabled = True
    mock_settings.dev_user_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    mock_settings.dev_user_email = email or "staff@optimal.example"
    mock_settings.dev_user_name = "Staff User"
    mock_settings.dev_user_role = role
    mock_settings.dev_user_is_active = True
    mock_settings.dev_auth_auto_create_user = False


def _step1(*, quote_number: str, external_job_id: str | None = None) -> dict:
    return {
        "quote_number": quote_number,
        "job_number": external_job_id or "JOB-001",
        "external_job_id": external_job_id,
        "client_name": "ACME Ltd",
        "trade_name": "Carpenter",
        "property_address": "1 Test Street",
    }


def _ui_state(final_total: str, *, vat_rate: str = "20") -> dict:
    return {
        "current_step": 3,
        "max_reachable_step": 3,
        "last_result": {
            "breakdown": {
                "final_total": final_total,
                "labour": [{"total": "100.00"}],
                "materials": [{"total": "20.00"}],
                "charges": [
                    {"label": "Parking", "total": "5.00"},
                    {"label": "Congestion", "total": "0"},
                    {"label": "Travel", "total": "0"},
                    {"label": "Other", "total": "0"},
                    {"label": "ULEZ", "total": "99.00"},
                    {"label": "Waste Disposal", "total": "50.00"},
                ],
                "vat_total": "24.00",
                "vat_rate": vat_rate,
            },
            "work_breakdowns": [
                {
                    "work_index": 0,
                    "breakdown": {
                        "final_total": final_total,
                        "labour": [{"total": "100.00"}],
                        "materials": [{"total": "20.00"}],
                    },
                }
            ],
        },
    }


@pytest.fixture()
def assign_db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for model in (
        User,
        Client,
        ClientAlias,
        Trade,
        CalculationSession,
        CalculationSessionVersion,
        AuditLog,
        EworksQuote,
        EworksJob,
        EworksQuoteAssignment,
        QuoteJobAssignment,
        SelectedEstimateDecision,
    ):
        model.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    manager_id = uuid4()
    engineer_id = uuid4()
    session.add_all(
        [
            User(
                id=manager_id,
                email="manager@example.com",
                full_name="Manager User",
                password_hash="hash",
                role="manager",
                is_active=True,
            ),
            User(
                id=engineer_id,
                email="rohit@example.com",
                full_name="Rohit",
                password_hash="hash",
                role="engineer",
                is_active=True,
            ),
        ]
    )
    session.flush()

    client = Client(name="ACME Ltd", default_vat_rate=Decimal("20"))
    trade = Trade(name="Carpenter", is_active=True)
    session.add_all([client, trade])
    session.flush()

    session_a = uuid4()
    session_b = uuid4()
    session.add_all(
        [
            CalculationSession(
                id=session_a,
                session_token="token-a",
                source="test",
                payload_snapshot={"eworks_quote_id": 29204, "assignment_id": 1},
                step1_snapshot=_step1(quote_number="Q22100", external_job_id="29204"),
                step2_snapshot={"works": [{"scope": "First submission", "product_code": "P-001"}]},
                ui_state=_ui_state("100.00"),
                client_id=client.id,
                trade_id=trade.id,
                expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
                status="submitted",
                submitted_at=datetime(2026, 6, 5, 15, 48, tzinfo=timezone.utc),
            ),
            CalculationSession(
                id=session_b,
                session_token="token-b",
                source="test",
                payload_snapshot={"eworks_quote_id": 29204},
                step1_snapshot=_step1(quote_number="Q22100", external_job_id="29204"),
                step2_snapshot={"works": [{"scope": "Second submission"}]},
                ui_state=_ui_state("174.24"),
                client_id=client.id,
                trade_id=trade.id,
                expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
                status="submitted",
                submitted_at=datetime(2026, 6, 5, 16, 4, tzinfo=timezone.utc),
            ),
        ]
    )
    session.flush()

    synced_quote = EworksQuote(eworks_quote_id=29204, quote_ref="Q22100", customer_name="ACME Ltd")
    session.add(synced_quote)
    session.flush()

    assignment = EworksQuoteAssignment(
        id=1,
        synced_quote_id=synced_quote.id,
        eworks_quote_id=29204,
        quote_ref="Q22100",
        assigned_user_id=engineer_id,
        assigned_user_email="rohit@example.com",
        assigned_user_name="Rohit",
        assignment_type="engineer",
        assignee_kind="registered",
        status="submitted",
        calculation_session_id=session_a,
        assignment_token="secret-token",
    )
    session.add(assignment)
    session.commit()

    yield session, session_a, session_b, assignment
    session.close()


@pytest.fixture()
def assign_api_client(assign_db_session):
    db_session, *_ = assign_db_session

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@patch("app.auth.dependencies.settings")
def test_manager_can_assign_job(mock_settings, assign_api_client, assign_db_session):
    _patch_dev_user(mock_settings, role="manager")
    _, session_a, _, assignment = assign_db_session

    response = assign_api_client.post(
        "/api/v1/manager/quotes/Q22100/assign-job",
        json={
            "selected_session_id": str(session_a),
            "assignee_name": "Rohit",
            "assignee_email": "rohit@example.com",
            "assignment_id": assignment.id,
        },
    )
    assert response.status_code == 200
    decision = response.json()["data"]["selected_estimate"]
    assert decision["selected_assignee_name"] == "Rohit"
    assert decision["selected_session_id"] == str(session_a)


@patch("app.auth.dependencies.settings")
def test_admin_can_assign_job(mock_settings, assign_api_client, assign_db_session):
    _patch_dev_user(mock_settings, role="admin")
    _, session_a, _, _ = assign_db_session

    response = assign_api_client.post(
        "/api/v1/manager/quotes/Q22100/assign-job",
        json={
            "selected_session_id": str(session_a),
            "assignee_name": "Rohit",
            "assignee_email": "rohit@example.com",
        },
    )
    assert response.status_code == 200


@pytest.mark.parametrize("role", ["estimator", "engineer", "client"])
@patch("app.auth.dependencies.settings")
def test_non_manager_roles_blocked_from_assign_job(mock_settings, assign_api_client, assign_db_session, role):
    _patch_dev_user(mock_settings, role=role)
    _, session_a, _, _ = assign_db_session

    response = assign_api_client.post(
        "/api/v1/manager/quotes/Q22100/assign-job",
        json={
            "selected_session_id": str(session_a),
            "assignee_name": "Rohit",
        },
    )
    assert response.status_code == 403


@patch("app.auth.dependencies.settings")
def test_assign_job_rejects_non_submitted_session(mock_settings, assign_api_client, assign_db_session):
    _patch_dev_user(mock_settings, role="manager")
    db_session, session_a, _, _ = assign_db_session
    row = db_session.get(CalculationSession, session_a)
    row.status = "in_progress"
    db_session.commit()

    response = assign_api_client.post(
        "/api/v1/manager/quotes/Q22100/assign-job",
        json={
            "selected_session_id": str(session_a),
            "assignee_name": "Rohit",
        },
    )
    assert response.status_code == 400


@patch("app.auth.dependencies.settings")
def test_assign_job_updates_existing_decision(mock_settings, assign_api_client, assign_db_session):
    _patch_dev_user(mock_settings, role="manager")
    db_session, session_a, session_b, assignment = assign_db_session

    first = assign_api_client.post(
        "/api/v1/manager/quotes/Q22100/assign-job",
        json={
            "selected_session_id": str(session_a),
            "assignee_name": "Rohit",
            "assignee_email": "rohit@example.com",
            "assignment_id": assignment.id,
        },
    )
    assert first.status_code == 200
    first_id = first.json()["data"]["selected_estimate"]["id"]

    second = assign_api_client.post(
        "/api/v1/manager/quotes/Q22100/assign-job",
        json={
            "selected_session_id": str(session_b),
            "assignee_name": "Other Assignee",
            "assignee_email": "other@example.com",
        },
    )
    assert second.status_code == 200
    second_id = second.json()["data"]["selected_estimate"]["id"]
    assert second_id == first_id
    assert db_session.query(SelectedEstimateDecision).count() == 1


@patch("app.auth.dependencies.settings")
def test_assign_job_creates_audit_event(mock_settings, assign_api_client, assign_db_session):
    _patch_dev_user(mock_settings, role="manager")
    db_session, session_a, _, _ = assign_db_session

    response = assign_api_client.post(
        "/api/v1/manager/quotes/Q22100/assign-job",
        json={
            "selected_session_id": str(session_a),
            "assignee_name": "Rohit",
        },
    )
    assert response.status_code == 200

    audit = db_session.query(AuditLog).filter(AuditLog.action == "quote_estimate_selected").one()
    assert audit.entity_type == "selected_estimate_decision"
    assert audit.new_value is not None
    assert "session_token" not in (audit.new_value or {})
    assert "assignment_token" not in (audit.new_value or {})


@patch("app.auth.dependencies.settings")
def test_assign_job_response_excludes_tokens(mock_settings, assign_api_client, assign_db_session):
    _patch_dev_user(mock_settings, role="manager")
    _, session_a, _, _ = assign_db_session

    response = assign_api_client.post(
        "/api/v1/manager/quotes/Q22100/assign-job",
        json={
            "selected_session_id": str(session_a),
            "assignee_name": "Rohit",
        },
    )
    body = response.text
    assert response.status_code == 200
    assert "session_token" not in body
    assert "assignment_token" not in body
    assert "raw_payload" not in body
    assert "secret-token" not in body


@patch("app.auth.dependencies.settings")
def test_group_detail_includes_selected_estimate_decision(mock_settings, assign_api_client, assign_db_session):
    _patch_dev_user(mock_settings, role="manager")
    _, session_a, _, assignment = assign_db_session

    assign_api_client.post(
        "/api/v1/manager/quotes/Q22100/assign-job",
        json={
            "selected_session_id": str(session_a),
            "assignee_name": "Rohit",
            "assignee_email": "rohit@example.com",
            "assignment_id": assignment.id,
        },
    )

    response = assign_api_client.get("/api/v1/dashboard/quote-groups/detail", params={"quote_ref": "Q22100"})
    assert response.status_code == 200
    group = response.json()["data"]["group"]
    assert group["selected_estimate_decision"]["assignee_name"] == "Rohit"
    assigned_rows = [row for row in group["assignment_submissions"] if row["is_selected_estimate"]]
    assert len(assigned_rows) == 1
    assert assigned_rows[0]["linked_session_id"] == str(session_a)
    assert assigned_rows[0]["can_select_estimate"] is True
    assert assigned_rows[0]["comparison_summary"] is not None
    assert "session_token" not in response.text


@patch("app.auth.dependencies.settings")
def test_group_detail_comparison_summary_excludes_secrets(mock_settings, assign_api_client, assign_db_session):
    _patch_dev_user(mock_settings, role="manager")
    response = assign_api_client.get("/api/v1/dashboard/quote-groups/detail", params={"quote_ref": "Q22100"})
    body = response.text
    for forbidden in ("profit", "margin", "denominator", "formula", "session_token", "raw_payload"):
        assert forbidden not in body


@patch("app.auth.dependencies.settings")
def test_group_detail_comparison_summary_has_breakdown(mock_settings, assign_api_client, assign_db_session):
    _patch_dev_user(mock_settings, role="manager")
    _, session_a, _, _ = assign_db_session
    response = assign_api_client.get("/api/v1/dashboard/quote-groups/detail", params={"quote_ref": "Q22100"})
    assert response.status_code == 200
    rows = response.json()["data"]["group"]["assignment_submissions"]
    submitted_rows = [row for row in rows if row["comparison_summary"] is not None]
    assert len(submitted_rows) >= 2

    summary = next(row["comparison_summary"] for row in submitted_rows if row["linked_session_id"] == str(session_a))
    assert summary["final_total"] == "100.00"
    assert summary["works_subtotal"] == "120.00"
    assert summary["labour_subtotal"] == "100.00"
    assert summary["materials_subtotal"] == "20.00"
    assert summary["additional_charges_total"] == "5.00"
    assert summary["vat_total"] == "24.00"
    assert summary["vat_rate"] == "20"
    assert len(summary["works"]) == 1
    assert summary["works"][0]["product_code"] == "P-001"
    assert summary["works"][0]["work_subtotal"] == "120.00"

    charge_labels = [line["label"] for line in summary["additional_charges"]]
    assert charge_labels == ["Parking", "Congestion", "Travel", "Other"]
    assert summary["additional_charges"][0]["amount"] == "5.00"
    assert summary["additional_charges"][1]["amount"] == "0"
    assert "ULEZ" not in response.text
    assert "Waste Disposal" not in response.text


@patch("app.auth.dependencies.settings")
def test_select_estimate_does_not_create_engineer_assigned_job(mock_settings, assign_api_client, assign_db_session):
    _, session_a, _, assignment = assign_db_session

    _patch_dev_user(mock_settings, role="manager")
    assign_resp = assign_api_client.post(
        "/api/v1/manager/quotes/Q22100/select-estimate",
        json={
            "selected_session_id": str(session_a),
            "assignee_name": "Rohit",
            "assignee_email": "rohit@example.com",
            "assignment_id": assignment.id,
        },
    )
    assert assign_resp.status_code == 200

    _patch_dev_user(mock_settings, role="engineer", email="rohit@example.com")
    response = assign_api_client.get("/api/v1/engineer/jobs/assigned")
    assert response.status_code == 200
    assert response.json()["data"] == []


@patch("app.auth.dependencies.settings")
def test_engineer_lists_eworks_assigned_jobs(mock_settings, assign_api_client, assign_db_session):
    db_session, _, _, _ = assign_db_session
    db_session.add(
        EworksJob(
            eworks_job_id=29226,
            job_ref="29226",
            eworks_quote_id=29204,
            customer_name="Douglas & Gordon",
            address="1 High Street",
            status_name="Assigned",
            raw_payload={"engineer": "rohit@example.com"},
        )
    )
    db_session.commit()

    _patch_dev_user(mock_settings, role="engineer", email="rohit@example.com")
    response = assign_api_client.get("/api/v1/engineer/jobs/assigned")
    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 1
    assert items[0]["eworks_job_id"] == 29226
    assert items[0]["customer_name"] == "Douglas & Gordon"
    assert "selected_session_id" not in items[0]
    assert "selected_estimate_total" not in items[0]


@patch("app.auth.dependencies.settings")
def test_engineer_does_not_see_other_engineers_eworks_jobs(mock_settings, assign_api_client, assign_db_session):
    db_session, _, _, _ = assign_db_session
    db_session.add(
        EworksJob(
            eworks_job_id=29227,
            job_ref="29227",
            customer_name="Other Client",
            raw_payload={"engineer": "other@example.com"},
        )
    )
    db_session.commit()

    _patch_dev_user(mock_settings, role="engineer", email="rohit@example.com")
    response = assign_api_client.get("/api/v1/engineer/jobs/assigned")
    assert response.status_code == 200
    assert response.json()["data"] == []


@patch("app.auth.dependencies.settings")
def test_manager_can_select_estimate_via_primary_endpoint(mock_settings, assign_api_client, assign_db_session):
    _patch_dev_user(mock_settings, role="manager")
    _, session_a, _, assignment = assign_db_session

    response = assign_api_client.post(
        "/api/v1/manager/quotes/Q22100/select-estimate",
        json={
            "selected_session_id": str(session_a),
            "selected_assignment_id": assignment.id,
        },
    )
    assert response.status_code == 200
    selected = response.json()["data"]["selected_estimate"]
    assert selected["selected_session_id"] == str(session_a)
    assert selected["selected_assignee_name"]


@patch("app.auth.dependencies.settings")
def test_engineer_assigned_jobs_unauthenticated_blocked(mock_settings, assign_api_client):
    mock_settings.auth_provider = "dev"
    mock_settings.dev_auth_enabled = False
    response = assign_api_client.get("/api/v1/engineer/jobs/assigned")
    assert response.status_code == 401


@patch("app.auth.dependencies.settings")
def test_engineer_assigned_jobs_response_excludes_tokens(mock_settings, assign_api_client, assign_db_session):
    _patch_dev_user(mock_settings, role="manager")
    _, session_a, _, assignment = assign_db_session

    assign_api_client.post(
        "/api/v1/manager/quotes/Q22100/select-estimate",
        json={
            "selected_session_id": str(session_a),
            "assignee_name": "Rohit",
            "assignee_email": "rohit@example.com",
            "assignment_id": assignment.id,
        },
    )

    _patch_dev_user(mock_settings, role="engineer", email="rohit@example.com")
    response = assign_api_client.get("/api/v1/engineer/jobs/assigned")
    body = response.text
    assert response.status_code == 200
    assert response.json()["data"] == []
    for forbidden in ("session_token", "assignment_token", "raw_payload", "profit", "margin", "formula", "denominator"):
        assert forbidden not in body
