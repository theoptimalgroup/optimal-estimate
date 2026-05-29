from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.calculation import CalculationBreakdown, ChargeInput, LabourInput, MaterialInput


class EworksLinkPayload(BaseModel):
    source: str
    quote_number: str
    job_number: str
    external_job_id: str | None = None
    engineer_name: str | None = None
    client: str
    trade: str
    property_address: str
    property_manager: str | None = None
    property_manager_email: str | None = None
    property_manager_phone: str | None = None
    tenant_name: str | None = None
    tenant_phone: str | None = None
    access_notes: str | None = None
    original_job_description: str | None = None
    booked_by: str | None = None
    contact: str | None = None
    quote_screening_answers: str | None = None
    date_visited: date | None = None
    travel_time_minutes: int = 0
    travel_notes: str | None = None
    parking_notes: str | None = None
    total_time_for_job: str | None = None
    quote_description: str | None = None
    findings_report: str | None = None
    scope: str | None = None
    materials_to_order: list["MaterialOrderRow"] = Field(default_factory=list)
    shelf_materials: str | None = None
    shelf_materials_cost: Decimal = Decimal("0")
    skill_required: str | None = None
    best_engineer: str | None = None
    subcontractors: str | None = None
    time_frame: str | None = None
    engineers_needed: int | None = None
    other_notes: str | None = None
    congestion_required: bool = False
    congestion_amount: Decimal = Decimal("0")
    travel: Decimal = Decimal("0")
    expires_at: datetime


class MaterialOrderRow(BaseModel):
    link: str | None = None
    quantity: Decimal = Decimal("0")
    cost: Decimal = Decimal("0")


class SessionAttachmentMeta(BaseModel):
    id: str
    file_name: str
    content_type: str
    size: int
    media_type: str
    stored_name: str


class FromLinkRequest(BaseModel):
    payload: str
    sig: str | None = None


class Step1Snapshot(BaseModel):
    quote_number: str
    job_number: str
    external_job_id: str | None = None
    engineer_name: str | None = None
    client_name: str
    trade_name: str
    property_address: str
    property_manager_name: str | None = None
    property_manager_email: str | None = None
    property_manager_phone: str | None = None
    tenant_name: str | None = None
    tenant_phone: str | None = None
    access_notes: str | None = None
    original_job_description: str | None = None
    booked_by: str | None = None
    contact: str | None = None
    quote_screening_answers: str | None = None
    date_visited: date | None = None
    travel_time_minutes: int = 0
    travel_notes: str | None = None
    parking_notes: str | None = None
    total_time_for_job: str | None = None
    quote_description: str | None = None
    findings_report: str | None = None
    congestion_required: bool = False
    congestion_amount: Decimal = Decimal("0")
    travel: Decimal = Decimal("0")


class ResolvedRuleInfo(BaseModel):
    client_id: UUID
    trade_id: UUID
    rule_id: UUID
    rule_version: str
    formula_source: str
    xlsx_client_name: str | None = None
    xlsx_trade_name: str | None = None


