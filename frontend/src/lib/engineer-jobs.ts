import { apiFetch } from "@/lib/api";

export type EngineerAssignedJob = {
  id: number;
  eworks_job_id: number;
  job_ref: string | null;
  eworks_quote_id: number | null;
  quote_ref: string | null;
  customer_name: string | null;
  address: string | null;
  status: string | null;
  status_name: string | null;
  job_date: string | null;
  description: string | null;
  total: string | null;
  appointment_user_name?: string | null;
  appointment_user_email?: string | null;
  appointment_type?: string | null;
  appointment_status?: string | null;
  appointment_start_at?: string | null;
  appointment_end_at?: string | null;
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
