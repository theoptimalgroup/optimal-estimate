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

export type DashboardQuoteSummaryBreakdown = {
  works_subtotal: number | string;
  additional_charges: number | string;
  vat_total: number | string;
  final_total: number | string;
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
  additional_charges?: string[];
  breakdown?: DashboardQuoteSummaryBreakdown | null;
  works: DashboardWorkItem[];
  acceptance?: QuoteAcceptanceStatus;
  status?: string;
  locked?: boolean;
  current_version_number?: number;
  revision_in_progress?: boolean;
  active_revision_reason?: string | null;
  can_revise?: boolean;
  can_continue_revision?: boolean;
};

export type DashboardQuotesResponse = {
  quotes: DashboardQuoteItem[];
};

export type DashboardQuoteGroupVersionItem = {
  version_id?: string | null;
  version_number: number;
  submitted_at?: string | null;
  submitted_by_name?: string | null;
  submitted_by_email?: string | null;
  submitted_by_role?: string | null;
  revision_reason?: string | null;
  final_total?: number | string | null;
  status: string;
  is_current?: boolean;
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
  current_version_number?: number;
  revision_in_progress?: boolean;
};

export type DashboardQuoteGroupSessionDetailItem = DashboardQuoteGroupSessionItem & {
  submitted_by_user_id?: string | null;
  submitted_by_name?: string;
  submitted_by_email?: string | null;
  submitted_by_role?: string | null;
  is_latest?: boolean;
  version_history?: DashboardQuoteGroupVersionItem[];
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

export type DashboardQuoteGroupComparisonChargeLine = {
  label: string;
  amount: number | string;
};

export type DashboardQuoteGroupComparisonWorkBreakdown = {
  product_name?: string | null;
  product_code?: string | null;
  scope_preview?: string | null;
  labour_subtotal?: number | string | null;
  materials_subtotal?: number | string | null;
  work_subtotal?: number | string | null;
};

export type DashboardQuoteGroupComparisonSummary = {
  final_total?: number | string | null;
  works_subtotal?: number | string | null;
  labour_subtotal?: number | string | null;
  materials_subtotal?: number | string | null;
  additional_charges_total?: number | string | null;
  vat_total?: number | string | null;
  vat_rate?: number | string | null;
  scope_preview?: string | null;
  product_preview?: string | null;
  works?: DashboardQuoteGroupComparisonWorkBreakdown[];
  additional_charges?: DashboardQuoteGroupComparisonChargeLine[];
};

export type DashboardSelectedEstimateDecision = {
  id: number;
  selected_session_id: string;
  assignee_name: string;
  assignee_email?: string | null;
  assignment_id?: number | null;
  assignee_type?: string | null;
  final_total?: number | string | null;
  selected_at: string;
  selected_by_name?: string | null;
  selected_by_email?: string | null;
};

/** @deprecated Use DashboardSelectedEstimateDecision */
export type DashboardQuoteJobAssignmentDecision = DashboardSelectedEstimateDecision;

export type DashboardQuoteGroupAssignmentSubmissionRow = {
  assignment_id: number | null;
  assignment_type: string;
  assignee_kind: string;
  assignee_name: string;
  assignee_email?: string | null;
  assignment_status: string;
  assigned_at?: string | null;
  started_at?: string | null;
  submitted_at?: string | null;
  linked_session_id?: string | null;
  submitted_by_name?: string | null;
  submitted_by_email?: string | null;
  submitted_by_role?: string | null;
  final_total?: number | string | null;
  works_count?: number | null;
  is_latest?: boolean;
  can_view_details?: boolean;
  can_reopen?: boolean;
  can_select_estimate?: boolean;
  is_selected_estimate?: boolean;
  /** @deprecated Use can_select_estimate */
  can_assign_job?: boolean;
  /** @deprecated Use is_selected_estimate */
  is_job_assigned?: boolean;
  comparison_summary?: DashboardQuoteGroupComparisonSummary | null;
  current_version_number?: number | null;
  version_count?: number;
  versions?: DashboardQuoteGroupVersionItem[];
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
  assignment_submissions?: DashboardQuoteGroupAssignmentSubmissionRow[];
  selected_estimate_decision?: DashboardSelectedEstimateDecision | null;
  /** @deprecated Use selected_estimate_decision */
  job_assignment_decision?: DashboardSelectedEstimateDecision | null;
  sessions: DashboardQuoteGroupSessionDetailItem[];
};

export type DashboardQuoteGroupsResponse = {
  groups: DashboardQuoteGroupItem[];
};

export type DashboardQuoteGroupDetailResponse = {
  group: DashboardQuoteGroupDetailItem;
};

export type SelectQuoteEstimateRequest = {
  selected_session_id: string;
  selected_assignment_id?: number | null;
  assignee_name?: string;
  assignee_email?: string | null;
  assignment_id?: number | null;
};

/** @deprecated Use SelectQuoteEstimateRequest */
export type AssignQuoteJobRequest = SelectQuoteEstimateRequest;

export type SelectQuoteEstimateResponse = {
  selected_estimate: DashboardSelectedEstimateDecision;
};

/** @deprecated Use SelectQuoteEstimateResponse */
export type AssignQuoteJobResponse = SelectQuoteEstimateResponse;

export type ManagerQuotePdfView = "client" | "internal" | "combined" | "all-trades";

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

export type ReviseEstimateResponse = {
  session_id: string;
  resume_url: string;
  revision_in_progress: boolean;
  active_revision_reason: string;
  current_version_number: number;
};

export type SessionVersionHistoryResponse = {
  session_id: string;
  current_version_number: number;
  revision_in_progress: boolean;
  active_revision_reason?: string | null;
  versions: DashboardQuoteGroupVersionItem[];
};

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

export async function fetchSubmittedQuoteDetail(
  password: string,
  sessionId: string,
  versionNumber?: number,
) {
  const search = versionNumber != null ? `?version=${versionNumber}` : "";
  const response = await fetch(`${getApiUrl()}/api/v1/dashboard/quotes/${sessionId}${search}`, {
    headers: { "X-Dashboard-Password": password },
  });
  const payload = await response.json();
  if (!response.ok) {
    const message = payload?.detail?.error?.message || payload?.detail || "Failed to load quote";
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
  return payload.data as DashboardQuoteItem;
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

export type CombinedWorksPdfViewType = "client" | "optimal" | "all_trades";

export function buildCombinedWorksPdfFileName(quoteNumber: string, viewType: CombinedWorksPdfViewType): string {
  const safeQuoteId = quoteNumber.replace(/[/\\]/g, "-").trim() || "quote";
  if (viewType === "client") return `${safeQuoteId}_Client_view.pdf`;
  if (viewType === "all_trades") return `${safeQuoteId}_all_trades.pdf`;
  return `${safeQuoteId}_optimal_view.pdf`;
}

export async function downloadCombinedWorksPdf(
  password: string,
  sessionId: string,
  workIndexes: number[],
  viewType: CombinedWorksPdfViewType,
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
