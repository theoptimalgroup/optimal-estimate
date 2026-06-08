"""Tests for eWorks quote attachment fetch/backfill sync."""

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
from app.models.eworks_sync import EworksAttachment, EworksQuote
from app.models.user import User
from app.services.eworks_attachment_sync_service import (
    list_attachments_for_parent,
    sync_parent_attachments,
)
from app.services.eworks_quote_attachment_sync_service import (
    backfill_quote_attachments_from_eworks,
    sync_quote_attachments_from_eworks,
)


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in [User.__table__, EworksQuote.__table__, EworksAttachment.__table__]:
        table.create(engine, checkfirst=True)

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
    session.add(admin)
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


def _patch_dev_user(mock_settings, *, role: str, email: str | None = None, name: str | None = None):
    email_map = {
        "admin": "admin@optimal.example",
    }
    mock_settings.auth_provider = "dev"
    mock_settings.dev_auth_enabled = True
    mock_settings.dev_user_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    mock_settings.dev_user_email = email or email_map.get(role, f"{role}@example.com")
    mock_settings.dev_user_name = name or role.title()
    mock_settings.dev_user_role = role
    mock_settings.dev_user_is_active = True
    mock_settings.dev_auth_auto_create_user = False


def _seed_quote(
    db_session,
    *,
    eworks_quote_id: int = 29228,
    quote_ref: str = "Q22124",
    raw_payload: dict | None = None,
) -> EworksQuote:
    quote = EworksQuote(
        eworks_quote_id=eworks_quote_id,
        quote_ref=quote_ref,
        raw_payload=raw_payload or {"id": eworks_quote_id, "quote_ref": quote_ref},
    )
    db_session.add(quote)
    db_session.commit()
    db_session.refresh(quote)
    return quote


@patch("app.services.eworks_attachment_sync_service.settings")
@patch("app.services.eworks_quote_attachment_sync_service.settings")
@patch("app.services.eworks_quote_attachment_sync_service.fetch_quote_attachments")
def test_quote_attachment_endpoint_creates_rows(
    mock_fetch, mock_quote_settings, mock_attachment_settings, db_session
):
    mock_quote_settings.eworks_sync_attachments_enabled = True
    mock_attachment_settings.eworks_sync_attachments_enabled = True
    quote = _seed_quote(db_session)
    mock_fetch.return_value = [
        {
            "id": 901,
            "filename": "scope.pdf",
            "mime_type": "application/pdf",
            "size_bytes": 4096,
            "uploaded_by": "Alice",
            "created_on": "2026-01-01",
            "download_url": "https://eworks.example/files/901",
        }
    ]

    result = sync_quote_attachments_from_eworks(db_session, quote)

    assert result.attachments_extracted == 1
    assert result.attachments_created == 1
    assert result.attachments_updated == 0
    assert "Attachments" in (result.endpoint_called or "")

    attachment = db_session.query(EworksAttachment).one()
    assert attachment.parent_type == "quote"
    assert attachment.parent_eworks_id == 29228
    assert attachment.parent_local_id == quote.id
    assert attachment.filename == "scope.pdf"


@patch("app.services.eworks_attachment_sync_service.settings")
@patch("app.services.eworks_quote_attachment_sync_service.settings")
@patch("app.services.eworks_quote_attachment_sync_service.fetch_quote_detail")
@patch("app.services.eworks_quote_attachment_sync_service.fetch_quote_attachments")
def test_quote_detail_payload_with_attachments_creates_rows(
    mock_fetch, mock_detail, mock_quote_settings, mock_attachment_settings, db_session
):
    mock_quote_settings.eworks_sync_attachments_enabled = True
    mock_attachment_settings.eworks_sync_attachments_enabled = True
    quote = _seed_quote(db_session)
    mock_fetch.return_value = []
    mock_detail.return_value = (
        {
            "id": 29228,
            "quote_ref": "Q22124",
            "Documents": [
                {
                    "document_id": "doc-1",
                    "name": "terms.pdf",
                    "content_type": "application/pdf",
                    "size": 1024,
                }
            ],
        },
        0,
    )

    result = sync_quote_attachments_from_eworks(db_session, quote)

    assert result.detail_fetched is True
    assert result.attachments_created == 1
    assert result.attachment_keys_found == ["Documents"]
    attachment = db_session.query(EworksAttachment).one()
    assert attachment.filename == "terms.pdf"


