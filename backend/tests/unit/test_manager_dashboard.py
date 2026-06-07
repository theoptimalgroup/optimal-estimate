"""Unit tests for manager dashboard — eWorks quote category classification."""

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
from app.models.eworks_sync import EworksQuote
from app.models.user import User
from app.services.manager_dashboard_service import (
    AWAITING_SUPPLIER_TAG,
    READY_TO_SEND_TAG,
    classify_eworks_quote_bucket,
    extract_all_tags,
    is_awaiting_supplier_tag,
    is_ready_to_send_tag,
    normalize_tag_text,
)


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in [User.__table__, EworksQuote.__table__]:
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
    estimator = User(
        id=uuid.uuid4(),
        email="estimator@optimal.example",
        full_name="Estimator",
        password_hash=get_password_hash("est12345"),
        role=UserRole.ESTIMATOR.value,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    session.add_all([admin, manager, engineer, estimator])
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
        "estimator": "estimator@optimal.example",
    }
    mock_settings.auth_provider = "dev"
    mock_settings.dev_auth_enabled = True
    mock_settings.dev_user_id = f"dev-{role}-1"
    mock_settings.dev_user_email = email_map[role]
    mock_settings.dev_user_name = f"{role.title()} User"
    mock_settings.dev_user_role = role
    mock_settings.dev_user_is_active = True
    mock_settings.dev_auth_auto_create_user = False


def _make_quote(**kwargs) -> EworksQuote:
    defaults = {"eworks_quote_id": 1, "quote_ref": "Q-1", "customer_name": "Test Co"}
    defaults.update(kwargs)
    return EworksQuote(**defaults)


# ---------------------------------------------------------------------------
# Classification unit tests
# ---------------------------------------------------------------------------


def test_classify_status_one_as_new_quotes():
    quote = _make_quote(status="1", status_name="New")
    assert classify_eworks_quote_bucket(quote) == "new_quotes"


def test_classify_awaiting_supplier_tag():
    quote = _make_quote(status="2", tags=[AWAITING_SUPPLIER_TAG])
    assert classify_eworks_quote_bucket(quote) == "awaiting_supplier"


def test_classify_ready_to_send_tag():
    quote = _make_quote(status="2", tags=[READY_TO_SEND_TAG])
    assert classify_eworks_quote_bucket(quote) == "ready_to_send"


def test_classify_ready_to_send_flexible_quote_variant():
    quote = _make_quote(
        status="1",
        tags="Quote Ready to Send (Quotes),To Send With Invoice (QUOTES),URGENT,",
    )
    assert classify_eworks_quote_bucket(quote) == "ready_to_send"


def test_classify_awaiting_supplier_comma_separated_with_status_one():
    quote = _make_quote(
        status="1",
        tags="Awaiting Supplier Info (Quotes),URGENT,",
    )
    assert classify_eworks_quote_bucket(quote) == "awaiting_supplier"


def test_classify_status_one_with_empty_tags():
    quote = _make_quote(status="1", tags=[])
    assert classify_eworks_quote_bucket(quote) == "new_quotes"


def test_classify_status_one_with_unrelated_tags_only():
    quote = _make_quote(status="1", tags=["URGENT", "Electrical"])
    assert classify_eworks_quote_bucket(quote) == "new_quotes"


def test_classify_unrelated_tags_without_status_one_returns_none():
    quote = _make_quote(status="2", tags=["URGENT", "Electrical"])
    assert classify_eworks_quote_bucket(quote) is None


def test_extract_all_tags_splits_comma_separated_string():
    quote = _make_quote(tags="Quote Ready to Send (Quotes),To Send With Invoice (QUOTES),URGENT,")
    assert extract_all_tags(quote) == [
        "Quote Ready to Send (Quotes)",
        "To Send With Invoice (QUOTES)",
        "URGENT",
    ]


def test_is_ready_to_send_tag_case_insensitive():
    assert is_ready_to_send_tag("quote ready to send (quotes)")
    assert is_ready_to_send_tag("Quotes Ready to send (Quotes)")


