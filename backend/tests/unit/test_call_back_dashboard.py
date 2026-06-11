"""Unit tests for Call Back dashboard."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.types import AuthenticatedUser
from app.core.security import UserRole, get_password_hash
from app.db.session import get_db
from app.main import app
from app.models.call_back_tracking import CallBackQuoteTracking
from app.models.eworks_sync import EworksQuote
from app.models.user import User
from app.schemas.call_back_dashboard import CallBackTrackingPatch
from app.services.call_back_dashboard_service import (
    _classify_call_bucket,
    get_call_back_dashboard,
    patch_call_back_tracking,
)
from app.services.quote_search_service import EWORKS_CALL_BACK_STATUS, quote_is_call_back


def _now() -> datetime:
    return datetime(2026, 6, 11, 12, 0, tzinfo=timezone.utc)


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in [User.__table__, EworksQuote.__table__, CallBackQuoteTracking.__table__]:
        table.create(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    now = _now()
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
    session.commit()
    yield session, admin, manager, engineer
    session.close()


def _quote(
    session,
    *,
    eworks_id: int,
    status: str,
    ref: str,
    total: float = 1000.0,
    status_name: str | None = None,
    raw_payload: dict | None = None,
) -> EworksQuote:
    payload = {"last_updated_on": "2026-06-01"}
    if raw_payload:
        payload.update(raw_payload)
    q = EworksQuote(
        eworks_quote_id=eworks_id,
        quote_ref=ref,
        customer_name="Acme Ltd",
        status=status,
        status_name=status_name,
        total=total,
        raw_payload=payload,
        synced_at=_now(),
        created_at=_now(),
        updated_at=_now(),
    )
    session.add(q)
    session.commit()
    session.refresh(q)
    return q


def _tracking(
    session,
    quote: EworksQuote,
    *,
    next_call_at: datetime | None = None,
    call_note: str | None = None,
) -> CallBackQuoteTracking:
    row = CallBackQuoteTracking(
        id=uuid.uuid4(),
        synced_quote_id=quote.id,
        eworks_quote_id=quote.eworks_quote_id,
        quote_ref=quote.quote_ref,
        next_call_at=next_call_at,
        call_note=call_note,
        call_status="no_call_date",
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@patch("app.services.call_back_dashboard_service._utcnow", _now)
def test_dashboard_includes_status_name_call_back(db_session):
    session, *_ = db_session
    _quote(session, eworks_id=1, status="", ref="Q-CB-1", status_name="Call Back", total=500.0)
    data = get_call_back_dashboard(session)
    assert data["totals"]["call_back_quotes"] == 1
    assert data["categories"]["no_call_date"]["quotes"][0]["status_name"] == "Call Back"


@patch("app.services.call_back_dashboard_service._utcnow", _now)
def test_dashboard_includes_status_five(db_session):
    session, *_ = db_session
    _quote(session, eworks_id=2, status=EWORKS_CALL_BACK_STATUS, ref="Q-CB-2", status_name="Call Back")
    data = get_call_back_dashboard(session)
    assert data["totals"]["call_back_quotes"] == 1
    assert data["categories"]["no_call_date"]["count"] == 1


@patch("app.services.call_back_dashboard_service._utcnow", _now)
def test_dashboard_excludes_draft_pending_approved_closed(db_session):
    session, *_ = db_session
    _quote(session, eworks_id=10, status="1", ref="Q-Draft", status_name="Draft")
    _quote(session, eworks_id=11, status="2", ref="Q-Pending", status_name="Pending")
    _quote(session, eworks_id=12, status="3", ref="Q-Approved", status_name="Approved")
    _quote(session, eworks_id=13, status="9", ref="Q-Closed", status_name="Closed")
    _quote(session, eworks_id=14, status="5", ref="Q-Callback", status_name="Call Back", total=100.0)
    data = get_call_back_dashboard(session)
    assert data["totals"]["call_back_quotes"] == 1
    assert data["totals"]["total_quote_value"] == 100.0


@patch("app.services.call_back_dashboard_service._utcnow", _now)
def test_missing_tracking_defaults_no_call_date(db_session):
    session, *_ = db_session
    _quote(session, eworks_id=20, status="5", ref="Q-NO-TRACK", status_name="Call Back")
    data = get_call_back_dashboard(session)
    assert data["totals"]["no_call_date"] == 1
    quote = data["categories"]["no_call_date"]["quotes"][0]
    assert quote["call_status"] == "no_call_date"
    assert quote["next_call_at"] is None


@patch("app.services.call_back_dashboard_service._utcnow", _now)
def test_call_buckets_overdue_due_today_upcoming(db_session):
    session, *_ = db_session
    now = _now()
    q_overdue = _quote(session, eworks_id=30, status="5", ref="Q-OVER", status_name="Call Back")
    q_today = _quote(session, eworks_id=31, status="5", ref="Q-TODAY", status_name="Call Back")
    q_upcoming = _quote(session, eworks_id=32, status="5", ref="Q-UP", status_name="Call Back")
    _tracking(session, q_overdue, next_call_at=now - timedelta(days=2))
    _tracking(session, q_today, next_call_at=now)
    _tracking(session, q_upcoming, next_call_at=now + timedelta(days=3))
    data = get_call_back_dashboard(session)
    assert data["totals"]["overdue_calls"] == 1
    assert data["totals"]["due_today_calls"] == 1
    assert data["totals"]["upcoming_calls"] == 1
    assert data["categories"]["overdue"]["quotes"][0]["quote_ref"] == "Q-OVER"
    assert data["categories"]["due_today"]["quotes"][0]["quote_ref"] == "Q-TODAY"
    assert data["categories"]["upcoming"]["quotes"][0]["quote_ref"] == "Q-UP"


@patch("app.services.call_back_dashboard_service._utcnow", _now)
def test_quote_total_contributes_to_total_value(db_session):
    session, *_ = db_session
    _quote(session, eworks_id=40, status="5", ref="Q-VAL", status_name="Call Back", total=678.0)
    data = get_call_back_dashboard(session)
    assert data["totals"]["total_quote_value"] == 678.0
    assert data["categories"]["no_call_date"]["value"] == 678.0


def test_classify_call_bucket():
    now = _now()
    assert _classify_call_bucket(now - timedelta(days=1), now) == "overdue"
    assert _classify_call_bucket(now, now) == "due_today"
    assert _classify_call_bucket(now + timedelta(days=2), now) == "upcoming"
    assert _classify_call_bucket(None, now) == "no_call_date"


def test_quote_is_call_back_with_raw_payload_status():
    q = EworksQuote(
        eworks_quote_id=99,
        quote_ref="Q-RAW",
        status="",
        status_name=None,
        raw_payload={"status": "5", "status_name": "Call Back"},
    )
    assert quote_is_call_back(q)


@pytest.fixture()
def api_client(db_session):
    session, admin, manager, engineer = db_session

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    with patch("app.auth.dependencies.settings") as mock_settings:
        mock_settings.auth_provider = "dev"
        mock_settings.dev_auth_enabled = True
        mock_settings.dev_user_email = admin.email

        from app.auth.resolution import resolve_dev_authenticated_user

        with patch(
            "app.auth.dependencies.resolve_dev_authenticated_user",
            side_effect=lambda db, config=None: resolve_dev_authenticated_user(db, mock_settings),
        ):
            client = TestClient(app)
            yield client, admin, manager, engineer
    app.dependency_overrides.clear()


@patch("app.services.call_back_dashboard_service._utcnow", _now)
def test_admin_and_manager_endpoints_return_same_data(api_client, db_session):
    client, *_ = api_client
    session, *_ = db_session
    _quote(session, eworks_id=50, status="5", ref="Q-SAME", status_name="Call Back", total=250.0)
    admin = client.get("/api/v1/admin/call-back-dashboard")
    manager = client.get("/api/v1/manager/call-back-dashboard")
    assert admin.status_code == 200
    assert manager.status_code == 200
    assert admin.json()["data"] == manager.json()["data"]
    assert admin.json()["data"]["totals"]["call_back_quotes"] == 1


def test_engineer_cannot_access_call_back_dashboard(api_client):
    client, admin, manager, engineer = api_client

    with patch("app.auth.dependencies.settings") as mock_settings:
        mock_settings.auth_provider = "dev"
        mock_settings.dev_auth_enabled = True
        mock_settings.dev_user_email = engineer.email

        from app.auth.resolution import resolve_dev_authenticated_user

        with patch(
            "app.auth.dependencies.resolve_dev_authenticated_user",
            side_effect=lambda db, config=None: resolve_dev_authenticated_user(db, mock_settings),
        ):
            resp = client.get("/api/v1/manager/call-back-dashboard")
    assert resp.status_code == 403


@patch("app.services.call_back_dashboard_service._utcnow", _now)
def test_patch_updates_call_note_and_next_call_date(db_session):
    session, admin, *_ = db_session
    q = _quote(session, eworks_id=60, status="5", ref="Q-PATCH", status_name="Call Back")
    actor = AuthenticatedUser(
        id=str(admin.id),
        email=admin.email,
        name=admin.full_name,
        role=UserRole.ADMIN,
        is_active=True,
        auth_provider="dev",
    )
    next_call = "2026-06-15T09:00:00Z"
    row = patch_call_back_tracking(
        session,
        q.id,
        CallBackTrackingPatch(call_note="Left voicemail", next_call_at=next_call),
        actor,
    )
    assert row.call_note == "Left voicemail"
    assert row.next_call_at is not None
    assert row.call_status == "upcoming"


@patch("app.services.call_back_dashboard_service._utcnow", _now)
def test_manager_can_patch_call_back_tracking(api_client, db_session):
    client, admin, manager, engineer = api_client
    session, *_ = db_session
    q = _quote(session, eworks_id=70, status="5", ref="Q-API", status_name="Call Back")
    with patch("app.auth.dependencies.settings") as mock_settings:
        mock_settings.auth_provider = "dev"
        mock_settings.dev_auth_enabled = True
        mock_settings.dev_user_email = manager.email
        from app.auth.resolution import resolve_dev_authenticated_user

        with patch(
            "app.auth.dependencies.resolve_dev_authenticated_user",
            side_effect=lambda db, config=None: resolve_dev_authenticated_user(db, mock_settings),
        ):
            resp = client.patch(
                f"/api/v1/call-back-quotes/{q.id}/tracking",
                json={"call_note": "Manager note", "next_call_at": "2026-06-12T09:00:00Z"},
            )
    assert resp.status_code == 200
    assert resp.json()["data"]["call_note"] == "Manager note"
