from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class DashboardQuoteGroupVersionItem(BaseModel):
    version_number: int
    submitted_at: datetime | None = None
    submitted_by_name: str | None = None
    revision_reason: str | None = None
    final_total: Decimal | None = None
    status: str
    is_current: bool = False


class DashboardQuoteGroupSessionItem(BaseModel):
    session_id: UUID
    submitted_at: datetime
    final_total: Decimal | None = None
    works_count: int = 0
    status: str
    accepted: bool = False
    client_accepted_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    current_version_number: int = 1
    revision_in_progress: bool = False


class DashboardQuoteGroupSessionDetailItem(DashboardQuoteGroupSessionItem):
    submitted_by_user_id: UUID | None = None
    submitted_by_name: str = "Unknown submitter"
    submitted_by_email: str | None = None
    submitted_by_role: str | None = None
    is_latest: bool = False
    version_history: list[DashboardQuoteGroupVersionItem] = Field(default_factory=list)


class DashboardQuoteGroupAssignmentItem(BaseModel):
    id: int
    assignment_type: str
    assignee_kind: str
    assigned_user_id: UUID | None = None
    assigned_user_name: str | None = None
    assigned_user_email: str | None = None
    status: str
    assigned_at: datetime
    started_at: datetime | None = None
    submitted_at: datetime | None = None
    calculation_session_id: UUID | None = None
    has_submission: bool = False


class DashboardQuoteGroupAssignmentSummary(BaseModel):
    total_assignments: int = 0
    estimator_assignments: int = 0
    engineer_assignments: int = 0
    pending_assignments: int = 0
    in_progress_assignments: int = 0
    submitted_assignments: int = 0
    cancelled_assignments: int = 0


class DashboardQuoteGroupItem(BaseModel):
    group_key: str
    quote_ref: str | None = None
    eworks_quote_id: int | None = None
    client_name: str
    trade_name: str
    submission_count: int
    latest_submitted_at: datetime
    latest_total: Decimal | None = None
    highest_total: Decimal | None = None
    lowest_total: Decimal | None = None
    accepted: bool = False
    client_accepted_at: datetime | None = None
    reopened_count: int = 0
    latest_session_id: UUID
    sessions: list[DashboardQuoteGroupSessionItem] = Field(default_factory=list)


class DashboardQuoteGroupComparisonChargeLine(BaseModel):
    label: str
    amount: Decimal


class DashboardQuoteGroupComparisonWorkBreakdown(BaseModel):
    product_name: str | None = None
    product_code: str | None = None
    scope_preview: str | None = None
    labour_subtotal: Decimal | None = None
    materials_subtotal: Decimal | None = None
    work_subtotal: Decimal | None = None


class DashboardQuoteGroupComparisonSummary(BaseModel):
    final_total: Decimal | None = None
    works_subtotal: Decimal | None = None
    labour_subtotal: Decimal | None = None
    materials_subtotal: Decimal | None = None
    additional_charges_total: Decimal | None = None
    vat_total: Decimal | None = None
    vat_rate: Decimal | None = None
    scope_preview: str | None = None
    product_preview: str | None = None
    works: list[DashboardQuoteGroupComparisonWorkBreakdown] = Field(default_factory=list)
    additional_charges: list[DashboardQuoteGroupComparisonChargeLine] = Field(default_factory=list)


class DashboardQuoteJobAssignmentDecision(BaseModel):
    id: int
    selected_session_id: UUID
    assignee_name: str
    assignee_email: str | None = None
    assignment_id: int | None = None
    assigned_at: datetime
    assigned_by_name: str | None = None
    assigned_by_email: str | None = None


class DashboardQuoteGroupAssignmentSubmissionRow(BaseModel):
    assignment_id: int | None = None
    assignment_type: str
    assignee_kind: str
    assignee_name: str
    assignee_email: str | None = None
    assignment_status: str
    assigned_at: datetime | None = None
    started_at: datetime | None = None
    submitted_at: datetime | None = None
    linked_session_id: UUID | None = None
    submitted_by_name: str | None = None
    submitted_by_email: str | None = None
    submitted_by_role: str | None = None
    final_total: Decimal | None = None
    works_count: int | None = None
    is_latest: bool = False
    can_view_details: bool = False
    can_reopen: bool = False
    can_assign_job: bool = False
    is_job_assigned: bool = False
    comparison_summary: DashboardQuoteGroupComparisonSummary | None = None


class DashboardQuoteGroupDetailItem(DashboardQuoteGroupItem):
    review_status: str = "pending"
    assignment_summary: DashboardQuoteGroupAssignmentSummary = Field(
        default_factory=DashboardQuoteGroupAssignmentSummary
    )
    assignments: list[DashboardQuoteGroupAssignmentItem] = Field(default_factory=list)
    sessions: list[DashboardQuoteGroupSessionDetailItem] = Field(default_factory=list)
    assignment_submissions: list[DashboardQuoteGroupAssignmentSubmissionRow] = Field(default_factory=list)
    job_assignment_decision: DashboardQuoteJobAssignmentDecision | None = None


class DashboardQuoteGroupsResponse(BaseModel):
    groups: list[DashboardQuoteGroupItem] = Field(default_factory=list)


class DashboardQuoteGroupDetailResponse(BaseModel):
    group: DashboardQuoteGroupDetailItem
