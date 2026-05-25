import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class RateRule(Base):
    __tablename__ = "rate_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"))
    trade_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("trades.id"))
    version: Mapped[str] = mapped_column(String(100), nullable=False)
    hourly_rate: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    half_day_rate: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    day_rate: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    minimum_hours: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    minimum_charge: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    material_markup_type: Mapped[str] = mapped_column(String(50), default="percentage")
    material_markup_value: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("0"))
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("20.00"))
    approval_threshold: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    minimum_margin_percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    rounding_rule: Mapped[str | None] = mapped_column(String(100))
    active_from: Mapped[date] = mapped_column(Date, nullable=False)
    active_to: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    client_fee_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0"))
    hourly_overhead_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0.30"))
    daily_overhead_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0.20"))
    daily_overhead_long_job_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0.15"))
    direct_hourly_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    direct_daily_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    labourer_hourly_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("18.75"))
    labourer_daily_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("150"))
    material_charge_denominator: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0.20"))
    parking_charge_denominator: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0.20"))
    congestion_charge_denominator: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0.20"))
    mround_increment: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("5"))
    oj_uplift_pct: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("10"))
    nhs_overhead_uplift_pct: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("15"))
    eaf_flat_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("1"))
    internal_notes_template: Mapped[str | None] = mapped_column(Text)
    formula_source: Mapped[str] = mapped_column(String(20), default="simplified")
    xlsx_client_name: Mapped[str | None] = mapped_column(String(255))
    xlsx_trade_name: Mapped[str | None] = mapped_column(String(255))

    client = relationship("Client", back_populates="rate_rules")
    trade = relationship("Trade", back_populates="rate_rules")
