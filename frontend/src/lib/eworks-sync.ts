import { apiFetch } from "@/lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export const EWORKS_ACTIVE_SYNC_RUN_KEY = "eworks-active-sync-run";

export type EworksActiveSync = {
  run_id: string;
  sync_type: string;
  started_at: string | null;
  phase?: string | null;
};

export type EworksBackgroundSyncConfig = {
  enabled: boolean;
  worker_enabled: boolean;
  scheduler_active: boolean;
  customers_enabled: boolean;
  quotes_enabled: boolean;
  jobs_enabled: boolean;
  products_enabled: boolean;
  attachments_enabled: boolean;
  customers_interval_minutes: number;
  quotes_interval_minutes: number;
  jobs_interval_minutes: number;
  products_interval_minutes: number;
  lookback_days: number;
  running_timeout_minutes: number;
  lock_timeout_minutes: number;
  lock_heartbeat_seconds: number;
};

export type EworksSyncLock = {
  sync_type: string;
  locked_by: string | null;
  status: string;
  started_at: string | null;
  heartbeat_at: string | null;
  expires_at: string | null;
  is_stale: boolean;
};

export type EworksBackgroundSyncLastRun = {
  run_id?: string | null;
  sync_type?: string | null;
  status?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  source?: string | null;
  phase?: string | null;
  fetched_count?: number | null;
  updated_count?: number | null;
  failed_count?: number | null;
  error_message?: string | null;
};

export type EworksSyncStatus = {
  quotes_count: number;
  jobs_count: number;
  customers_count: number;
  products_count: number;
  last_quotes_sync: string | null;
  last_jobs_sync: string | null;
  last_customers_sync: string | null;
  last_products_sync: string | null;
  eworks_api_enabled: boolean;
  active_sync?: EworksActiveSync | null;
  background_sync: EworksBackgroundSyncConfig;
  last_background_sync?: EworksBackgroundSyncLastRun | null;
  active_sync_locks?: EworksSyncLock[];
  stale_lock_warning?: boolean;
  last_successful_syncs?: Record<string, EworksBackgroundSyncLastRun | null>;
};

export type EworksSyncStartResponse = {
  run_id: string;
  sync_type: string;
  status: string;
  message: string;
};

export type EworksSyncBucketSummary = {
  fetched: number;
  created: number;
  updated: number;
  failed: number;
};

export type EworksSyncResult = {
  customers: EworksSyncBucketSummary;
  quotes: EworksSyncBucketSummary;
  jobs: EworksSyncBucketSummary;
  errors: string[];
};

export type EworksSyncRequest = {
  full?: boolean;
  date_from?: string | null;
  date_to?: string | null;
  status?: string | null;
  page_limit?: number | null;
};

export type EworksSyncRunRecord = {
  id: string;
  sync_type: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  fetched_count: number;
  created_count: number;
  updated_count: number;
  failed_count: number;
  error_message: string | null;
  metadata?: {
    phase?: string;
    quotes?: EworksSyncBucketSummary;
    jobs?: EworksSyncBucketSummary;
    summary?: EworksSyncBucketSummary;
    errors?: string[];
  } | null;
};

export type EworksQuoteRecord = {
  id: number;
  eworks_quote_id: number;
  quote_ref: string | null;
  customer_id: number | null;
  customer_name: string | null;
  status: string | null;
  status_name: string | null;
  quote_date: string | null;
  expiry_date: string | null;
  description: string | null;
  customer_ref: string | null;
  po_ref: string | null;
  wo_ref: string | null;
  subtotal: number | null;
  vat: number | null;
  total: number | null;
  tags?: string[];
  synced_at: string | null;
  display_customer_name?: string | null;
  display_status?: string | null;
  display_tags?: string[];
  display_total?: number | null;
  display_quote_date?: string | null;
};

export type EworksJobRecord = {
  id: number;
  eworks_job_id: number;
  job_ref: string | null;
  eworks_quote_id: number | null;
  customer_id: number | null;
  customer_name: string | null;
  status: string | null;
  status_name: string | null;
  job_date: string | null;
  description: string | null;
  address: string | null;
  subtotal: number | null;
  vat: number | null;
  total: number | null;
  tags?: string[];
  total_appointments?: number | null;
  completed_appointments?: number | null;
  detail_synced_at?: string | null;
  synced_at: string | null;
};

