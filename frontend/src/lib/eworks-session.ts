import { getApiUrl } from "@/lib/api";
import type { AttachmentMeta } from "@/lib/eworks-calculate-schema";

export type Step1Snapshot = {
  quote_number: string;
  job_number: string;
  external_job_id?: string | null;
  engineer_name?: string | null;
  engineer_name_source?: string | null;
  client_name: string;
  trade_name: string;
  property_address: string;
  property_manager_name?: string | null;
  property_manager_email?: string | null;
  property_manager_phone?: string | null;
  tenant_name?: string | null;
  tenant_phone?: string | null;
  access_notes?: string | null;
  original_job_description?: string | null;
  booked_by?: string | null;
  contact?: string | null;
  quote_screening_answers?: string | null;
  date_visited?: string | null;
  travel_time_minutes?: number;
  travel_notes?: string | null;
  parking_notes?: string | null;
  total_time_for_job?: string | null;
  quote_description?: string | null;
  findings_report?: string | null;
  congestion_required: boolean;
  congestion_amount: number | string;
  travel: number | string;
};

export type MaterialOrderRow = {
  link?: string | null;
  quantity: number | string;
  cost: number | string;
};

export type MaterialLinkRow = {
  link?: string | null;
  quantity: number | string;
  cost: number | string;
};

export type MaterialSupplier = {
  links: MaterialLinkRow[];
  delivery_charge: number | string;
  supplier_name?: string | null;
};

export type WorkBlockSnapshot = {
  scope?: string | null;
  selected_product_id?: number | null;
  is_custom_scope?: boolean;
  custom_title?: string | null;
  eworks_item_id?: number | null;
  product_name?: string | null;
  product_code?: string | null;
  product_quantity?: number | string;
  product_unit_price?: number | string;
  product_total_price?: number | string;
  scope_from_product?: boolean;
  materials_to_order?: MaterialSupplier[];
  shelf_materials_rows?: MaterialOrderRow[];
  shelf_materials?: string | null;
  shelf_materials_cost?: number | string;
  skill_required?: string | null;
  best_engineer?: string | null;
  subcontractors?: string | null;
  engineers_required?: boolean;
  engineers_needed?: number | null;
  engineer_time_unit?: string | null;
  engineer_time_value?: number | string;
  labour_required?: boolean;
  labour_needed?: number | null;
  labour_time_value?: number | string;
  time_frame?: string | null;
  other_notes?: string | null;
  attachments?: AttachmentMeta[];
  findings?: string | null;
  engineers?: number;
  labourers?: number;
  labourer_days?: number | string;
  labour_type?: string;
  hours?: number | string;
  days?: number | string;
  markup_value?: number | string;
  // Per-work charges
  parking_required?: boolean;
  parking_type?: string | null;
  parking_fixed_amount?: number | string | null;
  parking_rate_per_hour?: number | string | null;
  parking_hours?: number | string | null;
  parking_vehicles?: number | null;
  parking_notes?: string | null;
  parking_same_location_as_work1?: boolean;
  parking_latitude?: number | string | null;
  parking_longitude?: number | string | null;
  congestion_required?: boolean;
  congestion_amount?: number | string;
  travel_charge?: number | string;
  other_charge?: number | string;
  other_charge_reason?: string | null;
};

export type Step2Snapshot = {
  works?: WorkBlockSnapshot[];
  unmatched_attachments?: AttachmentMeta[];
  scope?: string | null;
  materials_to_order?: MaterialSupplier[];
  shelf_materials_rows?: MaterialOrderRow[];
  shelf_materials?: string | null;
  shelf_materials_cost?: number | string;
  skill_required?: string | null;
  best_engineer?: string | null;
  subcontractors?: string | null;
  time_frame?: string | null;
  engineers_needed?: number | null;
  other_notes?: string | null;
  attachments?: AttachmentMeta[];
  findings?: string | null;
  engineers?: number;
  labourers?: number;
  labourer_days?: number | string;
  labour_type?: string;
  hours?: number | string;
  days?: number | string;
  markup_value?: number | string;
  parking_required?: boolean;
  parking_type?: string | null;
  parking_rate_per_hour?: number | string | null;
  parking_hours?: number | string | null;
  parking_fixed_amount?: number | string | null;
  parking_vehicles?: number | null;
  parking_latitude?: number | string | null;
  parking_longitude?: number | string | null;
  congestion_required?: boolean;
  congestion_amount?: number | string;
  travel_charge?: number | string;
  other_charge?: number | string;
  other_charge_reason?: string | null;
  ulez_required?: boolean;
  ulez_amount?: number | string;
  waste_disposal_required?: boolean;
  waste_disposal_amount?: number | string;
  parking_notes?: string | null;
};