class WorkBlockSnapshot(BaseModel):
    scope: str | None = None
    materials_to_order: list[MaterialOrderRow] = Field(default_factory=list)
    shelf_materials_rows: list[MaterialOrderRow] = Field(default_factory=list)
    shelf_materials: str | None = None
    shelf_materials_cost: Decimal = Decimal("0")
    skill_required: str | None = None
    best_engineer: str | None = None
    subcontractors: str | None = None
    engineers_required: bool = True
    engineers_needed: int = 1
    engineer_time_unit: str = "hours"
    engineer_time_value: Decimal = Decimal("1.5")
    labour_required: bool = False
    labour_needed: int = 0
    labour_time_value: Decimal = Decimal("1")
    time_frame: str | None = None
    other_notes: str | None = None
    attachments: list[SessionAttachmentMeta] = Field(default_factory=list)
    markup_value: Decimal = Decimal("20")
    findings: str | None = None
    labour_type: str = "hourly"
    engineers: int = 1
    labourers: int = 0
    hours: Decimal = Decimal("0")
    days: Decimal = Decimal("0")
    labourer_days: Decimal = Decimal("0")
    material_name: str = "Materials"
    quantity: Decimal = Decimal("1")
    unit_cost: Decimal = Decimal("0")
    # Per-work charges
    parking_required: bool = False
    parking_type: str | None = None
    parking_fixed_amount: Decimal | None = None
    parking_rate_per_hour: Decimal | None = None
    parking_hours: Decimal | None = None
    congestion_required: bool = False
    congestion_amount: Decimal = Decimal("0")
    travel_charge: Decimal = Decimal("0")
    other_charge: Decimal = Decimal("0")
    other_charge_reason: str | None = None

    @model_validator(mode="after")
    def ensure_shelf_rows(self) -> "WorkBlockSnapshot":
        if self.shelf_materials_rows:
            return self
        if self.shelf_materials or self.shelf_materials_cost > 0:
            return self.model_copy(
                update={
                    "shelf_materials_rows": [
                        MaterialOrderRow(
                            link=self.shelf_materials,
                            quantity=Decimal("1"),
                            cost=self.shelf_materials_cost,
                        )
                    ]
                }
            )
        return self.model_copy(update={"shelf_materials_rows": [MaterialOrderRow()]})


class Step2Snapshot(BaseModel):
    works: list[WorkBlockSnapshot] = Field(default_factory=list)
    findings: str | None = None
    scope: str | None = None
    materials_to_order: list[MaterialOrderRow] = Field(default_factory=list)
    shelf_materials_rows: list[MaterialOrderRow] = Field(default_factory=list)
    shelf_materials: str | None = None
    shelf_materials_cost: Decimal = Decimal("0")
    skill_required: str | None = None
    best_engineer: str | None = None
    subcontractors: str | None = None
    time_frame: str | None = None
    engineers_needed: int | None = None
    other_notes: str | None = None
    attachments: list[SessionAttachmentMeta] = Field(default_factory=list)
    labour_type: str = "hourly"
    engineers: int = 1
    labourers: int = 0
    hours: Decimal = Decimal("0")
    days: Decimal = Decimal("0")
    labourer_days: Decimal = Decimal("0")
    material_name: str = "Materials"
    quantity: Decimal = Decimal("1")
    unit_cost: Decimal = Decimal("0")
    supplier_name: str | None = None
    supplier_link: str | None = None
    markup_value: Decimal = Decimal("20")
    parking_required: bool = False
    parking_type: str | None = None
    parking_rate_per_hour: Decimal | None = None
    parking_hours: Decimal | None = None
    parking_fixed_amount: Decimal | None = None
    congestion_required: bool = False
    congestion_amount: Decimal = Decimal("0")
    travel_charge: Decimal = Decimal("0")
    other_charge: Decimal = Decimal("0")
    other_charge_reason: str | None = None

    @model_validator(mode="after")
    def ensure_works(self) -> "Step2Snapshot":
        if self.works:
            return self
        if self.scope or self.materials_to_order or self.time_frame or self.unit_cost > 0:
            block = WorkBlockSnapshot(
                scope=self.scope,
                materials_to_order=self.materials_to_order,
                shelf_materials_rows=self.shelf_materials_rows,
                shelf_materials=self.shelf_materials,
                shelf_materials_cost=self.shelf_materials_cost,
                skill_required=self.skill_required,
                best_engineer=self.best_engineer,
                subcontractors=self.subcontractors,
                engineers_needed=self.engineers_needed or self.engineers,
                engineers_required=(self.engineers_needed or self.engineers or 0) > 0,
                time_frame=self.time_frame,
                other_notes=self.other_notes,
                attachments=self.attachments,
                markup_value=self.markup_value,
                findings=self.findings,
                labour_type=self.labour_type,
                engineers=self.engineers,
                labourers=self.labourers,
                hours=self.hours,
                days=self.days,
                labourer_days=self.labourer_days,
                material_name=self.material_name,
                quantity=self.quantity,
                unit_cost=self.unit_cost,
            )
            return self.model_copy(update={"works": [block]})
        return self.model_copy(update={"works": [WorkBlockSnapshot()]})