export type JobAppointmentBackfillSummary = {
  jobs_scanned: number;
  jobs_with_total_appointments: number;
  detail_fetches_attempted: number;
  detail_fetches_success: number;
  detail_fetches_failed: number;
  appointments_created: number;
  appointments_updated: number;
};

export type EworksCustomerRecord = {
  id: number;
  eworks_customer_id: number;
  customer_name: string | null;
  full_name: string | null;
  company_name: string | null;
  email: string | null;
  phone: string | null;
  billing_email: string | null;
  address_1: string | null;
  address_2: string | null;
  city: string | null;
  county: string | null;
  postcode: string | null;
  synced_at: string | null;
};

export type PaginatedResult<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};

export type QuoteFilters = {
  search?: string;
  customer_name?: string;
  status?: string;
  tag?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
};

export type JobFilters = {
  search?: string;
  customer_name?: string;
  status?: string;
  tag?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
};

export type CustomerFilters = {
  search?: string;
  limit?: number;
  offset?: number;
};

export const EWORKS_SYNC_DEFAULT_DAYS = 7;

export function buildDefaultSyncRequest(full = false): EworksSyncRequest {
  if (full) {
    return { full: true };
  }
  const today = new Date();
  const from = new Date(today);
  from.setDate(from.getDate() - EWORKS_SYNC_DEFAULT_DAYS);
  return {
    full: false,
    date_from: from.toISOString().slice(0, 10),
    date_to: today.toISOString().slice(0, 10),
  };
}

export async function getEworksSyncStatus(): Promise<EworksSyncStatus> {
  const resp = await apiFetch<EworksSyncStatus>("/api/v1/eworks-sync/status");
  return resp.data;
}

export async function triggerQuotesSync(req: EworksSyncRequest = {}): Promise<EworksSyncStartResponse> {
  const resp = await apiFetch<EworksSyncStartResponse>(
    "/api/v1/eworks-sync/quotes",
    { method: "POST", body: JSON.stringify(req) }
  );
  return resp.data;
}

export async function triggerJobsSync(req: EworksSyncRequest = {}): Promise<EworksSyncStartResponse> {
  const resp = await apiFetch<EworksSyncStartResponse>(
    "/api/v1/eworks-sync/jobs",
    { method: "POST", body: JSON.stringify(req) }
  );
  return resp.data;
}

export async function backfillJobAppointments(limit?: number): Promise<JobAppointmentBackfillSummary> {
  const params = new URLSearchParams();
  if (limit != null) params.set("limit", String(limit));
  const qs = params.toString();
  const resp = await apiFetch<JobAppointmentBackfillSummary>(
    `/api/v1/eworks-sync/jobs/backfill-appointments${qs ? `?${qs}` : ""}`,
    { method: "POST" },
  );
  return resp.data;
}

export async function triggerCustomersSync(req: EworksSyncRequest = {}): Promise<EworksSyncStartResponse> {
  const resp = await apiFetch<EworksSyncStartResponse>(
    "/api/v1/eworks-sync/customers",
    { method: "POST", body: JSON.stringify(req) }
  );
  return resp.data;
}

export async function triggerAllSync(req: EworksSyncRequest = {}): Promise<EworksSyncStartResponse> {
  const resp = await apiFetch<EworksSyncStartResponse>(
    "/api/v1/eworks-sync/all",
    { method: "POST", body: JSON.stringify(req) }
  );
  return resp.data;
}

export async function getSyncRun(runId: string): Promise<EworksSyncRunRecord> {
  const resp = await apiFetch<EworksSyncRunRecord>(`/api/v1/eworks-sync/runs/${runId}`);
  return resp.data;
}

export async function cancelSyncRun(runId: string): Promise<EworksSyncRunRecord> {
  const resp = await apiFetch<EworksSyncRunRecord>(`/api/v1/eworks-sync/runs/${runId}/cancel`, {
    method: "POST",
  });
  return resp.data;
}

