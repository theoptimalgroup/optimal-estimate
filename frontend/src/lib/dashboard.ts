import { getApiUrl } from "@/lib/api";
import type { AttachmentMeta, WorkBlockSnapshot } from "@/lib/eworks-session";

const DASHBOARD_PASSWORD_KEY = "eworks-dashboard-password";

export type DashboardWorkItem = {
  work_index: number;
  scope?: string | null;
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
};

export type DashboardQuotesResponse = {
  quotes: DashboardQuoteItem[];
};

export type ReopenQuoteResponse = {
  session_id: string;
  session_token: string;
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
