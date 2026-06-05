"""Models for eWorks quote/job sync (read-only from eWorks)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

_json_col = lambda: JSON().with_variant(JSONB, "postgresql")  # noqa: E731


class EworksQuote(Base):
    """Local mirror of a Quote record from eWorks Manager API (read-only sync)."""

    __tablename__ = "eworks_quotes"
    __table_args__ = (
        Index("ix_eworks_quotes_eworks_quote_id", "eworks_quote_id"),
        Index("ix_eworks_quotes_quote_ref", "quote_ref"),
        Index("ix_eworks_quotes_customer_id", "customer_id"),
        Index("ix_eworks_quotes_status", "status"),
        Index("ix_eworks_quotes_synced_at", "synced_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    eworks_quote_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    quote_ref: Mapped[str | None] = mapped_column(String(100))
    customer_id: Mapped[int | None] = mapped_column(Integer)
    customer_name: Mapped[str | None] = mapped_column(String(500))
    customer_contact_id: Mapped[int | None] = mapped_column(Integer)
    customer_site_id: Mapped[int | None] = mapped_column(Integer)
    project_id: Mapped[int | None] = mapped_column(Integer)
    quote_type_id: Mapped[int | None] = mapped_column(Integer)
    quote_source_id: Mapped[int | None] = mapped_column(Integer)
    quote_date: Mapped[str | None] = mapped_column(String(30))
    expiry_date: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[str | None] = mapped_column(String(100))
    status_name: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    customer_notes: Mapped[str | None] = mapped_column(Text)
    terms: Mapped[str | None] = mapped_column(Text)
    customer_ref: Mapped[str | None] = mapped_column(String(200))
    po_ref: Mapped[str | None] = mapped_column(String(200))
    wo_ref: Mapped[str | None] = mapped_column(String(200))
    subtotal: Mapped[float | None] = mapped_column(Numeric(14, 2))
    vat: Mapped[float | None] = mapped_column(Numeric(14, 2))
    total: Mapped[float | None] = mapped_column(Numeric(14, 2))
    raw_payload: Mapped[dict | None] = mapped_column(_json_col())
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EworksJob(Base):
    """Local mirror of a Job record from eWorks Manager API (read-only sync)."""

    __tablename__ = "eworks_jobs"
    __table_args__ = (
        Index("ix_eworks_jobs_eworks_job_id", "eworks_job_id"),
        Index("ix_eworks_jobs_job_ref", "job_ref"),
        Index("ix_eworks_jobs_customer_id", "customer_id"),
        Index("ix_eworks_jobs_eworks_quote_id", "eworks_quote_id"),
        Index("ix_eworks_jobs_status", "status"),
        Index("ix_eworks_jobs_synced_at", "synced_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    eworks_job_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    job_ref: Mapped[str | None] = mapped_column(String(100))
    eworks_quote_id: Mapped[int | None] = mapped_column(Integer)
    customer_id: Mapped[int | None] = mapped_column(Integer)
    customer_name: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str | None] = mapped_column(String(100))
    status_name: Mapped[str | None] = mapped_column(String(200))
    job_date: Mapped[str | None] = mapped_column(String(30))
    description: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(Text)
    subtotal: Mapped[float | None] = mapped_column(Numeric(14, 2))
    vat: Mapped[float | None] = mapped_column(Numeric(14, 2))
    total: Mapped[float | None] = mapped_column(Numeric(14, 2))
    raw_payload: Mapped[dict | None] = mapped_column(_json_col())
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EworksSyncRun(Base):
    """Tracks each admin-triggered eWorks sync run for history/audit."""

    __tablename__ = "eworks_sync_runs"
    __table_args__ = (
        Index("ix_eworks_sync_runs_sync_type", "sync_type"),
        Index("ix_eworks_sync_runs_started_at", "started_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sync_type: Mapped[str] = mapped_column(String(20), nullable=False)  # quotes | jobs | all
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")  # running|success|failed|partial
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    fetched_count: Mapped[int] = mapped_column(Integer, default=0)
    created_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict | None] = mapped_column("metadata", _json_col())
