from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

CallBackBucket = Literal["overdue", "due_today", "upcoming", "no_call_date"]
CallBackStatus = Literal["overdue", "due_today", "upcoming", "no_call_date", "completed"]


class CallBackDashboardQuoteRow(BaseModel):
    id: int
    quote_ref: str | None
    eworks_quote_id: int
    customer_name: str | None
    site_address: str | None
    quote_value: float | None
    status: str | None
    status_name: str | None
    tags: list[str] = Field(default_factory=list)
    created_on: str | None
    last_updated_on: str | None
    days_since_updated: int
    assigned_name: str | None
    assigned_email: str | None
    call_note: str | None
    last_called_at: str | None
    next_call_at: str | None
    call_status: CallBackStatus
    quote_detail_link: str


class CallBackDashboardCategory(BaseModel):
    count: int
    value: float
    quotes: list[CallBackDashboardQuoteRow]


class CallBackDashboardCategories(BaseModel):
    overdue: CallBackDashboardCategory
    due_today: CallBackDashboardCategory
    upcoming: CallBackDashboardCategory
    no_call_date: CallBackDashboardCategory


class CallBackDashboardTotals(BaseModel):
    call_back_quotes: int
    total_quote_value: float
    overdue_calls: int
    due_today_calls: int
    upcoming_calls: int
    no_call_date: int
    average_age_days: float


class CallBackDashboardRead(BaseModel):
    totals: CallBackDashboardTotals
    categories: CallBackDashboardCategories


class CallBackTrackingPatch(BaseModel):
    assigned_user_id: str | None = None
    assigned_name: str | None = None
    assigned_email: str | None = None
    call_note: str | None = None
    last_called_at: str | None = None
    next_call_at: str | None = None


class CallBackTrackingRead(BaseModel):
    id: str
    synced_quote_id: int | None
    eworks_quote_id: int
    quote_ref: str | None
    assigned_user_id: str | None
    assigned_name: str | None
    assigned_email: str | None
    call_note: str | None
    last_called_at: str | None
    next_call_at: str | None
    call_status: str | None
