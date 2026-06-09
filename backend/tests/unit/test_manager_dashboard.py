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
    AWAITING_DESKTOP_INFO_TAG,
    AWAITING_INTERNAL_INFO_TAG,
    AWAITING_SUPPLIER_TAG,
    BOOKED_TAG,
    MUST_ATTEND_TAG,
    READY_TO_SEND_TAG,
    classify_eworks_quote_bucket,
    extract_all_tags,
    is_awaiting_desktop_info_tag,
    is_awaiting_internal_info_tag,
    is_awaiting_supplier_tag,
    is_booked_tag,
    is_must_attend_tag,
    is_ready_to_send_tag,
    normalize_tag_text,
)
from app.services.quote_search_service import quote_is_draft


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
# quote_is_draft() unit tests
# ---------------------------------------------------------------------------


def test_quote_is_draft_true_for_status_1_string():
    assert quote_is_draft(_make_quote(status="1")) is True


def test_quote_is_draft_true_for_status_1_int():
    assert quote_is_draft(_make_quote(status=1)) is True


def test_quote_is_draft_false_for_status_2():
    assert quote_is_draft(_make_quote(status="2")) is False


def test_quote_is_draft_false_for_status_3():
    assert quote_is_draft(_make_quote(status="3")) is False


def test_quote_is_draft_false_for_status_4():
    assert quote_is_draft(_make_quote(status="4")) is False


def test_quote_is_draft_false_for_status_5():
    assert quote_is_draft(_make_quote(status="5")) is False


def test_quote_is_draft_false_for_status_9():
    assert quote_is_draft(_make_quote(status="9")) is False


def test_quote_is_draft_true_from_raw_payload_status():
    quote = _make_quote(status=None, raw_payload={"status": "1"})
    assert quote_is_draft(quote) is True


def test_quote_is_draft_true_from_raw_payload_Status_capitalized():
    quote = _make_quote(status=None, raw_payload={"Status": 1})
    assert quote_is_draft(quote) is True


def test_quote_is_draft_true_from_raw_quote_status_id():
    quote = _make_quote(status=None, raw_payload={"quote_status": {"id": 1}})
    assert quote_is_draft(quote) is True


def test_quote_is_draft_true_from_raw_quote_status_status():
    quote = _make_quote(status=None, raw_payload={"quote_status": {"status": "1"}})
    assert quote_is_draft(quote) is True


def test_quote_is_draft_true_from_raw_quote_status_id_camel():
    quote = _make_quote(status=None, raw_payload={"QuoteStatus": {"id": "1"}})
    assert quote_is_draft(quote) is True


def test_quote_is_draft_false_when_no_status_fields():
    quote = _make_quote(status=None, status_name=None, raw_payload=None)
    assert quote_is_draft(quote) is False


def test_quote_is_draft_does_not_use_status_name():
    """status_name alone does not determine draft status."""
    quote = _make_quote(status=None, status_name="1")
    assert quote_is_draft(quote) is False


# ---------------------------------------------------------------------------
# Classification unit tests
# ---------------------------------------------------------------------------


def test_classify_status_one_as_new_quotes():
    quote = _make_quote(status="1", status_name="New")
    assert classify_eworks_quote_bucket(quote) == "new_quotes"


def test_classify_awaiting_supplier_tag_with_draft():
    """Draft (status=1) + awaiting supplier tag → awaiting_supplier."""
    quote = _make_quote(status="1", tags=[AWAITING_SUPPLIER_TAG])
    assert classify_eworks_quote_bucket(quote) == "awaiting_supplier"


def test_classify_ready_to_send_tag_with_draft():
    """Draft (status=1) + ready to send tag → ready_to_send."""
    quote = _make_quote(status="1", tags=[READY_TO_SEND_TAG])
    assert classify_eworks_quote_bucket(quote) == "ready_to_send"


def test_classify_awaiting_supplier_tag_non_draft_excluded():
    """Non-draft (status=2) is excluded even with awaiting supplier tag."""
    quote = _make_quote(status="2", tags=[AWAITING_SUPPLIER_TAG])
    assert classify_eworks_quote_bucket(quote) is None


