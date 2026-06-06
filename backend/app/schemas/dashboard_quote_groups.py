from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


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


class DashboardQuoteGroupSessionDetailItem(DashboardQuoteGroupSessionItem):
    submitted_by_user_id: UUID | None = None
    submitted_by_name: str = "Unknown submitter"
    submitted_by_email: str | None = None
    submitted_by_role: str | None = None
    is_latest: bool = False


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


class DashboardQuoteGroupDetailItem(DashboardQuoteGroupItem):
    review_status: str = "pending"
    assignment_summary: DashboardQuoteGroupAssignmentSummary = Field(
        default_factory=DashboardQuoteGroupAssignmentSummary
    )
    assignments: list[DashboardQuoteGroupAssignmentItem] = Field(default_factory=list)
    sessions: list[DashboardQuoteGroupSessionDetailItem] = Field(default_factory=list)


class DashboardQuoteGroupsResponse(BaseModel):
    groups: list[DashboardQuoteGroupItem] = Field(default_factory=list)


class DashboardQuoteGroupDetailResponse(BaseModel):
    group: DashboardQuoteGroupDetailItem
