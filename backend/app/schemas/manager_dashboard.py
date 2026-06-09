from __future__ import annotations

from pydantic import BaseModel, Field


class ManagerDashboardQuoteRow(BaseModel):
    id: int
    eworks_quote_id: int
    quote_ref: str | None
    customer_name: str | None
    status: str | None
    status_name: str | None
    tags: list[str] = Field(default_factory=list)
    quote_date: str | None
    expiry_date: str | None
    total: float | None
    synced_at: str | None
    matched_reason: str | None = None


class ManagerDashboardCategory(BaseModel):
    count: int
    filtered_count: int | None = None
    quotes: list[ManagerDashboardQuoteRow]


class ManagerDashboardCategories(BaseModel):
    new_quotes: ManagerDashboardCategory
    awaiting_supplier: ManagerDashboardCategory
    ready_to_send: ManagerDashboardCategory


class ManagerDashboardTotals(BaseModel):
    all_open_quotes: int


class ManagerDashboardRead(BaseModel):
    categories: ManagerDashboardCategories
    last_synced_at: str | None
    totals: ManagerDashboardTotals
    quotes_excluded_non_draft: int = 0