def test_is_awaiting_supplier_tag_case_insensitive():
    assert is_awaiting_supplier_tag("AWAITING SUPPLIER INFO (QUOTES)")


def test_normalize_tag_text_collapses_spaces():
    assert normalize_tag_text("  Quote   Ready   to   Send  ") == "quote ready to send"


def test_classify_tag_case_insensitive():
    quote = _make_quote(status="2", tags=[f"  {AWAITING_SUPPLIER_TAG.upper()}  "])
    assert classify_eworks_quote_bucket(quote) == "awaiting_supplier"


def test_classify_status_string_one_same_as_int():
    quote_str = _make_quote(status="1")
    quote_int = _make_quote(status=1, eworks_quote_id=2)
    assert classify_eworks_quote_bucket(quote_str) == "new_quotes"
    assert classify_eworks_quote_bucket(quote_int) == "new_quotes"


def test_classify_status_one_from_status_name():
    quote = _make_quote(status=None, status_name="1")
    assert classify_eworks_quote_bucket(quote) == "new_quotes"


def test_classify_status_one_from_raw_payload_when_column_missing():
    quote = _make_quote(
        status=None,
        status_name=None,
        raw_payload={"status": "1", "secret": "hidden"},
    )
    assert classify_eworks_quote_bucket(quote) == "new_quotes"


def test_classify_status_one_from_raw_payload_status_capitalized():
    quote = _make_quote(
        status=None,
        raw_payload={"Status": 1},
    )
    assert classify_eworks_quote_bucket(quote) == "new_quotes"


def test_classify_status_one_from_raw_payload_quote_status_id():
    quote = _make_quote(
        status=None,
        raw_payload={"quote_status": {"id": 1, "quote_status": "New"}},
    )
    assert classify_eworks_quote_bucket(quote) == "new_quotes"


def test_classify_priority_awaiting_over_status_one():
    quote = _make_quote(status="1", tags=[AWAITING_SUPPLIER_TAG])
    assert classify_eworks_quote_bucket(quote) == "awaiting_supplier"


def test_classify_priority_ready_over_status_one():
    quote = _make_quote(status="1", tags=[READY_TO_SEND_TAG])
    assert classify_eworks_quote_bucket(quote) == "ready_to_send"


def test_classify_priority_ready_over_awaiting():
    quote = _make_quote(tags=[AWAITING_SUPPLIER_TAG, READY_TO_SEND_TAG])
    assert classify_eworks_quote_bucket(quote) == "ready_to_send"


def test_classify_unrelated_quote_returns_none():
    quote = _make_quote(status="5", tags=["Other"])
    assert classify_eworks_quote_bucket(quote) is None


# ---------------------------------------------------------------------------
# Dashboard endpoint tests
# ---------------------------------------------------------------------------


def test_classify_tag_from_raw_payload_labels():
    quote = _make_quote(
        status="5",
        tags=None,
        raw_payload={"labels": [READY_TO_SEND_TAG]},
    )
    assert classify_eworks_quote_bucket(quote) == "ready_to_send"


def test_classify_tag_from_json_string_tags_column():
    quote = _make_quote(
        status="5",
        tags=f'["{AWAITING_SUPPLIER_TAG}"]',
    )
    assert classify_eworks_quote_bucket(quote) == "awaiting_supplier"


