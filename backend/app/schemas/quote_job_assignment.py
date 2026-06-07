from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AssignQuoteJobRequest(BaseModel):
    selected_session_id: UUID
    assignee_name: str = Field(min_length=1, max_length=500)
    assignee_email: str | None = Field(default=None, max_length=320)
    assignment_id: int | None = None


class QuoteJobAssignmentDecisionRead(BaseModel):
    id: int
    selected_session_id: UUID
    assignee_name: str
    assignee_email: str | None = None
    assignment_id: int | None = None
    assigned_at: datetime
    assigned_by_name: str | None = None
    assigned_by_email: str | None = None


class AssignQuoteJobResponse(BaseModel):
    decision: QuoteJobAssignmentDecisionRead


class EngineerAssignedJobRead(BaseModel):
    id: int
    quote_ref: str | None = None
    eworks_quote_id: int | None = None
    job_ref: str | None = None
    customer_name: str | None = None
    address: str | None = None
    selected_at: datetime
    selected_estimate_total: str | None = None
    selected_session_id: UUID
    status: str = "assigned"
    assignment_id: int | None = None
