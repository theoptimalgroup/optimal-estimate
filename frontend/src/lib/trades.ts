import { apiFetch } from "@/lib/api";

export type Trade = {
  id: string;
  name: string;
  description?: string | null;
  is_active: boolean;
};

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
