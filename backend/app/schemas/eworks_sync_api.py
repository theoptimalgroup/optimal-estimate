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
    customers: EworksSyncBucketSummary = Field(default_factory=EworksSyncBucketSummary)
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
    tags: list[str] = Field(default_factory=list)
    synced_at: str | None
    display_customer_name: str | None = None
    display_status: str | None = None
    display_tags: list[str] = Field(default_factory=list)
    display_total: float | None = None
    display_quote_date: str | None = None

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
    tags: list[str] = Field(default_factory=list)
    total_appointments: int | None = None
    completed_appointments: int | None = None
    detail_synced_at: str | None = None
    synced_at: str | None

    model_config = {"from_attributes": True}


class EworksCustomerRead(BaseModel):
    id: int
    eworks_customer_id: int
    customer_name: str | None
    full_name: str | None
    company_name: str | None
    email: str | None
    phone: str | None
    billing_email: str | None
    address_1: str | None
    address_2: str | None
    city: str | None
    county: str | None
    postcode: str | None
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
    metadata: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class EworksSyncStartResponse(BaseModel):
    run_id: str
    sync_type: str
    status: str = "running"
    message: str = "Sync started in background"


class EworksActiveSyncRun(BaseModel):
    run_id: str
    sync_type: str
    started_at: str | None
    phase: str | None = None


class EworksBackgroundSyncConfigRead(BaseModel):
    enabled: bool
    worker_enabled: bool
    scheduler_active: bool
    customers_enabled: bool = True
    quotes_enabled: bool
    jobs_enabled: bool
    products_enabled: bool
    attachments_enabled: bool
    customers_interval_minutes: int = 720
    quotes_interval_minutes: int
    jobs_interval_minutes: int
    products_interval_minutes: int
    lookback_days: int
    running_timeout_minutes: int
    lock_timeout_minutes: int = 30
    lock_heartbeat_seconds: int = 60
    max_pages: int = 0
    # Incremental quote sync
    quotes_sync_mode: str = "incremental_recent"
    quotes_recent_window_minutes: int = 60
    quotes_timeout_seconds: int = 120
    attachments_during_quote_sync: bool = False
    quote_appointments_during_quote_sync: bool = False


class EworksSyncLockRead(BaseModel):
    sync_type: str
    locked_by: str | None = None
    status: str
    started_at: str | None = None
    heartbeat_at: str | None = None
    expires_at: str | None = None
    is_stale: bool = False


class EworksBackgroundSyncLastRunRead(BaseModel):
    run_id: str | None = None
    sync_type: str | None = None
    status: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    source: str | None = None
    phase: str | None = None
    fetched_count: int | None = None
    updated_count: int | None = None
    failed_count: int | None = None
    error_message: str | None = None


class EworksSyncStatusResponse(BaseModel):
    quotes_count: int
    jobs_count: int
    customers_count: int
    products_count: int = 0
    last_quotes_sync: str | None
    last_jobs_sync: str | None
    last_customers_sync: str | None
    last_products_sync: str | None = None
    eworks_api_enabled: bool
    active_sync: EworksActiveSyncRun | None = None
    background_sync: EworksBackgroundSyncConfigRead
    last_background_sync: EworksBackgroundSyncLastRunRead | None = None
    active_sync_locks: list[EworksSyncLockRead] = []
    stale_lock_warning: bool = False
    last_successful_syncs: dict[str, EworksBackgroundSyncLastRunRead | None] = {}


class EworksQuoteDetailRead(EworksQuoteRead):
    notes: str | None
    customer_notes: str | None
    terms: str | None
    project_id: int | None
    raw_payload: dict | None


class EworksSafeLineItem(BaseModel):
    name: str | None = None
    description: str | None = None
    quantity: str | None = None
    unit_price: str | None = None
    total: str | None = None


class EworksSafeCustomField(BaseModel):
    label: str
    field_key: str
    value: str


class EworksLinkedEstimate(BaseModel):
    has_estimate_session: bool = False
    session_id: str | None = None
    status: str | None = None
    client_accepted_at: str | None = None


class EworksQuoteSafeIdentity(BaseModel):
    id: int
    eworks_quote_id: int
    quote_ref: str | None = None
    status: str | None = None
    status_name: str | None = None
    synced_at: str | None = None


class EworksQuoteSafeCustomer(BaseModel):
    customer_id: int | str | None = None
    customer_name: str | None = None
    customer_contact_id: int | str | None = None
    customer_contact_name: str | None = None
    customer_site_id: int | str | None = None
    site_name: str | None = None
    site_address: str | None = None
    customer_ref: str | None = None
    po_ref: str | None = None
    wo_ref: str | None = None


class EworksQuoteSafeDetails(BaseModel):
    quote_type_id: int | str | None = None
    quote_source_id: int | str | None = None
    project_id: int | str | None = None
    quote_date: str | None = None
    expiry_date: str | None = None
    preferred_date: str | None = None
    preferred_time: str | None = None
    description: str | None = None
    notes: str | None = None
    customer_notes: str | None = None
    terms: str | None = None


class EworksSafeFinancials(BaseModel):
    subtotal: float | None = None
    vat: float | None = None
    total: float | None = None
    discount_type: str | None = None
    discount_value: str | None = None
    currency: str | None = None


