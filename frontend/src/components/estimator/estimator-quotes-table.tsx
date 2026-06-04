"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { EworksButton } from "@/components/eworks-ui";
import { QuoteAcceptanceBadge } from "@/components/quote-acceptance-badge";
import {
  buildCalculatorResumeUrl,
  formatEstimatorDate,
  formatMoney,
  resumeEstimatorQuote,
  statusLabel,
  type EstimatorQuoteRow,
} from "@/lib/estimator";

function StatusBadge({ status, isReopened }: { status: string; isReopened?: boolean }) {
  const label = statusLabel(status, isReopened);
  const tone =
    status === "submitted"
      ? "bg-emerald-100 text-emerald-800"
      : isReopened
        ? "bg-orange-100 text-orange-800"
        : status === "in_progress"
          ? "bg-amber-100 text-amber-800"
          : "bg-slate-100 text-slate-700";
  return <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${tone}`}>{label}</span>;
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
    return <p className="text-sm text-gray-500">No quotes match the current filters.</p>;
  }

  const headers = ["Quote Ref", "Client", "Trade", "Status", ...(showWorks ? ["Works"] : []), "Total", "Updated"];
  if (showSubmitted) headers.push("Submitted");
  headers.push("Actions");

  return (
    <div data-testid={testId}>
      {resumeError ? <p className="mb-3 text-sm text-red-600">{resumeError}</p> : null}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              {headers.map((header) => (
                <th key={header} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            {quotes.map((quote) => (
              <tr key={quote.session_id}>
                <td className="px-4 py-3 font-medium text-gray-900">{quote.quote_ref}</td>
                <td className="px-4 py-3 text-gray-700">{quote.client_name || "—"}</td>
                <td className="px-4 py-3 text-gray-700">{quote.trade_name || "—"}</td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge status={quote.status} isReopened={quote.is_reopened} />
                    {quote.acceptance?.accepted ? <QuoteAcceptanceBadge accepted /> : null}
                  </div>
                </td>
                {showWorks ? <td className="px-4 py-3 text-gray-700">{quote.work_count}</td> : null}
                <td className="px-4 py-3 text-gray-900">{formatMoney(quote.total)}</td>
                <td className="px-4 py-3 text-gray-700">{formatEstimatorDate(quote.updated_at)}</td>
                {showSubmitted ? (
                  <td className="px-4 py-3 text-gray-700">{formatEstimatorDate(quote.submitted_at)}</td>
                ) : null}
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-2">
                    {quote.can_resume ? (
                      <EworksButton
                        type="button"
                        className="px-2 py-1 text-xs"
                        disabled={resumingId === quote.session_id}
                        onClick={() => void handleResume(quote.session_id)}
                        data-testid={`resume-${quote.session_id}`}
                      >
                        {resumingId === quote.session_id ? "Opening…" : "Continue"}
                      </EworksButton>
                    ) : null}
                    {quote.can_view_review ? (
                      <Link
                        href={detailHref(quote.session_id)}
                        className="text-sm font-medium text-indigo-600 hover:text-indigo-800"
                        data-testid={`view-${quote.session_id}`}
                      >
                        View
                      </Link>
                    ) : null}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function EstimatorKpiCard({ label, value }: { label: string; value: string }) {
  return (
    <div
      className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm"
      data-testid={`kpi-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
    >
      <p className="text-sm font-medium text-gray-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-gray-900">{value}</p>
    </div>
  );
}
