"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { EworksButton, EworksLoadingScreen } from "@/components/eworks-ui";
import { QuoteAcceptancePanel } from "@/components/quote-acceptance-panel";
import {
  buildCalculatorResumeUrl,
  formatEstimatorDate,
  formatMoney,
  getEstimatorQuote,
  resumeEstimatorQuote,
  statusLabel,
  type EstimatorQuoteDetail,
} from "@/lib/estimator";

export default function EstimatorQuoteDetailPage({ params }: { params: { sessionId: string } }) {
  const { sessionId } = params;
  const router = useRouter();
  const [quote, setQuote] = useState<EstimatorQuoteDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [resuming, setResuming] = useState(false);

  const loadQuote = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setQuote(await getEstimatorQuote(sessionId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load quote");
      setQuote(null);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    void loadQuote();
  }, [loadQuote]);

  const handleResume = async () => {
    setResuming(true);
    setError(null);
    try {
      const resume = await resumeEstimatorQuote(sessionId);
      router.push(buildCalculatorResumeUrl(resume.session_id, resume.session_token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to resume quote");
    } finally {
      setResuming(false);
    }
  };

  return (
    <div className="space-y-6" data-testid="estimator-quote-detail-page">
      <div className="flex items-center justify-between gap-4">
        <div>
          <Link href="/estimator/quotes" className="text-sm text-indigo-600 hover:text-indigo-800">
            ← Back to quotes
          </Link>
          <h1 className="mt-2 text-2xl font-semibold text-gray-900">Quote Details</h1>
        </div>
        {quote?.can_resume ? (
          <EworksButton type="button" onClick={() => void handleResume()} disabled={resuming}>
            {resuming ? "Opening…" : "Continue Estimate"}
          </EworksButton>
        ) : null}
      </div>

      {loading ? (
        <EworksLoadingScreen message="Loading quote…" />
      ) : error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      ) : quote ? (
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <dl className="grid gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-sm font-medium text-gray-500">Quote ref</dt>
              <dd className="mt-1 text-gray-900">{quote.quote_ref}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">Job number</dt>
              <dd className="mt-1 text-gray-900">{quote.job_number || "—"}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">Client</dt>
              <dd className="mt-1 text-gray-900">{quote.client_name || "—"}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">Trade</dt>
              <dd className="mt-1 text-gray-900">{quote.trade_name || "—"}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">Status</dt>
              <dd className="mt-1 text-gray-900">{statusLabel(quote.status, quote.is_reopened)}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">Total</dt>
              <dd className="mt-1 text-gray-900">{formatMoney(quote.total)}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">Works</dt>
              <dd className="mt-1 text-gray-900">{quote.work_count}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">Updated</dt>
              <dd className="mt-1 text-gray-900">{formatEstimatorDate(quote.updated_at)}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">Submitted</dt>
              <dd className="mt-1 text-gray-900">{formatEstimatorDate(quote.submitted_at)}</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-sm font-medium text-gray-500">Property address</dt>
              <dd className="mt-1 text-gray-900">{quote.property_address || "—"}</dd>
            </div>
          </dl>
          <div className="mt-6">
            <QuoteAcceptancePanel acceptance={quote.acceptance} />
          </div>
          {quote.status === "submitted" ? (
            <p className="mt-6 text-sm text-gray-600">
              This quote is in the manager review queue. Estimators cannot approve or reject submitted quotes here.
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