class EworksSafeDates(BaseModel):
    created_on: str | None = None
    updated_on: str | None = None
    converted_date: str | None = None
    accepted_date: str | None = None


class EworksQuoteAppointmentSafeRead(BaseModel):
    appointment_id: int | None = None
    user_name: str | None = None
    user_email: str | None = None
    user_id: int | None = None
    user_mobile: str | None = None
    user_telephone: str | None = None
    appointment_type: str | None = None
    status: str | None = None
    is_sales_appointment: bool | None = None
    start_at: str | None = None
    end_at: str | None = None
    duration_minutes: int | None = None


class EworksAppointmentAssigneeSafeRead(BaseModel):
    name: str | None = None
    email: str | None = None
    registered_user_id: str | None = None
    assignee_kind: str | None = None
    appointment_type: str | None = None
    status: str | None = None
    start_at: str | None = None
    end_at: str | None = None
    source: str | None = None
    job_ref: str | None = None


class EworksQuoteSafeDetailRead(BaseModel):
    identity: EworksQuoteSafeIdentity
    customer: EworksQuoteSafeCustomer
    quote_details: EworksQuoteSafeDetails
    financials: EworksSafeFinancials
    tags: list[str] = Field(default_factory=list)
    items: list[EworksSafeLineItem] = Field(default_factory=list)
    custom_fields: list[EworksSafeCustomField] = Field(default_factory=list)
    dates: EworksSafeDates
    linked_estimate: EworksLinkedEstimate
    sales_appointments: list[EworksQuoteAppointmentSafeRead] = Field(default_factory=list)
    appointment_assignee: EworksAppointmentAssigneeSafeRead | None = None


class EworksJobSafeIdentity(BaseModel):
    id: int
    eworks_job_id: int
    job_ref: str | None = None
    status: str | None = None
    status_name: str | None = None
    synced_at: str | None = None


class EworksJobSafeCustomer(BaseModel):
    customer_id: int | str | None = None
    customer_name: str | None = None
    customer_contact_id: int | str | None = None
    customer_contact_name: str | None = None
    customer_site_id: int | str | None = None
    site_name: str | None = None
    site_address: str | None = None


class EworksJobSafeRelatedQuote(BaseModel):
    eworks_quote_id: int | str | None = None
    quote_ref: str | None = None


class EworksJobSafeDetails(BaseModel):
    job_date: str | None = None
    description: str | None = None
    notes: str | None = None


class EworksJobSafeDates(BaseModel):
    created_on: str | None = None
    updated_on: str | None = None
    completed_date: str | None = None


class EworksJobAppointmentSafeRead(BaseModel):
    appointment_id: int | None = None
    user_name: str | None = None
    user_email: str | None = None
    user_id: int | None = None
    user_mobile: str | None = None
    user_telephone: str | None = None
    appointment_type: str | None = None
    status: str | None = None
    is_sales_appointment: bool | None = None
    start_at: str | None = None
    end_at: str | None = None
    duration_minutes: int | None = None
    is_active_assignment: bool = False


class EworksJobSafeDetailRead(BaseModel):
    identity: EworksJobSafeIdentity
    customer: EworksJobSafeCustomer
    related_quote: EworksJobSafeRelatedQuote
    job_details: EworksJobSafeDetails
    financials: EworksSafeFinancials
    tags: list[str] = Field(default_factory=list)
    items: list[EworksSafeLineItem] = Field(default_factory=list)
    custom_fields: list[EworksSafeCustomField] = Field(default_factory=list)
    dates: EworksJobSafeDates
    linked_estimate: EworksLinkedEstimate
    appointments: list[EworksJobAppointmentSafeRead] = Field(default_factory=list)


class EworksAttachmentSafeRead(BaseModel):
    id: int
    filename: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    description: str | None = None
    uploaded_by: str | None = None
    created_on: str | None = None
    synced_at: str | None = None


class EworksAttachmentDetailRead(EworksAttachmentSafeRead):
    eworks_attachment_id: str | None = None
    parent_type: str
    parent_eworks_id: int
    parent_local_id: int | None = None
    download_endpoint: str | None = None
    local_storage_path: str | None = None
    downloaded_at: str | None = None
    raw_payload: dict | None = None


class EworksJobAppointmentBackfillRead(BaseModel):
    jobs_scanned: int
    jobs_with_total_appointments: int
    appointments_found: int = 0
    sales_appointments_found: int = 0
    detail_fetches_attempted: int
    detail_fetches_success: int
    detail_fetches_failed: int
    appointments_created: int
    appointments_updated: int
    failed: int = 0
    skipped: int = 0
    next_offset: int = 0
    has_more: bool = False
    elapsed_seconds: float = 0.0
    stopped_reason: str = "completed"


class EworksQuoteSalesAppointmentBackfillRead(BaseModel):
    quotes_scanned: int
    quote_details_fetched: int = 0
    appointments_found: int
    appointments_created: int
    appointments_updated: int
    sales_appointments_found: int
    failed: int
    skipped: int = 0
    next_offset: int = 0
    has_more: bool = False
    elapsed_seconds: float = 0.0
    stopped_reason: str = "completed"
    rate_limited_count: int = 0


class EworksQuoteAttachmentBackfillRead(BaseModel):
    quotes_scanned: int
    details_fetched: int
    attachment_endpoint_calls: int
    quotes_with_attachments: int
    attachments_created: int
    attachments_updated: int
    failed: int