export type ResolvedRuleInfo = {
  client_id: string;
  trade_id: string;
  rule_id?: string | null;
  rule_version: string;
  formula_source: string;
  xlsx_client_name?: string | null;
  xlsx_trade_name?: string | null;
  client_fee_pct?: number | string;
};

export type SessionUiState = {
  current_step: number;
  max_reachable_step: number;
  last_result?: CalculateResponse | null;
};

export type SharedStep2Meta = {
  updated_by_name?: string | null;
  updated_by_email?: string | null;
  updated_at?: string | null;
  version?: number;
};

export type FromLinkResponse = {
  session_id: string;
  session_token: string;
  step1: Step1Snapshot;
  step2?: Step2Snapshot | null;
  shared_step2?: SharedStep2Meta | null;
  resolved: ResolvedRuleInfo;
  expires_at: string;
  ui_state?: SessionUiState | null;
  resumed?: boolean;
  status?: string;
  locked?: boolean;
  revision_in_progress?: boolean;
  active_revision_reason?: string | null;
  current_version_number?: number;
};

type CalculationSessionRead = {
  session_id: string;
  step1: Step1Snapshot;
  step2?: Step2Snapshot | null;
  shared_step2?: SharedStep2Meta | null;
  resolved: ResolvedRuleInfo;
  expires_at: string;
  ui_state?: SessionUiState | null;
  status?: string;
  locked?: boolean;
  revision_in_progress?: boolean;
  active_revision_reason?: string | null;
  current_version_number?: number;
};

export type CalculationBreakdown = {
  labour: { label: string; formula: string; total: number | string }[];
  materials: { label: string; formula: string; total: number | string }[];
  charges: { label: string; formula: string; total: number | string }[];
  subtotal: number | string;
  vat_total: number | string;
  final_total: number | string;
  formula_source?: string;
  internal_notes?: string;
  profit_gbp?: number | string;
  profit_pct?: number | string;
  direct_labour_cost?: number | string;
  labour_charge_to_client?: number | string;
  materials_parking_cc_charge?: number | string;
};

export type WorkBreakdownResult = {
  work_index: number;
  scope?: string | null;
  breakdown: CalculationBreakdown;
  internal_notes?: string | null;
};

export type SkillGroupBreakdown = {
  skill: string;
  breakdown: CalculationBreakdown;
};

export type AggregatedQuoteSummary = {
  work_count: number;
  labour_type: string;
  quoted_engineer_hours?: number | string | null;
  quoted_engineer_days?: number | string | null;
  quoted_labour_days?: number | string | null;
  uses_mixed_units?: boolean;
  converted_from_hours?: boolean;
  mixed_skills?: boolean;
  skills?: string[];
  subtitle: string;
};

export type CalculateResponse = {
  breakdown: CalculationBreakdown;
  work_breakdowns?: WorkBreakdownResult[];
  aggregated_summary?: AggregatedQuoteSummary | null;
  skill_group_breakdowns?: SkillGroupBreakdown[];
  internal_view: Record<string, unknown>;
  internal_notes?: string | null;
  client_view: Record<string, unknown>;
};

export class EworksSessionError extends Error {
  code?: string;

  constructor(message: string, code?: string) {
    super(message);
    this.name = "EworksSessionError";
    this.code = code;
  }
}

function parseApiErrorPayload(body: { detail?: unknown; error?: { code?: string; message?: string } }): {
  message: string;
  code?: string;
} {
  if (body?.error?.message) {
    return { message: body.error.message, code: body.error.code };
  }
  const detail = body?.detail;
  if (detail && typeof detail === "object" && "message" in detail) {
    const structured = detail as { code?: string; message?: string };
    return {
      message: structured.message || "Request failed",
      code: structured.code,
    };
  }
  if (typeof detail === "string") {
    return { message: detail };
  }
  return { message: "Request failed" };
}