class WorkBreakdownResult(BaseModel):
    work_index: int
    scope: str | None = None
    breakdown: CalculationBreakdown
    internal_notes: str | None = None


class SkillGroupBreakdown(BaseModel):
    skill: str
    breakdown: CalculationBreakdown


class SessionUiState(BaseModel):
    current_step: int = 0
    max_reachable_step: int = 0
    last_result: dict | None = None


class CalculationSessionFromLinkResponse(BaseModel):
    session_id: UUID
    session_token: str
    step1: Step1Snapshot
    step2: Step2Snapshot | None = None
    resolved: ResolvedRuleInfo
    expires_at: datetime
    ui_state: SessionUiState | None = None
    resumed: bool = False


class UpdateCalculationSessionRequest(BaseModel):
    step2: Step2Snapshot | None = None
    ui_state: SessionUiState | None = None


class CalculateSessionRequest(BaseModel):
    step2: Step2Snapshot | None = None


class SessionPdfRequest(BaseModel):
    is_draft: bool = False


class CalculationSessionRead(BaseModel):
    session_id: UUID
    step1: Step1Snapshot
    step2: Step2Snapshot | None = None
    resolved: ResolvedRuleInfo
    expires_at: datetime
    ui_state: SessionUiState | None = None


class AggregatedQuoteSummary(BaseModel):
    work_count: int
    labour_type: str
    quoted_engineer_hours: Decimal | None = None
    quoted_engineer_days: Decimal | None = None
    quoted_labour_days: Decimal | None = None
    uses_mixed_units: bool = False
    converted_from_hours: bool = False
    mixed_skills: bool = False
    skills: list[str] = Field(default_factory=list)
    subtitle: str


class CalculateSessionResponse(BaseModel):
    breakdown: CalculationBreakdown
    work_breakdowns: list[WorkBreakdownResult] = Field(default_factory=list)
    aggregated_summary: AggregatedQuoteSummary | None = None
    skill_group_breakdowns: list[SkillGroupBreakdown] = Field(default_factory=list)
    internal_view: dict
    internal_notes: str | None = None
    client_view: dict


class SubmitSessionResponse(BaseModel):
    submitted: bool = True


class DashboardWorkItem(BaseModel):
    work_index: int
    scope: str | None = None
    labour_subtotal: Decimal | None = None
    materials_subtotal: Decimal | None = None
    internal_notes: str | None = None
    attachments: list[SessionAttachmentMeta] = Field(default_factory=list)
    details: WorkBlockSnapshot | None = None


class DashboardQuoteItem(BaseModel):
    session_id: UUID
    session_token: str
    quote_number: str
    job_number: str
    client_name: str
    trade_name: str
    submitted_at: datetime
    final_total: Decimal | None = None
    internal_notes: str | None = None
    works: list[DashboardWorkItem] = Field(default_factory=list)


class DashboardQuotesResponse(BaseModel):
    quotes: list[DashboardQuoteItem] = Field(default_factory=list)


class ReopenQuoteResponse(BaseModel):
    session_id: UUID
    session_token: str


class CombineWorkNotesRequest(BaseModel):
    work_indexes: list[int] = Field(min_length=1)


class CombineWorkNotesResponse(BaseModel):
    quote_number: str
    job_number: str
    client_name: str
    internal_notes: str


class CombinedPdfRequest(BaseModel):
    work_indexes: list[int] = Field(min_length=1)
    view_type: Literal["client", "optimal"] = "client"


