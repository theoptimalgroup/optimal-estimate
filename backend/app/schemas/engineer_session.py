from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.eworks_link import SessionAttachmentMeta

EngineerDurationType = Literal["hourly", "half_day", "day_up_to_2", "day_3_plus"]

MAX_ENGINEER_NOTE_LENGTH = 8000


class EngineerJobSummary(BaseModel):
    quote_number: str
    job_number: str
    client_name: str
    trade_name: str
    property_address: str
    engineer_name: str | None = None
    status: str


class EngineerSiteVisitRead(BaseModel):
    scope: str | None = None
    site_notes: str | None = None
    findings: str | None = None
    attachments: list[SessionAttachmentMeta] = Field(default_factory=list)
    engineer_count: int = 0
    labourer_count: int = 0
    duration_type: EngineerDurationType = "hourly"
    hours: Decimal | None = None
    days: Decimal | None = None
    materials_required: str | None = None
    unit_cost: Decimal | None = None
    parking_required: bool = False
    parking_amount: Decimal | None = None
    congestion_required: bool = False
    congestion_amount: Decimal | None = None
    ulez_required: bool = False
    ulez_amount: Decimal | None = None
    waste_required: bool = False
    waste_amount: Decimal | None = None


class EngineerSessionRead(BaseModel):
    session_id: UUID
    status: str
    expires_at: datetime
    job: EngineerJobSummary
    site_visit: EngineerSiteVisitRead


class EngineerSiteVisitUpdate(BaseModel):
    scope: str | None = None
    site_notes: str | None = None
    findings: str | None = None
    engineer_count: int = Field(default=0, ge=0)
    labourer_count: int = Field(default=0, ge=0)
    duration_type: EngineerDurationType = "hourly"
    hours: Decimal | None = None
    days: Decimal | None = None
    materials_required: str | None = None
    unit_cost: Decimal | None = Field(default=None, ge=0)
    parking_required: bool = False
    parking_amount: Decimal | None = Field(default=None, ge=0)
    congestion_required: bool = False
    congestion_amount: Decimal | None = Field(default=None, ge=0)
    ulez_required: bool = False
    ulez_amount: Decimal | None = Field(default=None, ge=0)
    waste_required: bool = False
    waste_amount: Decimal | None = Field(default=None, ge=0)

    @field_validator("scope", "site_notes", "findings", "materials_required")
    @classmethod
    def validate_note_lengths(cls, value: str | None) -> str | None:
        if value is not None and len(value) > MAX_ENGINEER_NOTE_LENGTH:
            raise ValueError(f"Text must be at most {MAX_ENGINEER_NOTE_LENGTH} characters")
        return value

    def model_validate_duration(self) -> None:
        if self.duration_type == "hourly":
            if self.hours is None or self.hours <= 0:
                raise ValueError("Hours must be greater than 0 for hourly duration")
        else:
            if self.days is None or self.days <= 0:
                raise ValueError("Days must be greater than 0 for day-based duration")


class EngineerSiteVisitUpdateResponse(BaseModel):
    session_id: UUID
    status: str
    saved: bool = True
    message: str = "Site visit saved for estimator review."
