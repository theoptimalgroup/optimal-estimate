"""ElevenLabs single-use Scribe token generation."""

from __future__ import annotations

import logging

import httpx

from app.core.config import settings
from app.core.exceptions import AppError

logger = logging.getLogger(__name__)

ELEVENLABS_TOKEN_URL = "https://api.elevenlabs.io/v1/single-use-token/realtime_scribe"


def create_elevenlabs_scribe_token() -> str:
    if not settings.voice_dictation_configured:
        logger.warning(
            "ElevenLabs token creation skipped: ELEVENLABS_API_KEY configured=%s",
            settings.voice_dictation_configured,
        )
        raise AppError(
            "voice_token_unconfigured",
            "Voice dictation is not configured",
            status_code=503,
        )

    logger.info(
        "Requesting ElevenLabs Scribe token ELEVENLABS_API_KEY configured=%s",
        settings.voice_dictation_configured,
    )

    try:
        response = httpx.post(
            ELEVENLABS_TOKEN_URL,
            headers={"xi-api-key": settings.elevenlabs_api_key or ""},
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "ElevenLabs token upstream error status_code=%s",
            exc.response.status_code,
        )
        raise AppError(
            "voice_token_upstream_error",
            "Failed to create ElevenLabs token",
            status_code=502,
            details={"status_code": exc.response.status_code},
        ) from exc
    except Exception as exc:
        logger.warning("ElevenLabs token request failed reason=%s", type(exc).__name__)
        raise AppError(
            "voice_token_failed",
            "Failed to create ElevenLabs token",
            status_code=502,
            details={"reason": str(exc)},
        ) from exc

    token = data.get("token") if isinstance(data, dict) else None
    if not token or not str(token).strip():
        logger.warning("ElevenLabs token response missing token field")
        raise AppError(
            "voice_token_empty_response",
            "ElevenLabs returned an empty token",
            status_code=502,
        )

    logger.info("ElevenLabs Scribe token received successfully")
    return str(token).strip()
