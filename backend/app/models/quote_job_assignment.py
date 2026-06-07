"""Manager selected-estimate decisions for quote groups (local only; no eWorks writes)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class QuoteJobAssignment(Base):
    __tablename__ = "quote_job_assignments"
    __table_args__ = (
        Index("ix_quote_job_assignments_quote_ref", "quote_ref"),
        Index("ix_quote_job_assignments_eworks_quote_id", "eworks_quote_id"),
        Index("ix_quote_job_assignments_selected_session_id", "selected_session_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quote_ref: Mapped[str | None] = mapped_column(String(100))
    eworks_quote_id: Mapped[int | None] = mapped_column(Integer)
    group_key: Mapped[str | None] = mapped_column(String(200))
    selected_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("calculation_sessions.id"), nullable=False
    )
    assignee_name: Mapped[str] = mapped_column(String(500), nullable=False)
    assignee_email: Mapped[str | None] = mapped_column(String(320))
    assignment_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("eworks_quote_assignments.id"), nullable=True
    )
    assigned_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    assigned_by_email: Mapped[str | None] = mapped_column(String(320))
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
