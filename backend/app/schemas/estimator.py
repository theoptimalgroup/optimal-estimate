from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.quote_acceptance import QuoteAcceptanceStatusRead


class EstimatorKpis(BaseModel):
    draft_count: int
    submitted_count: int
    reopened_count: int
    total_submitted_value: Decimal
    average_quote_value: Decimal
    accepted_count: int = 0


class EstimatorQuoteRow(BaseModel):
    session_id: UUID
    quote_ref: str
    client_name: str
    trade_name: str
    status: str
    total: Decimal | None = None
    updated_at: datetime
    submitted_at: datetime | None = None
    has_notes: bool = False
    work_count: int = 0
    can_resume: bool = False
    can_view_review: bool = False
    is_reopened: bool = False
    acceptance: QuoteAcceptanceStatusRead = Field(default_factory=QuoteAcceptanceStatusRead)


class EstimatorNeedsAttentionItem(BaseModel):
    session_id: UUID
    quote_ref: str
    reason: str


class EstimatorDashboardRead(BaseModel):
    kpis: EstimatorKpis
    recent_quotes: list[EstimatorQuoteRow] = Field(default_factory=list)
    needs_attention: list[EstimatorNeedsAttentionItem] = Field(default_factory=list)


class EstimatorQuoteDetailRead(EstimatorQuoteRow):
    job_number: str | None = None
    property_address: str | None = None


class EstimatorResumeRead(BaseModel):
    session_id: UUID
    session_token: str


class EstimatorClientRead(BaseModel):
    id: UUID
    name: str
    is_active: bool
    aliases: list[str] = Field(default_factory=list)


class EstimatorProductRead(BaseModel):
    id: int
    product_name: str
    product_code: str | None = None
    category: str | None = None
    scope_of_work: str | None = None
    is_active: bool = True
