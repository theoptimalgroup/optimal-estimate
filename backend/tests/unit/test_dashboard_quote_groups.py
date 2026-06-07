"""Unit tests for grouped manager quote review dashboard APIs."""

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
from app.models.eworks_sync import EworksQuote
from app.models.quote_assignment import EworksQuoteAssignment
from app.models.quote_job_assignment import QuoteJobAssignment
from app.models.support import AuditLog
from app.models.trade import Trade
from app.models.user import User


def _patch_dev_user(mock_settings, *, role: str, enabled: bool = True):
    mock_settings.auth_provider = "dev"
    mock_settings.dev_auth_enabled = enabled
    mock_settings.dev_user_id = "dev-user-1"
    mock_settings.dev_user_email = "staff@optimal.example"
    mock_settings.dev_user_name = "Staff User"
    mock_settings.dev_user_role = role
    mock_settings.dev_user_is_active = True
    mock_settings.dev_auth_auto_create_user = False
    mock_settings.dashboard_password = "test-dashboard-pass"


def _step1(*, quote_number: str, external_job_id: str | None = None) -> dict:
    return {
        "quote_number": quote_number,
        "job_number": external_job_id or "JOB-001",
        "external_job_id": external_job_id,
        "client_name": "ACME Ltd",
        "trade_name": "Carpenter",
        "property_address": "1 Test Street",
    }


def _ui_state(final_total: str) -> dict:
    return {
        "current_step": 3,
        "max_reachable_step": 3,
        "last_result": {
            "breakdown": {"final_total": final_total},
            "work_breakdowns": [{"work_index": 0, "breakdown": {"final_total": final_total}}],
        },
    }


def _add_session_versions(
    db_session,
    calc_session: CalculationSession,
    *,
    versions: list[dict],
) -> None:
    for item in versions:
        db_session.add(
            CalculationSessionVersion(
                session_id=calc_session.id,
                version_number=item["version_number"],
                step1_snapshot=dict(calc_session.step1_snapshot or {}),
                step2_snapshot=item.get("step2_snapshot", calc_session.step2_snapshot),
                calculation_result=item.get("calculation_result", (calc_session.ui_state or {}).get("last_result")),
                submitted_at=item.get("submitted_at", calc_session.submitted_at),
                submitted_by_name=item.get("submitted_by_name", calc_session.submitted_by_name),
                submitted_by_email=item.get("submitted_by_email", calc_session.submitted_by_email),
                revision_reason=item.get("revision_reason"),
                status="submitted",
                is_current=item.get("is_current", False),
            )
        )
    calc_session.current_version_number = max(item["version_number"] for item in versions)
    calc_session.locked = True


