"""Manager selected-estimate decisions for quote groups (local only; not eWorks job assignment)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class SelectedEstimateDecision(Base):
    __tablename__ = "selected_estimate_decisions"
    __table_args__ = (
        Index("ix_selected_estimate_decisions_quote_ref", "quote_ref"),
        Index("ix_selected_estimate_decisions_eworks_quote_id", "eworks_quote_id"),
        Index("ix_selected_estimate_decisions_selected_session_id", "selected_session_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quote_ref: Mapped[str | None] = mapped_column(String(100))
    eworks_quote_id: Mapped[int | None] = mapped_column(Integer)
    group_key: Mapped[str | None] = mapped_column(String(200))
    selected_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("calculation_sessions.id"), nullable=False
    )
    selected_assignment_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("eworks_quote_assignments.id"), nullable=True
    )
    selected_assignee_name: Mapped[str] = mapped_column(String(500), nullable=False)
    selected_assignee_email: Mapped[str | None] = mapped_column(String(320))
    selected_assignee_type: Mapped[str | None] = mapped_column(String(50))
    final_total: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    selected_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    selected_by_email: Mapped[str | None] = mapped_column(String(320))
    selected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
