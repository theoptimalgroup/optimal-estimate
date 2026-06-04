import { apiFetch } from "@/lib/api";

export type Trade = {
  id: string;
  name: string;
  description?: string | null;
  is_active: boolean;
};

export type ManagedTrade = {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  rate_rules_count: number;
  products_count: number;
  created_at: string;
  updated_at: string;
};

export type TradeListFilters = {
  search?: string;
  active?: boolean;
  limit?: number;
  offset?: number;
};

export type TradeListResult = {
  items: ManagedTrade[];
  total: number;
  limit: number;
  offset: number;
};

export type TradeUpdatePayload = {
  name?: string;
  description?: string | null;
  is_active?: boolean;
};

function normalizeManagedTrade(raw: Record<string, unknown>): ManagedTrade {
  return {
    id: String(raw.id ?? ""),
    name: String(raw.name ?? ""),
    description: raw.description != null ? String(raw.description) : null,
    is_active: raw.is_active !== false,
    rate_rules_count: Number(raw.rate_rules_count ?? 0),
    products_count: Number(raw.products_count ?? 0),
    created_at: String(raw.created_at ?? ""),
    updated_at: String(raw.updated_at ?? ""),
  };
}

function buildAdminQuery(filters: TradeListFilters): string {
  const params = new URLSearchParams();
  if (filters.search?.trim()) params.set("search", filters.search.trim());
  if (filters.active !== undefined) params.set("active", String(filters.active));
  params.set("limit", String(filters.limit ?? 50));
  params.set("offset", String(filters.offset ?? 0));
  const query = params.toString();
  return query ? `?${query}` : "";
}

export async function listTrades(filters: TradeListFilters = {}): Promise<TradeListResult> {
  const response = await apiFetch<ManagedTrade[]>(`/api/v1/trades${buildAdminQuery(filters)}`);
  const meta = response.meta ?? {};
  return {
    items: (response.data ?? []).map((item) => normalizeManagedTrade(item as unknown as Record<string, unknown>)),
    total: Number(meta.total ?? 0),
    limit: Number(meta.limit ?? filters.limit ?? 50),
    offset: Number(meta.offset ?? filters.offset ?? 0),
  };
}

export async function getTrade(tradeId: string): Promise<ManagedTrade> {
  const response = await apiFetch<ManagedTrade>(`/api/v1/trades/${tradeId}?enriched=true`);
  return normalizeManagedTrade(response.data as unknown as Record<string, unknown>);
}

export async function updateTrade(tradeId: string, payload: TradeUpdatePayload): Promise<ManagedTrade> {
  const response = await apiFetch<ManagedTrade>(`/api/v1/trades/${tradeId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  return normalizeManagedTrade(response.data as unknown as Record<string, unknown>);
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export async function fetchAllTrades(token?: string | null, isActive = true): Promise<Trade[]> {
  const pageSize = 100;
  let page = 1;
  let all: Trade[] = [];

  while (true) {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (isActive) params.set("is_active", "true");

    const res = await apiFetch<Trade[]>(`/api/v1/trades?${params.toString()}`, {}, token);
    all = all.concat(res.data);
    const totalPages = Number(res.meta?.total_pages ?? 1);
    if (page >= totalPages) break;
    page += 1;
  }

  return all;
}

export async function searchTrades(query: string, token?: string | null, isActive = true): Promise<Trade[]> {
  const params = new URLSearchParams({
    page: "1",
    page_size: "100",
    search: query,
  });
  if (isActive) params.set("is_active", "true");
  const res = await apiFetch<Trade[]>(`/api/v1/trades?${params.toString()}`, {}, token);
  return res.data;
}

export function tradeOptions(trades: Trade[]) {
  return trades.map((trade) => ({
    id: trade.id,
    label: trade.name,
  }));
}
