import { apiFetch } from "@/lib/api";

export type CallBackBucket = "overdue" | "due_today" | "upcoming" | "no_call_date";
export type CallBackStatus = "overdue" | "due_today" | "upcoming" | "no_call_date" | "completed";

export type CallBackDashboardQuote = {
  id: number;
  quote_ref: string | null;
  eworks_quote_id: number;
  customer_name: string | null;
  site_address: string | null;
  quote_value: number | null;
  status: string | null;
  status_name: string | null;
  tags: string[];
  created_on: string | null;
  last_updated_on: string | null;
  days_since_updated: number;
  assigned_name: string | null;
  assigned_email: string | null;
  call_note: string | null;
  last_called_at: string | null;
  next_call_at: string | null;
  call_status: CallBackStatus;
  quote_detail_link: string;
};

export type CallBackDashboardCategory = {
  count: number;
  value: number;
  quotes: CallBackDashboardQuote[];
};

export type CallBackDashboardTotals = {
  call_back_quotes: number;
  total_quote_value: number;
  overdue_calls: number;
  due_today_calls: number;
  upcoming_calls: number;
  no_call_date: number;
  average_age_days: number;
};

export type CallBackDashboard = {
  totals: CallBackDashboardTotals;
  categories: Record<CallBackBucket, CallBackDashboardCategory>;
};

export type CallBackTrackingPatch = {
  assigned_user_id?: string | null;
  assigned_name?: string | null;
  assigned_email?: string | null;
  call_note?: string | null;
  last_called_at?: string | null;
  next_call_at?: string | null;
};

export async function getCallBackDashboard(
  apiBase: "manager" | "admin",
  search?: string,
): Promise<CallBackDashboard> {
  const params = new URLSearchParams();
  if (search?.trim()) params.set("search", search.trim());
  const qs = params.toString();
  const res = await apiFetch<CallBackDashboard>(
    `/api/v1/${apiBase}/call-back-dashboard${qs ? `?${qs}` : ""}`,
  );
  const data = res.data;
  if (!data?.totals || !data?.categories) {
    throw new Error("Invalid Call Back dashboard response");
  }
  return data;
}

export async function patchCallBackTracking(quoteId: number, patch: CallBackTrackingPatch): Promise<void> {
  await apiFetch(`/api/v1/call-back-quotes/${quoteId}/tracking`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export const BUCKET_LABELS: Record<CallBackBucket, string> = {
  overdue: "Overdue",
  due_today: "Due Today",
  upcoming: "Upcoming",
  no_call_date: "No Call Date",
};

export const CALL_STATUS_LABELS: Record<CallBackStatus, string> = {
  overdue: "Overdue",
  due_today: "Due today",
  upcoming: "Upcoming",
  no_call_date: "No call date",
  completed: "Completed",
};
