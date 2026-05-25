from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, computed_field

from app.schemas.common import ORMModel


class JobCreate(BaseModel):
    job_number: str
    external_eworks_job_id: str | None = None
    client_id: UUID | None = None
    property_address: str
    property_manager_name: str | None = None
    property_manager_email: str | None = None
    property_manager_phone: str | None = None
    tenant_name: str | None = None
    tenant_phone: str | None = None
    access_notes: str | None = None
    original_job_description: str | None = None
    engineer_name: str | None = None
    date_visited: date | None = None
    travel_time_minutes: int = 0


class JobUpdate(BaseModel):
    job_number: str | None = None
    external_eworks_job_id: str | None = None
    client_id: UUID | None = None
    property_address: str | None = None
    property_manager_name: str | None = None
    property_manager_email: str | None = None
    property_manager_phone: str | None = None
    tenant_name: str | None = None
    tenant_phone: str | None = None
    access_notes: str | None = None
    original_job_description: str | None = None
    engineer_name: str | None = None
    date_visited: date | None = None
    travel_time_minutes: int | None = None


class JobFindingCreate(BaseModel):
    findings: str
    problem_summary: str | None = None
    access_confirmed: bool = False
    tenant_call_required: bool = False


class JobFindingRead(ORMModel):
    id: UUID
    job_id: UUID
    findings: str
    problem_summary: str | None
    access_confirmed: bool
    tenant_call_required: bool
    created_at: datetime


class JobRead(ORMModel):
    id: UUID
    job_number: str
    external_eworks_job_id: str | None
    client_id: UUID | None
    property_address: str
    property_manager_name: str | None
    property_manager_email: str | None
    property_manager_phone: str | None
    tenant_name: str | None
    tenant_phone: str | None
    access_notes: str | None
    original_job_description: str | None
    engineer_name: str | None
    date_visited: date | None
    travel_time_minutes: int
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime
    findings: list[JobFindingRead] = Field(default_factory=list)


class QuoteScopeItemCreate(BaseModel):
    description: str
    client_visible: bool = True
    internal_only: bool = False
    sort_order: int = 0


class QuoteLabourCreate(BaseModel):
    trade_id: UUID | None = None
    skill_required: str | None = None
    best_engineer: str | None = None
    labour_type: str
    number_of_engineers: int = Field(ge=1)
    hours_on_site: Decimal | None = None
    days_on_site: Decimal | None = None
    manual_override: bool = False
    manual_rate: Decimal | None = None
    override_reason: str | None = None


class QuoteMaterialCreate(BaseModel):
    material_name: str
    supplier_name: str | None = None
    supplier_link: str | None = None
    quantity: Decimal = Field(gt=0)
    unit_cost: Decimal = Field(ge=0)
    delivery_cost: Decimal = Decimal("0")
    markup_type: str = "percentage"
    markup_value: Decimal = Decimal("0")
    client_visible: bool = True
    internal_notes: str | None = None


class QuoteChargeCreate(BaseModel):
    parking_required: bool = False
    parking_type: str | None = None
    parking_rate_per_hour: Decimal | None = None
    parking_hours: Decimal | None = None
    parking_fixed_amount: Decimal | None = None
    congestion_required: bool = False
    congestion_amount: Decimal = Decimal("0")
    ulez_required: bool = False
    ulez_amount: Decimal = Decimal("0")
    waste_disposal_required: bool = False
    waste_disposal_amount: Decimal = Decimal("0")
    travel_charge: Decimal = Decimal("0")
    other_charge: Decimal = Decimal("0")
    other_charge_reason: str | None = None


class QuoteCreate(BaseModel):
    quote_number: str
    job_id: UUID
    internal_notes: str | None = None
    client_notes: str | None = None
    scope_items: list[QuoteScopeItemCreate] = Field(default_factory=list)
    labour_items: list[QuoteLabourCreate] = Field(default_factory=list)
    material_items: list[QuoteMaterialCreate] = Field(default_factory=list)
    charges: QuoteChargeCreate | None = None


