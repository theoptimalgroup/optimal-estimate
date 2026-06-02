import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class CalculationSession(Base):
    __tablename__ = "calculation_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    session_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    payload_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    step1_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    step2_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ui_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    client_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"))
    trade_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("trades.id"))
    rate_rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rate_rules.id"))
    eworks_customer_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="in_progress", index=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
