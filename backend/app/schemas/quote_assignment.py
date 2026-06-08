from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

AssignmentType = Literal["estimator", "engineer"]
AssigneeKind = Literal["registered", "external"]
AssignmentStatus = Literal["assigned", "in_progress", "submitted", "cancelled"]


class AssignmentCreate(BaseModel):
    assignment_type: AssignmentType
    assignee_kind: AssigneeKind
    assigned_user_id: UUID | None = None
    assigned_user_email: EmailStr | None = None
    assigned_user_name: str | None = None
    notes: str | None = None
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def validate_assignee(self) -> AssignmentCreate:
        if self.assignee_kind == "registered":
            if self.assigned_user_id is None:
                raise ValueError("assigned_user_id is required for registered assignments")
        elif self.assignee_kind == "external":
            if not self.assigned_user_email and not self.assigned_user_name:
                raise ValueError("assigned_user_email or assigned_user_name is required for external assignments")
        return self


class AssignmentUpdateStatus(BaseModel):
    status: AssignmentStatus


class AssignmentQuoteSummary(BaseModel):
    synced_quote_id: int
    eworks_quote_id: int
    quote_ref: str | None = None
    customer_name: str | None = None
    site_address: str | None = None
    quote_date: str | None = None
    expiry_date: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)


class AssignmentRead(BaseModel):
    id: int
    synced_quote_id: int
    eworks_quote_id: int
    quote_ref: str | None = None
    assigned_user_id: str | None = None
    assigned_user_email: str | None = None
    assigned_user_name: str | None = None
    assignment_type: AssignmentType
    assignee_kind: AssigneeKind
    status: AssignmentStatus
    assignment_token: str | None = None
    assignment_token_created_at: str | None = None
    assignment_token_expires_at: str | None = None
    assignment_token_revoked_at: str | None = None
    assigned_by_user_id: str | None = None
    assigned_by_email: str | None = None
    assigned_at: str | None = None
    notes: str | None = None
    quote_summary: AssignmentQuoteSummary | None = None
    assignment_link: str | None = None
    has_calculation_session: bool = False
    calculation_session_id: str | None = None
    can_start_estimate: bool = False
    submitted_at: str | None = None
    final_total: str | None = None
    current_version_number: int | None = None
    revision_in_progress: bool = False
    active_revision_reason: str | None = None
    can_revise: bool = False
    can_continue_revision: bool = False
    can_view_submission: bool = False
    source: str = "manual"
    is_derived: bool = False
    appointment_start_at: str | None = None
    appointment_end_at: str | None = None
    appointment_status: str | None = None
    appointment_type: str | None = None
    job_ref: str | None = None


class AssignmentStartEstimateRead(BaseModel):
    session_id: str
    session_token: str
    resume_url: str
    assignment_id: int
    quote_ref: str | None = None


class AssignmentPublicRead(BaseModel):
    assignment_id: int
    assignment_type: AssignmentType
    assignee_kind: AssigneeKind
    status: AssignmentStatus
    assigned_user_name: str | None = None
    assigned_user_email: str | None = None
    assigned_by_name: str | None = None
    assigned_at: str | None = None
    notes: str | None = None
    quote_ref: str | None = None
    customer_name: str | None = None
    site_address: str | None = None
    quote_date: str | None = None
    expiry_date: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)


class AssignmentTokenResponse(BaseModel):
    assignment_id: int
    assignment_link: str


class AssigneeUserRead(BaseModel):
    id: str
    name: str
    email: str
    role: str
    is_active: bool


class AssignmentPublicSubmit(BaseModel):
    notes: str | None = None

    @field_validator("notes")
    @classmethod
    def trim_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None
