"""Pydantic schemas for eWorks Quote/Job API responses and local sync models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# eWorks API response schemas (shared pagination envelope)
# ---------------------------------------------------------------------------

class EworksSyncMeta(BaseModel):
    total: int = 0
    last_page: int = 1
    current_page: int = 1
    from_: int | None = Field(default=None, alias="from")
    to: int | None = None
    per_page: int = 25

    model_config = {"populate_by_name": True}


class EworksSyncCollection(BaseModel):
    meta: EworksSyncMeta = Field(default_factory=EworksSyncMeta)
    data: list[dict[str, Any]] = Field(default_factory=list)


class EworksSyncApiResponse(BaseModel):
    status: int
    collection: EworksSyncCollection = Field(default_factory=EworksSyncCollection)

    model_config = {"extra": "allow"}


# ---------------------------------------------------------------------------
# Sync summary schemas
# ---------------------------------------------------------------------------

class EworksSyncBucketSummary(BaseModel):
    fetched: int = 0
    created: int = 0
    updated: int = 0
    failed: int = 0


class EworksSyncSummary(BaseModel):
    quotes: EworksSyncBucketSummary = Field(default_factory=EworksSyncBucketSummary)
    jobs: EworksSyncBucketSummary = Field(default_factory=EworksSyncBucketSummary)
    errors: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class EworksSyncRequest(BaseModel):
    full: bool = False
    date_from: str | None = None
    date_to: str | None = None
    status: str | None = None
    page_limit: int | None = None


# ---------------------------------------------------------------------------
# Read schemas for local DB records
# ---------------------------------------------------------------------------

class EworksQuoteRead(BaseModel):
    id: int
    eworks_quote_id: int
    quote_ref: str | None
    customer_id: int | None
    customer_name: str | None
    status: str | None
    status_name: str | None
    quote_date: str | None
    expiry_date: str | None
    description: str | None
    customer_ref: str | None
    po_ref: str | None
    wo_ref: str | None
    subtotal: float | None
    vat: float | None
    total: float | None
    synced_at: str | None

    model_config = {"from_attributes": True}


class EworksJobRead(BaseModel):
    id: int
    eworks_job_id: int
    job_ref: str | None
    eworks_quote_id: int | None
    customer_id: int | None
    customer_name: str | None
    status: str | None
    status_name: str | None
    job_date: str | None
    description: str | None
    address: str | None
    subtotal: float | None
    vat: float | None
    total: float | None
    synced_at: str | None

    model_config = {"from_attributes": True}


class EworksSyncRunRead(BaseModel):
    id: str
    sync_type: str
    status: str
    started_at: str | None
    finished_at: str | None
    fetched_count: int
    created_count: int
    updated_count: int
    failed_count: int
    error_message: str | None

    model_config = {"from_attributes": True}


class EworksSyncStatusResponse(BaseModel):
    quotes_count: int
    jobs_count: int
    last_quotes_sync: str | None
    last_jobs_sync: str | None
    eworks_api_enabled: bool


class EworksQuoteDetailRead(EworksQuoteRead):
    notes: str | None
    customer_notes: str | None
    terms: str | None
    project_id: int | None
    raw_payload: dict | None