def step2_to_calculation_inputs(
    step1: Step1Snapshot,
    step2: Step2Snapshot,
    *,
    trade_id: UUID,
    include_charges: bool = True,
) -> tuple[list[LabourInput], list[MaterialInput], ChargeInput]:
    from app.services.eworks_questionnaire_service import apply_questionnaire_defaults, build_material_items

    normalized = apply_questionnaire_defaults(step2, trade_name=step1.trade_name)
    labour = LabourInput(
        labour_type=normalized.labour_type,
        number_of_engineers=normalized.engineers,
        number_of_labourers=normalized.labourers,
        hours_on_site=normalized.hours if normalized.labour_type == "hourly" else None,
        days_on_site=normalized.days if normalized.labour_type in {"day", "half_day"} else None,
        labourer_days=normalized.labourer_days if normalized.labour_type in {"day", "half_day"} else None,
        trade_id=trade_id,
    )
    materials: list[MaterialInput] = []
    for material_name, quantity, unit_cost in build_material_items(normalized):
        materials.append(
            MaterialInput(
                material_name=material_name,
                quantity=quantity,
                unit_cost=unit_cost,
                markup_type="percentage",
                markup_value=normalized.markup_value,
                client_visible=True,
            )
        )
    if not include_charges:
        return [labour], materials, ChargeInput()
    congestion_required = step2.congestion_required or step1.congestion_required
    congestion_amount = step2.congestion_amount if step2.congestion_amount > 0 else step1.congestion_amount
    travel = step2.travel_charge if step2.travel_charge > 0 else step1.travel
    charges = ChargeInput(
        parking_required=step2.parking_required,
        parking_type=step2.parking_type if step2.parking_required else None,
        parking_rate_per_hour=step2.parking_rate_per_hour,
        parking_hours=step2.parking_hours,
        parking_fixed_amount=step2.parking_fixed_amount,
        congestion_required=congestion_required,
        congestion_amount=congestion_amount,
        travel_charge=travel,
        other_charge=step2.other_charge,
        other_charge_reason=step2.other_charge_reason,
    )
    return [labour], materials, charges


def aggregate_work_charges(step1: Step1Snapshot, works: list[WorkBlockSnapshot]) -> ChargeInput:
    """Aggregate per-work charges from individual WorkBlockSnapshot entries.

    Falls back to step1 link-level values when no per-work values are set.
    """
    has_parking = any(b.parking_required for b in works)
    parking_total = Decimal("0")
    for b in works:
        if not b.parking_required:
            continue
        if b.parking_type == "hourly" and b.parking_rate_per_hour and b.parking_hours:
            parking_total += b.parking_rate_per_hour * b.parking_hours
        elif b.parking_fixed_amount:
            parking_total += b.parking_fixed_amount
    has_congestion = any(b.congestion_required for b in works) or step1.congestion_required
    congestion_total = sum((b.congestion_amount for b in works if b.congestion_required), Decimal("0"))
    if not congestion_total and step1.congestion_required:
        congestion_total = step1.congestion_amount
    travel_total = sum((b.travel_charge for b in works), Decimal("0")) or step1.travel
    other_total = sum((b.other_charge for b in works), Decimal("0"))
    other_reasons = " / ".join(
        b.other_charge_reason for b in works if b.other_charge_reason and b.other_charge_reason.strip()
    )
    return ChargeInput(
        parking_required=has_parking,
        parking_type="fixed" if has_parking else None,
        parking_fixed_amount=parking_total if has_parking else None,
        congestion_required=has_congestion,
        congestion_amount=congestion_total,
        travel_charge=travel_total,
        other_charge=other_total,
        other_charge_reason=other_reasons or None,
    )


def step2_session_charges(step1: Step1Snapshot, step2: Step2Snapshot) -> ChargeInput:
    congestion_required = step2.congestion_required or step1.congestion_required
    congestion_amount = step2.congestion_amount if step2.congestion_amount > 0 else step1.congestion_amount
    travel = step2.travel_charge if step2.travel_charge > 0 else step1.travel
    return ChargeInput(
        parking_required=step2.parking_required,
        parking_type=step2.parking_type if step2.parking_required else None,
        parking_rate_per_hour=step2.parking_rate_per_hour,
        parking_hours=step2.parking_hours,
        parking_fixed_amount=step2.parking_fixed_amount,
        congestion_required=congestion_required,
        congestion_amount=congestion_amount,
        travel_charge=travel,
        other_charge=step2.other_charge,
        other_charge_reason=step2.other_charge_reason,
    )
