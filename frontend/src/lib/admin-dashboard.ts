import { apiFetch } from "@/lib/api";
import {
  AWAITING_SUPPLIER_TAG,
  READY_TO_SEND_TAG,
  type OperationalDashboardData,
} from "@/lib/dashboard-quotes";

export { AWAITING_SUPPLIER_TAG, READY_TO_SEND_TAG };

export type AdminDashboardStats = {
  users: number;
  products: number;
  audit_logs: number;
  eworks_api_enabled: boolean;
  database_reachable: boolean;
};

export type AdminDashboard = OperationalDashboardData & {
  admin_stats: AdminDashboardStats;
};

export async function fetchAdminDashboard(
  limitPerCategory = 10,
  search?: string,
): Promise<AdminDashboard> {
  const params = new URLSearchParams({ limit_per_category: String(limitPerCategory) });
  if (search?.trim()) params.set("search", search.trim());
  const res = await apiFetch<AdminDashboard>(`/api/v1/admin/dashboard?${params}`);
  return res.data;
}

export function buildAdminQuotesFilterUrl(params: {
  tab?: "quotes" | "jobs" | "customers" | "sync" | "products";
  status?: string;
  tag?: string;
}): string {
  const search = new URLSearchParams();
  if (params.tab) search.set("tab", params.tab);
  if (params.status) search.set("status", params.status);
  if (params.tag) search.set("tag", params.tag);
  const qs = search.toString();
  return qs ? `/admin/eworks-sync?${qs}` : "/admin/eworks-sync";
}