def test_classify_ready_to_send_tag_non_draft_excluded():
    """Non-draft (status=2) is excluded even with ready to send tag."""
    quote = _make_quote(status="2", tags=[READY_TO_SEND_TAG])
    assert classify_eworks_quote_bucket(quote) is None


def test_classify_non_draft_no_tags_excluded():
    """Non-draft (status=2) with no tags is excluded."""
    quote = _make_quote(status="2")
    assert classify_eworks_quote_bucket(quote) is None


def test_classify_non_draft_status3_awaiting_excluded():
    """status=3 + awaiting tag → excluded."""
    quote = _make_quote(status="3", tags=[AWAITING_SUPPLIER_TAG])
    assert classify_eworks_quote_bucket(quote) is None


def test_classify_non_draft_status4_ready_excluded():
    """status=4 + ready tag → excluded."""
    quote = _make_quote(status="4", tags=[READY_TO_SEND_TAG])
    assert classify_eworks_quote_bucket(quote) is None


def test_classify_non_draft_status5_ready_excluded():
    """status=5 + ready tag → excluded."""
    quote = _make_quote(status="5", tags=[READY_TO_SEND_TAG])
    assert classify_eworks_quote_bucket(quote) is None


def test_classify_non_draft_status9_awaiting_excluded():
    """status=9 + awaiting tag → excluded."""
    quote = _make_quote(status="9", tags=[AWAITING_SUPPLIER_TAG])
    assert classify_eworks_quote_bucket(quote) is None


def test_classify_draft_with_random_tag_only_returns_none():
    """Draft (status=1) with only unrecognised tags is not shown."""
    quote = _make_quote(status="1", tags=["BILLIE"])
    assert classify_eworks_quote_bucket(quote) is None


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
    """Draft with only unrecognised tags → not shown (None)."""
    quote = _make_quote(status="1", tags=["URGENT", "Electrical"])
    assert classify_eworks_quote_bucket(quote) is None


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
    quote = _make_quote(status="1", tags=[f"  {AWAITING_SUPPLIER_TAG.upper()}  "])
    assert classify_eworks_quote_bucket(quote) == "awaiting_supplier"


def test_classify_status_string_one_same_as_int():
    quote_str = _make_quote(status="1")
    quote_int = _make_quote(status=1, eworks_quote_id=2)
    assert classify_eworks_quote_bucket(quote_str) == "new_quotes"
    assert classify_eworks_quote_bucket(quote_int) == "new_quotes"


def test_classify_status_one_from_status_name_does_not_count():
    """status_name alone is not used by quote_is_draft — returns None."""
    quote = _make_quote(status=None, status_name="1")
    assert classify_eworks_quote_bucket(quote) is None


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
    """When both bucket tags present (and draft), ready_to_send wins."""
    quote = _make_quote(status="1", tags=[AWAITING_SUPPLIER_TAG, READY_TO_SEND_TAG])
    assert classify_eworks_quote_bucket(quote) == "ready_to_send"


def test_classify_unrelated_quote_returns_none():
    quote = _make_quote(status="5", tags=["Other"])
    assert classify_eworks_quote_bucket(quote) is None


# ---------------------------------------------------------------------------
# Dashboard endpoint tests
# ---------------------------------------------------------------------------


def test_classify_tag_from_raw_payload_labels_non_draft_excluded():
    """Non-draft quote with ready_to_send label in raw_payload is excluded."""
    quote = _make_quote(
        status="5",
        tags=None,
        raw_payload={"labels": [READY_TO_SEND_TAG]},
    )
    assert classify_eworks_quote_bucket(quote) is None


def test_classify_tag_from_raw_payload_labels_draft_classified():
    """Draft quote with ready_to_send label in raw_payload is classified."""
    quote = _make_quote(
        status="1",
        tags=None,
        raw_payload={"labels": [READY_TO_SEND_TAG]},
    )
    assert classify_eworks_quote_bucket(quote) == "ready_to_send"


