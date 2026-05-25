from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class ClientCreate(BaseModel):
    name: str
    billing_email: EmailStr | None = None
    default_vat_rate: Decimal = Decimal("20.00")


class ClientUpdate(BaseModel):
    name: str | None = None
    billing_email: EmailStr | None = None
    default_vat_rate: Decimal | None = None
    is_active: bool | None = None


class ClientRead(ORMModel):
    id: UUID
    name: str
    billing_email: EmailStr | None
    default_vat_rate: Decimal
    is_active: bool
    created_at: datetime
    aliases: list[str] = Field(default_factory=list)


class TradeCreate(BaseModel):
    name: str
    description: str | None = None


class TradeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class TradeRead(ORMModel):
    id: UUID
    name: str
    description: str | None
    is_active: bool
    created_at: datetime


class RateRuleCreate(BaseModel):
    client_id: UUID | None = None
    trade_id: UUID | None = None
    version: str
    hourly_rate: Decimal | None = None
    half_day_rate: Decimal | None = None
    day_rate: Decimal | None = None
    minimum_hours: Decimal | None = None
    minimum_charge: Decimal | None = None
    material_markup_type: str = "percentage"
    material_markup_value: Decimal = Decimal("0")
    vat_rate: Decimal = Decimal("20.00")
    approval_threshold: Decimal | None = None
    minimum_margin_percentage: Decimal | None = None
    rounding_rule: str | None = None
    active_from: date
    active_to: date | None = None
    is_active: bool = True
    client_fee_pct: Decimal = Decimal("0")
    hourly_overhead_pct: Decimal = Decimal("0.30")
    daily_overhead_pct: Decimal = Decimal("0.20")
    daily_overhead_long_job_pct: Decimal = Decimal("0.15")
    direct_hourly_cost: Decimal | None = None
    direct_daily_cost: Decimal | None = None
    labourer_hourly_cost: Decimal = Decimal("18.75")
    labourer_daily_cost: Decimal = Decimal("150")
    material_charge_denominator: Decimal = Decimal("0.20")
    parking_charge_denominator: Decimal = Decimal("0.20")
    congestion_charge_denominator: Decimal = Decimal("0.20")
    mround_increment: Decimal = Decimal("5")
    oj_uplift_pct: Decimal = Decimal("10")
    nhs_overhead_uplift_pct: Decimal = Decimal("15")
    eaf_flat_fee: Decimal = Decimal("1")
    internal_notes_template: str | None = None
    formula_source: str = "simplified"
    xlsx_client_name: str | None = None
    xlsx_trade_name: str | None = None


class RateRuleUpdate(BaseModel):
    client_id: UUID | None = None
    trade_id: UUID | None = None
    version: str | None = None
    hourly_rate: Decimal | None = None
    half_day_rate: Decimal | None = None
    day_rate: Decimal | None = None
    minimum_hours: Decimal | None = None
    minimum_charge: Decimal | None = None
    material_markup_type: str | None = None
    material_markup_value: Decimal | None = None
    vat_rate: Decimal | None = None
    approval_threshold: Decimal | None = None
    minimum_margin_percentage: Decimal | None = None
    rounding_rule: str | None = None
    active_from: date | None = None
    active_to: date | None = None
    is_active: bool | None = None
    client_fee_pct: Decimal | None = None
    hourly_overhead_pct: Decimal | None = None
    daily_overhead_pct: Decimal | None = None
    daily_overhead_long_job_pct: Decimal | None = None
    direct_hourly_cost: Decimal | None = None
    direct_daily_cost: Decimal | None = None
    labourer_hourly_cost: Decimal | None = None
    labourer_daily_cost: Decimal | None = None
    material_charge_denominator: Decimal | None = None
    parking_charge_denominator: Decimal | None = None
    congestion_charge_denominator: Decimal | None = None
    mround_increment: Decimal | None = None
    oj_uplift_pct: Decimal | None = None
    nhs_overhead_uplift_pct: Decimal | None = None
    eaf_flat_fee: Decimal | None = None
    internal_notes_template: str | None = None
    formula_source: str | None = None
    xlsx_client_name: str | None = None
    xlsx_trade_name: str | None = None


class RateRuleRead(ORMModel):
    id: UUID
    client_id: UUID | None
    trade_id: UUID | None
    version: str
    hourly_rate: Decimal | None
    half_day_rate: Decimal | None
    day_rate: Decimal | None
    minimum_hours: Decimal | None
    minimum_charge: Decimal | None
    material_markup_type: str
    material_markup_value: Decimal
    vat_rate: Decimal
    approval_threshold: Decimal | None
    minimum_margin_percentage: Decimal | None
    rounding_rule: str | None
    active_from: date
    active_to: date | None
    is_active: bool
    created_at: datetime
    client_fee_pct: Decimal
    hourly_overhead_pct: Decimal
    daily_overhead_pct: Decimal
    daily_overhead_long_job_pct: Decimal
    direct_hourly_cost: Decimal | None
    direct_daily_cost: Decimal | None
    labourer_hourly_cost: Decimal
    labourer_daily_cost: Decimal
    material_charge_denominator: Decimal
    parking_charge_denominator: Decimal
    congestion_charge_denominator: Decimal
    mround_increment: Decimal
    oj_uplift_pct: Decimal
    nhs_overhead_uplift_pct: Decimal
    eaf_flat_fee: Decimal
    internal_notes_template: str | None
    formula_source: str
    xlsx_client_name: str | None
    xlsx_trade_name: str | None


class RateRuleTestRequest(BaseModel):
    client_id: UUID | None = None
    trade_id: UUID | None = None
    quote_date: date | None = None
