"""Models for eWorks quote/job sync (read-only from eWorks)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
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
    tags: Mapped[list | None] = mapped_column(_json_col())
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
    tags: Mapped[list | None] = mapped_column(_json_col())
    raw_payload: Mapped[dict | None] = mapped_column(_json_col())
    total_appointments: Mapped[int | None] = mapped_column(Integer)
    completed_appointments: Mapped[int | None] = mapped_column(Integer)
    total_appointment_time: Mapped[str | None] = mapped_column(String(100))
    total_appointment_cost: Mapped[float | None] = mapped_column(Numeric(14, 2))
    raw_detail_payload: Mapped[dict | None] = mapped_column(_json_col())
    detail_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assigned_user_name: Mapped[str | None] = mapped_column(String(500))
    assigned_user_email: Mapped[str | None] = mapped_column(String(320))
    assigned_user_id: Mapped[int | None] = mapped_column(Integer)
    next_appointment_at: Mapped[str | None] = mapped_column(String(50))
    active_appointment_id: Mapped[int | None] = mapped_column(Integer)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EworksJobAppointment(Base):
    """Normalized eWorks job appointment rows extracted from synced job payloads."""

    __tablename__ = "eworks_job_appointments"
    __table_args__ = (
        Index("ix_eworks_job_appointments_eworks_job_id", "eworks_job_id"),
        Index("ix_eworks_job_appointments_user_email", "user_email"),
        Index("ix_eworks_job_appointments_user_name", "user_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    eworks_job_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("eworks_jobs.eworks_job_id", ondelete="CASCADE"), nullable=False
    )
    appointment_id: Mapped[int | None] = mapped_column(Integer)
    job_ref: Mapped[str | None] = mapped_column(String(100))
    user_id: Mapped[int | None] = mapped_column(Integer)
    user_name: Mapped[str | None] = mapped_column(String(500))
    user_email: Mapped[str | None] = mapped_column(String(320))
    appointment_type: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str | None] = mapped_column(String(200))
    is_sales_appointment: Mapped[bool | None] = mapped_column(Boolean)
    start_at: Mapped[str | None] = mapped_column(String(50))
    end_at: Mapped[str | None] = mapped_column(String(50))
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    user_mobile: Mapped[str | None] = mapped_column(String(100))
    user_telephone: Mapped[str | None] = mapped_column(String(100))
    raw_safe_snapshot: Mapped[dict | None] = mapped_column(_json_col())
    dedupe_key: Mapped[str] = mapped_column(String(300), nullable=False)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EworksQuoteAppointment(Base):
    """Normalized eWorks quote sales appointment rows extracted from quote detail payloads."""

    __tablename__ = "eworks_quote_appointments"
    __table_args__ = (
        Index("ix_eworks_quote_appointments_eworks_quote_id", "eworks_quote_id"),
        Index("ix_eworks_quote_appointments_user_email", "user_email"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    eworks_quote_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("eworks_quotes.eworks_quote_id", ondelete="CASCADE"), nullable=False
    )
    appointment_id: Mapped[int | None] = mapped_column(Integer)
    quote_ref: Mapped[str | None] = mapped_column(String(100))
    user_id: Mapped[int | None] = mapped_column(Integer)
    user_name: Mapped[str | None] = mapped_column(String(500))
    user_email: Mapped[str | None] = mapped_column(String(320))
    user_mobile: Mapped[str | None] = mapped_column(String(100))
    user_telephone: Mapped[str | None] = mapped_column(String(100))
    appointment_type: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str | None] = mapped_column(String(200))
    is_sales_appointment: Mapped[bool | None] = mapped_column(Boolean)
    start_at: Mapped[str | None] = mapped_column(String(50))
    end_at: Mapped[str | None] = mapped_column(String(50))
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    raw_safe_snapshot: Mapped[dict | None] = mapped_column(_json_col())
    dedupe_key: Mapped[str] = mapped_column(String(300), nullable=False)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EworksCustomer(Base):
    """Local mirror of a Customer record from eWorks Manager API (read-only sync)."""

    __tablename__ = "eworks_customers"
    __table_args__ = (
        Index("ix_eworks_customers_eworks_customer_id", "eworks_customer_id"),
        Index("ix_eworks_customers_customer_name", "customer_name"),
        Index("ix_eworks_customers_synced_at", "synced_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    eworks_customer_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    customer_name: Mapped[str | None] = mapped_column(String(500))
    full_name: Mapped[str | None] = mapped_column(String(500))
    company_name: Mapped[str | None] = mapped_column(String(500))
    email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(100))
    billing_email: Mapped[str | None] = mapped_column(String(320))
    address_1: Mapped[str | None] = mapped_column(String(500))
    address_2: Mapped[str | None] = mapped_column(String(500))
    city: Mapped[str | None] = mapped_column(String(200))
    county: Mapped[str | None] = mapped_column(String(200))
    postcode: Mapped[str | None] = mapped_column(String(50))
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
    sync_type: Mapped[str] = mapped_column(String(20), nullable=False)  # quotes | jobs | customers | all
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


class EworksSyncLock(Base):
    """Database-backed lock for eWorks sync jobs (background worker + manual sync)."""

    __tablename__ = "eworks_sync_locks"
    __table_args__ = (Index("ix_eworks_sync_locks_status", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sync_type: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    locked_by: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EworksAttachment(Base):
    """Metadata mirror of eWorks quote/job attachments (read-only sync; files not downloaded by default)."""

    __tablename__ = "eworks_attachments"
    __table_args__ = (
        Index("ix_eworks_attachments_parent", "parent_type", "parent_eworks_id"),
        Index("ix_eworks_attachments_eworks_attachment_id", "eworks_attachment_id"),
        Index("ix_eworks_attachments_filename", "filename"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    eworks_attachment_id: Mapped[str | None] = mapped_column(String(100))
    parent_type: Mapped[str] = mapped_column(String(10), nullable=False)  # quote | job
    parent_eworks_id: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_local_id: Mapped[int | None] = mapped_column(Integer)
    filename: Mapped[str | None] = mapped_column(String(500))
    mime_type: Mapped[str | None] = mapped_column(String(200))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)
    created_on: Mapped[str | None] = mapped_column(String(30))
    uploaded_by: Mapped[str | None] = mapped_column(String(200))
    download_endpoint: Mapped[str | None] = mapped_column(String(1000))
    local_storage_path: Mapped[str | None] = mapped_column(String(1000))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EworksCustomFieldDefinition(Base):
    """Local mirror of eWorks CustomFields definitions (read-only sync)."""

    __tablename__ = "eworks_custom_field_definitions"
    __table_args__ = (
        Index("ix_eworks_custom_field_definitions_field_key", "field_key"),
        Index("ix_eworks_custom_field_definitions_synced_at", "synced_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    eworks_custom_field_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    field_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    field_label: Mapped[str | None] = mapped_column(String(500))
    field_type: Mapped[str | None] = mapped_column(String(50))
    default_value: Mapped[str | None] = mapped_column(Text)
    options: Mapped[list | None] = mapped_column(_json_col())
    sections: Mapped[list | None] = mapped_column(_json_col())
    status: Mapped[int | None] = mapped_column(Integer)
    raw_payload: Mapped[dict | None] = mapped_column(_json_col())
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
