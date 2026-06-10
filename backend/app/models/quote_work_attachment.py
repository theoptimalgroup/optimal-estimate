import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class QuoteWorkAttachment(Base):
    __tablename__ = "quote_work_attachments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attachment_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    quote_ref: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    eworks_quote_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    synced_quote_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("eworks_quotes.id"), nullable=True, index=True
    )
    work_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    product_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    product_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_custom_scope: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    custom_scope_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    scope_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    work_block_label: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(200), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    media_type: Mapped[str] = mapped_column(String(32), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    uploaded_by_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    uploaded_by_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("calculation_sessions.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
