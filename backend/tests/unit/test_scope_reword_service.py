"""Unit tests for Azure OpenAI scope rewording."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import AppError
from app.services import scope_reword_service


@pytest.fixture(autouse=True)
def clear_client_cache():
    scope_reword_service._azure_openai_client.cache_clear()
    yield
    scope_reword_service._azure_openai_client.cache_clear()


@pytest.fixture
def enabled_settings():
    settings = SimpleNamespace(
        effective_scope_reword_enabled=True,
        scope_reword_configured=True,
        azure_openai_endpoint="https://example.openai.azure.com/",
        azure_openai_deployment="gpt-4o-mini",
        azure_openai_api_key="test-key",
        azure_openai_api_version="2024-10-21",
        azure_openai_use_managed_identity=False,
    )
    with patch.object(scope_reword_service, "settings", settings):
        yield settings


def test_reword_scope_text_returns_ai_content(enabled_settings):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="  Professional scope text.  "))]
    )

    with patch.object(scope_reword_service, "_azure_openai_client", return_value=mock_client):
        result = scope_reword_service.reword_scope_text("fix broken door hinge and replace lock")

    assert result == "Professional scope text."
    mock_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "gpt-4o-mini"
    assert call_kwargs["temperature"] == 0.3
    messages = call_kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert "British English" in messages[0]["content"]
    assert "fix broken door hinge and replace lock" in messages[1]["content"]


def test_reword_scope_text_rejects_empty_input(enabled_settings):
    with pytest.raises(AppError) as exc_info:
        scope_reword_service.reword_scope_text("   ")

    assert exc_info.value.code == "scope_reword_text_too_short"
    assert exc_info.value.status_code == 400


def test_reword_scope_text_rejects_too_long_input(enabled_settings):
    with pytest.raises(AppError) as exc_info:
        scope_reword_service.reword_scope_text("x" * 4001)

    assert exc_info.value.code == "scope_reword_text_too_long"
    assert exc_info.value.status_code == 400


def test_reword_scope_text_disabled():
    settings = SimpleNamespace(effective_scope_reword_enabled=False)
    with patch.object(scope_reword_service, "settings", settings):
        with pytest.raises(AppError) as exc_info:
            scope_reword_service.reword_scope_text("enough text here")

    assert exc_info.value.code == "scope_reword_disabled"
    assert exc_info.value.status_code == 503


def test_reword_scope_text_handles_api_failure(enabled_settings):
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("upstream error")

    with patch.object(scope_reword_service, "_azure_openai_client", return_value=mock_client):
        with pytest.raises(AppError) as exc_info:
            scope_reword_service.reword_scope_text("replace kitchen tap and test for leaks")

    assert exc_info.value.code == "scope_reword_failed"
    assert exc_info.value.status_code == 502


def test_reword_scope_text_handles_empty_ai_response(enabled_settings):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="   "))]
    )

    with patch.object(scope_reword_service, "_azure_openai_client", return_value=mock_client):
        with pytest.raises(AppError) as exc_info:
            scope_reword_service.reword_scope_text("replace kitchen tap and test for leaks")

    assert exc_info.value.code == "scope_reword_empty_response"
    assert exc_info.value.status_code == 502