export function runToSyncResult(run: EworksSyncRunRecord): EworksSyncResult | EworksSyncBucketSummary | null {
  if (run.sync_type === "all" && run.metadata) {
    return {
      customers: run.metadata.customers ?? { fetched: 0, created: 0, updated: 0, failed: 0 },
      quotes: run.metadata.quotes ?? { fetched: 0, created: 0, updated: 0, failed: 0 },
      jobs: run.metadata.jobs ?? { fetched: 0, created: 0, updated: 0, failed: 0 },
      errors: run.metadata.errors ?? (run.error_message ? [run.error_message] : []),
    };
  }
  if (run.metadata?.summary) {
    return run.metadata.summary;
  }
  if (run.status !== "running") {
    return {
      fetched: run.fetched_count,
      created: run.created_count,
      updated: run.updated_count,
      failed: run.failed_count,
    };
  }
  return null;
}

export async function getSyncRuns(params: { limit?: number; offset?: number } = {}): Promise<
  PaginatedResult<EworksSyncRunRecord>
> {
  const qs = new URLSearchParams();
  if (params.limit !== undefined) qs.set("limit", String(params.limit));
  if (params.offset !== undefined) qs.set("offset", String(params.offset));
  const resp = await apiFetch<PaginatedResult<EworksSyncRunRecord>>(
    `/api/v1/eworks-sync/runs${qs.size ? `?${qs}` : ""}`
  );
  return resp.data;
}

export async function listSyncedQuotes(
  filters: QuoteFilters = {}
): Promise<PaginatedResult<EworksQuoteRecord>> {
  const qs = new URLSearchParams();
  if (filters.search) qs.set("search", filters.search);
  if (filters.customer_name) qs.set("customer_name", filters.customer_name);
  if (filters.status) qs.set("status", filters.status);
  if (filters.tag) qs.set("tag", filters.tag);
  if (filters.date_from) qs.set("date_from", filters.date_from);
  if (filters.date_to) qs.set("date_to", filters.date_to);
  if (filters.limit !== undefined) qs.set("limit", String(filters.limit));
  if (filters.offset !== undefined) qs.set("offset", String(filters.offset));
  const resp = await apiFetch<PaginatedResult<EworksQuoteRecord>>(
    `/api/v1/eworks-sync/quotes${qs.size ? `?${qs}` : ""}`
  );
  return resp.data;
}

export async function listSyncedJobs(
  filters: JobFilters = {}
): Promise<PaginatedResult<EworksJobRecord>> {
  const qs = new URLSearchParams();
  if (filters.search) qs.set("search", filters.search);
  if (filters.customer_name) qs.set("customer_name", filters.customer_name);
  if (filters.status) qs.set("status", filters.status);
  if (filters.tag) qs.set("tag", filters.tag);
  if (filters.date_from) qs.set("date_from", filters.date_from);
  if (filters.date_to) qs.set("date_to", filters.date_to);
  if (filters.limit !== undefined) qs.set("limit", String(filters.limit));
  if (filters.offset !== undefined) qs.set("offset", String(filters.offset));
  const resp = await apiFetch<PaginatedResult<EworksJobRecord>>(
    `/api/v1/eworks-sync/jobs${qs.size ? `?${qs}` : ""}`
  );
  return resp.data;
}

export async function listSyncedCustomers(
  filters: CustomerFilters = {}
): Promise<PaginatedResult<EworksCustomerRecord>> {
  const qs = new URLSearchParams();
  if (filters.search) qs.set("search", filters.search);
  if (filters.limit !== undefined) qs.set("limit", String(filters.limit));
  if (filters.offset !== undefined) qs.set("offset", String(filters.offset));
  const resp = await apiFetch<PaginatedResult<EworksCustomerRecord>>(
    `/api/v1/eworks-sync/customers${qs.size ? `?${qs}` : ""}`
  );
  return resp.data;
}

export type EworksSafeLineItem = {
  name?: string | null;
  description?: string | null;
  quantity?: string | null;
  unit_price?: string | null;
  total?: string | null;
};

export type EworksSafeCustomField = {
  label: string;
  field_key: string;
  value: string;
};

export type EworksLinkedEstimate = {
  has_estimate_session: boolean;
  session_id?: string | null;
  status?: string | null;
  client_accepted_at?: string | null;
};

