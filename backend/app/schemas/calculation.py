from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class LabourInput(BaseModel):
    labour_type: str
    number_of_engineers: int = Field(ge=0, default=1)
    number_of_labourers: int = Field(ge=0, default=0)
    hours_on_site: Decimal | None = None
    days_on_site: Decimal | None = None
    labourer_days: Decimal | None = None
    labourer_hourly_rate: Decimal | None = None
    labourer_half_day_rate: Decimal | None = None
    labourer_day_rate: Decimal | None = None
    manual_override: bool = False
    manual_rate: Decimal | None = None
    override_reason: str | None = None
    trade_id: UUID | None = None


class MaterialInput(BaseModel):
    material_name: str
    quantity: Decimal = Field(gt=0)
    unit_cost: Decimal = Field(ge=0)
    delivery_cost: Decimal = Decimal("0")
    markup_type: str = "percentage"
    markup_value: Decimal = Decimal("0")
    client_visible: bool = True


class InternalNotesContext(BaseModel):
    product: str = ""
    important_info: str = ""
    links_and_quantity: str = ""
    who_quoted: str = ""
    best_engineer: str = ""
    duration_days: str = ""
    duration_hours: str = ""
    parking_summary: str = ""
    cc_summary: str = ""


class ChargeInput(BaseModel):
    parking_required: bool = False
    parking_type: str | None = None
    parking_rate_per_hour: Decimal | None = None
    parking_hours: Decimal | None = None
    parking_fixed_amount: Decimal | None = None
    parking_vehicles: int = 1
    parking_duration_days: Decimal = Decimal("0")
    parking_duration_hours: Decimal = Decimal("0")
    parking_amount_override: Decimal | None = None
    congestion_required: bool = False
    congestion_amount: Decimal = Decimal("0")
    ulez_required: bool = False
    ulez_amount: Decimal = Decimal("0")
    waste_disposal_required: bool = False
    waste_disposal_amount: Decimal = Decimal("0")
    travel_charge: Decimal = Decimal("0")
    other_charge: Decimal = Decimal("0")
    other_charge_reason: str | None = None


class CalculationPreviewRequest(BaseModel):
    quote_id: UUID | None = None
    client_id: UUID | None = None
    trade_id: UUID | None = None
    quote_date: date | None = None
    labour_items: list[LabourInput] = Field(default_factory=list)
    material_items: list[MaterialInput] = Field(default_factory=list)
    charges: ChargeInput | None = None
    internal_notes_context: InternalNotesContext | None = None
    client_fee_pct_override: Decimal | None = None
    calculation_client_name: str | None = None


class CalculationFinalizeRequest(BaseModel):
    quote_id: UUID


class LineBreakdown(BaseModel):
    label: str
    formula: str
    total: Decimal


class CalculationBreakdown(BaseModel):
    labour: list[LineBreakdown] = Field(default_factory=list)
    materials: list[LineBreakdown] = Field(default_factory=list)
    charges: list[LineBreakdown] = Field(default_factory=list)
    subtotal: Decimal
    vat_rate: Decimal
    vat_total: Decimal
    final_total: Decimal
    margin_total: Decimal | None = None
    rule_version: str | None = None
    formula_version: str
    approval_required: bool = False
    approval_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    formula_source: str | None = None
    xlsx_formula_version: str | None = None
    direct_labour_cost: Decimal | None = None
    overhead_cost: Decimal | None = None
    labour_charge_to_client: Decimal | None = None
    materials_parking_cc_charge: Decimal | None = None
    client_fee_pct: Decimal | None = None
    denominator_used: Decimal | None = None
    profit_gbp: Decimal | None = None
    profit_pct: Decimal | None = None
    internal_notes: str | None = None
    cost_to_optimal_labour: Decimal | None = None
    cost_to_optimal_materials: Decimal | None = None


class CalculationSnapshotRead(BaseModel):
    id: UUID
    quote_id: UUID
    input_snapshot: dict
    rule_snapshot: dict
    output_snapshot: dict
    calculated_by: UUID | None
    calculated_at: str
