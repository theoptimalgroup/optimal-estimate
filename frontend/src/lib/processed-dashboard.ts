import { apiFetch } from "@/lib/api";

export type SalesBucket = "pending" | "possible" | "strong" | "dormant";
export type FollowUpStatus = "overdue" | "due_today" | "due_this_week" | "no_followup" | "future";

export type ProcessedDashboardQuote = {
  id: number;
  quote_ref: string | null;
  eworks_quote_id: number;
  customer_name: string | null;
  site_address: string | null;
  quote_value: number | null;
  processed_at: string | null;
  days_since_processed: number;
  days_in_current_bucket: number;
  last_follow_up_at: string | null;
  next_follow_up_at: string | null;
  follow_up_status: FollowUpStatus;
  sales_bucket: SalesBucket;
  sales_note: string | null;
  assigned_sales_name: string | null;
  assigned_sales_email: string | null;
  assigned_sales_user_id: string | null;
  eworks_status: string | null;
  eworks_status_name: string | null;
  tags: string[];
  quote_detail_link: string;
};

export type ProcessedDashboardCategory = {
  count: number;
  value: number;
  average_age_days: number;
  overdue_followups: number;
  quotes: ProcessedDashboardQuote[];
};

export type ProcessedDashboardTotals = {
  processed_quotes: number;
  pipeline_value: number;
  strong_value: number;
  dormant_quotes: number;
  overdue_followups: number;
  due_today_followups: number;
  no_followup_set: number;
  average_age_days: number;
  conversion_rate: number;
  accepted_count: number;
  rejected_count: number;
  accepted_value: number;
  rejected_value: number;
};

export type SalespersonPerformanceRow = {
  salesperson_name: string | null;
  salesperson_email: string | null;
  assigned_count: number;
  pipeline_value: number;
  strong_value: number;
  accepted_count: number;
  rejected_count: number;
  conversion_rate: number;
  overdue_followups: number;
  average_days_to_close: number | null;
};

export type ProcessedDashboard = {
  totals: ProcessedDashboardTotals;
  categories: Record<SalesBucket, ProcessedDashboardCategory>;
  aging: Record<string, { count: number; value: number }>;
  follow_up_reminders: {
    overdue: ProcessedDashboardQuote[];
    due_today: ProcessedDashboardQuote[];
    due_this_week: ProcessedDashboardQuote[];
    no_followup_set: ProcessedDashboardQuote[];
  };
  salesperson_performance: SalespersonPerformanceRow[];
  accepted_rejected_trend: Array<{
    month: string;
    accepted_count: number;
    rejected_count: number;
    accepted_value: number;
    rejected_value: number;
  }>;
  monthly_pipeline_value: Array<{
    month: string;
    new_processed_value: number;
    active_pipeline_value: number;
    strong_pipeline_value: number;
    accepted_value: number;
    rejected_value: number;
  }>;
};

export type SalesPipelinePatch = {
  sales_bucket?: SalesBucket;
  sales_note?: string | null;
  assigned_sales_user_id?: string | null;
  assigned_sales_email?: string | null;
  assigned_sales_name?: string | null;
  last_follow_up_at?: string | null;
  next_follow_up_at?: string | null;
};

export async function getProcessedDashboard(
  apiBase: "manager" | "admin",
  search?: string,
): Promise<ProcessedDashboard> {
  const params = new URLSearchParams();
  if (search?.trim()) params.set("search", search.trim());
  const qs = params.toString();
  const res = await apiFetch<ProcessedDashboard>(
    `/api/v1/${apiBase}/processed-dashboard${qs ? `?${qs}` : ""}`,
  );
  const data = res.data;
  if (!data?.totals || !data?.categories) {
    throw new Error("Invalid processed dashboard response");
  }
  return data;
}

export async function patchSalesPipeline(quoteId: number, patch: SalesPipelinePatch): Promise<void> {
  await apiFetch(`/api/v1/processed-quotes/${quoteId}/sales-pipeline`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export const BUCKET_LABELS: Record<SalesBucket, string> = {
  pending: "Pending",
  possible: "Possible",
  strong: "Strong",
  dormant: "Dormant",
};

export const FOLLOW_UP_LABELS: Record<FollowUpStatus, string> = {
  overdue: "Overdue",
  due_today: "Due today",
  due_this_week: "Due this week",
  no_followup: "No follow-up",
  future: "Scheduled",
};

export const AGING_LABELS: Record<string, string> = {
  "0_7_days": "0–7 days",
  "8_14_days": "8–14 days",
  "15_30_days": "15–30 days",
  "31_60_days": "31–60 days",
  "60_plus_days": "60+ days",
};
