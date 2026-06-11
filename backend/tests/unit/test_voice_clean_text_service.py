"""Unit tests for Azure OpenAI voice transcript cleanup."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import AppError
from app.services import voice_clean_text_service


@pytest.fixture(autouse=True)
def clear_client_cache():
    voice_clean_text_service._azure_openai_cleanup_client.cache_clear()
    yield
    voice_clean_text_service._azure_openai_cleanup_client.cache_clear()


@pytest.fixture
def configured_settings():
    settings = SimpleNamespace(
        voice_cleanup_configured=True,
        azure_openai_endpoint="https://example.openai.azure.com/",
        azure_openai_cleanup_deployment="gpt-4o-mini",
        azure_openai_api_key="test-key",
        azure_openai_cleanup_api_version="2024-10-21",
        azure_openai_use_managed_identity=False,
    )
    with patch.object(voice_clean_text_service, "settings", settings):
        yield settings


def test_clean_voice_text_returns_ai_content(configured_settings):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="  Professional scope text.  "))]
    )

    with patch.object(voice_clean_text_service, "_azure_openai_cleanup_client", return_value=mock_client):
        result = voice_clean_text_service.clean_voice_text(
            "um so like fix the broken door hinge",
            "scope_of_work",
        )

    assert result == "Professional scope text."
    mock_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "gpt-4o-mini"
    messages = call_kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert "scope-of-works" in messages[0]["content"]
    assert "fix the broken door hinge" in messages[1]["content"]


def test_clean_voice_text_uses_context_specific_prompt(configured_settings):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="Clean findings."))]
    )

    with patch.object(voice_clean_text_service, "_azure_openai_cleanup_client", return_value=mock_client):
        voice_clean_text_service.clean_voice_text("leaking pipe under sink", "engineer_findings")

    messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
    assert "engineer findings" in messages[0]["content"]


def test_clean_voice_text_rejects_empty_input(configured_settings):
    with pytest.raises(AppError) as exc_info:
        voice_clean_text_service.clean_voice_text("   ", "internal_notes")

    assert exc_info.value.code == "voice_cleanup_text_empty"
    assert exc_info.value.status_code == 400


def test_clean_voice_text_rejects_too_short_input(configured_settings):
    """Transcript shorter than CLEAN_TEXT_MIN_LENGTH (3) must be rejected."""
    with pytest.raises(AppError) as exc_info:
        voice_clean_text_service.clean_voice_text("um", "scope_of_work")

    assert exc_info.value.code == "voice_cleanup_text_empty"
    assert exc_info.value.status_code == 400


def test_clean_voice_text_rejects_too_long_input(configured_settings):
    with pytest.raises(AppError) as exc_info:
        voice_clean_text_service.clean_voice_text("x" * 8001, "client_description")

    assert exc_info.value.code == "voice_cleanup_text_too_long"
    assert exc_info.value.status_code == 400


def test_clean_voice_text_unconfigured():
    settings = SimpleNamespace(voice_cleanup_configured=False)
    with patch.object(voice_clean_text_service, "settings", settings):
        with pytest.raises(AppError) as exc_info:
            voice_clean_text_service.clean_voice_text("enough text", "manager_review_notes")

    assert exc_info.value.code == "voice_cleanup_unconfigured"
    assert exc_info.value.status_code == 503


def test_clean_voice_text_falls_back_on_meta_response(configured_settings):
    """When the AI returns a meta-prompt instead of cleaned text, the service
    must return the raw validated input unchanged rather than propagating the
    model's instruction string to the frontend."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="Please provide the full dictated text for cleaning."
                )
            )
        ]
    )

    with patch.object(voice_clean_text_service, "_azure_openai_cleanup_client", return_value=mock_client):
        result = voice_clean_text_service.clean_voice_text(
            "  replace kitchen tap  ", "scope_of_work"
        )

    # Should return the validated (stripped) raw input, not the meta-response
    assert result == "replace kitchen tap"


def test_clean_voice_text_falls_back_on_various_meta_responses(configured_settings):
    """Meta-response detection covers a range of common model refusal patterns."""
    meta_responses = [
        "Please enter the dictated text you want cleaned.",
        "Could you please provide the text?",
        "I need the actual transcript to clean.",
        "No text was provided for cleanup.",
        "It seems like no text was supplied.",
    ]
    mock_client = MagicMock()

    for meta_text in meta_responses:
        mock_client.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=meta_text))]
        )
        with patch.object(
            voice_clean_text_service, "_azure_openai_cleanup_client", return_value=mock_client
        ):
            result = voice_clean_text_service.clean_voice_text(
                "leaking pipe under sink", "engineer_findings"
            )
        assert result == "leaking pipe under sink", f"Failed for meta response: {meta_text!r}"


def test_clean_voice_text_handles_api_failure(configured_settings):
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("upstream error")

    with patch.object(voice_clean_text_service, "_azure_openai_cleanup_client", return_value=mock_client):
        with pytest.raises(AppError) as exc_info:
            voice_clean_text_service.clean_voice_text("replace kitchen tap", "scope_of_work")

    assert exc_info.value.code == "voice_cleanup_failed"
    assert exc_info.value.status_code == 502
