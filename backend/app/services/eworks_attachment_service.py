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


def _blob_name(session_id: uuid.UUID, stored_name: str, *, eworks_quote_id: int | None = None) -> str:
    if eworks_quote_id is not None:
        return f"eworks-attachments/quotes/{eworks_quote_id}/{stored_name}"
    return f"eworks-attachments/{session_id}/{stored_name}"


def _quote_dir(eworks_quote_id: int) -> Path:
    root = Path(settings.eworks_attachment_path)
    path = root / "quotes" / str(eworks_quote_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _stored_quote_path(eworks_quote_id: int, stored_name: str) -> Path:
    return _quote_dir(eworks_quote_id) / stored_name


async def _save_to_blob(
    session_id: uuid.UUID,
    stored_name: str,
    data: bytes,
    content_type: str,
    *,
    eworks_quote_id: int | None = None,
) -> str:
    from azure.storage.blob import BlobServiceClient, ContentSettings

    conn_str = settings.azure_storage_connection_string
    container = settings.azure_storage_container_name
    blob_name = _blob_name(session_id, stored_name, eworks_quote_id=eworks_quote_id)

    client = BlobServiceClient.from_connection_string(conn_str)
    container_client = client.get_container_client(container)

    try:
        container_client.create_container()
    except Exception:
        pass

    blob_client = container_client.get_blob_client(blob_name)
    blob_client.upload_blob(data, overwrite=True, content_settings=ContentSettings(content_type=content_type))
    return blob_name


def _stored_path(session_id: uuid.UUID, stored_name: str) -> Path:
    return _session_dir(session_id) / stored_name


def _uses_blob_storage() -> bool:
    return settings.storage_backend == "azure_blob" and bool(settings.azure_storage_connection_string)


async def read_session_attachment(
    session_id: uuid.UUID,
    stored_name: str,
    *,
    eworks_quote_id: int | None = None,
) -> tuple[bytes, str]:
    if _uses_blob_storage():
        from azure.storage.blob import BlobServiceClient

        conn_str = settings.azure_storage_connection_string
        container = settings.azure_storage_container_name
        client = BlobServiceClient.from_connection_string(conn_str)

        candidates = []
        if eworks_quote_id is not None:
            candidates.append(_blob_name(session_id, stored_name, eworks_quote_id=eworks_quote_id))
        candidates.append(_blob_name(session_id, stored_name))

        for blob_name in candidates:
            blob_client = client.get_blob_client(container=container, blob=blob_name)
            if not blob_client.exists():
                continue
            downloader = blob_client.download_blob()
            data = downloader.readall()
            content_type = blob_client.get_blob_properties().content_settings.content_type or "application/octet-stream"
            return data, content_type
        raise FileNotFoundError(stored_name)

    if eworks_quote_id is not None:
        quote_target = _stored_quote_path(eworks_quote_id, stored_name)
        if quote_target.is_file():
            return quote_target.read_bytes(), "application/octet-stream"

    target = _stored_path(session_id, stored_name)
    if not target.is_file():
        raise FileNotFoundError(stored_name)
    return target.read_bytes(), "application/octet-stream"


async def delete_stored_attachment(
    session_id: uuid.UUID,
    stored_name: str,
    *,
    eworks_quote_id: int | None = None,
) -> None:
    if _uses_blob_storage():
        from azure.storage.blob import BlobServiceClient

        conn_str = settings.azure_storage_connection_string
        container = settings.azure_storage_container_name
        client = BlobServiceClient.from_connection_string(conn_str)

        candidates = []
        if eworks_quote_id is not None:
            candidates.append(_blob_name(session_id, stored_name, eworks_quote_id=eworks_quote_id))
        candidates.append(_blob_name(session_id, stored_name))

        for blob_name in candidates:
            blob_client = client.get_blob_client(container=container, blob=blob_name)
            if blob_client.exists():
                blob_client.delete_blob()
        return

    if eworks_quote_id is not None:
        quote_target = _stored_quote_path(eworks_quote_id, stored_name)
        if quote_target.is_file():
            quote_target.unlink()

    target = _stored_path(session_id, stored_name)
    if target.is_file():
        target.unlink()


async def save_session_attachment(
    session_id: uuid.UUID,
    upload: UploadFile,
    *,
    eworks_quote_id: int | None = None,
) -> SessionAttachmentMeta:
    content_type = upload.content_type or "application/octet-stream"
    if content_type not in ALLOWED_IMAGE_TYPES | ALLOWED_VIDEO_TYPES:
        raise ValueError("Only photo and video files are supported")

    data = await upload.read()
    if len(data) > MAX_ATTACHMENT_BYTES:
        raise ValueError("File exceeds 50MB limit")

    attachment_id = str(uuid.uuid4())
    safe_name = Path(upload.filename or "upload").name
    stored_name = f"{attachment_id}_{safe_name}"

    if _uses_blob_storage():
        await _save_to_blob(session_id, stored_name, data, content_type, eworks_quote_id=eworks_quote_id)
    elif eworks_quote_id is not None:
        _stored_quote_path(eworks_quote_id, stored_name).write_bytes(data)
    else:
        _stored_path(session_id, stored_name).write_bytes(data)

    return SessionAttachmentMeta(
        id=attachment_id,
        file_name=safe_name,
        content_type=content_type,
        size=len(data),
        media_type=_media_type(content_type),
        stored_name=stored_name,
    )
