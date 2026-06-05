import { apiFetch } from "@/lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type EworksSyncStatus = {
  quotes_count: number;
  jobs_count: number;
  last_quotes_sync: string | null;
  last_jobs_sync: string | null;
  eworks_api_enabled: boolean;
};

export type EworksSyncBucketSummary = {
  fetched: number;
  created: number;
  updated: number;
  failed: number;
};

export type EworksSyncResult = {
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
  synced_at: string | null;
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
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
};

export type JobFilters = {
  search?: string;
  customer_name?: string;
  status?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
};

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export async function getEworksSyncStatus(): Promise<EworksSyncStatus> {
  const resp = await apiFetch<EworksSyncStatus>("/api/v1/eworks-sync/status");
  return resp.data;
}

export async function triggerQuotesSync(req: EworksSyncRequest = {}): Promise<{
  summary: EworksSyncBucketSummary;
  run_id: string;
}> {
  const resp = await apiFetch<{ summary: EworksSyncBucketSummary; run_id: string }>(
    "/api/v1/eworks-sync/quotes",
    { method: "POST", body: JSON.stringify(req) }
  );
  return resp.data;
}

export async function triggerJobsSync(req: EworksSyncRequest = {}): Promise<{
  summary: EworksSyncBucketSummary;
  run_id: string;
}> {
  const resp = await apiFetch<{ summary: EworksSyncBucketSummary; run_id: string }>(
    "/api/v1/eworks-sync/jobs",
    { method: "POST", body: JSON.stringify(req) }
  );
  return resp.data;
}

export async function triggerAllSync(req: EworksSyncRequest = {}): Promise<EworksSyncResult> {
  const resp = await apiFetch<EworksSyncResult>(
    "/api/v1/eworks-sync/all",
    { method: "POST", body: JSON.stringify(req) }
  );
  return resp.data;
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
  if (filters.date_from) qs.set("date_from", filters.date_from);
  if (filters.date_to) qs.set("date_to", filters.date_to);
  if (filters.limit !== undefined) qs.set("limit", String(filters.limit));
  if (filters.offset !== undefined) qs.set("offset", String(filters.offset));
  const resp = await apiFetch<PaginatedResult<EworksJobRecord>>(
    `/api/v1/eworks-sync/jobs${qs.size ? `?${qs}` : ""}`
  );
  return resp.data;
}
