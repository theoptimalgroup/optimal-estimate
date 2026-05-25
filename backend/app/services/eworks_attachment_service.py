"""Store eWorks session photo/video attachments locally."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.schemas.eworks_link import SessionAttachmentMeta

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/heic", "image/heif"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/webm", "video/mpeg"}
MAX_ATTACHMENT_BYTES = 50 * 1024 * 1024


def _media_type(content_type: str) -> str:
    if content_type in ALLOWED_IMAGE_TYPES:
        return "photo"
    if content_type in ALLOWED_VIDEO_TYPES:
        return "video"
    return "file"


def _session_dir(session_id: uuid.UUID) -> Path:
    root = Path(settings.eworks_attachment_path)
    path = root / str(session_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


async def save_session_attachment(session_id: uuid.UUID, upload: UploadFile) -> SessionAttachmentMeta:
    content_type = upload.content_type or "application/octet-stream"
    if content_type not in ALLOWED_IMAGE_TYPES | ALLOWED_VIDEO_TYPES:
        raise ValueError("Only photo and video files are supported")

    data = await upload.read()
    if len(data) > MAX_ATTACHMENT_BYTES:
        raise ValueError("File exceeds 50MB limit")

    attachment_id = str(uuid.uuid4())
    safe_name = Path(upload.filename or "upload").name
    stored_name = f"{attachment_id}_{safe_name}"
    target = _session_dir(session_id) / stored_name
    target.write_bytes(data)

    return SessionAttachmentMeta(
        id=attachment_id,
        file_name=safe_name,
        content_type=content_type,
        size=len(data),
        media_type=_media_type(content_type),
        stored_name=stored_name,
    )
