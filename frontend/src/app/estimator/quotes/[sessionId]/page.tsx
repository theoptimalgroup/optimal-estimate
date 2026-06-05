"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { QuoteAcceptancePanel } from "@/components/quote-acceptance-panel";
import {
  DateText,
  ErrorState,
  LoadingState,
  MoneyText,
  PageHeader,
  PrimaryButton,
  quoteStatusTone,
  SectionCard,
  StatusBadge,
  type StatusTone,
} from "@/components/ui";
import {
  buildCalculatorResumeUrl,
  formatMoney,
  getEstimatorQuote,
  resumeEstimatorQuote,
  statusLabel,
  type EstimatorQuoteDetail,
} from "@/lib/estimator";

function estimatorQuoteTone(status: string, isReopened?: boolean): StatusTone {
  if (isReopened && status === "in_progress") return "warning";
  return quoteStatusTone(status);
}

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
      <Link href="/estimator/quotes" className="text-sm font-medium text-blue-600 hover:text-blue-700">
        ← Back to quotes
      </Link>
      <PageHeader
        title="Quote Details"
        description={quote?.quote_ref}
        actions={
          quote?.can_resume ? (
            <PrimaryButton onClick={() => void handleResume()} disabled={resuming}>
              {resuming ? "Opening…" : "Continue Estimate"}
            </PrimaryButton>
          ) : undefined
        }
      />

      {loading ? (
        <LoadingState message="Loading quote…" />
      ) : error ? (
        <ErrorState message={error} onRetry={() => void loadQuote()} />
      ) : quote ? (
        <>
          <SectionCard title="Overview">
            <dl className="grid gap-4 sm:grid-cols-2">
              <div>
                <dt className="text-sm font-medium text-slate-500">Quote ref</dt>
                <dd className="mt-1 font-medium text-slate-900">{quote.quote_ref}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-slate-500">Job number</dt>
                <dd className="mt-1 text-slate-900">{quote.job_number || "—"}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-slate-500">Client</dt>
                <dd className="mt-1 text-slate-900">{quote.client_name || "—"}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-slate-500">Trade</dt>
                <dd className="mt-1 text-slate-900">{quote.trade_name || "—"}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-slate-500">Status</dt>
                <dd className="mt-1">
                  <StatusBadge tone={estimatorQuoteTone(quote.status, quote.is_reopened)}>
                    {statusLabel(quote.status, quote.is_reopened)}
                  </StatusBadge>
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-slate-500">Total</dt>
                <dd className="mt-1">
                  <MoneyText value={formatMoney(quote.total)} />
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-slate-500">Works</dt>
                <dd className="mt-1 text-slate-900">{quote.work_count}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-slate-500">Updated</dt>
                <dd className="mt-1">
                  <DateText value={quote.updated_at} includeTime />
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-slate-500">Submitted</dt>
                <dd className="mt-1">
                  <DateText value={quote.submitted_at} includeTime />
                </dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="text-sm font-medium text-slate-500">Property address</dt>
                <dd className="mt-1 text-slate-900">{quote.property_address || "—"}</dd>
              </div>
            </dl>
          </SectionCard>

          <QuoteAcceptancePanel acceptance={quote.acceptance} />

          {quote.status === "submitted" ? (
            <p className="text-sm text-slate-600">
              This quote is in the manager review queue. Estimators cannot approve or reject submitted quotes here.
            </p>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
