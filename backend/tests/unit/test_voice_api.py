"""Unit tests for voice dictation API."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import UserRole, get_password_hash
from app.db.session import get_db
from app.main import app
from app.models.calculation_session import CalculationSession
from app.models.client import Client
from app.models.rate_rule import RateRule
from app.models.trade import Trade
from app.models.user import User


def _patch_dev_user(mock_settings, *, role: str = "estimator"):
    mock_settings.dev_auth_enabled = True
    mock_settings.dev_user_id = "dev-user-1"
    mock_settings.dev_user_email = "staff@optimal.example"
    mock_settings.dev_user_name = "Staff User"
    mock_settings.dev_user_role = role
    mock_settings.dev_user_is_active = True
    mock_settings.dev_auth_auto_create_user = False
    mock_settings.auth_provider = "dev"


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for model in (User, Client, Trade, RateRule, CalculationSession):
        model.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    now = datetime.now(timezone.utc)
    session.add(
        User(
            id=uuid4(),
            email="staff@optimal.example",
            full_name="Staff User",
            role=UserRole.ESTIMATOR.value,
            password_hash=get_password_hash("password"),
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    )
    session.commit()
    yield session
    session.close()


@pytest.fixture()
def voice_client(db_session):
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
@patch("app.api.v1.voice.create_elevenlabs_scribe_token", return_value="scribe-token-123")
def test_get_elevenlabs_token_returns_token(mock_create_token, mock_settings, voice_client, caplog):
    _patch_dev_user(mock_settings, role="estimator")
    with caplog.at_level("INFO"):
        response = voice_client.get("/api/v1/voice/elevenlabs-token")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["token"] == "scribe-token-123"
    mock_create_token.assert_called_once()
    assert "GET /api/v1/voice/elevenlabs-token called" in caplog.text
    assert "ElevenLabs token creation succeeded" in caplog.text
    assert "scribe-token-123" not in caplog.text


@patch("app.auth.dependencies.settings")
@patch("app.api.v1.voice.create_elevenlabs_scribe_token")
def test_get_elevenlabs_token_propagates_service_error(mock_create_token, mock_settings, voice_client, caplog):
    from app.core.exceptions import AppError

    mock_create_token.side_effect = AppError("voice_token_unconfigured", "Voice dictation is not configured", 503)
    _patch_dev_user(mock_settings, role="estimator")
    with caplog.at_level("WARNING"):
        response = voice_client.get("/api/v1/voice/elevenlabs-token")
    assert response.status_code == 503
    assert response.json()["detail"] == "Voice dictation is not configured"
    assert "ElevenLabs token creation failed" in caplog.text


@patch("app.auth.dependencies.settings")
@patch("app.api.v1.voice.clean_voice_text", return_value="Replace the kitchen tap and test for leaks.")
def test_clean_text_returns_cleaned_text(mock_clean, mock_settings, voice_client):
    _patch_dev_user(mock_settings, role="engineer")
    response = voice_client.post(
        "/api/v1/voice/clean-text",
        json={"text": "um replace kitchen tap and test for leaks", "context": "scope_of_work"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["text"] == "Replace the kitchen tap and test for leaks."
    mock_clean.assert_called_once_with("um replace kitchen tap and test for leaks", "scope_of_work")


@patch("app.auth.dependencies.settings")
def test_clean_text_rejects_invalid_context(mock_settings, voice_client):
    _patch_dev_user(mock_settings, role="estimator")
    response = voice_client.post(
        "/api/v1/voice/clean-text",
        json={"text": "some dictated text", "context": "invalid_context"},
    )
    assert response.status_code == 422


@patch("app.auth.dependencies.settings")
def test_voice_endpoints_require_auth(mock_settings, voice_client):
    mock_settings.dev_auth_enabled = False
    mock_settings.auth_provider = "dev"
    response = voice_client.get("/api/v1/voice/elevenlabs-token")
    assert response.status_code == 401