function hashPayload(value: unknown): string {
  const raw = JSON.stringify(value);
  let hash = 0;
  for (let i = 0; i < raw.length; i += 1) {
    hash = (hash << 5) - hash + raw.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash).toString(16);
}

function buildIdempotencyKey(scope: string, payload: unknown): string {
  return `${scope}-${hashPayload(payload)}`;
}

async function sessionFetch<T>(path: string, sessionToken: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
    "X-Session-Token": sessionToken,
  };
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(`${getApiUrl()}${path}`, { ...options, headers });
  const payload = await response.json();
  if (!response.ok) {
    const message = payload?.detail?.error?.message || payload?.detail || "Request failed";
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
  return payload.data as T;
}

export async function createSessionFromLink(payload: string, sig?: string | null) {
  let response: Response;
  try {
    response = await fetch(`${getApiUrl()}/api/v1/calculation-session/from-link`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ payload, sig: sig ?? null }),
    });
  } catch {
    throw new Error(
      `Could not reach the API at ${getApiUrl()}. Check that the backend is running and migrations are up to date.`,
    );
  }
  let body: { success?: boolean; data?: FromLinkResponse; detail?: unknown };
  try {
    body = await response.json();
  } catch {
    throw new Error(
      response.ok
        ? "Unexpected response from the server."
        : `Server error (${response.status}). Check backend logs and run: docker compose exec backend alembic upgrade head`,
    );
  }
  if (!response.ok) {
    const { message, code } = parseApiErrorPayload(body);
    throw new EworksSessionError(typeof message === "string" ? message : JSON.stringify(message), code);
  }
  return body as { success: boolean; data: FromLinkResponse };
}

export async function fetchSession(sessionId: string, sessionToken: string): Promise<FromLinkResponse> {
  const data = await sessionFetch<CalculationSessionRead>(
    `/api/v1/calculation-session/${sessionId}`,
    sessionToken,
  );
  return {
    session_id: sessionId,
    session_token: sessionToken,
    step1: data.step1,
    step2: data.step2,
    shared_step2: data.shared_step2,
    resolved: data.resolved,
    expires_at: data.expires_at,
    ui_state: data.ui_state,
    resumed: true,
    status: data.status,
    locked: data.locked,
    revision_in_progress: data.revision_in_progress,
    active_revision_reason: data.active_revision_reason,
    current_version_number: data.current_version_number,
  };
}

export async function createDevTestSession() {
  let response: Response;
  try {
    response = await fetch(`${getApiUrl()}/api/v1/calculation-session/dev-bootstrap`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
  } catch {
    throw new Error(
      `Could not reach the API at ${getApiUrl()}. Check that the backend is running.`,
    );
  }
  let body: { success?: boolean; data?: FromLinkResponse; detail?: unknown };
  try {
    body = await response.json();
  } catch {
    throw new Error(`Server error (${response.status}).`);
  }
  if (!response.ok) {
    const message = (body?.detail as { error?: { message?: string } })?.error?.message || body?.detail || "Request failed";
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
  return body as { success: boolean; data: FromLinkResponse };
}

export async function patchSession(
  sessionId: string,
  sessionToken: string,
  payload: { step2?: Step2Snapshot; ui_state?: SessionUiState; findings_report?: string },
  options?: { idempotency?: boolean },
) {
  const headers: Record<string, string> = {};
  if (options?.idempotency !== false) {
    headers["Idempotency-Key"] = buildIdempotencyKey(`eworks-${sessionId}-patch`, payload);
  }
  return sessionFetch<{ step2?: Step2Snapshot; ui_state?: SessionUiState }>(
    `/api/v1/calculation-session/${sessionId}`,
    sessionToken,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
      headers,
    },
  );
}

export async function patchSessionStep2(sessionId: string, sessionToken: string, step2: Step2Snapshot) {
  return patchSession(sessionId, sessionToken, { step2 });
}

export async function patchFindingsReport(sessionId: string, sessionToken: string, findingsReport: string) {
  return patchSession(sessionId, sessionToken, { findings_report: findingsReport }, { idempotency: false });
}

function sessionStorageKey(quoteNumber: string, jobNumber: string) {
  return `eworks-session:${quoteNumber}:${jobNumber}`;
}

export function storeSessionCredentials(quoteNumber: string, jobNumber: string, sessionId: string, sessionToken: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(
    sessionStorageKey(quoteNumber, jobNumber),
    JSON.stringify({ sessionId, sessionToken }),
  );
}

export function readStoredSessionCredentials(quoteNumber: string, jobNumber: string) {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(sessionStorageKey(quoteNumber, jobNumber));
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as { sessionId?: string; sessionToken?: string };
    if (!parsed.sessionId || !parsed.sessionToken) return null;
    return { sessionId: parsed.sessionId, sessionToken: parsed.sessionToken };
  } catch {
    return null;
  }
}

