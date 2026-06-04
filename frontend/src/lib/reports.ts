import { apiFetch } from "@/lib/api";

export type ReportKpis = {
  submitted_quotes: number;
  total_value: number;
  average_quote_value: number;
  approved_or_ready_count?: number | null;
  reopened_count?: number | null;
  with_internal_notes_count?: number | null;
  accepted_count?: number | null;
  accepted_value?: number | null;
};

export type ReportStatusBreakdown = {
  status: string;
  count: number;
  value: number;
};

export type ReportClientBreakdown = {
  client_id: string | null;
  client_name: string;
  count: number;
  value: number;
};

export type ReportTradeBreakdown = {
  trade_id: string | null;
  trade_name: string;
  count: number;
  value: number;
};

export type ReportTrendPoint = {
  period: string;
  count: number;
  value: number;
};

export type ReportRecentQuote = {
  session_id: string;
  quote_ref: string;
  client_name: string;
  trade_name: string;
  status: string;
  total: number | null;
  submitted_at: string | null;
  client_accepted?: boolean;
  client_accepted_at?: string | null;
};

export type ReportSummary = {
  kpis: ReportKpis;
  by_status: ReportStatusBreakdown[];
  by_client: ReportClientBreakdown[];
  by_trade: ReportTradeBreakdown[];
  trend: ReportTrendPoint[];
  recent_quotes: ReportRecentQuote[];
};

export type ReportSummaryFilters = {
  date_from?: string;
  date_to?: string;
  client_id?: string;
  trade_id?: string;
  status?: string;
  group_by?: "day" | "week" | "month";
};

export type ReportQuoteRow = ReportRecentQuote & {
  job_number?: string | null;
  has_internal_notes?: boolean;
};

export type ReportQuotesFilters = ReportSummaryFilters & {
  limit?: number;
  offset?: number;
};

function buildQuery(filters: Record<string, string | number | undefined>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== "") {
      params.set(key, String(value));
    }
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

function normalizeSummary(raw: Record<string, unknown>): ReportSummary {
  const kpisRaw = (raw.kpis ?? {}) as Record<string, unknown>;
  const mapBreakdown = <T>(items: unknown[], mapper: (item: Record<string, unknown>) => T): T[] =>
    (items ?? []).map((item) => mapper(item as Record<string, unknown>));

  return {
    kpis: {
      submitted_quotes: Number(kpisRaw.submitted_quotes ?? 0),
      total_value: Number(kpisRaw.total_value ?? 0),
      average_quote_value: Number(kpisRaw.average_quote_value ?? 0),
      approved_or_ready_count:
        kpisRaw.approved_or_ready_count != null ? Number(kpisRaw.approved_or_ready_count) : null,
      reopened_count: kpisRaw.reopened_count != null ? Number(kpisRaw.reopened_count) : null,
      with_internal_notes_count:
        kpisRaw.with_internal_notes_count != null ? Number(kpisRaw.with_internal_notes_count) : null,
      accepted_count: kpisRaw.accepted_count != null ? Number(kpisRaw.accepted_count) : null,
      accepted_value: kpisRaw.accepted_value != null ? Number(kpisRaw.accepted_value) : null,
    },
    by_status: mapBreakdown(raw.by_status as unknown[], (item) => ({
      status: String(item.status ?? ""),
      count: Number(item.count ?? 0),
      value: Number(item.value ?? 0),
    })),
    by_client: mapBreakdown(raw.by_client as unknown[], (item) => ({
      client_id: item.client_id != null ? String(item.client_id) : null,
      client_name: String(item.client_name ?? "Unknown client"),
      count: Number(item.count ?? 0),
      value: Number(item.value ?? 0),
    })),
    by_trade: mapBreakdown(raw.by_trade as unknown[], (item) => ({
      trade_id: item.trade_id != null ? String(item.trade_id) : null,
      trade_name: String(item.trade_name ?? "Unknown trade"),
      count: Number(item.count ?? 0),
      value: Number(item.value ?? 0),
    })),
    trend: mapBreakdown(raw.trend as unknown[], (item) => ({
      period: String(item.period ?? ""),
      count: Number(item.count ?? 0),
      value: Number(item.value ?? 0),
    })),
    recent_quotes: mapBreakdown(raw.recent_quotes as unknown[], (item) => ({
      session_id: String(item.session_id ?? ""),
      quote_ref: String(item.quote_ref ?? "—"),
      client_name: String(item.client_name ?? "—"),
      trade_name: String(item.trade_name ?? "—"),
      status: String(item.status ?? ""),
      total: item.total != null ? Number(item.total) : null,
      submitted_at: item.submitted_at != null ? String(item.submitted_at) : null,
      client_accepted: Boolean(item.client_accepted),
      client_accepted_at: item.client_accepted_at != null ? String(item.client_accepted_at) : null,
    })),
  };
}

export async function getReportSummary(filters: ReportSummaryFilters = {}): Promise<ReportSummary> {
  const response = await apiFetch<Record<string, unknown>>(
    `/api/v1/reports/summary${buildQuery({
      date_from: filters.date_from,
      date_to: filters.date_to,
      client_id: filters.client_id,
      trade_id: filters.trade_id,
      status: filters.status,
      group_by: filters.group_by ?? "day",
    })}`,
  );
  return normalizeSummary((response.data ?? {}) as Record<string, unknown>);
}

export async function listReportQuotes(filters: ReportQuotesFilters = {}): Promise<{
  items: ReportQuoteRow[];
  total: number;
  limit: number;
  offset: number;
}> {
  const response = await apiFetch<ReportQuoteRow[]>(
    `/api/v1/reports/quotes${buildQuery({
      date_from: filters.date_from,
      date_to: filters.date_to,
      client_id: filters.client_id,
      trade_id: filters.trade_id,
      status: filters.status,
      limit: filters.limit ?? 50,
      offset: filters.offset ?? 0,
    })}`,
  );
  const meta = response.meta ?? {};
  return {
    items: (response.data ?? []).map((item) => ({
      session_id: String(item.session_id ?? ""),
      quote_ref: String(item.quote_ref ?? "—"),
      job_number: item.job_number ?? null,
      client_name: String(item.client_name ?? "—"),
      trade_name: String(item.trade_name ?? "—"),
      status: String(item.status ?? ""),
      total: item.total != null ? Number(item.total) : null,
      submitted_at: item.submitted_at != null ? String(item.submitted_at) : null,
      has_internal_notes: Boolean(item.has_internal_notes),
    })),
    total: Number(meta.total ?? 0),
    limit: Number(meta.limit ?? filters.limit ?? 50),
    offset: Number(meta.offset ?? filters.offset ?? 0),
  };
}

export function formatReportDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export function formatMoney(value?: number | null): string {
  if (value === undefined || value === null || Number.isNaN(value)) return "—";
  return `£${value.toFixed(2)}`;
}

export function formatPeriod(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-GB", { dateStyle: "medium" }).format(date);
}
