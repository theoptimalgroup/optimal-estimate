"""Unit tests for processed sales pipeline dashboard."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import UserRole, get_password_hash
from app.db.session import get_db
from app.main import app
from app.models.eworks_sync import EworksQuote
from app.models.processed_sales_pipeline import ProcessedQuoteSalesPipeline
from app.models.user import User
from app.schemas.processed_dashboard import SalesPipelinePatch
from app.services.processed_dashboard_service import (
    _classify_follow_up,
    _coerce_quote_numeric,
    _quote_value,
    get_processed_dashboard,
    patch_sales_pipeline,
)
from app.services.quote_search_service import (
    EWORKS_STATUS_ACCEPTED,
    EWORKS_STATUS_PROCESSED,
    EWORKS_STATUS_REJECTED,
    quote_is_sales_pipeline_active,
)


def _now() -> datetime:
    return datetime(2026, 6, 11, 12, 0, tzinfo=timezone.utc)


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in [User.__table__, EworksQuote.__table__, ProcessedQuoteSalesPipeline.__table__]:
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


def _pipeline(
    session,
    quote: EworksQuote,
    *,
    sales_bucket: str = "pending",
    assigned_sales_email: str | None = None,
    assigned_sales_name: str | None = None,
    next_follow_up_at: datetime | None = None,
    processed_at: datetime | None = None,
    accepted_at: datetime | None = None,
    rejected_at: datetime | None = None,
    closed_at: datetime | None = None,
    closed_reason: str | None = None,
) -> ProcessedQuoteSalesPipeline:
    row = ProcessedQuoteSalesPipeline(
        id=uuid.uuid4(),
        synced_quote_id=quote.id,
        eworks_quote_id=quote.eworks_quote_id,
        quote_ref=quote.quote_ref,
        sales_bucket=sales_bucket,
        assigned_sales_email=assigned_sales_email,
        assigned_sales_name=assigned_sales_name,
        next_follow_up_at=next_follow_up_at,
        processed_at=processed_at or _now(),
        bucket_changed_at=processed_at or _now(),
        accepted_at=accepted_at,
        rejected_at=rejected_at,
        closed_at=closed_at,
        closed_reason=closed_reason,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def _quote(
    session,
    *,
    eworks_id: int,
    status: str,
    ref: str,
    total: float = 1000.0,
    status_name: str | None = None,
) -> EworksQuote:
    q = EworksQuote(
        eworks_quote_id=eworks_id,
        quote_ref=ref,
        customer_name="Acme Ltd",
        status=status,
        status_name=status_name,
        total=total,
        raw_payload={"last_updated_on": "2026-06-01"},
        synced_at=_now(),
        created_at=_now(),
        updated_at=_now(),
    )
    session.add(q)
    session.commit()
    session.refresh(q)
    return q


def test_pending_status_name_with_empty_status_code_included(db_session):
    session, *_ = db_session
    q = _quote(
        session,
        eworks_id=22135,
        status="",
        ref="Q22135/02",
        status_name="Pending",
        total=474.0,
    )
    assert quote_is_sales_pipeline_active(q)
    data = get_processed_dashboard(session)
    assert data["totals"]["processed_quotes"] == 1
    assert data["categories"]["pending"]["quotes"][0]["quote_value"] == 474.0
    assert data["totals"]["pipeline_value"] == 474.0


def test_status_two_and_pending_name_included(db_session):
    session, *_ = db_session
    _quote(
        session,
        eworks_id=22136,
        status="2",
        ref="Q22136",
        status_name="Pending",
        total=474.0,
    )
    data = get_processed_dashboard(session)
    assert data["totals"]["processed_quotes"] == 1
    assert data["categories"]["pending"]["value"] == 474.0


def test_excluded_statuses_not_in_active_pipeline(db_session):
    session, *_ = db_session
    _quote(session, eworks_id=1, status="1", ref="Q-Draft", status_name="Draft")
    _quote(session, eworks_id=2, status="3", ref="Q-Approved", status_name="Approved")
    _quote(session, eworks_id=3, status="5", ref="Q-Callback", status_name="Call Back")
    _quote(session, eworks_id=4, status="9", ref="Q-Closed", status_name="Closed")
    _quote(session, eworks_id=5, status="2", ref="Q-Active", status_name="Pending", total=100.0)
    data = get_processed_dashboard(session)
    assert data["totals"]["processed_quotes"] == 1
    assert data["totals"]["pipeline_value"] == 100.0


def test_only_processed_in_active_pipeline(db_session):
    session, *_ = db_session
    _quote(session, eworks_id=1, status=EWORKS_STATUS_PROCESSED, ref="Q100")
    _quote(session, eworks_id=2, status="1", ref="Q101")
    _quote(session, eworks_id=3, status=EWORKS_STATUS_ACCEPTED, ref="Q102")
    data = get_processed_dashboard(session)
    assert data["totals"]["processed_quotes"] == 1


def test_missing_pipeline_row_defaults_pending(db_session):
    session, *_ = db_session
    _quote(session, eworks_id=10, status=EWORKS_STATUS_PROCESSED, ref="Q200")
    data = get_processed_dashboard(session)
    assert data["categories"]["pending"]["quotes"][0]["sales_bucket"] == "pending"


def test_quote_value_from_total_column(db_session):
    """Regression: synced quote total=678.0 must flow to dashboard values."""
    session, *_ = db_session
    _quote(session, eworks_id=22105, status=EWORKS_STATUS_PROCESSED, ref="Q22105", total=678.0)
    data = get_processed_dashboard(session)
    pending_quotes = data["categories"]["pending"]["quotes"]
    assert len(pending_quotes) == 1
    assert pending_quotes[0]["quote_ref"] == "Q22105"
    assert pending_quotes[0]["quote_value"] == 678.0
    assert data["categories"]["pending"]["value"] == 678.0
    assert data["totals"]["pipeline_value"] == 678.0


def test_quote_value_from_raw_payload_when_column_missing(db_session):
    session, *_ = db_session
    q = EworksQuote(
        eworks_quote_id=22106,
        quote_ref="Q22106",
        customer_name="Acme Ltd",
        status=EWORKS_STATUS_PROCESSED,
        total=None,
        raw_payload={"quote_total": 1250.5, "last_updated_on": "2026-06-01"},
        synced_at=_now(),
        created_at=_now(),
        updated_at=_now(),
    )
    session.add(q)
    session.commit()
    data = get_processed_dashboard(session)
    assert data["categories"]["pending"]["quotes"][0]["quote_value"] == 1250.5
    assert data["totals"]["pipeline_value"] == 1250.5


def test_coerce_quote_numeric_handles_currency_and_decimal():
    from decimal import Decimal

    assert _coerce_quote_numeric(Decimal("678.00")) == 678.0
    assert _coerce_quote_numeric("£1,234.50") == 1234.5
    assert _coerce_quote_numeric("") is None
    assert _coerce_quote_numeric(None) is None


def test_bucket_counts_and_values(db_session):
    session, *_ = db_session
    q1 = _quote(session, eworks_id=11, status=EWORKS_STATUS_PROCESSED, ref="Q201", total=500)
    q2 = _quote(session, eworks_id=12, status=EWORKS_STATUS_PROCESSED, ref="Q202", total=1500)
    session.add(
        ProcessedQuoteSalesPipeline(
            id=uuid.uuid4(),
            synced_quote_id=q2.id,
            eworks_quote_id=q2.eworks_quote_id,
            quote_ref=q2.quote_ref,
            sales_bucket="strong",
            processed_at=_now(),
            bucket_changed_at=_now(),
        )
    )
    session.commit()
    data = get_processed_dashboard(session)
    assert data["categories"]["pending"]["count"] == 1
    assert data["categories"]["strong"]["count"] == 1
    assert data["totals"]["pipeline_value"] == 2000


def test_aging_buckets(db_session):
    session, *_ = db_session
    old = _quote(session, eworks_id=20, status=EWORKS_STATUS_PROCESSED, ref="Q300")
    session.add(
        ProcessedQuoteSalesPipeline(
            id=uuid.uuid4(),
            synced_quote_id=old.id,
            eworks_quote_id=old.eworks_quote_id,
            quote_ref=old.quote_ref,
            sales_bucket="pending",
            processed_at=_now() - timedelta(days=45),
            bucket_changed_at=_now() - timedelta(days=45),
        )
    )
    session.commit()
    data = get_processed_dashboard(session)
    assert data["aging"]["31_60_days"]["count"] == 1


def test_follow_up_classification():
    now = _now()
    assert _classify_follow_up(now - timedelta(days=1), now) == "overdue"
    assert _classify_follow_up(now, now) == "due_today"
    assert _classify_follow_up(None, now) == "no_followup"


def test_accepted_rejected_in_trend_not_active(db_session):
    session, *_ = db_session
    _quote(session, eworks_id=30, status=EWORKS_STATUS_PROCESSED, ref="Q400", status_name="Pending")
    _quote(session, eworks_id=31, status=EWORKS_STATUS_ACCEPTED, ref="Q401", total=2000, status_name="Approved")
    _quote(session, eworks_id=32, status=EWORKS_STATUS_REJECTED, ref="Q402", total=500, status_name="Call Back")
    data = get_processed_dashboard(session)
    assert data["totals"]["processed_quotes"] == 1
    assert data["totals"]["accepted_count"] == 0
    assert data["totals"]["rejected_count"] == 0


def test_tracked_pipeline_closed_quotes_in_trend(db_session):
    session, *_ = db_session
    now = _now()
    _quote(session, eworks_id=30, status="2", ref="Q400", status_name="Pending", total=100)
    q_acc = _quote(session, eworks_id=31, status="4", ref="Q401", total=2000, status_name="Approved")
    q_rej = _quote(session, eworks_id=32, status="5", ref="Q402", total=500, status_name="Call Back")
    _pipeline(session, q_acc, accepted_at=now, closed_at=now, closed_reason="accepted")
    _pipeline(session, q_rej, rejected_at=now, closed_at=now, closed_reason="rejected")
    data = get_processed_dashboard(session)
    assert data["totals"]["processed_quotes"] == 1
    assert data["totals"]["accepted_count"] == 1
    assert data["totals"]["rejected_count"] == 1
    assert data["totals"]["accepted_value"] == 2000.0
    assert data["totals"]["rejected_value"] == 500.0


def test_conversion_rate(db_session):
    session, *_ = db_session
    now = _now()
    q_acc1 = _quote(session, eworks_id=40, status="4", ref="Q500", status_name="Approved")
    q_acc2 = _quote(session, eworks_id=41, status="4", ref="Q501", status_name="Approved")
    q_rej = _quote(session, eworks_id=42, status="5", ref="Q502", status_name="Call Back")
    _pipeline(session, q_acc1, accepted_at=now, closed_at=now, closed_reason="accepted")
    _pipeline(session, q_acc2, accepted_at=now, closed_at=now, closed_reason="accepted")
    _pipeline(session, q_rej, rejected_at=now, closed_at=now, closed_reason="rejected")
    data = get_processed_dashboard(session)
    assert data["totals"]["conversion_rate"] == pytest.approx(66.7, abs=0.1)


def test_admin_and_manager_endpoints_return_same_dashboard(api_client, db_session):
    client, *_ = api_client
    session, *_ = db_session
    _quote(session, eworks_id=99, status="2", ref="Q-SAME", status_name="Pending", total=250.0)
    _quote(
        session,
        eworks_id=100,
        status="",
        ref="Q-SAME-2",
        status_name="Pending",
        total=474.0,
    )
    admin = client.get("/api/v1/admin/processed-dashboard")
    manager = client.get("/api/v1/manager/processed-dashboard")
    assert admin.status_code == 200
    assert manager.status_code == 200
    admin_data = admin.json()["data"]
    manager_data = manager.json()["data"]
    assert admin_data["totals"] == manager_data["totals"]
    assert admin_data["totals"]["processed_quotes"] == 2
    assert admin_data["totals"]["pipeline_value"] == 724.0
    assert admin_data["categories"]["pending"]["value"] == 724.0
    assert admin_data == manager_data


def test_admin_can_patch_sales_pipeline(db_session):
    session, admin, *_ = db_session
    q = _quote(session, eworks_id=50, status=EWORKS_STATUS_PROCESSED, ref="Q600")
    from app.auth.types import AuthenticatedUser

    actor = AuthenticatedUser(
        id=str(admin.id),
        email=admin.email,
        name=admin.full_name,
        role=UserRole.ADMIN,
        is_active=True,
        auth_provider="dev",
    )
    row = patch_sales_pipeline(
        session,
        q.id,
        SalesPipelinePatch(sales_bucket="possible", sales_note="Called client"),
        actor,
    )
    assert row.sales_bucket == "possible"


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


def test_manager_cannot_access_admin_processed_dashboard(api_client):
    client, admin, manager, engineer = api_client

    with patch("app.auth.dependencies.settings") as mock_settings:
        mock_settings.auth_provider = "dev"
        mock_settings.dev_auth_enabled = True
        mock_settings.dev_user_email = manager.email

        from app.auth.resolution import resolve_dev_authenticated_user

        with patch(
            "app.auth.dependencies.resolve_dev_authenticated_user",
            side_effect=lambda db, config=None: resolve_dev_authenticated_user(db, mock_settings),
        ):
            resp = client.get("/api/v1/admin/processed-dashboard")
    assert resp.status_code == 403


def test_admin_processed_dashboard_api(api_client):
    client, *_ = api_client
    resp = client.get("/api/v1/admin/processed-dashboard")
    assert resp.status_code == 200
    assert "categories" in resp.json()["data"]


def test_engineer_cannot_get_processed_dashboard(api_client):
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
            resp = client.get("/api/v1/manager/processed-dashboard")
    assert resp.status_code == 403


def test_manager_processed_dashboard_api(api_client):
    client, *_ = api_client
    resp = client.get("/api/v1/manager/processed-dashboard")
    assert resp.status_code == 200
    assert "totals" in resp.json()["data"]


@patch("app.services.processed_dashboard_service._utcnow", _now)
def test_follow_up_totals_in_dashboard(db_session):
    session, *_ = db_session
    now = _now()
    q_overdue = _quote(session, eworks_id=70, status=EWORKS_STATUS_PROCESSED, ref="Q800")
    q_today = _quote(session, eworks_id=71, status=EWORKS_STATUS_PROCESSED, ref="Q801")
    q_none = _quote(session, eworks_id=72, status=EWORKS_STATUS_PROCESSED, ref="Q802")
    _pipeline(session, q_overdue, next_follow_up_at=now - timedelta(days=2))
    _pipeline(session, q_today, next_follow_up_at=now)
    _pipeline(session, q_none, next_follow_up_at=None)
    data = get_processed_dashboard(session)
    assert data["totals"]["overdue_followups"] == 1
    assert data["totals"]["due_today_followups"] == 1
    assert data["totals"]["no_followup_set"] == 1
    assert len(data["follow_up_reminders"]["overdue"]) == 1
    assert len(data["follow_up_reminders"]["due_today"]) == 1
    assert len(data["follow_up_reminders"]["no_followup_set"]) == 1


@patch("app.services.processed_dashboard_service._utcnow", _now)
def test_salesperson_performance(db_session):
    session, *_ = db_session
    now = _now()
    q_pending = _quote(session, eworks_id=80, status=EWORKS_STATUS_PROCESSED, ref="Q900", total=1000)
    q_strong = _quote(session, eworks_id=81, status=EWORKS_STATUS_PROCESSED, ref="Q901", total=2000)
    q_accepted = _quote(session, eworks_id=82, status=EWORKS_STATUS_ACCEPTED, ref="Q902", total=3000)
    _pipeline(
        session,
        q_pending,
        sales_bucket="pending",
        assigned_sales_email="alice@example.com",
        assigned_sales_name="Alice",
        next_follow_up_at=now + timedelta(days=3),
    )
    _pipeline(
        session,
        q_strong,
        sales_bucket="strong",
        assigned_sales_email="alice@example.com",
        assigned_sales_name="Alice",
        next_follow_up_at=now - timedelta(days=1),
    )
    _pipeline(
        session,
        q_accepted,
        sales_bucket="strong",
        assigned_sales_email="alice@example.com",
        assigned_sales_name="Alice",
        processed_at=now - timedelta(days=30),
        accepted_at=now,
        closed_at=now,
        closed_reason="accepted",
    )
    data = get_processed_dashboard(session)
    alice = next(r for r in data["salesperson_performance"] if r["salesperson_email"] == "alice@example.com")
    assert alice["assigned_count"] == 2
    assert alice["pipeline_value"] == 3000
    assert alice["strong_value"] == 2000
    assert alice["overdue_followups"] == 1
    assert alice["accepted_count"] == 1
    assert alice["conversion_rate"] == 100.0


@patch("app.services.processed_dashboard_service._utcnow", _now)
def test_monthly_pipeline_value(db_session):
    session, *_ = db_session
    june = _quote(session, eworks_id=90, status=EWORKS_STATUS_PROCESSED, ref="Q1000", total=1500)
    may = _quote(session, eworks_id=91, status=EWORKS_STATUS_PROCESSED, ref="Q1001", total=2500)
    _pipeline(session, june, sales_bucket="pending", processed_at=datetime(2026, 6, 5, tzinfo=timezone.utc))
    _pipeline(session, may, sales_bucket="strong", processed_at=datetime(2026, 5, 10, tzinfo=timezone.utc))
    data = get_processed_dashboard(session)
    by_month = {row["month"]: row for row in data["monthly_pipeline_value"]}
    assert by_month["2026-06"]["new_processed_value"] == 1500
    assert by_month["2026-06"]["active_pipeline_value"] == 1500
    assert by_month["2026-06"]["strong_pipeline_value"] == 0
    assert by_month["2026-05"]["new_processed_value"] == 2500
    assert by_month["2026-05"]["strong_pipeline_value"] == 2500


def test_manager_can_patch_sales_pipeline(api_client, db_session):
    client, admin, manager, engineer = api_client
    session, *_ = db_session
    q = _quote(session, eworks_id=95, status=EWORKS_STATUS_PROCESSED, ref="Q1100")
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
                f"/api/v1/processed-quotes/{q.id}/sales-pipeline",
                json={"sales_bucket": "possible", "sales_note": "Manager follow-up"},
            )
    assert resp.status_code == 200
    assert resp.json()["data"]["sales_bucket"] == "possible"
    assert resp.json()["data"]["sales_note"] == "Manager follow-up"


def test_estimator_cannot_patch_pipeline(api_client, db_session):
    client, admin, manager, engineer = api_client
    session, *_ = db_session
    q = _quote(session, eworks_id=60, status=EWORKS_STATUS_PROCESSED, ref="Q700")

    with patch("app.auth.dependencies.settings") as mock_settings:
        mock_settings.auth_provider = "dev"
        mock_settings.dev_auth_enabled = True
        mock_settings.dev_user_email = engineer.email

        from app.auth.resolution import resolve_dev_authenticated_user

        with patch(
            "app.auth.dependencies.resolve_dev_authenticated_user",
            side_effect=lambda db, config=None: resolve_dev_authenticated_user(db, mock_settings),
        ):
            resp = client.patch(
                f"/api/v1/processed-quotes/{q.id}/sales-pipeline",
                json={"sales_bucket": "strong"},
            )
    assert resp.status_code == 403
