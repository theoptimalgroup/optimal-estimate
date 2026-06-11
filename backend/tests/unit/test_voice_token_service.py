"""Unit tests for ElevenLabs token generation."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.core.exceptions import AppError
from app.services import voice_token_service


@pytest.fixture
def configured_settings():
    settings = SimpleNamespace(
        voice_dictation_configured=True,
        elevenlabs_api_key="test-elevenlabs-key",
    )
    with patch.object(voice_token_service, "settings", settings):
        yield settings


def test_create_elevenlabs_scribe_token_returns_token(configured_settings, caplog):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"token": "single-use-token"}

    with patch("app.services.voice_token_service.httpx.post", return_value=mock_response) as mock_post:
        with caplog.at_level("INFO"):
            token = voice_token_service.create_elevenlabs_scribe_token()

    assert token == "single-use-token"
    mock_post.assert_called_once()
    assert mock_post.call_args.kwargs["headers"]["xi-api-key"] == "test-elevenlabs-key"
    assert "ElevenLabs Scribe token received successfully" in caplog.text
    assert "single-use-token" not in caplog.text
    assert "test-elevenlabs-key" not in caplog.text


def test_create_elevenlabs_scribe_token_unconfigured(caplog):
    settings = SimpleNamespace(voice_dictation_configured=False, elevenlabs_api_key=None)
    with patch.object(voice_token_service, "settings", settings):
        with caplog.at_level("WARNING"):
            with pytest.raises(AppError) as exc_info:
                voice_token_service.create_elevenlabs_scribe_token()

    assert exc_info.value.code == "voice_token_unconfigured"
    assert exc_info.value.status_code == 503
    assert "ELEVENLABS_API_KEY configured=False" in caplog.text


def test_create_elevenlabs_scribe_token_handles_upstream_error(configured_settings, caplog):
    mock_response = MagicMock()
    mock_response.status_code = 401
    error = httpx.HTTPStatusError("Unauthorized", request=MagicMock(), response=mock_response)

    with patch("app.services.voice_token_service.httpx.post", side_effect=error):
        with caplog.at_level("WARNING"):
            with pytest.raises(AppError) as exc_info:
                voice_token_service.create_elevenlabs_scribe_token()

    assert exc_info.value.code == "voice_token_upstream_error"
    assert exc_info.value.status_code == 502
    assert "ElevenLabs token upstream error status_code=401" in caplog.text
