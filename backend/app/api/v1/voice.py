import logging

from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import AuthenticatedUser, require_roles
from app.core.config import settings
from app.core.exceptions import AppError, success_response
from app.core.security import UserRole
from app.schemas.voice import CleanTextRequest, CleanTextResponse, ElevenLabsTokenResponse
from app.services.voice_clean_text_service import clean_voice_text
from app.services.voice_token_service import create_elevenlabs_scribe_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["voice"])

VOICE_ALLOWED_ROLES = (
    UserRole.ADMIN,
    UserRole.ESTIMATOR,
    UserRole.ENGINEER,
    UserRole.MANAGER,
)


@router.get("/elevenlabs-token")
def get_elevenlabs_token(
    user: AuthenticatedUser = Depends(require_roles(*VOICE_ALLOWED_ROLES)),
):
    logger.info(
        "GET /api/v1/voice/elevenlabs-token called user_id=%s user_email=%s "
        "elevenlabs_api_key_configured=%s",
        user.id,
        user.email,
        settings.voice_dictation_configured,
    )
    try:
        token = create_elevenlabs_scribe_token()
    except AppError as exc:
        logger.warning(
            "ElevenLabs token creation failed user_id=%s error_code=%s status_code=%s",
            user.id,
            exc.code,
            exc.status_code,
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    logger.info("ElevenLabs token creation succeeded user_id=%s", user.id)
    return success_response(ElevenLabsTokenResponse(token=token))


@router.post("/clean-text")
def clean_text(
    payload: CleanTextRequest,
    _user: AuthenticatedUser = Depends(require_roles(*VOICE_ALLOWED_ROLES)),
):
    try:
        cleaned = clean_voice_text(payload.text, payload.context)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return success_response(CleanTextResponse(text=cleaned))
