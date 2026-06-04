from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class ReportKpis(BaseModel):
    submitted_quotes: int
    total_value: Decimal
    average_quote_value: Decimal
    approved_or_ready_count: int | None = None
    reopened_count: int | None = None
    with_internal_notes_count: int | None = None
    accepted_count: int | None = None
    accepted_value: Decimal | None = None


class ReportStatusBreakdown(BaseModel):
    status: str
    count: int
    value: Decimal


class ReportClientBreakdown(BaseModel):
    client_id: UUID | None = None
    client_name: str
    count: int
    value: Decimal


class ReportTradeBreakdown(BaseModel):
    trade_id: UUID | None = None
    trade_name: str
    count: int
    value: Decimal


class ReportTrendPoint(BaseModel):
    period: str
    count: int
    value: Decimal


class ReportRecentQuote(BaseModel):
    session_id: UUID
    quote_ref: str
    client_name: str
    trade_name: str
    status: str
    total: Decimal | None = None
    submitted_at: datetime | None = None
    client_accepted: bool = False
    client_accepted_at: datetime | None = None


class ReportSummaryRead(BaseModel):
    kpis: ReportKpis
    by_status: list[ReportStatusBreakdown] = Field(default_factory=list)
    by_client: list[ReportClientBreakdown] = Field(default_factory=list)
    by_trade: list[ReportTradeBreakdown] = Field(default_factory=list)
    trend: list[ReportTrendPoint] = Field(default_factory=list)
    recent_quotes: list[ReportRecentQuote] = Field(default_factory=list)


class ReportQuoteRow(BaseModel):
    session_id: UUID
    quote_ref: str
    job_number: str | None = None
    client_name: str
    trade_name: str
    status: str
    total: Decimal | None = None
    submitted_at: datetime | None = None
    has_internal_notes: bool = False
