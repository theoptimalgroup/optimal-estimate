import { apiFetch } from "@/lib/api";

export type RateRuleUsage = {
  quotes_using_version: number;
  jobs_for_client: number;
  lookup_priority: string | null;
};

export type RateRule = {
  id: string;
  client_id: string | null;
  trade_id: string | null;
  client_name: string | null;
  trade_name: string | null;
  version: string;
  formula_source: string;
  is_active: boolean;
  hourly_rate: string | null;
  half_day_rate: string | null;
  day_rate: string | null;
  minimum_hours: string | null;
  minimum_charge: string | null;
  material_markup_type: string;
  material_markup_value: string;
  vat_rate: string;
  approval_threshold: string | null;
  minimum_margin_percentage: string | null;
  rounding_rule: string | null;
  active_from: string;
  active_to: string | null;
  created_at: string;
  client_fee_pct: string;
  hourly_overhead_pct: string;
  daily_overhead_pct: string;
  daily_overhead_long_job_pct: string;
  direct_hourly_cost: string | null;
  direct_daily_cost: string | null;
  labourer_hourly_cost: string;
  labourer_daily_cost: string;
  material_charge_denominator: string;
  parking_charge_denominator: string;
  congestion_charge_denominator: string;
  mround_increment: string;
  oj_uplift_pct: string;
  nhs_overhead_uplift_pct: string;
  eaf_flat_fee: string;
  internal_notes_template: string | null;
  xlsx_client_name: string | null;
  xlsx_trade_name: string | null;
};

export type RateRuleDetail = RateRule & {
  usage: RateRuleUsage;
};

export type RateRuleListFilters = {
  client_id?: string;
  trade_id?: string;
  client_name?: string;
  trade_name?: string;
  active?: boolean;
  formula_source?: string;
  limit?: number;
  offset?: number;
};

export type RateRuleListResult = {
  items: RateRule[];
  total: number;
  limit: number;
  offset: number;
};

function buildQuery(filters: RateRuleListFilters): string {
  const params = new URLSearchParams();
  if (filters.client_id) params.set("client_id", filters.client_id);
  if (filters.trade_id) params.set("trade_id", filters.trade_id);
  if (filters.client_name?.trim()) params.set("client_name", filters.client_name.trim());
  if (filters.trade_name?.trim()) params.set("trade_name", filters.trade_name.trim());
  if (filters.active !== undefined) params.set("active", String(filters.active));
  if (filters.formula_source) params.set("formula_source", filters.formula_source);
  params.set("limit", String(filters.limit ?? 50));
  params.set("offset", String(filters.offset ?? 0));
  return params.toString();
}

export async function listRateRules(
  filters: RateRuleListFilters = {},
  token?: string | null,
): Promise<RateRuleListResult> {
  const response = await apiFetch<RateRule[]>(`/api/v1/rate-rules?${buildQuery(filters)}`, {}, token);
  return {
    items: response.data,
    total: Number(response.meta?.total ?? response.data.length),
    limit: Number(response.meta?.limit ?? filters.limit ?? 50),
    offset: Number(response.meta?.offset ?? filters.offset ?? 0),
  };
}

export async function getRateRule(ruleId: string, token?: string | null): Promise<RateRuleDetail> {
  const response = await apiFetch<RateRuleDetail>(`/api/v1/rate-rules/${ruleId}`, {}, token);
  return response.data;
}

export async function updateRateRuleStatus(
  ruleId: string,
  active: boolean,
  token?: string | null,
): Promise<RateRuleDetail> {
  const response = await apiFetch<RateRuleDetail>(
    `/api/v1/rate-rules/${ruleId}/status`,
    {
      method: "PATCH",
      body: JSON.stringify({ is_active: active }),
    },
    token,
  );
  return response.data;
}

export function formatRate(value: string | null | undefined): string {
  if (value == null || value === "") return "—";
  const num = Number(value);
  if (Number.isNaN(num)) return value;
  return new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP" }).format(num);
}

export function formatMarkup(rule: Pick<RateRule, "material_markup_type" | "material_markup_value">): string {
  if (rule.material_markup_type === "percentage") {
    return `${rule.material_markup_value}%`;
  }
  return formatRate(rule.material_markup_value);
}

export function formatPercent(value: string | null | undefined): string {
  if (value == null || value === "") return "—";
  const num = Number(value);
  if (Number.isNaN(num)) return value;
  return `${num}%`;
}

export function formatFractionAsPercent(value: string | null | undefined): string {
  if (value == null || value === "") return "—";
  const num = Number(value);
  if (Number.isNaN(num)) return value;
  const percent = num * 100;
  return `${Number.isInteger(percent) ? percent : percent.toFixed(2)}%`;
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-GB");
}
