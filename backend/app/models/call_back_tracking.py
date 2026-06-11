"""Local call-back tracking for eWorks Call Back quotes (not synced to eWorks)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class CallBackQuoteTracking(Base):
    __tablename__ = "call_back_quote_tracking"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    synced_quote_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    eworks_quote_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    quote_ref: Mapped[str | None] = mapped_column(String(100))
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    assigned_name: Mapped[str | None] = mapped_column(String(500))
    assigned_email: Mapped[str | None] = mapped_column(String(320))
    call_note: Mapped[str | None] = mapped_column(Text)
    last_called_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_call_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    call_status: Mapped[str | None] = mapped_column(String(20))
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
