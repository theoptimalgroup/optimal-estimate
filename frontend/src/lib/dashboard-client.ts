import * as passwordDashboard from "@/lib/dashboard";
import * as roleDashboard from "@/lib/dashboard-auth";
import type {
  CombineWorkNotesResponse,
  CombinedWorksPdfViewType,
  DashboardQuoteItem,
  DashboardQuotesResponse,
  ReopenQuoteResponse,
} from "@/lib/dashboard";

export type DashboardAccessMode = "password" | "role";

export type DashboardClient = {
  mode: DashboardAccessMode;
  fetchSubmittedQuotes: () => Promise<DashboardQuotesResponse>;
  fetchSubmittedQuoteDetail: (sessionId: string, versionNumber?: number) => Promise<DashboardQuoteItem>;
  reopenQuoteForRefill: (sessionId: string) => Promise<ReopenQuoteResponse>;
  fetchCombinedWorkNotes: (sessionId: string, workIndexes: number[]) => Promise<CombineWorkNotesResponse>;
  downloadCombinedWorksPdf: (
    sessionId: string,
    workIndexes: number[],
    viewType: CombinedWorksPdfViewType,
    quoteNumber?: string,
  ) => Promise<void>;
};

export function createPasswordDashboardClient(password: string): DashboardClient {
  return {
    mode: "password",
    fetchSubmittedQuotes: () => passwordDashboard.fetchSubmittedQuotes(password),
    fetchSubmittedQuoteDetail: (sessionId, versionNumber) =>
      passwordDashboard.fetchSubmittedQuoteDetail(password, sessionId, versionNumber),
    reopenQuoteForRefill: (sessionId) => passwordDashboard.reopenQuoteForRefill(password, sessionId),
    fetchCombinedWorkNotes: (sessionId, workIndexes) =>
      passwordDashboard.fetchCombinedWorkNotes(password, sessionId, workIndexes),
    downloadCombinedWorksPdf: (sessionId, workIndexes, viewType, quoteNumber) =>
      passwordDashboard.downloadCombinedWorksPdf(password, sessionId, workIndexes, viewType, quoteNumber),
  };
}

export function createRoleDashboardClient(): DashboardClient {
  return {
    mode: "role",
    fetchSubmittedQuotes: roleDashboard.fetchSubmittedQuotes,
    fetchSubmittedQuoteDetail: roleDashboard.fetchSubmittedQuoteDetail,
    reopenQuoteForRefill: roleDashboard.reopenQuoteForRefill,
    fetchCombinedWorkNotes: roleDashboard.fetchCombinedWorkNotes,
    downloadCombinedWorksPdf: roleDashboard.downloadCombinedWorksPdf,
  };
}
