from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class ReviseEstimateRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class ReviseEstimateResponse(BaseModel):
    session_id: UUID
    resume_url: str
    revision_in_progress: bool = True
    active_revision_reason: str
    current_version_number: int


class CalculationSessionVersionRead(BaseModel):
    version_number: int
    submitted_at: datetime | None = None
    submitted_by_name: str | None = None
    submitted_by_email: str | None = None
    revision_reason: str | None = None
    final_total: Decimal | None = None
    status: str
    is_current: bool = False


class SessionVersionHistoryResponse(BaseModel):
    session_id: UUID
    current_version_number: int
    revision_in_progress: bool = False
    active_revision_reason: str | None = None
    versions: list[CalculationSessionVersionRead] = Field(default_factory=list)
