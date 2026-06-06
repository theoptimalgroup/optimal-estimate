import { getApiUrl } from "@/lib/api";
import type { AttachmentMeta } from "@/lib/eworks-calculate-schema";
import type { WorkBlockSnapshot } from "@/lib/eworks-session";
import type { QuoteAcceptanceStatus } from "@/lib/quote-acceptance";

const DASHBOARD_PASSWORD_KEY = "eworks-dashboard-password";

export type DashboardWorkItem = {
  work_index: number;
  scope?: string | null;
  product_name?: string | null;
  product_code?: string | null;
  display_label?: string | null;
  labour_subtotal?: number | string | null;
  materials_subtotal?: number | string | null;
  internal_notes?: string | null;
  attachments: AttachmentMeta[];
  details?: WorkBlockSnapshot | null;
};

export type DashboardQuoteItem = {
  session_id: string;
  session_token: string;
  quote_number: string;
  job_number: string;
  client_name: string;
  trade_name: string;
  submitted_at: string;
  final_total?: number | string | null;
  internal_notes?: string | null;
  works: DashboardWorkItem[];
  acceptance?: QuoteAcceptanceStatus;
};

export type DashboardQuotesResponse = {
  quotes: DashboardQuoteItem[];
};

export type DashboardQuoteGroupSessionItem = {
  session_id: string;
  submitted_at: string;
  final_total?: number | string | null;
  works_count: number;
  status: string;
  accepted: boolean;
  client_accepted_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type DashboardQuoteGroupSessionDetailItem = DashboardQuoteGroupSessionItem & {
  submitted_by_user_id?: string | null;
  submitted_by_name?: string;
  submitted_by_email?: string | null;
  submitted_by_role?: string | null;
  is_latest?: boolean;
};

export type DashboardQuoteGroupAssignmentItem = {
  id: number;
  assignment_type: "estimator" | "engineer" | string;
  assignee_kind: "registered" | "external" | string;
  assigned_user_id?: string | null;
  assigned_user_name?: string | null;
  assigned_user_email?: string | null;
  status: "assigned" | "in_progress" | "submitted" | "cancelled" | string;
  assigned_at: string;
  started_at?: string | null;
  submitted_at?: string | null;
  calculation_session_id?: string | null;
  has_submission: boolean;
};

export type DashboardQuoteGroupAssignmentSummary = {
  total_assignments: number;
  estimator_assignments: number;
  engineer_assignments: number;
  pending_assignments: number;
  in_progress_assignments: number;
  submitted_assignments: number;
  cancelled_assignments: number;
};

export type DashboardQuoteGroupItem = {
  group_key: string;
  quote_ref: string | null;
  eworks_quote_id: number | null;
  client_name: string;
  trade_name: string;
  submission_count: number;
  latest_submitted_at: string;
  latest_total?: number | string | null;
  highest_total?: number | string | null;
  lowest_total?: number | string | null;
  accepted: boolean;
  client_accepted_at?: string | null;
  reopened_count: number;
  latest_session_id: string;
  sessions: DashboardQuoteGroupSessionItem[];
};

export type DashboardQuoteGroupDetailItem = DashboardQuoteGroupItem & {
  review_status?: "pending" | "in_progress" | "ready_for_review" | "accepted" | string;
  assignment_summary?: DashboardQuoteGroupAssignmentSummary;
  assignments?: DashboardQuoteGroupAssignmentItem[];
  sessions: DashboardQuoteGroupSessionDetailItem[];
};

export type DashboardQuoteGroupsResponse = {
  groups: DashboardQuoteGroupItem[];
};

export type DashboardQuoteGroupDetailResponse = {
  group: DashboardQuoteGroupDetailItem;
};

export function buildQuoteGroupHref(group: Pick<DashboardQuoteGroupItem, "quote_ref" | "eworks_quote_id">): string {
  const params = new URLSearchParams();
  if (group.quote_ref) {
    params.set("quote_ref", group.quote_ref);
  } else if (group.eworks_quote_id != null) {
    params.set("eworks_quote_id", String(group.eworks_quote_id));
  }
  const query = params.toString();
  return query ? `/manager/review/group?${query}` : "/manager/review/group";
}

export type ReopenQuoteResponse = {
  session_id: string;
  session_token: string;
};

export type CombineWorkNotesResponse = {
  quote_number: string;
  job_number: string;
  client_name: string;
  internal_notes: string;
};

export function storeDashboardPassword(password: string) {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(DASHBOARD_PASSWORD_KEY, password);
}

export function readDashboardPassword() {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(DASHBOARD_PASSWORD_KEY);
}

export function clearDashboardPassword() {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(DASHBOARD_PASSWORD_KEY);
}

export async function fetchSubmittedQuotes(password: string) {
  const response = await fetch(`${getApiUrl()}/api/v1/dashboard/quotes`, {
    headers: { "X-Dashboard-Password": password },
  });
  const payload = await response.json();
  if (!response.ok) {
    const message = payload?.detail?.error?.message || payload?.detail || "Failed to load quotes";
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
  return payload.data as DashboardQuotesResponse;
}

export async function reopenQuoteForRefill(password: string, sessionId: string) {
  const response = await fetch(`${getApiUrl()}/api/v1/dashboard/quotes/${sessionId}/reopen`, {
    method: "POST",
    headers: { "X-Dashboard-Password": password },
  });
  const payload = await response.json();
  if (!response.ok) {
    const message = payload?.detail?.error?.message || payload?.detail || "Failed to reopen quote";
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
  return payload.data as ReopenQuoteResponse;
}

export async function fetchCombinedWorkNotes(
  password: string,
  sessionId: string,
  workIndexes: number[],
) {
  const response = await fetch(`${getApiUrl()}/api/v1/dashboard/quotes/${sessionId}/combine-notes`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Dashboard-Password": password,
    },
    body: JSON.stringify({ work_indexes: workIndexes }),
  });
  const payload = await response.json();
  if (!response.ok) {
    const message = payload?.detail?.error?.message || payload?.detail || "Failed to combine internal notes";
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
  return payload.data as CombineWorkNotesResponse;
}

export function buildCombinedWorksPdfFileName(quoteNumber: string, viewType: "client" | "optimal"): string {
  const safeQuoteId = quoteNumber.replace(/[/\\]/g, "-").trim() || "quote";
  return viewType === "client" ? `${safeQuoteId}_Client_view.pdf` : `${safeQuoteId}_optimal_view.pdf`;
}

export async function downloadCombinedWorksPdf(
  password: string,
  sessionId: string,
  workIndexes: number[],
  viewType: "client" | "optimal",
  quoteNumber?: string,
): Promise<void> {
  const response = await fetch(`${getApiUrl()}/api/v1/dashboard/quotes/${sessionId}/combined-pdf`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Dashboard-Password": password,
    },
    body: JSON.stringify({ work_indexes: workIndexes, view_type: viewType }),
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
  const headerFileName = disposition?.match(/filename="([^"]+)"/)?.[1];
  const fileName =
    headerFileName ??
    (quoteNumber ? buildCombinedWorksPdfFileName(quoteNumber, viewType) : `quote-${viewType}.pdf`);
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