def test_classify_tag_from_json_string_tags_column_non_draft_excluded():
    """Non-draft quote with awaiting tag as JSON string is excluded."""
    quote = _make_quote(
        status="5",
        tags=f'["{AWAITING_SUPPLIER_TAG}"]',
    )
    assert classify_eworks_quote_bucket(quote) is None


def test_classify_tag_from_json_string_tags_column_draft_classified():
    """Draft quote with awaiting tag as JSON string is classified."""
    quote = _make_quote(
        status="1",
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
                status="1",
                tags=[AWAITING_SUPPLIER_TAG],
                quote_date="2026-06-02",
                total=200.0,
                synced_at=synced,
            ),
            EworksQuote(
                eworks_quote_id=103,
                quote_ref="Q-READY",
                customer_name="Ready Co",
                status="1",
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
def test_dashboard_includes_quotes_excluded_non_draft(mock_settings, api_client, db_session):
    """API response includes quotes_excluded_non_draft count."""
    _patch_dev_user(mock_settings, role="manager")
    synced = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    db_session.add_all(
        [
            EworksQuote(
                eworks_quote_id=501,
                quote_ref="Q-DRAFT",
                status="1",
                quote_date="2026-06-01",
                synced_at=synced,
            ),
            EworksQuote(
                eworks_quote_id=502,
                quote_ref="Q-NON-DRAFT",
                status="2",
                quote_date="2026-06-01",
                synced_at=synced,
            ),
            EworksQuote(
                eworks_quote_id=503,
                quote_ref="Q-CLOSED",
                status="9",
                quote_date="2026-06-01",
                synced_at=synced,
            ),
        ]
    )
    db_session.commit()

    resp = api_client.get("/api/v1/manager/dashboard")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "quotes_excluded_non_draft" in data
    assert data["quotes_excluded_non_draft"] == 2


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
                status="1",
                tags=[AWAITING_SUPPLIER_TAG, "URGENT"],
                quote_date="2026-06-03",
                synced_at=synced,
            ),
            EworksQuote(
                eworks_quote_id=304,
                quote_ref="Q-DELTA",
                customer_name="Delta Group",
                status="1",
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


@patch("app.auth.dependencies.settings")
def test_dashboard_search_excludes_non_draft_quotes(mock_settings, api_client, db_session):
    """Non-draft quotes do not appear in search results even if they match the query."""
    _patch_dev_user(mock_settings, role="manager")
    synced = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    db_session.add_all(
        [
            EworksQuote(
                eworks_quote_id=601,
                quote_ref="Q-DRAFT-MATCH",
                customer_name="Match Corp",
                status="1",
                quote_date="2026-06-01",
                synced_at=synced,
            ),
            EworksQuote(
                eworks_quote_id=602,
                quote_ref="Q-NONDRAFT-MATCH",
                customer_name="Match Corp",
                status="2",
                quote_date="2026-06-01",
                synced_at=synced,
            ),
        ]
    )
    db_session.commit()

    resp = api_client.get("/api/v1/manager/dashboard", params={"search": "match corp"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    # Only the draft quote should appear
    assert data["categories"]["new_quotes"]["filtered_count"] == 1
    assert data["categories"]["new_quotes"]["quotes"][0]["quote_ref"] == "Q-DRAFT-MATCH"
    assert data["quotes_excluded_non_draft"] == 1


# ---------------------------------------------------------------------------
# New tag-based bucket classification tests
# ---------------------------------------------------------------------------


def test_classify_must_attend_tag_with_draft():
    """Draft + Must Attend tag → must_attend bucket."""
    quote = _make_quote(status="1", tags=[MUST_ATTEND_TAG])
    assert classify_eworks_quote_bucket(quote) == "must_attend"


def test_classify_booked_tag_with_draft():
    """Draft + Booked tag → booked bucket."""
    quote = _make_quote(status="1", tags=[BOOKED_TAG])
    assert classify_eworks_quote_bucket(quote) == "booked"


def test_classify_awaiting_desktop_info_tag_with_draft():
    """Draft + Awaiting Desktop Info tag → awaiting_desktop_info bucket."""
    quote = _make_quote(status="1", tags=[AWAITING_DESKTOP_INFO_TAG])
    assert classify_eworks_quote_bucket(quote) == "awaiting_desktop_info"


def test_classify_awaiting_internal_info_tag_with_draft():
    """Draft + Awaiting Internal Info tag → awaiting_internal_info bucket."""
    quote = _make_quote(status="1", tags=[AWAITING_INTERNAL_INFO_TAG])
    assert classify_eworks_quote_bucket(quote) == "awaiting_internal_info"


def test_classify_must_attend_tag_non_draft_excluded():
    """Non-draft + Must Attend tag → excluded (None)."""
    quote = _make_quote(status="2", tags=[MUST_ATTEND_TAG])
    assert classify_eworks_quote_bucket(quote) is None


def test_classify_booked_tag_non_draft_excluded():
    """Non-draft + Booked tag → excluded (None)."""
    quote = _make_quote(status="2", tags=[BOOKED_TAG])
    assert classify_eworks_quote_bucket(quote) is None


def test_classify_priority_ready_over_must_attend():
    """Draft + Ready to Send + Must Attend → ready_to_send wins."""
    quote = _make_quote(status="1", tags=[READY_TO_SEND_TAG, MUST_ATTEND_TAG])
    assert classify_eworks_quote_bucket(quote) == "ready_to_send"


def test_classify_priority_booked_over_must_attend():
    """Draft + Booked + Must Attend → booked wins."""
    quote = _make_quote(status="1", tags=[BOOKED_TAG, MUST_ATTEND_TAG])
    assert classify_eworks_quote_bucket(quote) == "booked"


def test_classify_priority_awaiting_supplier_over_awaiting_desktop():
    """Draft + Awaiting Supplier + Awaiting Desktop Info → awaiting_supplier wins."""
    quote = _make_quote(status="1", tags=[AWAITING_SUPPLIER_TAG, AWAITING_DESKTOP_INFO_TAG])
    assert classify_eworks_quote_bucket(quote) == "awaiting_supplier"


def test_is_must_attend_tag_case_insensitive():
    assert is_must_attend_tag("MUST ATTEND (QUOTES)")
    assert is_must_attend_tag("Must Attend (Quotes)")
    assert is_must_attend_tag("must attend")


def test_is_booked_tag_case_insensitive():
    assert is_booked_tag("BOOKED (QUOTES)")
    assert is_booked_tag("Booked (Quotes)")


def test_is_awaiting_desktop_info_tag_case_insensitive():
    assert is_awaiting_desktop_info_tag("AWAITING DESKTOP INFO (QUOTES)")
    assert is_awaiting_desktop_info_tag("Awaiting Desktop Info (Quotes)")


def test_is_awaiting_internal_info_tag_case_insensitive():
    assert is_awaiting_internal_info_tag("AWAITING INTERNAL INFO (QUOTES)")
    assert is_awaiting_internal_info_tag("Awaiting Internal Info (Quotes)")


@patch("app.auth.dependencies.settings")
def test_dashboard_api_includes_all_seven_bucket_categories(mock_settings, api_client):
    """API response categories include all 7 bucket keys."""
    _patch_dev_user(mock_settings, role="manager")
    resp = api_client.get("/api/v1/manager/dashboard")
    assert resp.status_code == 200
    data = resp.json()["data"]
    expected_buckets = {
        "new_quotes",
        "awaiting_supplier",
        "ready_to_send",
        "booked",
        "must_attend",
        "awaiting_desktop_info",
        "awaiting_internal_info",
    }
    assert set(data["categories"].keys()) == expected_buckets


@patch("app.auth.dependencies.settings")
def test_dashboard_bucketed_quotes_total_includes_all_seven_buckets(
    mock_settings, api_client, db_session
):
    """totals.all_open_quotes sums across all 7 buckets."""
    _patch_dev_user(mock_settings, role="manager")
    synced = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    db_session.add_all(
        [
            EworksQuote(
                eworks_quote_id=701,
                quote_ref="Q-NEW",
                status="1",
                quote_date="2026-06-01",
                synced_at=synced,
            ),
            EworksQuote(
                eworks_quote_id=702,
                quote_ref="Q-AWAIT",
                status="1",
                tags=[AWAITING_SUPPLIER_TAG],
                quote_date="2026-06-01",
                synced_at=synced,
            ),
            EworksQuote(
                eworks_quote_id=703,
                quote_ref="Q-READY",
                status="1",
                tags=[READY_TO_SEND_TAG],
                quote_date="2026-06-01",
                synced_at=synced,
            ),
            EworksQuote(
                eworks_quote_id=704,
                quote_ref="Q-BOOKED",
                status="1",
                tags=[BOOKED_TAG],
                quote_date="2026-06-01",
                synced_at=synced,
            ),
            EworksQuote(
                eworks_quote_id=705,
                quote_ref="Q-MUST",
                status="1",
                tags=[MUST_ATTEND_TAG],
                quote_date="2026-06-01",
                synced_at=synced,
            ),
            EworksQuote(
                eworks_quote_id=706,
                quote_ref="Q-DESKTOP",
                status="1",
                tags=[AWAITING_DESKTOP_INFO_TAG],
                quote_date="2026-06-01",
                synced_at=synced,
            ),
            EworksQuote(
                eworks_quote_id=707,
                quote_ref="Q-INTERNAL",
                status="1",
                tags=[AWAITING_INTERNAL_INFO_TAG],
                quote_date="2026-06-01",
                synced_at=synced,
            ),
        ]
    )
    db_session.commit()

    resp = api_client.get("/api/v1/manager/dashboard")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["totals"]["all_open_quotes"] == 7
    assert data["categories"]["booked"]["count"] == 1
    assert data["categories"]["must_attend"]["count"] == 1
    assert data["categories"]["awaiting_desktop_info"]["count"] == 1
    assert data["categories"]["awaiting_internal_info"]["count"] == 1


@patch("app.auth.dependencies.settings")
def test_search_finds_quotes_in_new_buckets(mock_settings, api_client, db_session):
    """Search by customer name works across all new buckets."""
    _patch_dev_user(mock_settings, role="manager")
    synced = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    db_session.add_all(
        [
            EworksQuote(
                eworks_quote_id=801,
                quote_ref="Q-BOOKED-SEARCH",
                customer_name="Foxglove Ltd",
                status="1",
                tags=[BOOKED_TAG],
                quote_date="2026-06-01",
                synced_at=synced,
            ),
            EworksQuote(
                eworks_quote_id=802,
                quote_ref="Q-MUST-SEARCH",
                customer_name="Redwood Corp",
                status="1",
                tags=[MUST_ATTEND_TAG],
                quote_date="2026-06-01",
                synced_at=synced,
            ),
            EworksQuote(
                eworks_quote_id=803,
                quote_ref="Q-DESKTOP-SEARCH",
                customer_name="Pinewood Inc",
                status="1",
                tags=[AWAITING_DESKTOP_INFO_TAG],
                quote_date="2026-06-01",
                synced_at=synced,
            ),
            EworksQuote(
                eworks_quote_id=804,
                quote_ref="Q-INTERNAL-SEARCH",
                customer_name="Elmwood PLC",
                status="1",
                tags=[AWAITING_INTERNAL_INFO_TAG],
                quote_date="2026-06-01",
                synced_at=synced,
            ),
        ]
    )
    db_session.commit()

    for ref, bucket, term in [
        ("Q-BOOKED-SEARCH", "booked", "foxglove"),
        ("Q-MUST-SEARCH", "must_attend", "redwood"),
        ("Q-DESKTOP-SEARCH", "awaiting_desktop_info", "pinewood"),
        ("Q-INTERNAL-SEARCH", "awaiting_internal_info", "elmwood"),
    ]:
        resp = api_client.get("/api/v1/manager/dashboard", params={"search": term})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["categories"][bucket]["filtered_count"] == 1, f"bucket={bucket} term={term}"
        assert data["categories"][bucket]["quotes"][0]["quote_ref"] == ref