@patch("app.auth.dependencies.settings")
def test_dashboard_includes_quote_with_only_raw_payload_status(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    db_session.add(
        EworksQuote(
            eworks_quote_id=22104,
            quote_ref="Q22104",
            customer_name="Linked Co",
            status=None,
            status_name=None,
            quote_date="2026-06-01",
            raw_payload={"status": "1", "Status": "1", "secret_token": "hidden"},
        )
    )
    db_session.commit()

    resp = api_client.get("/api/v1/manager/dashboard")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["categories"]["new_quotes"]["count"] == 1
    assert data["categories"]["new_quotes"]["quotes"][0]["quote_ref"] == "Q22104"
    assert "raw_payload" not in resp.text
    assert "secret_token" not in resp.text


@patch("app.auth.dependencies.settings")
def test_manager_can_access_dashboard(mock_settings, api_client):
    _patch_dev_user(mock_settings, role="manager")
    resp = api_client.get("/api/v1/manager/dashboard")
    assert resp.status_code == 200


@patch("app.auth.dependencies.settings")
def test_manager_dashboard_endpoint_returns_categories(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    synced = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    db_session.add_all(
        [
            EworksQuote(
                eworks_quote_id=101,
                quote_ref="Q-NEW",
                customer_name="New Co",
                status="1",
                status_name="New",
                quote_date="2026-06-01",
                total=100.0,
                synced_at=synced,
                raw_payload={"secret": "hidden"},
            ),
            EworksQuote(
                eworks_quote_id=102,
                quote_ref="Q-AWAIT",
                customer_name="Await Co",
                status="2",
                tags=[AWAITING_SUPPLIER_TAG],
                quote_date="2026-06-02",
                total=200.0,
                synced_at=synced,
            ),
            EworksQuote(
                eworks_quote_id=103,
                quote_ref="Q-READY",
                customer_name="Ready Co",
                status="2",
                tags=[READY_TO_SEND_TAG],
                quote_date="2026-06-03",
                total=300.0,
                synced_at=synced,
            ),
            EworksQuote(
                eworks_quote_id=104,
                quote_ref="Q-CLOSED",
                customer_name="Closed Co",
                status="9",
                quote_date="2026-06-01",
            ),
        ]
    )
    db_session.commit()

    resp = api_client.get("/api/v1/manager/dashboard")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["categories"]["new_quotes"]["count"] == 1
    assert data["categories"]["awaiting_supplier"]["count"] == 1
    assert data["categories"]["ready_to_send"]["count"] == 1
    assert data["totals"]["all_open_quotes"] == 3
    assert data["last_synced_at"] is not None

    refs = {q["quote_ref"] for q in data["categories"]["new_quotes"]["quotes"]}
    assert refs == {"Q-NEW"}

    body_text = resp.text
    assert "raw_payload" not in body_text
    assert "secret" not in body_text
    for category in data["categories"].values():
        for item in category["quotes"]:
            assert "raw_payload" not in item
            assert set(item.keys()) <= {
                "id",
                "eworks_quote_id",
                "quote_ref",
                "customer_name",
                "status",
                "status_name",
                "tags",
                "quote_date",
                "expiry_date",
                "total",
                "synced_at",
                "matched_reason",
            }


@patch("app.auth.dependencies.settings")
def test_admin_can_access_manager_dashboard(mock_settings, api_client):
    _patch_dev_user(mock_settings, role="admin")
    resp = api_client.get("/api/v1/manager/dashboard")
    assert resp.status_code == 200


@patch("app.auth.dependencies.settings")
def test_engineer_blocked_from_manager_dashboard(mock_settings, api_client):
    _patch_dev_user(mock_settings, role="engineer")
    resp = api_client.get("/api/v1/manager/dashboard")
    assert resp.status_code == 403


@patch("app.auth.dependencies.settings")
def test_estimator_blocked_from_manager_dashboard(mock_settings, api_client):
    _patch_dev_user(mock_settings, role="estimator")
    resp = api_client.get("/api/v1/manager/dashboard")
    assert resp.status_code == 403


@patch("app.auth.dependencies.settings")
def test_manager_dashboard_respects_limit_per_category(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    for i in range(5):
        db_session.add(
            EworksQuote(
                eworks_quote_id=200 + i,
                quote_ref=f"Q-{i}",
                status="1",
                quote_date=f"2026-06-{i + 1:02d}",
            )
        )
    db_session.commit()

    resp = api_client.get("/api/v1/manager/dashboard", params={"limit_per_category": 2})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["categories"]["new_quotes"]["count"] == 5
    assert len(data["categories"]["new_quotes"]["quotes"]) == 2


def _seed_search_quotes(db_session):
    synced = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    db_session.add_all(
        [
            EworksQuote(
                eworks_quote_id=301,
                quote_ref="Q-ALPHA",
                customer_name="Alpha Industries",
                status="1",
                quote_date="2026-06-01",
                synced_at=synced,
            ),
            EworksQuote(
                eworks_quote_id=302,
                quote_ref="Q-BETA",
                customer_name="Beta Services",
                status="1",
                quote_date="2026-06-02",
                synced_at=synced,
            ),
            EworksQuote(
                eworks_quote_id=303,
                quote_ref="Q-GAMMA",
                customer_name="Gamma Ltd",
                status="2",
                tags=[AWAITING_SUPPLIER_TAG, "URGENT"],
                quote_date="2026-06-03",
                synced_at=synced,
            ),
            EworksQuote(
                eworks_quote_id=304,
                quote_ref="Q-DELTA",
                customer_name="Delta Group",
                status="2",
                tags=[READY_TO_SEND_TAG],
                quote_date="2026-06-04",
                synced_at=synced,
                raw_payload={"site": {"address_1": "10 High Street", "city": "London"}},
            ),
        ]
    )
    db_session.commit()


@patch("app.auth.dependencies.settings")
def test_dashboard_without_search_returns_existing_buckets(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    _seed_search_quotes(db_session)

    resp = api_client.get("/api/v1/manager/dashboard")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["categories"]["new_quotes"]["count"] == 2
    assert data["categories"]["awaiting_supplier"]["count"] == 1
    assert data["categories"]["ready_to_send"]["count"] == 1
    assert data["categories"]["new_quotes"]["filtered_count"] is None
    assert len(data["categories"]["new_quotes"]["quotes"]) == 2


@patch("app.auth.dependencies.settings")
def test_search_by_quote_ref_returns_matching_quote(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    _seed_search_quotes(db_session)

    resp = api_client.get("/api/v1/manager/dashboard", params={"search": "Q-ALPHA"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["categories"]["new_quotes"]["count"] == 2
    assert data["categories"]["new_quotes"]["filtered_count"] == 1
    assert [q["quote_ref"] for q in data["categories"]["new_quotes"]["quotes"]] == ["Q-ALPHA"]
    assert data["categories"]["awaiting_supplier"]["filtered_count"] == 0
    assert data["categories"]["ready_to_send"]["filtered_count"] == 0


@patch("app.auth.dependencies.settings")
def test_search_by_customer_returns_matching_quote(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    _seed_search_quotes(db_session)

    resp = api_client.get("/api/v1/manager/dashboard", params={"search": "gamma"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["categories"]["awaiting_supplier"]["count"] == 1
    assert data["categories"]["awaiting_supplier"]["filtered_count"] == 1
    assert data["categories"]["awaiting_supplier"]["quotes"][0]["quote_ref"] == "Q-GAMMA"
    assert data["categories"]["new_quotes"]["filtered_count"] == 0


@patch("app.auth.dependencies.settings")
def test_search_by_tag_returns_matching_quote(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    _seed_search_quotes(db_session)

    resp = api_client.get("/api/v1/manager/dashboard", params={"search": "urgent"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["categories"]["awaiting_supplier"]["filtered_count"] == 1
    assert data["categories"]["awaiting_supplier"]["quotes"][0]["quote_ref"] == "Q-GAMMA"


@patch("app.auth.dependencies.settings")
def test_search_is_case_insensitive(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    _seed_search_quotes(db_session)

    resp = api_client.get("/api/v1/manager/dashboard", params={"search": "high street"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["categories"]["ready_to_send"]["filtered_count"] == 1
    assert data["categories"]["ready_to_send"]["quotes"][0]["quote_ref"] == "Q-DELTA"


@patch("app.auth.dependencies.settings")
def test_search_does_not_expose_raw_payload(mock_settings, api_client, db_session):
    _patch_dev_user(mock_settings, role="manager")
    _seed_search_quotes(db_session)

    resp = api_client.get("/api/v1/manager/dashboard", params={"search": "high street"})
    assert resp.status_code == 200
    assert "raw_payload" not in resp.text
    assert "secret" not in resp.text
