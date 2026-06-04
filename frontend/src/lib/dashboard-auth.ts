import { apiFetch, getApiUrl } from "@/lib/api";
import { getAuthHeaders } from "@/lib/auth/token-provider";
import {
  buildCombinedWorksPdfFileName,
  type CombineWorkNotesResponse,
  type DashboardQuotesResponse,
  type ReopenQuoteResponse,
} from "@/lib/dashboard";

export async function fetchSubmittedQuotes() {
  const response = await apiFetch<DashboardQuotesResponse>("/api/v1/dashboard/quotes");
  return response.data;
}

export async function reopenQuoteForRefill(sessionId: string) {
  const response = await apiFetch<ReopenQuoteResponse>(`/api/v1/dashboard/quotes/${sessionId}/reopen`, {
    method: "POST",
  });
  return response.data;
}

export async function fetchCombinedWorkNotes(sessionId: string, workIndexes: number[]) {
  const response = await apiFetch<CombineWorkNotesResponse>(
    `/api/v1/dashboard/quotes/${sessionId}/combine-notes`,
    {
      method: "POST",
      body: JSON.stringify({ work_indexes: workIndexes }),
    },
  );
  return response.data;
}

export async function downloadCombinedWorksPdf(
  sessionId: string,
  workIndexes: number[],
  viewType: "client" | "optimal",
  quoteNumber?: string,
): Promise<void> {
  const response = await fetch(`${getApiUrl()}/api/v1/dashboard/quotes/${sessionId}/combined-pdf`, {
    method: "POST",
    headers: await getAuthHeaders({ "Content-Type": "application/json" }),
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
