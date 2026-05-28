"""Store eWorks session photo/video attachments — local disk or Azure Blob Storage."""

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


def _blob_name(session_id: uuid.UUID, stored_name: str) -> str:
    return f"eworks-attachments/{session_id}/{stored_name}"


async def _save_to_blob(session_id: uuid.UUID, stored_name: str, data: bytes, content_type: str) -> str:
    from azure.storage.blob import BlobServiceClient, ContentSettings

    conn_str = settings.azure_storage_connection_string
    container = settings.azure_storage_container_name
    blob_name = _blob_name(session_id, stored_name)

    client = BlobServiceClient.from_connection_string(conn_str)
    container_client = client.get_container_client(container)

    try:
        container_client.create_container()
    except Exception:
        pass

    blob_client = container_client.get_blob_client(blob_name)
    blob_client.upload_blob(data, overwrite=True, content_settings=ContentSettings(content_type=content_type))
    return blob_name


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

    if settings.storage_backend == "azure_blob" and settings.azure_storage_connection_string:
        await _save_to_blob(session_id, stored_name, data, content_type)
    else:
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
