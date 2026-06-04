import { apiFetch } from "@/lib/api";
import { normalizeQuoteAcceptance, type QuoteAcceptanceStatus } from "@/lib/quote-acceptance";

export type EstimatorKpis = {
  draft_count: number;
  submitted_count: number;
  reopened_count: number;
  total_submitted_value: number;
  average_quote_value: number;
  accepted_count?: number;
};

export type EstimatorNeedsAttentionItem = {
  session_id: string;
  quote_ref: string;
  reason: string;
};

export type EstimatorQuoteRow = {
  session_id: string;
  quote_ref: string;
  client_name: string;
  trade_name: string;
  status: string;
  total: number | null;
  updated_at: string;
  submitted_at: string | null;
  has_notes: boolean;
  work_count: number;
  can_resume: boolean;
  can_view_review: boolean;
  is_reopened: boolean;
  acceptance: QuoteAcceptanceStatus;
};

export type EstimatorDashboard = {
  kpis: EstimatorKpis;
  recent_quotes: EstimatorQuoteRow[];
  needs_attention: EstimatorNeedsAttentionItem[];
};

export type EstimatorQuoteDetail = EstimatorQuoteRow & {
  job_number?: string | null;
  property_address?: string | null;
};

export type EstimatorResume = {
  session_id: string;
  session_token: string;
};

export type EstimatorClient = {
  id: string;
  name: string;
  is_active: boolean;
  aliases: string[];
};

export type EstimatorProduct = {
  id: number;
  product_name: string;
  product_code: string | null;
  category: string | null;
  scope_of_work: string | null;
  is_active: boolean;
};

export type EstimatorQuoteFilters = {
  search?: string;
  status?: string;
  client_id?: string;
  trade_id?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
};

function buildQuery(filters: Record<string, string | number | undefined>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== "") params.set(key, String(value));
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

function normalizeQuoteRow(raw: Record<string, unknown>): EstimatorQuoteRow {
  return {
    session_id: String(raw.session_id ?? ""),
    quote_ref: String(raw.quote_ref ?? "—"),
    client_name: String(raw.client_name ?? "—"),
    trade_name: String(raw.trade_name ?? "—"),
    status: String(raw.status ?? ""),
    total: raw.total != null ? Number(raw.total) : null,
    updated_at: String(raw.updated_at ?? ""),
    submitted_at: raw.submitted_at != null ? String(raw.submitted_at) : null,
    has_notes: Boolean(raw.has_notes),
    work_count: Number(raw.work_count ?? 0),
    can_resume: Boolean(raw.can_resume),
    can_view_review: Boolean(raw.can_view_review),
    is_reopened: Boolean(raw.is_reopened),
    acceptance: normalizeQuoteAcceptance(raw.acceptance as Record<string, unknown> | undefined),
  };
}

export async function getEstimatorDashboard(): Promise<EstimatorDashboard> {
  const response = await apiFetch<Record<string, unknown>>("/api/v1/estimator/dashboard");
  const raw = (response.data ?? {}) as Record<string, unknown>;
  const kpisRaw = (raw.kpis ?? {}) as Record<string, unknown>;
  return {
    kpis: {
      draft_count: Number(kpisRaw.draft_count ?? 0),
      submitted_count: Number(kpisRaw.submitted_count ?? 0),
      reopened_count: Number(kpisRaw.reopened_count ?? 0),
      total_submitted_value: Number(kpisRaw.total_submitted_value ?? 0),
      average_quote_value: Number(kpisRaw.average_quote_value ?? 0),
      accepted_count: Number(kpisRaw.accepted_count ?? 0),
    },
    recent_quotes: ((raw.recent_quotes as unknown[]) ?? []).map((item) =>
      normalizeQuoteRow(item as Record<string, unknown>),
    ),
    needs_attention: ((raw.needs_attention as unknown[]) ?? []).map((item) => {
      const row = item as Record<string, unknown>;
      return {
        session_id: String(row.session_id ?? ""),
        quote_ref: String(row.quote_ref ?? ""),
        reason: String(row.reason ?? ""),
      };
    }),
  };
}

