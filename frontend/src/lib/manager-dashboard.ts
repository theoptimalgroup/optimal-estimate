import { apiFetch } from "@/lib/api";

export const AWAITING_SUPPLIER_TAG = "Awaiting Supplier Info (Quotes)";
export const READY_TO_SEND_TAG = "Quotes Ready to send (Quotes)";

export type ManagerDashboardQuoteRow = {
  id: number;
  eworks_quote_id: number;
  quote_ref: string | null;
  customer_name: string | null;
  status: string | null;
  status_name: string | null;
  tags: string[];
  quote_date: string | null;
  expiry_date: string | null;
  total: number | null;
  synced_at: string | null;
};

export type ManagerDashboardCategory = {
  count: number;
  quotes: ManagerDashboardQuoteRow[];
};

export type ManagerDashboard = {
  categories: {
    new_quotes: ManagerDashboardCategory;
    awaiting_supplier: ManagerDashboardCategory;
    ready_to_send: ManagerDashboardCategory;
  };
  last_synced_at: string | null;
  totals: {
    all_open_quotes: number;
  };
};

export async function getManagerDashboard(limitPerCategory = 10): Promise<ManagerDashboard> {
  const params = new URLSearchParams({ limit_per_category: String(limitPerCategory) });
  const res = await apiFetch<ManagerDashboard>(`/api/v1/manager/dashboard?${params}`);
  return res.data;
}

export function buildQuotesFilterUrl(params: {
  type?: "quotes" | "jobs";
  status?: string;
  tag?: string;
}): string {
  const search = new URLSearchParams();
  if (params.type) search.set("type", params.type);
  if (params.status) search.set("status", params.status);
  if (params.tag) search.set("tag", params.tag);
  const qs = search.toString();
  return qs ? `/manager/quotes?${qs}` : "/manager/quotes";
}
