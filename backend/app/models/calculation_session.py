import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func
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
    public_quote_token: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True, index=True)
    public_quote_token_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    public_quote_token_revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    public_quote_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    client_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    client_acceptance_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client_acceptance_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client_acceptance_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_acceptance_ip: Mapped[str | None] = mapped_column(String(100), nullable=True)
    client_acceptance_user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    eworks_acceptance_sync_status: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    eworks_acceptance_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    eworks_acceptance_sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    eworks_acceptance_sync_attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    eworks_acceptance_last_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    eworks_acceptance_last_response: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
