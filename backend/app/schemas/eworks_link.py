from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.quote_acceptance import QuoteAcceptanceStatusRead

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
    cost: Decimal = Decimal("0")  # cost per item
    line_total: Decimal | None = None


class MaterialLinkRow(BaseModel):
    link: str | None = None
    quantity: Decimal = Decimal("0")
    cost: Decimal = Decimal("0")  # cost per item


class MaterialSupplier(BaseModel):
    links: list[MaterialLinkRow] = Field(default_factory=list)
    delivery_charge: Decimal = Decimal("0")
    supplier_name: str | None = None


def migrate_legacy_material_rows(rows: list | None) -> list[dict]:
    """Convert flat MaterialOrderRow list to supplier shape (one supplier, all links)."""
    if not rows:
        return [{"links": [{"link": "", "quantity": 0, "cost": 0}], "delivery_charge": 0}]
    first = rows[0]
    if isinstance(first, dict) and "links" in first:
        return rows
    if isinstance(first, MaterialSupplier):
        return [s.model_dump(mode="json") for s in rows]
    links: list[dict] = []
    for row in rows:
        if isinstance(row, dict):
            qty = Decimal(str(row.get("quantity", 0)))
            cost = Decimal(str(row.get("cost", 0)))
            link = row.get("link")
        else:
            qty = row.quantity
            cost = row.cost
            link = row.link
        cost_per_item = cost / max(qty, Decimal("1")) if cost > 0 else Decimal("0")
        links.append({"link": link, "quantity": qty, "cost": cost_per_item})
    if not links:
        links = [{"link": "", "quantity": 0, "cost": 0}]
    return [{"links": links, "delivery_charge": 0}]


def flatten_supplier_links(suppliers: list[MaterialSupplier]) -> list[MaterialLinkRow]:
    rows: list[MaterialLinkRow] = []
    for supplier in suppliers:
        rows.extend(supplier.links)
    return rows


def default_material_suppliers() -> list[MaterialSupplier]:
    return [MaterialSupplier(links=[MaterialLinkRow()])]

class SessionAttachmentMeta(BaseModel):
    id: str
    file_name: str
    content_type: str
    size: int
    media_type: str
    stored_name: str
    uploaded_by_name: str | None = None
    uploaded_by_email: str | None = None
    uploaded_at: datetime | None = None
    work_index: int | None = None
    product_id: int | None = None
    product_name: str | None = None
    is_custom_scope: bool | None = None
    custom_scope_title: str | None = None
    scope_snapshot: str | None = None
    work_block_label: str | None = None


class FromLinkRequest(BaseModel):
    payload: str
    sig: str | None = None


class Step1Snapshot(BaseModel):
    quote_number: str
    job_number: str
    external_job_id: str | None = None
    engineer_name: str | None = None
    engineer_name_source: str | None = None
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
    rule_id: UUID | None = None
    rule_version: str = ""
    formula_source: str = "none"
    xlsx_client_name: str | None = None
    xlsx_trade_name: str | None = None
    client_fee_pct: Decimal = Decimal("0")


