import { apiFetch } from "@/lib/api";

export type ManualEstimateSession = {
  session_id: string;
  session_token: string;
  resume_url: string;
};

export type ManualEstimateSessionRequest = {
  quote_ref?: string;
  job_ref?: string;
  client_name?: string;
  trade_name?: string;
};

export async function createManualEstimateSession(
  payload: ManualEstimateSessionRequest = {},
): Promise<ManualEstimateSession> {
  const response = await apiFetch<ManualEstimateSession>("/api/v1/calculation-session/manual", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return response.data;
}
