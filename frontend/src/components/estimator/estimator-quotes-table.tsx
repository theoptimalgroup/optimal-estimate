"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  DataTable,
  DataTableBody,
  DataTableCell,
  DataTableHead,
  DataTableRow,
  DateText,
  EmptyState,
  MoneyText,
  PrimaryButton,
  quoteStatusTone,
  StatusBadge,
  type StatusTone,
} from "@/components/ui";
import { QuoteAcceptanceBadge } from "@/components/quote-acceptance-badge";
import {
  buildCalculatorResumeUrl,
  formatMoney,
  resumeEstimatorQuote,
  statusLabel,
  type EstimatorQuoteRow,
} from "@/lib/estimator";

function estimatorQuoteTone(status: string, isReopened?: boolean): StatusTone {
  if (isReopened && status === "in_progress") return "warning";
  return quoteStatusTone(status);
}

type EstimatorQuotesTableProps = {
  quotes: EstimatorQuoteRow[];
  showWorks?: boolean;
  showSubmitted?: boolean;
  detailHref?: (sessionId: string) => string;
  testId?: string;
};

export function EstimatorQuotesTable({
  quotes,
  showWorks = false,
  showSubmitted = false,
  detailHref = (sessionId) => `/estimator/quotes/${sessionId}`,
  testId = "estimator-quotes-table",
}: EstimatorQuotesTableProps) {
  const router = useRouter();
  const [resumingId, setResumingId] = useState<string | null>(null);
  const [resumeError, setResumeError] = useState<string | null>(null);

  const handleResume = async (sessionId: string) => {
    setResumingId(sessionId);
    setResumeError(null);
    try {
      const resume = await resumeEstimatorQuote(sessionId);
      router.push(buildCalculatorResumeUrl(resume.session_id, resume.session_token));
    } catch (err) {
      setResumeError(err instanceof Error ? err.message : "Failed to resume quote");
    } finally {
      setResumingId(null);
    }
  };

  if (quotes.length === 0) {
    return (
      <EmptyState
        title="No quotes found"
        description="No quotes match the current filters."
        className="border-0 bg-transparent"
      />
    );
  }

  const headers = ["Quote Ref", "Client", "Trade", "Status", ...(showWorks ? ["Works"] : []), "Total", "Updated"];
  if (showSubmitted) headers.push("Submitted");
  headers.push("Actions");

  return (
    <div data-testid={testId}>
      {resumeError ? (
        <p className="mb-3 text-sm text-rose-700" role="alert">
          {resumeError}
        </p>
      ) : null}
      <DataTable>
        <DataTableHead>
          {headers.map((header) => (
            <DataTableCell key={header} header>
              {header}
            </DataTableCell>
          ))}
        </DataTableHead>
        <DataTableBody>
          {quotes.map((quote) => (
            <DataTableRow key={quote.session_id}>
              <DataTableCell className="font-medium text-slate-900">{quote.quote_ref}</DataTableCell>
              <DataTableCell>{quote.client_name || "—"}</DataTableCell>
              <DataTableCell>{quote.trade_name || "—"}</DataTableCell>
              <DataTableCell>
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge tone={estimatorQuoteTone(quote.status, quote.is_reopened)}>
                    {statusLabel(quote.status, quote.is_reopened)}
                  </StatusBadge>
                  {quote.acceptance?.accepted ? <QuoteAcceptanceBadge accepted /> : null}
                </div>
              </DataTableCell>
              {showWorks ? <DataTableCell>{quote.work_count}</DataTableCell> : null}
              <DataTableCell>
                <MoneyText value={formatMoney(quote.total)} />
              </DataTableCell>
              <DataTableCell>
                <DateText value={quote.updated_at} includeTime />
              </DataTableCell>
              {showSubmitted ? (
                <DataTableCell>
                  <DateText value={quote.submitted_at} includeTime />
                </DataTableCell>
              ) : null}
              <DataTableCell>
                <div className="flex flex-wrap items-center gap-2">
                  {quote.can_resume ? (
                    <PrimaryButton
                      className="min-h-0 px-2.5 py-1 text-xs"
                      disabled={resumingId === quote.session_id}
                      onClick={() => void handleResume(quote.session_id)}
                      data-testid={`resume-${quote.session_id}`}
                    >
                      {resumingId === quote.session_id ? "Opening…" : "Continue"}
                    </PrimaryButton>
                  ) : null}
                  {quote.can_view_review ? (
                    <Link
                      href={detailHref(quote.session_id)}
                      className="text-sm font-medium text-blue-600 hover:text-blue-700"
                      data-testid={`view-${quote.session_id}`}
                    >
                      View
                    </Link>
                  ) : null}
                </div>
              </DataTableCell>
            </DataTableRow>
          ))}
        </DataTableBody>
      </DataTable>
    </div>
  );
}

export function EstimatorKpiCard({ label, value }: { label: string; value: string }) {
  const testId = `kpi-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
  return (
    <div data-testid={testId}>
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <p className="text-sm font-medium text-slate-600">{label}</p>
        <p className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">{value}</p>
      </div>
    </div>
  );
}
