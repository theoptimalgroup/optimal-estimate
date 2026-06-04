import { apiFetch } from "@/lib/api";

export type ManagedClient = {
  id: string;
  name: string;
  billing_email: string | null;
  default_vat_rate: string | number;
  is_active: boolean;
  aliases: string[];
  rate_rules_count: number;
  calculation_sessions_count: number;
  created_at: string;
  updated_at: string;
};

export type ClientListFilters = {
  search?: string;
  active?: boolean;
  limit?: number;
  offset?: number;
};

export type ClientListResult = {
  items: ManagedClient[];
  total: number;
  limit: number;
  offset: number;
};

export type ClientUpdatePayload = {
  name?: string;
  billing_email?: string | null;
  default_vat_rate?: string | number;
  is_active?: boolean;
};

function normalizeClient(raw: Record<string, unknown>): ManagedClient {
  return {
    id: String(raw.id ?? ""),
    name: String(raw.name ?? ""),
    billing_email: raw.billing_email != null ? String(raw.billing_email) : null,
    default_vat_rate: raw.default_vat_rate ?? 0,
    is_active: raw.is_active !== false,
    aliases: Array.isArray(raw.aliases) ? raw.aliases.map(String) : [],
    rate_rules_count: Number(raw.rate_rules_count ?? 0),
    calculation_sessions_count: Number(raw.calculation_sessions_count ?? 0),
    created_at: String(raw.created_at ?? ""),
    updated_at: String(raw.updated_at ?? ""),
  };
}

function buildQuery(filters: ClientListFilters): string {
  const params = new URLSearchParams();
  if (filters.search?.trim()) params.set("search", filters.search.trim());
  if (filters.active !== undefined) params.set("active", String(filters.active));
  params.set("limit", String(filters.limit ?? 50));
  params.set("offset", String(filters.offset ?? 0));
  const query = params.toString();
  return query ? `?${query}` : "";
}

export async function listClients(filters: ClientListFilters = {}): Promise<ClientListResult> {
  const response = await apiFetch<ManagedClient[]>(`/api/v1/clients${buildQuery(filters)}`);
  const meta = response.meta ?? {};
  return {
    items: (response.data ?? []).map((item) => normalizeClient(item as unknown as Record<string, unknown>)),
    total: Number(meta.total ?? 0),
    limit: Number(meta.limit ?? filters.limit ?? 50),
    offset: Number(meta.offset ?? filters.offset ?? 0),
  };
}

export async function getClient(clientId: string): Promise<ManagedClient> {
  const response = await apiFetch<ManagedClient>(`/api/v1/clients/${clientId}`);
  return normalizeClient(response.data as unknown as Record<string, unknown>);
}

export async function updateClient(clientId: string, payload: ClientUpdatePayload): Promise<ManagedClient> {
  const response = await apiFetch<ManagedClient>(`/api/v1/clients/${clientId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  return normalizeClient(response.data as unknown as Record<string, unknown>);
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export function aliasDisplay(aliases: string[]): string {
  if (!aliases.length) return "—";
  return aliases.join(", ");
}
