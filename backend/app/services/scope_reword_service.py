"""Reword Scope of Works text via Azure OpenAI."""

from __future__ import annotations

from functools import lru_cache

from openai import AzureOpenAI

from app.core.config import settings
from app.core.exceptions import AppError

SCOPE_REWORD_MIN_LENGTH = 10
SCOPE_REWORD_MAX_LENGTH = 4000

SYSTEM_PROMPT = """You reword scope-of-works text for professional UK building-services quotes.

Rules:
- Use British English.
- Keep every factual detail, work item, material, measurement, and constraint.
- Do not add, remove, or invent work.
- Improve clarity, grammar, and client-facing tone.
- Return only the reworded scope text with no preamble or explanation."""

USER_PROMPT_TEMPLATE = "Reword the following scope of works:\n\n{text}"


def _normalize_azure_openai_endpoint(endpoint: str) -> str:
    """Strip portal copy-paste paths so the SDK receives the resource base URL."""
    base = endpoint.strip().rstrip("/")
    for suffix in ("/openai/v1/responses", "/openai/v1", "/openai"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    return base.rstrip("/")


@lru_cache
def _azure_openai_client() -> AzureOpenAI:
    if not settings.scope_reword_configured:
        raise AppError(
            "scope_reword_unconfigured",
            "Scope rewording is not configured",
            status_code=503,
        )

    endpoint = _normalize_azure_openai_endpoint(settings.azure_openai_endpoint or "")
    if settings.azure_openai_use_managed_identity:
        from azure.identity import DefaultAzureCredential

        credential = DefaultAzureCredential()
        return AzureOpenAI(
            azure_endpoint=endpoint,
            azure_ad_token_provider=lambda: credential.get_token(
                "https://cognitiveservices.azure.com/.default"
            ).token,
            api_version=settings.azure_openai_api_version,
        )

    return AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
    )


def _validate_scope_text(text: str) -> str:
    trimmed = text.strip()
    if len(trimmed) < SCOPE_REWORD_MIN_LENGTH:
        raise AppError(
            "scope_reword_text_too_short",
            f"Scope text must be at least {SCOPE_REWORD_MIN_LENGTH} characters",
            status_code=400,
        )
    if len(trimmed) > SCOPE_REWORD_MAX_LENGTH:
        raise AppError(
            "scope_reword_text_too_long",
            f"Scope text must be at most {SCOPE_REWORD_MAX_LENGTH} characters",
            status_code=400,
        )
    return trimmed


def reword_scope_text(text: str) -> str:
    if not settings.effective_scope_reword_enabled:
        raise AppError(
            "scope_reword_disabled",
            "Scope rewording is disabled",
            status_code=503,
        )

    validated = _validate_scope_text(text)
    client = _azure_openai_client()

    try:
        response = client.chat.completions.create(
            model=settings.azure_openai_deployment,
            temperature=0.3,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT_TEMPLATE.format(text=validated)},
            ],
        )
    except Exception as exc:
        raise AppError(
            "scope_reword_failed",
            "Failed to reword scope text",
            status_code=502,
            details={"reason": str(exc)},
        ) from exc

    content = response.choices[0].message.content if response.choices else None
    if not content or not content.strip():
        raise AppError(
            "scope_reword_empty_response",
            "AI returned an empty response",
            status_code=502,
        )

    return content.strip()
