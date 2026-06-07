from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class SelectQuoteEstimateRequest(BaseModel):
    selected_session_id: UUID
    selected_assignment_id: int | None = None
    assignee_name: str | None = Field(default=None, max_length=500)
    assignee_email: str | None = Field(default=None, max_length=320)
    assignment_id: int | None = None

    @model_validator(mode="after")
    def resolve_assignment_id(self) -> SelectQuoteEstimateRequest:
        if self.selected_assignment_id is None and self.assignment_id is not None:
            self.selected_assignment_id = self.assignment_id
        return self


# Legacy alias
AssignQuoteJobRequest = SelectQuoteEstimateRequest


class SelectedEstimateDecisionRead(BaseModel):
    id: int
    selected_session_id: UUID
    selected_assignment_id: int | None = None
    selected_assignee_name: str
    selected_assignee_email: str | None = None
    selected_assignee_type: str | None = None
    final_total: Decimal | None = None
    selected_at: datetime
    selected_by_name: str | None = None
    selected_by_email: str | None = None


class SelectQuoteEstimateResponse(BaseModel):
    selected_estimate: SelectedEstimateDecisionRead


# Legacy aliases
QuoteJobAssignmentDecisionRead = SelectedEstimateDecisionRead
AssignQuoteJobResponse = SelectQuoteEstimateResponse


class EngineerAssignedJobRead(BaseModel):
    id: int
    eworks_job_id: int
    job_ref: str | None = None
    eworks_quote_id: int | None = None
    quote_ref: str | None = None
    customer_name: str | None = None
    address: str | None = None
    status: str | None = None
    status_name: str | None = None
    job_date: str | None = None
    description: str | None = None
    total: str | None = None
    appointment_user_name: str | None = None
    appointment_user_email: str | None = None
    appointment_type: str | None = None
    appointment_status: str | None = None
    appointment_start_at: str | None = None
    appointment_end_at: str | None = None
