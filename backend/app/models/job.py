import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    external_eworks_job_id: Mapped[str | None] = mapped_column(String(100))
    client_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"))
    property_address: Mapped[str] = mapped_column(Text, nullable=False)
    property_manager_name: Mapped[str | None] = mapped_column(String(255))
    property_manager_email: Mapped[str | None] = mapped_column(String(255))
    property_manager_phone: Mapped[str | None] = mapped_column(String(100))
    tenant_name: Mapped[str | None] = mapped_column(String(255))
    tenant_phone: Mapped[str | None] = mapped_column(String(100))
    access_notes: Mapped[str | None] = mapped_column(Text)
    original_job_description: Mapped[str | None] = mapped_column(Text)
    engineer_name: Mapped[str | None] = mapped_column(String(255))
    date_visited: Mapped[date | None] = mapped_column(Date)
    travel_time_minutes: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    client = relationship("Client", back_populates="jobs")
    findings = relationship("JobFinding", back_populates="job", cascade="all, delete-orphan")
    quotes = relationship("Quote", back_populates="job", cascade="all, delete-orphan")


class JobFinding(Base):
    __tablename__ = "job_findings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"))
    findings: Mapped[str] = mapped_column(Text, nullable=False)
    problem_summary: Mapped[str | None] = mapped_column(Text)
    access_confirmed: Mapped[bool] = mapped_column(default=False)
    tenant_call_required: Mapped[bool] = mapped_column(default=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job = relationship("Job", back_populates="findings")
