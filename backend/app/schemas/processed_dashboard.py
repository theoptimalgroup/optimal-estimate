from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

SalesBucket = Literal["pending", "possible", "strong", "dormant"]
FollowUpStatus = Literal["overdue", "due_today", "due_this_week", "no_followup", "future"]
AgingBucketKey = Literal["0_7_days", "8_14_days", "15_30_days", "31_60_days", "60_plus_days"]


class ProcessedDashboardQuoteRow(BaseModel):
    id: int
    quote_ref: str | None
    eworks_quote_id: int
    customer_name: str | None
    site_address: str | None
    quote_value: float | None
    processed_at: str | None
    days_since_processed: int
    days_in_current_bucket: int
    last_follow_up_at: str | None
    next_follow_up_at: str | None
    follow_up_status: FollowUpStatus
    sales_bucket: SalesBucket
    sales_note: str | None
    assigned_sales_name: str | None
    assigned_sales_email: str | None
    assigned_sales_user_id: str | None
    eworks_status: str | None
    eworks_status_name: str | None
    tags: list[str] = Field(default_factory=list)
    quote_detail_link: str


class ProcessedDashboardCategory(BaseModel):
    count: int
    value: float
    average_age_days: float
    overdue_followups: int
    quotes: list[ProcessedDashboardQuoteRow]


class ProcessedDashboardCategories(BaseModel):
    pending: ProcessedDashboardCategory
    possible: ProcessedDashboardCategory
    strong: ProcessedDashboardCategory
    dormant: ProcessedDashboardCategory


class ProcessedDashboardAgingBucket(BaseModel):
    count: int
    value: float


class ProcessedDashboardAging(BaseModel):
    days_0_7: ProcessedDashboardAgingBucket = Field(alias="0_7_days")
    days_8_14: ProcessedDashboardAgingBucket = Field(alias="8_14_days")
    days_15_30: ProcessedDashboardAgingBucket = Field(alias="15_30_days")
    days_31_60: ProcessedDashboardAgingBucket = Field(alias="31_60_days")
    days_60_plus: ProcessedDashboardAgingBucket = Field(alias="60_plus_days")

    model_config = {"populate_by_name": True}


class ProcessedDashboardFollowUpReminders(BaseModel):
    overdue: list[ProcessedDashboardQuoteRow]
    due_today: list[ProcessedDashboardQuoteRow]
    due_this_week: list[ProcessedDashboardQuoteRow]
    no_followup_set: list[ProcessedDashboardQuoteRow]


class SalespersonPerformanceRow(BaseModel):
    salesperson_name: str | None
    salesperson_email: str | None
    assigned_count: int
    pipeline_value: float
    strong_value: float
    accepted_count: int
    rejected_count: int
    conversion_rate: float
    overdue_followups: int
    average_days_to_close: float | None


class AcceptedRejectedTrendMonth(BaseModel):
    month: str
    accepted_count: int
    rejected_count: int
    accepted_value: float
    rejected_value: float


class MonthlyPipelineValueMonth(BaseModel):
    month: str
    new_processed_value: float
    active_pipeline_value: float
    strong_pipeline_value: float
    accepted_value: float
    rejected_value: float


class ProcessedDashboardTotals(BaseModel):
    processed_quotes: int
    pipeline_value: float
    strong_value: float
    dormant_quotes: int
    overdue_followups: int
    due_today_followups: int
    no_followup_set: int
    average_age_days: float
    conversion_rate: float
    accepted_count: int
    rejected_count: int
    accepted_value: float
    rejected_value: float


class ProcessedDashboardRead(BaseModel):
    totals: ProcessedDashboardTotals
    categories: ProcessedDashboardCategories
    aging: dict[str, ProcessedDashboardAgingBucket]
    follow_up_reminders: ProcessedDashboardFollowUpReminders
    salesperson_performance: list[SalespersonPerformanceRow]
    accepted_rejected_trend: list[AcceptedRejectedTrendMonth]
    monthly_pipeline_value: list[MonthlyPipelineValueMonth]


class SalesPipelinePatch(BaseModel):
    sales_bucket: SalesBucket | None = None
    sales_note: str | None = None
    assigned_sales_user_id: str | None = None
    assigned_sales_email: str | None = None
    assigned_sales_name: str | None = None
    last_follow_up_at: str | None = None
    next_follow_up_at: str | None = None


class SalesPipelineRead(BaseModel):
    id: str
    synced_quote_id: int | None
    eworks_quote_id: int
    quote_ref: str | None
    sales_bucket: SalesBucket
    sales_note: str | None
    assigned_sales_user_id: str | None
    assigned_sales_email: str | None
    assigned_sales_name: str | None
    processed_at: str | None
    last_follow_up_at: str | None
    next_follow_up_at: str | None
    bucket_changed_at: str | None
    accepted_at: str | None
    rejected_at: str | None
    closed_at: str | None
