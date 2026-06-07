import { apiFetch } from "@/lib/api";

export type EngineerAssignedJob = {
  id: number;
  quote_ref: string | null;
  eworks_quote_id: number | null;
  job_ref: string | null;
  customer_name: string | null;
  address: string | null;
  selected_at: string;
  selected_estimate_total: string | null;
  selected_session_id: string;
  status: string;
  assignment_id?: number | null;
};

export async function listEngineerAssignedJobs(): Promise<EngineerAssignedJob[]> {
  const resp = await apiFetch<EngineerAssignedJob[]>("/api/v1/engineer/jobs/assigned");
  return resp.data;
}

export function formatEstimateTotal(value: string | null | undefined): string {
  if (value == null || value === "") return "—";
  const amount = Number(value);
  if (Number.isNaN(amount)) return value;
  return new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP" }).format(amount);
}