@pytest.fixture()
def review_db_session():
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
        EworksQuoteAssignment,
        QuoteJobAssignment,
    ):
        model.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    client = Client(name="ACME Ltd", default_vat_rate=Decimal("20"))
    trade = Trade(name="Carpenter", is_active=True)
    session.add_all([client, trade])
    session.flush()

    session.add_all(
        [
            CalculationSession(
                id=uuid4(),
                session_token="token-1",
                source="test",
                payload_snapshot={"eworks_quote_id": 29204},
                step1_snapshot=_step1(quote_number="Q22100", external_job_id="29204"),
                step2_snapshot={"works": [{"scope": "First submission"}]},
                ui_state=_ui_state("0.00"),
                client_id=client.id,
                trade_id=trade.id,
                expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
                status="submitted",
                submitted_at=datetime(2026, 6, 5, 15, 48, tzinfo=timezone.utc),
            ),
            CalculationSession(
                id=uuid4(),
                session_token="token-2",
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
            CalculationSession(
                id=uuid4(),
                session_token="token-other",
                source="test",
                payload_snapshot={},
                step1_snapshot=_step1(quote_number="Q99999"),
                step2_snapshot={"works": [{"scope": "Other quote"}]},
                ui_state=_ui_state("50.00"),
                client_id=client.id,
                trade_id=trade.id,
                expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
                status="submitted",
                submitted_at=datetime(2026, 6, 4, 12, 0, tzinfo=timezone.utc),
            ),
        ]
    )
    session.commit()
    yield session
    session.close()


@pytest.fixture()
def review_api_client(review_db_session):
    def override_get_db():
        try:
            yield review_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@patch("app.auth.dependencies.settings")
def test_two_sessions_same_quote_ref_produce_one_group(mock_settings, review_api_client):
    _patch_dev_user(mock_settings, role="manager")
    response = review_api_client.get("/api/v1/dashboard/quote-groups")
    assert response.status_code == 200
    groups = response.json()["data"]["groups"]
    q22100_groups = [group for group in groups if group.get("quote_ref") == "Q22100"]
    assert len(q22100_groups) == 1
    group = q22100_groups[0]
    assert group["submission_count"] == 2
    assert group["latest_total"] == "174.24"
    assert group["highest_total"] == "174.24"
    assert group["lowest_total"] in {"0", "0.00"}
    assert group["sessions"][0]["final_total"] == "174.24"
    assert group["sessions"][1]["final_total"] in {"0", "0.00"}


@patch("app.auth.dependencies.settings")
def test_group_detail_by_quote_ref(mock_settings, review_api_client):
    _patch_dev_user(mock_settings, role="manager")
    response = review_api_client.get("/api/v1/dashboard/quote-groups/detail", params={"quote_ref": "Q22100"})
    assert response.status_code == 200
    group = response.json()["data"]["group"]
    assert group["submission_count"] == 2
    assert len(group["sessions"]) == 2


@patch("app.auth.dependencies.settings")
def test_different_quote_ref_creates_separate_groups(mock_settings, review_api_client):
    _patch_dev_user(mock_settings, role="manager")
    response = review_api_client.get("/api/v1/dashboard/quote-groups")
    quote_refs = {group["quote_ref"] for group in response.json()["data"]["groups"]}
    assert quote_refs == {"Q22100", "Q99999"}


@patch("app.auth.dependencies.settings")
def test_missing_quote_ref_groups_by_session_id(mock_settings, review_db_session, review_api_client):
    _patch_dev_user(mock_settings, role="manager")
    lone_id = uuid4()
    review_db_session.add(
        CalculationSession(
            id=lone_id,
            session_token="token-lone",
            source="test",
            payload_snapshot={},
            step1_snapshot={
                "quote_number": "",
                "job_number": "JOB-LONE",
                "client_name": "Solo Client",
                "trade_name": "Carpenter",
                "property_address": "Solo Street",
            },
            step2_snapshot={"works": []},
            ui_state=_ui_state("10.00"),
            expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
            status="submitted",
            submitted_at=datetime(2026, 6, 3, 9, 0, tzinfo=timezone.utc),
        )
    )
    review_db_session.commit()

    response = review_api_client.get("/api/v1/dashboard/quote-groups")
    group_keys = {group["group_key"] for group in response.json()["data"]["groups"]}
    assert f"session_id:{lone_id}" in group_keys


@patch("app.auth.dependencies.settings")
def test_quote_groups_response_excludes_session_token(mock_settings, review_api_client):
    _patch_dev_user(mock_settings, role="manager")
    response = review_api_client.get("/api/v1/dashboard/quote-groups")
    assert response.status_code == 200
    assert "session_token" not in response.text
    assert "raw_payload" not in response.text


@pytest.mark.parametrize("role", ["manager", "admin", "estimator"])
@patch("app.auth.dependencies.settings")
def test_staff_roles_can_access_quote_groups(mock_settings, review_api_client, role):
    _patch_dev_user(mock_settings, role=role)
    response = review_api_client.get("/api/v1/dashboard/quote-groups")
    assert response.status_code == 200


@pytest.mark.parametrize("role", ["engineer", "client"])
@patch("app.auth.dependencies.settings")
def test_engineer_and_client_blocked_from_quote_groups(mock_settings, review_api_client, role):
    _patch_dev_user(mock_settings, role=role)
    response = review_api_client.get("/api/v1/dashboard/quote-groups")
    assert response.status_code == 403


@pytest.fixture()
def review_detail_db_session(review_db_session):
    session = review_db_session
    estimator_id = uuid4()
    engineer_id = uuid4()
    session.add_all(
        [
            User(
                id=estimator_id,
                email="estimator@example.com",
                full_name="Estimator User",
                password_hash="hash",
                role="estimator",
                is_active=True,
            ),
            User(
                id=engineer_id,
                email="engineer@example.com",
                full_name="Engineer User",
                password_hash="hash",
                role="engineer",
                is_active=True,
            ),
        ]
    )
    session.flush()

    synced_quote = EworksQuote(eworks_quote_id=29204, quote_ref="Q22100", customer_name="ACME Ltd")
    session.add(synced_quote)
    session.flush()

    submitted_sessions = (
        session.query(CalculationSession)
        .filter(CalculationSession.status == "submitted")
        .order_by(CalculationSession.submitted_at.asc())
        .all()
    )
    q22100_sessions = [
        row
        for row in submitted_sessions
        if isinstance(row.step1_snapshot, dict) and row.step1_snapshot.get("quote_number") == "Q22100"
    ]
    assert len(q22100_sessions) == 2
    older_session, newer_session = q22100_sessions

    estimator_assignment = EworksQuoteAssignment(
        synced_quote_id=synced_quote.id,
        eworks_quote_id=29204,
        quote_ref="Q22100",
        assigned_user_id=estimator_id,
        assigned_user_email="estimator@example.com",
        assigned_user_name="Estimator User",
        assignment_type="estimator",
        assignee_kind="registered",
        status="assigned",
        assignment_token="secret-estimator-token",
    )
    engineer_assignment = EworksQuoteAssignment(
        synced_quote_id=synced_quote.id,
        eworks_quote_id=29204,
        quote_ref="Q22100",
        assigned_user_id=engineer_id,
        assigned_user_email="engineer@example.com",
        assigned_user_name="Engineer User",
        assignment_type="engineer",
        assignee_kind="registered",
        status="in_progress",
        calculation_session_id=older_session.id,
        assignment_token="secret-engineer-token",
    )
    external_assignment = EworksQuoteAssignment(
        synced_quote_id=synced_quote.id,
        eworks_quote_id=29204,
        quote_ref="Q22100",
        assigned_user_name="Rohit",
        assigned_user_email="rohit@example.com",
        assignment_type="engineer",
        assignee_kind="external",
        status="assigned",
        assignment_token="secret-external-token",
    )
    session.add_all([estimator_assignment, engineer_assignment, external_assignment])
    session.flush()
    older_session.payload_snapshot = {
        "eworks_quote_id": 29204,
        "assignment_id": engineer_assignment.id,
    }
    newer_session.payload_snapshot = {
        "eworks_quote_id": 29204,
    }

    _add_session_versions(
        session,
        older_session,
        versions=[
            {
                "version_number": 1,
                "step2_snapshot": {"works": [{"scope": "First submission"}]},
                "calculation_result": _ui_state("0.00")["last_result"],
                "revision_reason": None,
                "is_current": False,
                "submitted_by_name": "Engineer User",
                "submitted_by_email": "engineer@example.com",
            },
            {
                "version_number": 2,
                "step2_snapshot": {"works": [{"scope": "Revised engineer scope"}]},
                "calculation_result": _ui_state("0.00")["last_result"],
                "revision_reason": "Client requested scope change",
                "is_current": True,
                "submitted_by_name": "Engineer User",
                "submitted_by_email": "engineer@example.com",
            },
        ],
    )
    _add_session_versions(
        session,
        newer_session,
        versions=[
            {
                "version_number": 1,
                "step2_snapshot": {"works": [{"scope": "Second submission"}]},
                "calculation_result": _ui_state("174.24")["last_result"],
                "revision_reason": None,
                "is_current": True,
                "submitted_by_name": "Unknown submitter",
            },
        ],
    )

    session.commit()
    return session


@patch("app.auth.dependencies.settings")
def test_group_detail_includes_assignments(mock_settings, review_api_client, review_detail_db_session):
    _patch_dev_user(mock_settings, role="manager")
    response = review_api_client.get("/api/v1/dashboard/quote-groups/detail", params={"quote_ref": "Q22100"})
    assert response.status_code == 200
    group = response.json()["data"]["group"]
    assert len(group["assignments"]) == 3
    assert group["assignment_summary"]["total_assignments"] == 3
    assert group["assignment_summary"]["pending_assignments"] == 2
    assert group["assignment_summary"]["in_progress_assignments"] == 0
    assert group["assignment_summary"]["submitted_assignments"] == 1
    assert group["review_status"] == "ready_for_review"


@patch("app.auth.dependencies.settings")
def test_group_detail_includes_submitter_info_when_available(mock_settings, review_api_client, review_detail_db_session):
    _patch_dev_user(mock_settings, role="manager")
    response = review_api_client.get("/api/v1/dashboard/quote-groups/detail", params={"quote_ref": "Q22100"})
    group = response.json()["data"]["group"]
    submitters = {item["submitted_by_name"] for item in group["sessions"]}
    assert "Engineer User" in submitters
    assert "Unknown submitter" in submitters
    latest = next(item for item in group["sessions"] if item["is_latest"])
    assert latest["submitted_by_name"] == "Unknown submitter"


@patch("app.auth.dependencies.settings")
def test_group_detail_missing_submitter_returns_unknown(mock_settings, review_api_client, review_detail_db_session):
    _patch_dev_user(mock_settings, role="manager")
    response = review_api_client.get("/api/v1/dashboard/quote-groups/detail", params={"quote_ref": "Q22100"})
    unknown_sessions = [
        item for item in response.json()["data"]["group"]["sessions"] if item["submitted_by_name"] == "Unknown submitter"
    ]
    assert len(unknown_sessions) >= 1


@patch("app.auth.dependencies.settings")
def test_group_detail_excludes_tokens(mock_settings, review_api_client, review_detail_db_session):
    _patch_dev_user(mock_settings, role="manager")
    response = review_api_client.get("/api/v1/dashboard/quote-groups/detail", params={"quote_ref": "Q22100"})
    body = response.text
    assert "assignment_token" not in body
    assert "session_token" not in body
    assert "raw_payload" not in body
    assert "secret-" not in body


@patch("app.auth.dependencies.settings")
def test_group_detail_sessions_sorted_newest_first(mock_settings, review_api_client, review_detail_db_session):
    _patch_dev_user(mock_settings, role="manager")
    response = review_api_client.get("/api/v1/dashboard/quote-groups/detail", params={"quote_ref": "Q22100"})
    sessions = response.json()["data"]["group"]["sessions"]
    assert sessions[0]["is_latest"] is True
    assert sessions[0]["submitted_at"] >= sessions[1]["submitted_at"]


@patch("app.auth.dependencies.settings")
def test_group_detail_submitted_assignment_count(mock_settings, review_api_client, review_detail_db_session):
    _patch_dev_user(mock_settings, role="manager")
    response = review_api_client.get("/api/v1/dashboard/quote-groups/detail", params={"quote_ref": "Q22100"})
    summary = response.json()["data"]["group"]["assignment_summary"]
    assert summary["submitted_assignments"] == 1
    assert summary["estimator_assignments"] == 1
    assert summary["engineer_assignments"] == 2


@patch("app.auth.dependencies.settings")
def test_group_detail_includes_assignment_submission_rows(mock_settings, review_api_client, review_detail_db_session):
    _patch_dev_user(mock_settings, role="manager")
    response = review_api_client.get("/api/v1/dashboard/quote-groups/detail", params={"quote_ref": "Q22100"})
    group = response.json()["data"]["group"]
    rows = group["assignment_submissions"]
    assert len(rows) == 4
    assert len(group["assignments"]) == 3
    assert len(group["sessions"]) == 2

    assignment_ids = {row["assignment_id"] for row in rows if row["assignment_id"] is not None}
    assert assignment_ids == {1, 2, 3}

    submitted_rows = [row for row in rows if row["assignment_status"] == "submitted"]
    assert len(submitted_rows) == 2
    engineer_row = next(row for row in rows if row["assignment_id"] == 2)
    assert engineer_row["linked_session_id"] is not None
    assert engineer_row["final_total"] is not None
    assert engineer_row["submitted_by_name"] == "Engineer User"
    assert engineer_row["can_view_details"] is True
    assert engineer_row["can_reopen"] is True

    pending_row = next(row for row in rows if row["assignment_id"] == 1)
    assert pending_row["assignment_status"] == "assigned"
    assert pending_row["final_total"] is None
    assert pending_row["can_view_details"] is False

    unlinked_row = next(row for row in rows if row["assignment_id"] is None)
    assert unlinked_row["assignment_type"] == "unknown"
    assert unlinked_row["assignee_name"] == "Unknown"
    assert unlinked_row["submitted_by_name"] == "Unknown submitter"


@patch("app.auth.dependencies.settings")
def test_group_detail_assignment_submissions_latest_badge(mock_settings, review_api_client, review_detail_db_session):
    _patch_dev_user(mock_settings, role="manager")
    response = review_api_client.get("/api/v1/dashboard/quote-groups/detail", params={"quote_ref": "Q22100"})
    rows = response.json()["data"]["group"]["assignment_submissions"]
    latest_rows = [row for row in rows if row["is_latest"]]
    assert len(latest_rows) == 1
    assert latest_rows[0]["linked_session_id"] == response.json()["data"]["group"]["latest_session_id"]


@patch("app.auth.dependencies.settings")
def test_group_detail_assignment_submissions_exclude_tokens(mock_settings, review_api_client, review_detail_db_session):
    _patch_dev_user(mock_settings, role="manager")
    response = review_api_client.get("/api/v1/dashboard/quote-groups/detail", params={"quote_ref": "Q22100"})
    body = response.text
    assert "assignment_token" not in body
    assert "session_token" not in body
    for row in response.json()["data"]["group"]["assignment_submissions"]:
        assert "token" not in row


@patch("app.auth.dependencies.settings")
def test_group_detail_assignment_submissions_include_versions(mock_settings, review_api_client, review_detail_db_session):
    _patch_dev_user(mock_settings, role="manager")
    response = review_api_client.get("/api/v1/dashboard/quote-groups/detail", params={"quote_ref": "Q22100"})
    assert response.status_code == 200
    rows = response.json()["data"]["group"]["assignment_submissions"]

    engineer_row = next(row for row in rows if row["assignment_id"] == 2)
    assert engineer_row["version_count"] == 2
    assert engineer_row["current_version_number"] == 2
    assert len(engineer_row["versions"]) == 2
    version_numbers = {item["version_number"] for item in engineer_row["versions"]}
    assert version_numbers == {1, 2}
    v1 = next(item for item in engineer_row["versions"] if item["version_number"] == 1)
    v2 = next(item for item in engineer_row["versions"] if item["version_number"] == 2)
    assert v1["revision_reason"] is None
    assert v2["revision_reason"] == "Client requested scope change"
    assert v2["is_current"] is True

    unlinked_row = next(row for row in rows if row["assignment_id"] is None)
    assert unlinked_row["version_count"] == 1
    assert unlinked_row["current_version_number"] == 1
    assert len(unlinked_row["versions"]) == 1
    assert unlinked_row["versions"][0]["version_number"] == 1
    assert unlinked_row["versions"][0]["revision_reason"] is None


@patch("app.auth.dependencies.settings")
def test_group_detail_assignment_versions_exclude_sensitive_fields(
    mock_settings, review_api_client, review_detail_db_session
):
    _patch_dev_user(mock_settings, role="manager")
    response = review_api_client.get("/api/v1/dashboard/quote-groups/detail", params={"quote_ref": "Q22100"})
    body = response.text
    assert "session_token" not in body
    assert "assignment_token" not in body
    assert "raw_payload" not in body
    assert "step1_snapshot" not in body
    assert "step2_snapshot" not in body
    assert "calculation_result" not in body
    assert "secret-" not in body

    for row in response.json()["data"]["group"]["assignment_submissions"]:
        for version in row.get("versions") or []:
            assert "step1_snapshot" not in version
            assert "step2_snapshot" not in version
            assert "calculation_result" not in version


@patch("app.auth.dependencies.settings")
def test_manager_session_versions_endpoint_returns_v1_and_v2(
    mock_settings, review_api_client, review_detail_db_session
):
    _patch_dev_user(mock_settings, role="manager")
    submitted_sessions = (
        review_detail_db_session.query(CalculationSession)
        .filter(CalculationSession.status == "submitted")
        .order_by(CalculationSession.submitted_at.asc())
        .all()
    )
    engineer_session = next(
        row
        for row in submitted_sessions
        if isinstance(row.step1_snapshot, dict) and row.step1_snapshot.get("quote_number") == "Q22100"
    )

    response = review_api_client.get(f"/api/v1/manager/quotes/sessions/{engineer_session.id}/versions")
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["current_version_number"] == 2
    assert len(payload["versions"]) == 2
    assert "session_token" not in payload
    reasons = {item["version_number"]: item.get("revision_reason") for item in payload["versions"]}
    assert reasons[1] is None
    assert reasons[2] == "Client requested scope change"


@pytest.mark.parametrize("role", ["engineer", "client"])
@patch("app.auth.dependencies.settings")
def test_engineer_and_client_blocked_from_manager_versions_endpoint(
    mock_settings, review_api_client, review_detail_db_session, role
):
    _patch_dev_user(mock_settings, role=role)
    session_id = review_detail_db_session.query(CalculationSession).first().id
    response = review_api_client.get(f"/api/v1/manager/quotes/sessions/{session_id}/versions")
    assert response.status_code == 403
