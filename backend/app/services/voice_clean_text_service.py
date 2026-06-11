"""Clean voice transcripts via Azure OpenAI."""

from __future__ import annotations

from functools import lru_cache

from openai import AzureOpenAI

from app.core.config import settings
from app.core.exceptions import AppError
from app.schemas.voice import VoiceCleanupContext

CLEAN_TEXT_MIN_LENGTH = 3
CLEAN_TEXT_MAX_LENGTH = 8000

# Phrases that indicate the AI failed to clean the text and instead returned a
# meta-response asking for more input.  When the model echoes one of these back
# as its completion we fall back to the raw validated input so the user at least
# sees their transcript rather than a confusing instruction string.
_META_RESPONSE_PREFIXES = (
    "please provide",
    "please enter",
    "please give",
    "could you provide",
    "could you please",
    "i need the",
    "i need you to",
    "no text was provided",
    "no dictated text",
    "the text is empty",
    "it seems like",
    "it looks like no",
)

CONTEXT_PROMPTS: dict[VoiceCleanupContext, str] = {
    "scope_of_work": """You clean up dictated scope-of-works text for professional UK building-services quotes.

Rules:
- Use British English.
- Keep every factual detail, work item, material, measurement, and constraint.
- Do not add, remove, or invent work.
- Fix grammar, filler words, and spoken-language phrasing.
- Return only the cleaned scope text with no preamble or explanation.""",
    "internal_notes": """You clean up dictated internal notes for a UK building-services estimating team.

Rules:
- Use British English.
- Keep every factual detail, cost note, risk, and operational constraint.
- Do not add, remove, or invent information.
- Use concise professional internal-note tone.
- Return only the cleaned notes with no preamble or explanation.""",
    "engineer_findings": """You clean up dictated engineer findings from a site visit for a UK building-services quote.

Rules:
- Use British English.
- Keep every observed defect, measurement, location, and recommendation.
- Do not add, remove, or invent findings.
- Use clear technical site-report tone.
- Return only the cleaned findings with no preamble or explanation.""",
    "client_description": """You clean up dictated client-facing work descriptions for a UK building-services quote.

Rules:
- Use British English.
- Keep every factual detail about the requested work.
- Do not add, remove, or invent work.
- Use clear, professional client-facing tone without jargon where possible.
- Return only the cleaned description with no preamble or explanation.""",
    "manager_review_notes": """You clean up dictated manager review notes for a UK building-services quote.

Rules:
- Use British English.
- Keep every review point, concern, approval condition, and pricing note.
- Do not add, remove, or invent information.
- Use concise professional review tone.
- Return only the cleaned notes with no preamble or explanation.""",
}

USER_PROMPT_TEMPLATE = "Clean up the following dictated text:\n\n{text}"


def _normalize_azure_openai_endpoint(endpoint: str) -> str:
    base = endpoint.strip().rstrip("/")
    for suffix in ("/openai/v1/responses", "/openai/v1", "/openai"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    return base.rstrip("/")


@lru_cache
def _azure_openai_cleanup_client() -> AzureOpenAI:
    if not settings.voice_cleanup_configured:
        raise AppError(
            "voice_cleanup_unconfigured",
            "Voice text cleanup is not configured",
            status_code=503,
        )

    endpoint = _normalize_azure_openai_endpoint(settings.azure_openai_endpoint or "")
    api_version = settings.azure_openai_cleanup_api_version
    if settings.azure_openai_use_managed_identity:
        from azure.identity import DefaultAzureCredential

        credential = DefaultAzureCredential()
        return AzureOpenAI(
            azure_endpoint=endpoint,
            azure_ad_token_provider=lambda: credential.get_token(
                "https://cognitiveservices.azure.com/.default"
            ).token,
            api_version=api_version,
        )

    return AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=api_version,
    )


def _is_meta_response(content: str) -> bool:
    """Return True if the AI responded with a meta-prompt rather than cleaned text."""
    lower = content.lower().strip()
    return any(lower.startswith(prefix) for prefix in _META_RESPONSE_PREFIXES)


def _validate_transcript(text: str) -> str:
    trimmed = text.strip()
    if len(trimmed) < CLEAN_TEXT_MIN_LENGTH:
        raise AppError(
            "voice_cleanup_text_empty",
            "Transcript text is required",
            status_code=400,
        )
    if len(trimmed) > CLEAN_TEXT_MAX_LENGTH:
        raise AppError(
            "voice_cleanup_text_too_long",
            f"Transcript text must be at most {CLEAN_TEXT_MAX_LENGTH} characters",
            status_code=400,
        )
    return trimmed


def clean_voice_text(text: str, context: VoiceCleanupContext) -> str:
    validated = _validate_transcript(text)
    client = _azure_openai_cleanup_client()
    system_prompt = CONTEXT_PROMPTS[context]

    try:
        response = client.chat.completions.create(
            model=settings.azure_openai_cleanup_deployment,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": USER_PROMPT_TEMPLATE.format(text=validated)},
            ],
        )
    except Exception as exc:
        raise AppError(
            "voice_cleanup_failed",
            "Failed to clean dictated text",
            status_code=502,
            details={"reason": str(exc)},
        ) from exc

    content = response.choices[0].message.content if response.choices else None
    if not content or not content.strip():
        raise AppError(
            "voice_cleanup_empty_response",
            "AI returned an empty response",
            status_code=502,
        )

    cleaned = content.strip()

    # Guard against the model returning a meta-prompt instead of cleaned text
    # (e.g. "Please provide the full dictated text for cleaning.").  This can
    # happen when the transcript is very short or when there is an API-version /
    # model mismatch on the Azure AI Foundry endpoint.  In that case we return
    # the raw validated input so the user at least gets their transcript.
    if _is_meta_response(cleaned):
        return validated

    return cleaned