export async function uploadSessionAttachment(
  sessionId: string,
  sessionToken: string,
  file: File,
  workIndex = 0,
) {
  const formData = new FormData();
  formData.append("file", file);
  return sessionFetch<AttachmentMeta>(
    `/api/v1/calculation-session/${sessionId}/attachments?work_index=${workIndex}`,
    sessionToken,
    {
      method: "POST",
      body: formData,
    },
  );
}

export function getAttachmentUrl(sessionId: string, sessionToken: string, attachmentId: string) {
  const params = new URLSearchParams({ token: sessionToken });
  return `${getApiUrl()}/api/v1/calculation-session/${sessionId}/attachments/${attachmentId}?${params.toString()}`;
}

export async function deleteSessionAttachment(sessionId: string, sessionToken: string, attachmentId: string) {
  const response = await fetch(
    `${getApiUrl()}/api/v1/calculation-session/${sessionId}/attachments/${attachmentId}`,
    {
      method: "DELETE",
      headers: { "X-Session-Token": sessionToken },
    },
  );
  if (!response.ok) {
    let message = "Failed to delete attachment";
    try {
      const payload = await response.json();
      message = payload?.detail?.error?.message || payload?.detail || message;
    } catch {
      // ignore parse errors
    }
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
}

export async function submitSession(sessionId: string, sessionToken: string, step2?: Step2Snapshot) {
  const body = step2 ? { step2 } : {};
  const idempotencyKey = buildIdempotencyKey(`eworks-${sessionId}-submit`, body);
  return sessionFetch<{ submitted: boolean; version_number?: number; revision?: boolean }>(
    `/api/v1/calculation-session/${sessionId}/submit`,
    sessionToken,
    {
      method: "POST",
      body: JSON.stringify(body),
      headers: { "Idempotency-Key": idempotencyKey },
    },
  );
}

export async function reviseEstimate(sessionId: string, sessionToken: string, reason: string) {
  return sessionFetch<{
    session_id: string;
    resume_url: string;
    revision_in_progress: boolean;
    active_revision_reason: string;
    current_version_number: number;
  }>(`/api/v1/calculation-session/${sessionId}/revise`, sessionToken, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export async function calculateSession(sessionId: string, sessionToken: string, step2?: Step2Snapshot) {
  const body = step2 ? { step2 } : {};
  const idempotencyKey = buildIdempotencyKey(`eworks-${sessionId}-calculate`, body);
  return sessionFetch<CalculateResponse>(`/api/v1/calculation-session/${sessionId}/calculate`, sessionToken, {
    method: "POST",
    body: JSON.stringify(body),
    headers: { "Idempotency-Key": idempotencyKey },
  });
}

export async function rewordScope(sessionId: string, sessionToken: string, text: string) {
  return sessionFetch<{ reworded_text: string }>(
    `/api/v1/calculation-session/${sessionId}/reword-scope`,
    sessionToken,
    {
      method: "POST",
      body: JSON.stringify({ text }),
    },
  );
}

export async function downloadSessionPdf(
  sessionId: string,
  sessionToken: string,
  options?: { isDraft?: boolean },
): Promise<void> {
  const response = await fetch(`${getApiUrl()}/api/v1/calculation-session/${sessionId}/pdf`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Session-Token": sessionToken,
    },
    body: JSON.stringify({ is_draft: options?.isDraft ?? false }),
  });
  if (!response.ok) {
    let message = "PDF download failed";
    try {
      const payload = await response.json();
      message = payload?.detail?.error?.message || payload?.detail || message;
    } catch {
      // ignore parse errors
    }
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition");
  const fileName = disposition?.match(/filename="([^"]+)"/)?.[1] ?? "quote.pdf";
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  anchor.click();
  URL.revokeObjectURL(url);
}