@patch("app.services.eworks_attachment_sync_service.settings")
def test_quote_list_without_attachment_keys_does_not_create_attachments(mock_settings, db_session):
    mock_settings.eworks_sync_attachments_enabled = True
    quote = _seed_quote(
        db_session,
        raw_payload={"id": 29228, "quote_ref": "Q22124", "status": "Open", "total": 100.0},
    )

    count = sync_parent_attachments(
        db_session,
        parent_type="quote",
        parent_eworks_id=quote.eworks_quote_id,
        parent_local_id=quote.id,
        raw_payload=quote.raw_payload,
    )

    assert count == 0
    assert db_session.query(EworksAttachment).count() == 0


def test_list_attachments_for_parent_matches_by_eworks_id(db_session):
    quote = _seed_quote(db_session, eworks_quote_id=8001, quote_ref="Q-8001")
    db_session.add(
        EworksAttachment(
            eworks_attachment_id="att-parent-eworks",
            parent_type="quote",
            parent_eworks_id=8001,
            parent_local_id=None,
            filename="invoice.pdf",
            mime_type="application/pdf",
        )
    )
    db_session.commit()

    rows = list_attachments_for_parent(
        db_session,
        parent_type="quote",
        parent_local_id=quote.id,
        parent_eworks_id=quote.eworks_quote_id,
    )
    assert len(rows) == 1
    assert rows[0].filename == "invoice.pdf"


@patch("app.services.eworks_attachment_sync_service.settings")
@patch("app.services.eworks_quote_attachment_sync_service.settings")
@patch("app.services.eworks_quote_attachment_sync_service.fetch_quote_attachments")
@patch("app.auth.dependencies.settings")
def test_backfill_endpoint_returns_summary_fields(
    mock_auth_settings, mock_fetch, mock_quote_settings, mock_attachment_settings, api_client, db_session
):
    _patch_dev_user(mock_auth_settings, role="admin")
    mock_quote_settings.eworks_sync_attachments_enabled = True
    mock_attachment_settings.eworks_sync_attachments_enabled = True
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr("app.core.config.settings.eworks_api_enabled", True)
    monkeypatch.setattr("app.core.config.settings.eworks_sync_attachments_enabled", True)
    try:
        _seed_quote(db_session, eworks_quote_id=29228, quote_ref="Q22124")
        _seed_quote(db_session, eworks_quote_id=29229, quote_ref="Q22125")
        mock_fetch.side_effect = [
            [{"id": 1, "filename": "a.pdf", "mime_type": "application/pdf"}],
            [],
        ]

        resp = api_client.post("/api/v1/eworks-sync/quotes/backfill-attachments?limit=5")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["quotes_scanned"] == 2
        assert data["attachment_endpoint_calls"] == 2
        assert data["quotes_with_attachments"] == 1
        assert data["attachments_created"] == 1
        assert data["attachments_updated"] == 0
        assert "raw_payload" not in resp.text
        assert "EWORKS_API_KEY" not in resp.text
    finally:
        monkeypatch.undo()


@patch("app.services.eworks_attachment_sync_service.settings")
@patch("app.services.eworks_quote_attachment_sync_service.settings")
@patch("app.services.eworks_quote_attachment_sync_service.fetch_quote_detail")
@patch("app.services.eworks_quote_attachment_sync_service.fetch_quote_attachments")
def test_backfill_service_counts_failures(mock_fetch, mock_detail, mock_quote_settings, mock_attachment_settings, db_session):
    mock_quote_settings.eworks_sync_attachments_enabled = True
    mock_attachment_settings.eworks_sync_attachments_enabled = True
    _seed_quote(db_session, eworks_quote_id=29228, quote_ref="Q22124")
    mock_fetch.side_effect = RuntimeError("attachment API unavailable")
    mock_detail.side_effect = RuntimeError("detail API unavailable")

    summary = backfill_quote_attachments_from_eworks(db_session, limit=1)

    assert summary.quotes_scanned == 1
    assert summary.attachment_endpoint_calls == 1
    assert summary.failed == 1