class WorkBlockSnapshot(BaseModel):
    scope: str | None = None
    selected_product_id: int | None = None
    is_custom_scope: bool = False
    custom_title: str | None = None
    eworks_item_id: int | None = None
    product_name: str | None = None
    product_code: str | None = None
    product_quantity: Decimal = Decimal("1")
    product_unit_price: Decimal = Decimal("0")
    product_total_price: Decimal = Decimal("0")
    scope_from_product: bool = False
    materials_to_order: list[MaterialSupplier] = Field(default_factory=default_material_suppliers)
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
    parking_vehicles: int = 1
    parking_notes: str | None = None
    parking_same_location_as_work1: bool = False
    parking_latitude: Decimal | None = None
    parking_longitude: Decimal | None = None
    congestion_required: bool = False
    congestion_amount: Decimal = Decimal("0")
    travel_charge: Decimal = Decimal("0")
    other_charge: Decimal = Decimal("0")
    other_charge_reason: str | None = None
    ulez_required: bool = False
    ulez_amount: Decimal = Decimal("0")
    waste_disposal_required: bool = False
    waste_disposal_amount: Decimal = Decimal("0")

    @model_validator(mode="before")
    @classmethod
    def migrate_materials(cls, data: object) -> object:
        if isinstance(data, dict) and "materials_to_order" in data:
            data = {**data, "materials_to_order": migrate_legacy_material_rows(data.get("materials_to_order") or [])}
        return data

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
    unmatched_attachments: list[SessionAttachmentMeta] = Field(default_factory=list)
    findings: str | None = None
    scope: str | None = None
    materials_to_order: list[MaterialSupplier] = Field(default_factory=default_material_suppliers)
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
    parking_vehicles: int = 1
    parking_notes: str | None = None
    parking_latitude: Decimal | None = None
    parking_longitude: Decimal | None = None
    congestion_required: bool = False
    congestion_amount: Decimal = Decimal("0")
    travel_charge: Decimal = Decimal("0")
    other_charge: Decimal = Decimal("0")
    other_charge_reason: str | None = None
    ulez_required: bool = False
    ulez_amount: Decimal = Decimal("0")
    waste_disposal_required: bool = False
    waste_disposal_amount: Decimal = Decimal("0")

    @model_validator(mode="before")
    @classmethod
    def migrate_materials(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        updated = dict(data)
        if "materials_to_order" in updated:
            updated["materials_to_order"] = migrate_legacy_material_rows(updated.get("materials_to_order") or [])
        if "works" in updated and isinstance(updated["works"], list):
            updated["works"] = [
                {**work, "materials_to_order": migrate_legacy_material_rows(work.get("materials_to_order") or [])}
                if isinstance(work, dict) and "materials_to_order" in work
                else work
                for work in updated["works"]
            ]
        return updated

    @model_validator(mode="after")
    def ensure_works(self) -> "Step2Snapshot":
        if self.works:
            return self
        if self.scope or self.materials_to_order or self.time_frame or self.unit_cost > 0:
            block = WorkBlockSnapshot(
                scope=self.scope,
                materials_to_order=self.materials_to_order or default_material_suppliers(),
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


class SharedStep2Meta(BaseModel):
    updated_by_name: str | None = None
    updated_by_email: str | None = None
    updated_at: datetime | None = None
    version: int = 1


class CalculationSessionFromLinkResponse(BaseModel):
    session_id: UUID
    session_token: str
    step1: Step1Snapshot
    step2: Step2Snapshot | None = None
    shared_step2: SharedStep2Meta | None = None
    resolved: ResolvedRuleInfo
    expires_at: datetime
    ui_state: SessionUiState | None = None
    resumed: bool = False


class ManualCalculationSessionRequest(BaseModel):
    quote_ref: str | None = Field(default=None, max_length=255)
    job_ref: str | None = Field(default=None, max_length=255)
    client_name: str | None = Field(default=None, max_length=255)
    trade_name: str | None = Field(default=None, max_length=255)


class ManualCalculationSessionResponse(BaseModel):
    session_id: UUID
    session_token: str
    resume_url: str


class UpdateCalculationSessionRequest(BaseModel):
    step2: Step2Snapshot | None = None
    ui_state: SessionUiState | None = None
    findings_report: str | None = None


class CalculateSessionRequest(BaseModel):
    step2: Step2Snapshot | None = None


class SessionPdfRequest(BaseModel):
    is_draft: bool = False


class CalculationSessionRead(BaseModel):
    session_id: UUID
    step1: Step1Snapshot
    step2: Step2Snapshot | None = None
    shared_step2: SharedStep2Meta | None = None
    resolved: ResolvedRuleInfo
    expires_at: datetime
    ui_state: SessionUiState | None = None
    status: str = "in_progress"
    locked: bool = False
    revision_in_progress: bool = False
    active_revision_reason: str | None = None
    current_version_number: int = 0


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
    combined_duration_days: Decimal | None = None
    combined_duration_hours: Decimal | None = None
    combined_parking_total: Decimal | None = None
    combined_cc_total: Decimal | None = None
    combined_cc_days: int | None = None


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
    version_number: int | None = None
    revision: bool = False


class RewordScopeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class RewordScopeResponse(BaseModel):
    reworded_text: str


class DashboardWorkItem(BaseModel):
    work_index: int
    scope: str | None = None
    product_name: str | None = None
    product_code: str | None = None
    display_label: str | None = None
    labour_subtotal: Decimal | None = None
    materials_subtotal: Decimal | None = None
    parking_subtotal: Decimal | None = None
    cc_subtotal: Decimal | None = None
    cc_chargeable_days: int | None = None
    duration_days: Decimal | None = None
    duration_hours: Decimal | None = None
    internal_notes: str | None = None
    attachments: list[SessionAttachmentMeta] = Field(default_factory=list)
    details: WorkBlockSnapshot | None = None


def quote_additional_charge_lines(step2: Step2Snapshot, works: list[WorkBlockSnapshot] | None = None) -> list[str]:
    """Format quote-level additional charges for review surfaces."""
    from app.services.parking_charge_service import (
        calculate_cc_total,
        decompose_duration_hours,
        format_combined_cc_review_lines,
        format_parking_summary,
        format_parking_type_label,
        works_combined_duration_hours,
    )

    lines: list[str] = []
    work_blocks = works or step2.works
    combined_hours = works_combined_duration_hours(work_blocks) if work_blocks else Decimal("0")
    duration_days, duration_hours = decompose_duration_hours(combined_hours)
    if duration_days > 0 or duration_hours > 0:
        lines.append(f"Combined duration: {duration_days.normalize()} days, {duration_hours.normalize()} hours")
    if step2.parking_required:
        parking_total = quote_parking_raw(step2, work_blocks)
        summary = format_parking_summary(
            step2,
            days=duration_days,
            hours=duration_hours,
            parking_total=parking_total,
        )
        if summary:
            lines.append(summary)
        else:
            label = format_parking_type_label(step2.parking_type)
            lines.append(f"Parking ({label}): £{parking_total}")
        if step2.parking_latitude is not None and step2.parking_longitude is not None:
            lines.append(
                f"GPS snapshot: https://www.google.com/maps?q={step2.parking_latitude},{step2.parking_longitude}"
            )
    if step2.congestion_required and step2.congestion_amount > 0:
        lines.extend(format_combined_cc_review_lines(step2, work_blocks))
    if step2.travel_charge > 0:
        lines.append(f"Travel: £{step2.travel_charge}")
    if step2.other_charge > 0:
        reason = (step2.other_charge_reason or "").strip()
        suffix = f" ({reason})" if reason else ""
        lines.append(f"Other: £{step2.other_charge}{suffix}")
    if step2.parking_notes and step2.parking_notes.strip():
        lines.append(f"Parking notes: {step2.parking_notes.strip()}")
    return lines


class DashboardQuoteSummaryBreakdown(BaseModel):
    works_subtotal: Decimal
    additional_charges: Decimal
    vat_total: Decimal
    final_total: Decimal


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
    additional_charges: list[str] = Field(default_factory=list)
    breakdown: DashboardQuoteSummaryBreakdown | None = None
    works: list[DashboardWorkItem] = Field(default_factory=list)
    acceptance: QuoteAcceptanceStatusRead = Field(default_factory=QuoteAcceptanceStatusRead)
    status: str = "submitted"
    locked: bool = True
    current_version_number: int = 1
    revision_in_progress: bool = False
    active_revision_reason: str | None = None
    can_revise: bool = False
    can_continue_revision: bool = False


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
    view_type: Literal["client", "optimal", "all_trades"] = "client"


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
    for material_name, quantity, unit_cost, delivery_cost in build_material_items(normalized):
        materials.append(
            MaterialInput(
                material_name=material_name,
                quantity=quantity,
                unit_cost=unit_cost,
                delivery_cost=delivery_cost,
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
        parking_vehicles=max(1, step2.parking_vehicles or 1),
        congestion_required=congestion_required,
        congestion_amount=congestion_amount,
        travel_charge=travel,
        other_charge=step2.other_charge,
        other_charge_reason=step2.other_charge_reason,
    )
    return [labour], materials, charges


def quote_parking_raw(step2: Step2Snapshot, works: list[WorkBlockSnapshot] | None = None) -> Decimal:
    """Raw quote-level parking cost from grouped work durations (1 day = 8 hours)."""
    if not step2.parking_required:
        return Decimal("0")
    from app.services.parking_charge_service import calculate_parking_total

    work_blocks = works or step2.works
    if not work_blocks:
        combined_hours = step2.parking_hours or Decimal("0")
        if combined_hours <= 0:
            return Decimal("0")
        from app.services.parking_charge_service import calculate_parking_charge

        return calculate_parking_charge(
            step2.parking_type,
            rate_per_day=step2.parking_fixed_amount or Decimal("0"),
            rate_per_hour=step2.parking_rate_per_hour or Decimal("0"),
            days=Decimal("0"),
            hours=combined_hours,
            vehicles=step2.parking_vehicles or 1,
        )
    return calculate_parking_total(step2, work_blocks)


def work_parking_raw(block: WorkBlockSnapshot, *, step2: Step2Snapshot | None = None) -> Decimal:
    """Raw parking for one work block using quote parking settings and work duration."""
    if step2 is None or not step2.parking_required:
        return Decimal("0")
    from app.services.parking_charge_service import calculate_parking_charge, work_duration_components

    days, hours = work_duration_components(block)
    return calculate_parking_charge(
        step2.parking_type,
        rate_per_day=step2.parking_fixed_amount or Decimal("0"),
        rate_per_hour=step2.parking_rate_per_hour or Decimal("0"),
        days=days,
        hours=hours,
        vehicles=step2.parking_vehicles or 1,
    )


def aggregate_work_charges(
    step1: Step1Snapshot,
    works: list[WorkBlockSnapshot],
    *,
    step2: Step2Snapshot | None = None,
) -> ChargeInput:
    """Return quote-level additional charges from the Step2 snapshot and work durations."""
    from app.services.parking_charge_service import charge_input_for_combined

    snapshot = step2 or Step2Snapshot()
    congestion_required = snapshot.congestion_required or step1.congestion_required
    congestion_amount = snapshot.congestion_amount if snapshot.congestion_amount > 0 else step1.congestion_amount
    travel = snapshot.travel_charge if snapshot.travel_charge > 0 else step1.travel
    combined = charge_input_for_combined(snapshot, works)
    return combined.model_copy(
        update={
            "congestion_required": congestion_required,
            "congestion_amount": congestion_amount,
            "travel_charge": travel,
        }
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
        parking_vehicles=max(1, step2.parking_vehicles or 1),
        congestion_required=congestion_required,
        congestion_amount=congestion_amount,
        travel_charge=travel,
        other_charge=step2.other_charge,
        other_charge_reason=step2.other_charge_reason,
    )