export type EworksSafeFinancials = {
  subtotal?: number | null;
  vat?: number | null;
  total?: number | null;
  discount_type?: string | null;
  discount_value?: string | null;
  currency?: string | null;
};

export type EworksQuoteSafeDetail = {
  identity: {
    id: number;
    eworks_quote_id: number;
    quote_ref?: string | null;
    status?: string | null;
    status_name?: string | null;
    synced_at?: string | null;
  };
  customer: {
    customer_id?: number | string | null;
    customer_name?: string | null;
    customer_contact_id?: number | string | null;
    customer_contact_name?: string | null;
    customer_site_id?: number | string | null;
    site_name?: string | null;
    site_address?: string | null;
    customer_ref?: string | null;
    po_ref?: string | null;
    wo_ref?: string | null;
  };
  quote_details: {
    quote_type_id?: number | string | null;
    quote_source_id?: number | string | null;
    project_id?: number | string | null;
    quote_date?: string | null;
    expiry_date?: string | null;
    preferred_date?: string | null;
    preferred_time?: string | null;
    description?: string | null;
    notes?: string | null;
    customer_notes?: string | null;
    terms?: string | null;
  };
  financials: EworksSafeFinancials;
  tags: string[];
  items: EworksSafeLineItem[];
  custom_fields: EworksSafeCustomField[];
  dates: {
    created_on?: string | null;
    updated_on?: string | null;
    converted_date?: string | null;
    accepted_date?: string | null;
  };
  linked_estimate: EworksLinkedEstimate;
};

export type EworksJobAppointmentSafe = {
  appointment_id?: number | null;
  user_name?: string | null;
  user_email?: string | null;
  user_id?: number | null;
  appointment_type?: string | null;
  status?: string | null;
  start_at?: string | null;
  end_at?: string | null;
  is_active_assignment?: boolean;
};

export type EworksJobSafeDetail = {
  identity: {
    id: number;
    eworks_job_id: number;
    job_ref?: string | null;
    status?: string | null;
    status_name?: string | null;
    synced_at?: string | null;
  };
  customer: {
    customer_id?: number | string | null;
    customer_name?: string | null;
    customer_contact_id?: number | string | null;
    customer_contact_name?: string | null;
    customer_site_id?: number | string | null;
    site_name?: string | null;
    site_address?: string | null;
  };
  related_quote: {
    eworks_quote_id?: number | string | null;
    quote_ref?: string | null;
  };
  job_details: {
    job_date?: string | null;
    description?: string | null;
    notes?: string | null;
  };
  financials: EworksSafeFinancials;
  tags: string[];
  items: EworksSafeLineItem[];
  custom_fields: EworksSafeCustomField[];
  dates: {
    created_on?: string | null;
    updated_on?: string | null;
    completed_date?: string | null;
  };
  linked_estimate: EworksLinkedEstimate;
  appointments?: EworksJobAppointmentSafe[];
};

export async function getSafeQuoteDetail(id: number): Promise<EworksQuoteSafeDetail> {
  const resp = await apiFetch<EworksQuoteSafeDetail>(`/api/v1/eworks-sync/quotes/${id}/safe`);
  return resp.data;
}

export async function getSafeJobDetail(id: number): Promise<EworksJobSafeDetail> {
  const resp = await apiFetch<EworksJobSafeDetail>(`/api/v1/eworks-sync/jobs/${id}/safe`);
  return resp.data;
}

export type EworksAttachmentSafe = {
  id: number;
  filename?: string | null;
  mime_type?: string | null;
  size_bytes?: number | null;
  description?: string | null;
  uploaded_by?: string | null;
  created_on?: string | null;
  synced_at?: string | null;
};

export async function listQuoteAttachments(quoteId: number): Promise<EworksAttachmentSafe[]> {
  const resp = await apiFetch<{ items: EworksAttachmentSafe[]; total: number }>(
    `/api/v1/eworks-sync/quotes/${quoteId}/attachments`
  );
  return resp.data.items;
}

export async function listJobAttachments(jobId: number): Promise<EworksAttachmentSafe[]> {
  const resp = await apiFetch<{ items: EworksAttachmentSafe[]; total: number }>(
    `/api/v1/eworks-sync/jobs/${jobId}/attachments`
  );
  return resp.data.items;
}
