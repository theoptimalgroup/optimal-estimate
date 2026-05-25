import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Quote(Base):
    __tablename__ = "quotes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quote_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(50), default="draft")
    rule_version: Mapped[str | None] = mapped_column(String(100))
    formula_version: Mapped[str | None] = mapped_column(String(100))
    template_version: Mapped[str | None] = mapped_column(String(100))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("20.00"))
    vat_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    final_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    margin_total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    internal_notes: Mapped[str | None] = mapped_column(Text)
    client_notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    job = relationship("Job", back_populates="quotes")
    scope_items = relationship("QuoteScopeItem", back_populates="quote", cascade="all, delete-orphan")
    labour_items = relationship("QuoteLabour", back_populates="quote", cascade="all, delete-orphan")
    material_items = relationship("QuoteMaterial", back_populates="quote", cascade="all, delete-orphan")
    charges = relationship("QuoteCharge", back_populates="quote", cascade="all, delete-orphan", uselist=False)
    snapshots = relationship("CalculationSnapshot", back_populates="quote", cascade="all, delete-orphan")
    approvals = relationship("Approval", back_populates="quote", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="quote", cascade="all, delete-orphan")


class QuoteScopeItem(Base):
    __tablename__ = "quote_scope_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quote_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quotes.id", ondelete="CASCADE"))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    client_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    internal_only: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    quote = relationship("Quote", back_populates="scope_items")


class QuoteLabour(Base):
    __tablename__ = "quote_labour"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quote_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quotes.id", ondelete="CASCADE"))
    trade_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("trades.id"))
    skill_required: Mapped[str | None] = mapped_column(String(255))
    best_engineer: Mapped[str | None] = mapped_column(String(255))
    labour_type: Mapped[str] = mapped_column(String(50), nullable=False)
    number_of_engineers: Mapped[int] = mapped_column(Integer, nullable=False)
    hours_on_site: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    days_on_site: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    rate_used: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    labour_total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    manual_override: Mapped[bool] = mapped_column(Boolean, default=False)
    manual_rate: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    override_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    quote = relationship("Quote", back_populates="labour_items")


class QuoteMaterial(Base):
    __tablename__ = "quote_materials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quote_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quotes.id", ondelete="CASCADE"))
    material_name: Mapped[str] = mapped_column(String(255), nullable=False)
    supplier_name: Mapped[str | None] = mapped_column(String(255))
    supplier_link: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    delivery_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    markup_type: Mapped[str] = mapped_column(String(50), default="percentage")
    markup_value: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("0"))
    base_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    markup_total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    sell_total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    client_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    internal_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    quote = relationship("Quote", back_populates="material_items")


class QuoteCharge(Base):
    __tablename__ = "quote_charges"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quote_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quotes.id", ondelete="CASCADE"))
    parking_required: Mapped[bool] = mapped_column(Boolean, default=False)
    parking_type: Mapped[str | None] = mapped_column(String(50))
    parking_rate_per_hour: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    parking_hours: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    parking_fixed_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    parking_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    congestion_required: Mapped[bool] = mapped_column(Boolean, default=False)
    congestion_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    ulez_required: Mapped[bool] = mapped_column(Boolean, default=False)
    ulez_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    waste_disposal_required: Mapped[bool] = mapped_column(Boolean, default=False)
    waste_disposal_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    travel_charge: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    other_charge: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    other_charge_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    quote = relationship("Quote", back_populates="charges")
