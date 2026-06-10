import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class QuoteWorkSnapshot(Base):
    __tablename__ = "quote_work_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quote_ref: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    eworks_quote_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    synced_quote_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("eworks_quotes.id"), nullable=True, index=True
    )
    step2_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    updated_by_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    updated_by_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
