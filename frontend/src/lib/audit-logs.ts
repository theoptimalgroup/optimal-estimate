import { apiFetch } from "@/lib/api";

export type AuditLog = {
  id: string;
  actor_user_id: string | null;
  actor_email: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  summary: string;
  ip_address: string | null;
  created_at: string;
};

export type AuditLogDetail = AuditLog & {
  metadata: Record<string, unknown> | null;
  before_snapshot: Record<string, unknown> | null;
  after_snapshot: Record<string, unknown> | null;
};

export type AuditLogListFilters = {
  search?: string;
  actor_email?: string;
  action?: string;
  entity_type?: string;
  entity_id?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
};

export type AuditLogListResult = {
  items: AuditLog[];
  total: number;
  limit: number;
  offset: number;
};

function normalizeAuditLog(raw: Record<string, unknown>): AuditLog {
  return {
    id: String(raw.id ?? ""),
    actor_user_id: raw.actor_user_id != null ? String(raw.actor_user_id) : null,
    actor_email: raw.actor_email != null ? String(raw.actor_email) : null,
    action: String(raw.action ?? ""),
    entity_type: String(raw.entity_type ?? ""),
    entity_id: raw.entity_id != null ? String(raw.entity_id) : null,
    summary: String(raw.summary ?? ""),
    ip_address: raw.ip_address != null ? String(raw.ip_address) : null,
    created_at: String(raw.created_at ?? ""),
  };
}

function buildQuery(filters: AuditLogListFilters): string {
  const params = new URLSearchParams();
  if (filters.search?.trim()) params.set("search", filters.search.trim());
  if (filters.actor_email?.trim()) params.set("actor_email", filters.actor_email.trim());
  if (filters.action?.trim()) params.set("action", filters.action.trim());
  if (filters.entity_type?.trim()) params.set("entity_type", filters.entity_type.trim());
  if (filters.entity_id?.trim()) params.set("entity_id", filters.entity_id.trim());
  if (filters.date_from) params.set("date_from", filters.date_from);
  if (filters.date_to) params.set("date_to", filters.date_to);
  params.set("limit", String(filters.limit ?? 50));
  params.set("offset", String(filters.offset ?? 0));
  const query = params.toString();
  return query ? `?${query}` : "";
}

export async function listAuditLogs(filters: AuditLogListFilters = {}): Promise<AuditLogListResult> {
  const response = await apiFetch<AuditLog[]>(`/api/v1/audit-logs${buildQuery(filters)}`);
  const meta = response.meta ?? {};
  return {
    items: (response.data ?? []).map((item) => normalizeAuditLog(item as unknown as Record<string, unknown>)),
    total: Number(meta.total ?? 0),
    limit: Number(meta.limit ?? filters.limit ?? 50),
    offset: Number(meta.offset ?? filters.offset ?? 0),
  };
}

export async function getAuditLog(auditLogId: string): Promise<AuditLogDetail> {
  const response = await apiFetch<AuditLogDetail>(`/api/v1/audit-logs/${auditLogId}`);
  const raw = response.data as unknown as Record<string, unknown>;
  return {
    ...normalizeAuditLog(raw),
    metadata: (raw.metadata as Record<string, unknown> | null) ?? null,
    before_snapshot: (raw.before_snapshot as Record<string, unknown> | null) ?? null,
    after_snapshot: (raw.after_snapshot as Record<string, unknown> | null) ?? null,
  };
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export function formatJson(value: Record<string, unknown> | null | undefined): string {
  if (!value || Object.keys(value).length === 0) return "—";
  return JSON.stringify(value, null, 2);
}

export const COMMON_ACTIONS = [
  "user_updated",
  "product_updated",
  "rate_rule_status_updated",
  "client_updated",
  "trade_updated",
  "quote_reopened",
  "combined_pdf_generated",
];

export const COMMON_ENTITY_TYPES = [
  "user",
  "product",
  "rate_rule",
  "client",
  "trade",
  "calculation_session",
];
