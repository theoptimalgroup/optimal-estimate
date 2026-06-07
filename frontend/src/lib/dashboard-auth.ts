import { apiFetch, getApiUrl } from "@/lib/api";
import { getAuthHeaders } from "@/lib/auth/token-provider";
import {
  buildCombinedWorksPdfFileName,
  type CombinedWorksPdfViewType,
  type SelectQuoteEstimateRequest,
  type SelectQuoteEstimateResponse,
  type CombineWorkNotesResponse,
  type DashboardQuoteGroupDetailResponse,
  type DashboardQuoteGroupsResponse,
  type DashboardQuoteItem,
  type DashboardQuotesResponse,
  type ManagerQuotePdfView,
  type ReopenQuoteResponse,
} from "@/lib/dashboard";

export async function fetchSubmittedQuotes() {
  const response = await apiFetch<DashboardQuotesResponse>("/api/v1/dashboard/quotes");
  return response.data;
}

export async function fetchSubmittedQuoteDetail(sessionId: string, versionNumber?: number) {
  const search = versionNumber != null ? `?version=${versionNumber}` : "";
  const response = await apiFetch<DashboardQuoteItem>(`/api/v1/dashboard/quotes/${sessionId}${search}`);
  return response.data;
}

export async function fetchSubmittedQuoteGroups() {
  const response = await apiFetch<DashboardQuoteGroupsResponse>("/api/v1/dashboard/quote-groups");
  return {
    groups: response.data?.groups ?? [],
    total: Number(response.meta?.total ?? response.data?.groups?.length ?? 0),
  };
}

export async function fetchSubmittedQuoteGroupDetail(params: {
  quote_ref?: string;
  eworks_quote_id?: number;
  group_key?: string;
}) {
  const search = new URLSearchParams();
  if (params.group_key) search.set("group_key", params.group_key);
  if (params.quote_ref) search.set("quote_ref", params.quote_ref);
  if (params.eworks_quote_id != null) search.set("eworks_quote_id", String(params.eworks_quote_id));
  const response = await apiFetch<DashboardQuoteGroupDetailResponse>(
    `/api/v1/dashboard/quote-groups/detail?${search.toString()}`,
  );
  return response.data;
}

export async function reopenQuoteForRefill(sessionId: string) {
  const response = await apiFetch<ReopenQuoteResponse>(`/api/v1/dashboard/quotes/${sessionId}/reopen`, {
    method: "POST",
  });
  return response.data;
}

/** Record manager's selected submitted estimate for a quote group. */
export async function selectQuoteEstimate(quoteRef: string, payload: SelectQuoteEstimateRequest) {
  const response = await apiFetch<SelectQuoteEstimateResponse>(
    `/api/v1/manager/quotes/${encodeURIComponent(quoteRef)}/select-estimate`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
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
  viewType: CombinedWorksPdfViewType,
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

function buildManagerQuotePdfFileName(quoteNumber: string | undefined, view: ManagerQuotePdfView): string {
  const safeQuoteId = (quoteNumber ?? "quote").replace(/[/\\]/g, "-").trim() || "quote";
  if (view === "client") return `${safeQuoteId}_Client_view.pdf`;
  if (view === "internal") return `${safeQuoteId}_optimal_view.pdf`;
  if (view === "all-trades") return `${safeQuoteId}_all_trades.pdf`;
  return `${safeQuoteId}_combined.pdf`;
}

export async function downloadManagerQuotePdf(
  sessionId: string,
  view: ManagerQuotePdfView,
  quoteNumber?: string,
  version?: number,
): Promise<void> {
  const params = new URLSearchParams();
  if (version != null) {
    params.set("version", String(version));
  }
  const query = params.toString();
  const response = await fetch(
    `${getApiUrl()}/api/v1/manager/quotes/${sessionId}/pdf/${view}${query ? `?${query}` : ""}`,
    {
      method: "GET",
      headers: await getAuthHeaders(),
    },
  );
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
  const fileName = headerFileName ?? buildManagerQuotePdfFileName(quoteNumber, view);
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
