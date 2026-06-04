import { apiFetch } from "@/lib/api";
import type { AttachmentMeta } from "@/lib/eworks-calculate-schema";
import {
  deleteSessionAttachment,
  getAttachmentUrl,
  uploadSessionAttachment,
} from "@/lib/eworks-session";

export type EngineerDurationType = "hourly" | "half_day" | "day_up_to_2" | "day_3_plus";

export type EngineerJobSummary = {
  quote_number: string;
  job_number: string;
  client_name: string;
  trade_name: string;
  property_address: string;
  engineer_name?: string | null;
  status: string;
};

export type EngineerSiteVisit = {
  scope?: string | null;
  site_notes?: string | null;
  findings?: string | null;
  attachments: AttachmentMeta[];
  engineer_count: number;
  labourer_count: number;
  duration_type: EngineerDurationType;
  hours?: number | string | null;
  days?: number | string | null;
  materials_required?: string | null;
  unit_cost?: number | string | null;
  parking_required: boolean;
  parking_amount?: number | string | null;
  congestion_required: boolean;
  congestion_amount?: number | string | null;
  ulez_required: boolean;
  ulez_amount?: number | string | null;
  waste_required: boolean;
  waste_amount?: number | string | null;
};

export type EngineerSession = {
  session_id: string;
  status: string;
  expires_at: string;
  job: EngineerJobSummary;
  site_visit: EngineerSiteVisit;
};

export type EngineerSiteVisitPayload = {
  scope?: string | null;
  site_notes?: string | null;
  findings?: string | null;
  engineer_count: number;
  labourer_count: number;
  duration_type: EngineerDurationType;
  hours?: number | null;
  days?: number | null;
  materials_required?: string | null;
  unit_cost?: number | null;
  parking_required: boolean;
  parking_amount?: number | null;
  congestion_required: boolean;
  congestion_amount?: number | null;
  ulez_required: boolean;
  ulez_amount?: number | null;
  waste_required: boolean;
  waste_amount?: number | null;
};

const ENGINEER_SESSION_STORAGE_PREFIX = "engineer-session:";

export function storeEngineerSessionCredentials(sessionId: string, sessionToken: string) {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(
    `${ENGINEER_SESSION_STORAGE_PREFIX}${sessionId}`,
    sessionToken,
  );
}

export function readEngineerSessionCredentials(sessionId: string): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(`${ENGINEER_SESSION_STORAGE_PREFIX}${sessionId}`);
}

export async function fetchEngineerSession(
  sessionId: string,
  sessionToken: string,
): Promise<EngineerSession> {
  const response = await apiFetch<EngineerSession>(`/api/v1/engineer/sessions/${sessionId}`, {
    headers: { "X-Session-Token": sessionToken },
  });
  return response.data;
}

export async function saveEngineerSiteVisit(
  sessionId: string,
  sessionToken: string,
  payload: EngineerSiteVisitPayload,
): Promise<{ message: string }> {
  const response = await apiFetch<{ message: string }>(
    `/api/v1/engineer/sessions/${sessionId}/site-visit`,
    {
      method: "PUT",
      body: JSON.stringify(payload),
      headers: { "X-Session-Token": sessionToken },
    },
  );
  return response.data;
}

export { uploadSessionAttachment, deleteSessionAttachment, getAttachmentUrl };

export function buildEngineerJobDetailPath(sessionId: string, sessionToken: string) {
  const params = new URLSearchParams({ token: sessionToken });
  return `/engineer/jobs/${sessionId}?${params.toString()}`;
}