class QuoteUpdate(BaseModel):
    quote_number: str | None = None
    internal_notes: str | None = None
    client_notes: str | None = None
    status: str | None = None
    scope_items: list[QuoteScopeItemCreate] | None = None
    labour_items: list[QuoteLabourCreate] | None = None
    material_items: list[QuoteMaterialCreate] | None = None
    charges: QuoteChargeCreate | None = None


class QuoteScopeItemRead(ORMModel):
    id: UUID
    description: str
    client_visible: bool
    internal_only: bool
    sort_order: int


class QuoteLabourRead(ORMModel):
    id: UUID
    trade_id: UUID | None
    skill_required: str | None
    best_engineer: str | None
    labour_type: str
    number_of_engineers: int
    hours_on_site: Decimal | None
    days_on_site: Decimal | None
    rate_used: Decimal | None
    labour_total: Decimal | None
    manual_override: bool
    manual_rate: Decimal | None
    override_reason: str | None


class QuoteMaterialRead(ORMModel):
    id: UUID
    material_name: str
    supplier_name: str | None = None
    supplier_link: str | None = None
    quantity: Decimal
    unit_cost: Decimal | None = None
    delivery_cost: Decimal
    markup_type: str
    markup_value: Decimal
    base_cost: Decimal | None
    markup_total: Decimal | None
    sell_total: Decimal | None
    client_visible: bool
    internal_notes: str | None = None


class QuoteMaterialClientRead(ORMModel):
    id: UUID
    material_name: str
    quantity: Decimal
    sell_total: Decimal | None
    client_visible: bool


class QuoteChargeRead(ORMModel):
    id: UUID
    parking_required: bool
    parking_type: str | None
    parking_rate_per_hour: Decimal | None
    parking_hours: Decimal | None
    parking_fixed_amount: Decimal | None
    parking_total: Decimal
    congestion_required: bool
    congestion_amount: Decimal
    ulez_required: bool
    ulez_amount: Decimal
    waste_disposal_required: bool
    waste_disposal_amount: Decimal
    travel_charge: Decimal
    other_charge: Decimal
    other_charge_reason: str | None


class QuoteRead(ORMModel):
    id: UUID
    quote_number: str
    job_id: UUID
    status: str
    rule_version: str | None
    formula_version: str | None
    template_version: str | None
    subtotal: Decimal
    vat_rate: Decimal
    vat_total: Decimal
    final_total: Decimal
    margin_total: Decimal | None
    internal_notes: str | None
    client_notes: str | None
    created_by: UUID | None
    approved_by: UUID | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime
    scope_items: list[QuoteScopeItemRead] = Field(default_factory=list)
    labour_items: list[QuoteLabourRead] = Field(default_factory=list)
    material_items: list[QuoteMaterialRead] = Field(default_factory=list)
    charges: QuoteChargeRead | None = None


class ApprovalAction(BaseModel):
    reason: str | None = None


class QuoteInternalNotesRead(BaseModel):
    quote_id: UUID
    quote_number: str
    formula_source: str | None = None
    xlsx_formula_version: str | None = None
    internal_notes: str | None = None
    calculated_at: str | None = None


class DocumentRead(ORMModel):
    id: UUID
    quote_id: UUID
    document_type: str
    file_name: str
    template_version: str | None
    is_draft: bool
    generated_at: datetime


class CalculationSnapshotRead(ORMModel):
    id: UUID
    quote_id: UUID
    input_snapshot: dict
    rule_snapshot: dict
    output_snapshot: dict
    calculated_by: UUID | None
    calculated_at: datetime

    @computed_field
    @property
    def formula_breakdown(self) -> dict:
        return self.output_snapshot


class AuditLogRead(ORMModel):
    id: UUID
    user_id: UUID | None
    action: str
    entity_type: str
    entity_id: UUID | None
    old_value: dict | None
    new_value: dict | None
    created_at: datetime
