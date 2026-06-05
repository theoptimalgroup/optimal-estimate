"""Local eWorks quote assignments to estimators/engineers (no eWorks writes)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class EworksQuoteAssignment(Base):
    __tablename__ = "eworks_quote_assignments"
    __table_args__ = (
        Index("ix_eworks_quote_assignments_synced_quote_id", "synced_quote_id"),
        Index("ix_eworks_quote_assignments_assigned_user_id", "assigned_user_id"),
        Index("ix_eworks_quote_assignments_assigned_user_email", "assigned_user_email"),
        Index("ix_eworks_quote_assignments_assignment_token", "assignment_token"),
        Index("ix_eworks_quote_assignments_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    synced_quote_id: Mapped[int] = mapped_column(Integer, ForeignKey("eworks_quotes.id"), nullable=False)
    eworks_quote_id: Mapped[int] = mapped_column(Integer, nullable=False)
    quote_ref: Mapped[str | None] = mapped_column(String(100))
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    assigned_user_email: Mapped[str | None] = mapped_column(String(320))
    assigned_user_name: Mapped[str | None] = mapped_column(String(500))
    assignment_type: Mapped[str] = mapped_column(String(20), nullable=False)  # estimator | engineer
    assignee_kind: Mapped[str] = mapped_column(String(20), nullable=False)  # registered | external
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="assigned")
    assignment_token: Mapped[str | None] = mapped_column(String(128), unique=True)
    assignment_token_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assignment_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assignment_token_revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assigned_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    assigned_by_email: Mapped[str | None] = mapped_column(String(320))
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    notes: Mapped[str | None] = mapped_column(Text)
    calculation_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("calculation_sessions.id")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
