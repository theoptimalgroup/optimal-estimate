import { apiFetch } from "@/lib/api";
import {
  AWAITING_DESKTOP_INFO_TAG,
  AWAITING_INTERNAL_INFO_TAG,
  AWAITING_SUPPLIER_TAG,
  BOOKED_TAG,
  MUST_ATTEND_TAG,
  READY_TO_SEND_TAG,
  type DashboardCategory,
  type DashboardQuoteRow,
  type OperationalDashboardData,
} from "@/lib/dashboard-quotes";

export {
  AWAITING_DESKTOP_INFO_TAG,
  AWAITING_INTERNAL_INFO_TAG,
  AWAITING_SUPPLIER_TAG,
  BOOKED_TAG,
  MUST_ATTEND_TAG,
  READY_TO_SEND_TAG,
  type DashboardCategory,
  type DashboardQuoteRow,
  type OperationalDashboardData,
};

export type ManagerDashboardQuoteRow = DashboardQuoteRow;
export type ManagerDashboardCategory = DashboardCategory;
export type ManagerDashboard = OperationalDashboardData;

export async function getManagerDashboard(
  limitPerCategory = 10,
  search?: string,
): Promise<ManagerDashboard> {
  const params = new URLSearchParams({ limit_per_category: String(limitPerCategory) });
  if (search?.trim()) params.set("search", search.trim());
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