export async function listEstimatorQuotes(filters: EstimatorQuoteFilters = {}): Promise<{
  items: EstimatorQuoteRow[];
  total: number;
  limit: number;
  offset: number;
}> {
  const response = await apiFetch<EstimatorQuoteRow[]>(
    `/api/v1/estimator/quotes${buildQuery({
      search: filters.search,
      status: filters.status,
      client_id: filters.client_id,
      trade_id: filters.trade_id,
      date_from: filters.date_from,
      date_to: filters.date_to,
      limit: filters.limit ?? 50,
      offset: filters.offset ?? 0,
    })}`,
  );
  const meta = response.meta ?? {};
  return {
    items: (response.data ?? []).map((item) => normalizeQuoteRow(item as unknown as Record<string, unknown>)),
    total: Number(meta.total ?? 0),
    limit: Number(meta.limit ?? filters.limit ?? 50),
    offset: Number(meta.offset ?? filters.offset ?? 0),
  };
}

export async function listEstimatorApprovals(limit = 50, offset = 0) {
  const response = await apiFetch<EstimatorQuoteRow[]>(
    `/api/v1/estimator/approvals${buildQuery({ limit, offset })}`,
  );
  const meta = response.meta ?? {};
  return {
    items: (response.data ?? []).map((item) => normalizeQuoteRow(item as unknown as Record<string, unknown>)),
    total: Number(meta.total ?? 0),
    limit: Number(meta.limit ?? limit),
    offset: Number(meta.offset ?? offset),
  };
}

export async function getEstimatorQuote(sessionId: string): Promise<EstimatorQuoteDetail> {
  const response = await apiFetch<Record<string, unknown>>(`/api/v1/estimator/quotes/${sessionId}`);
  const raw = (response.data ?? {}) as Record<string, unknown>;
  return {
    ...normalizeQuoteRow(raw),
    job_number: raw.job_number != null ? String(raw.job_number) : null,
    property_address: raw.property_address != null ? String(raw.property_address) : null,
  };
}

export async function resumeEstimatorQuote(sessionId: string): Promise<EstimatorResume> {
  const response = await apiFetch<EstimatorResume>(`/api/v1/estimator/quotes/${sessionId}/resume`, {
    method: "POST",
  });
  return {
    session_id: String(response.data.session_id ?? sessionId),
    session_token: String(response.data.session_token ?? ""),
  };
}

export async function listEstimatorClients(): Promise<EstimatorClient[]> {
  const response = await apiFetch<EstimatorClient[]>("/api/v1/estimator/clients");
  return (response.data ?? []).map((item) => {
    const raw = item as unknown as Record<string, unknown>;
    return {
      id: String(raw.id ?? ""),
      name: String(raw.name ?? ""),
      is_active: raw.is_active !== false,
      aliases: Array.isArray(raw.aliases) ? raw.aliases.map(String) : [],
    };
  });
}

export async function listEstimatorProducts(search?: string, limit = 100, offset = 0) {
  const response = await apiFetch<EstimatorProduct[]>(
    `/api/v1/estimator/products${buildQuery({ search, limit, offset })}`,
  );
  const meta = response.meta ?? {};
  return {
    items: (response.data ?? []).map((item) => {
      const raw = item as unknown as Record<string, unknown>;
      return {
        id: Number(raw.id ?? 0),
        product_name: String(raw.product_name ?? ""),
        product_code: raw.product_code != null ? String(raw.product_code) : null,
        category: raw.category != null ? String(raw.category) : null,
        scope_of_work: raw.scope_of_work != null ? String(raw.scope_of_work) : null,
        is_active: raw.is_active !== false,
      };
    }),
    total: Number(meta.total ?? 0),
    limit: Number(meta.limit ?? limit),
    offset: Number(meta.offset ?? offset),
  };
}

export function buildCalculatorResumeUrl(sessionId: string, token: string): string {
  const params = new URLSearchParams({ session_id: sessionId, token });
  return `/eworks/calculate?${params.toString()}`;
}

export function formatEstimatorDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export function formatMoney(value?: number | null): string {
  if (value === undefined || value === null || Number.isNaN(value)) return "—";
  return `£${value.toFixed(2)}`;
}

export function statusLabel(status: string, isReopened?: boolean): string {
  if (isReopened && status === "in_progress") return "Needs changes";
  if (status === "in_progress") return "In progress";
  if (status === "submitted") return "Submitted";
  return status;
}
