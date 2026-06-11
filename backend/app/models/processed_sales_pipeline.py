"""Local sales pipeline state for processed eWorks quotes (not written back to eWorks)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

SalesBucket = Literal["pending", "possible", "strong", "dormant"]


class ProcessedQuoteSalesPipeline(Base):
    __tablename__ = "processed_quote_sales_pipeline"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    synced_quote_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    eworks_quote_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    quote_ref: Mapped[str | None] = mapped_column(String(100))
    sales_bucket: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    sales_note: Mapped[str | None] = mapped_column(Text)
    assigned_sales_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    assigned_sales_email: Mapped[str | None] = mapped_column(String(320))
    assigned_sales_name: Mapped[str | None] = mapped_column(String(500))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_follow_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_follow_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    bucket_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_reason: Mapped[str | None] = mapped_column(String(100))
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
