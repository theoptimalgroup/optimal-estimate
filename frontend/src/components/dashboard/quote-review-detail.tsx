"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  CombinedNotesModal,
  formatSubmittedAt,
  money,
  WorkSection,
  WorkSelectionBar,
  QuoteAdditionalChargesSection,
  QuoteSummaryBreakdown,
} from "@/components/eworks-dashboard";
import { ClientLinkPanel } from "@/components/dashboard/client-link-panel";
import { QuoteAcceptancePanel } from "@/components/quote-acceptance-panel";
import {
  BackLink,
  EmptyState,
  ErrorState,
  LoadingState,
  MoneyText,
  PageHeader,
  PrimaryButton,
  SecondaryButton,
  SectionCard,
} from "@/components/ui";
import { retryEworksAcceptanceSync } from "@/lib/client-quotes";
import { normalizeQuoteAcceptance } from "@/lib/quote-acceptance";
import { DashboardPageShell, EworksSectionTitle, cn } from "@/components/eworks-ui";
import type { DashboardClient } from "@/lib/dashboard-client";
import type { DashboardQuoteItem, ReopenQuoteResponse } from "@/lib/dashboard";
import { downloadManagerQuotePdf } from "@/lib/dashboard-auth";
import { downloadSessionPdf } from "@/lib/eworks-session";
import { defaultOpenWorkIndexes, formatQuoteSummaryTitle } from "@/lib/work-label";

function defaultBackLabel(backHref: string): string {
  if (backHref === "/manager/review" || backHref.startsWith("/manager/review?")) {
    return "Back to Quote Review";
  }
  if (backHref === "/manager/quotes" || backHref.startsWith("/manager/quotes")) {
    return "Back to Quotes";
  }
  if (backHref === "/manager/dashboard" || backHref.startsWith("/manager/dashboard")) {
    return "Back to Dashboard";
  }
  if (backHref === "/eworks/dashboard" || backHref.startsWith("/eworks/dashboard")) {
    return "Back to Dashboard";
  }
  if (backHref === "/estimator/dashboard" || backHref.startsWith("/estimator/dashboard")) {
    return "Back to Estimator Dashboard";
  }
  if (backHref === "/estimator/quotes" || backHref.startsWith("/estimator/quotes")) {
    return "Back to Quotes";
  }
  if (
    backHref === "/engineer/assigned-estimates" ||
    backHref.startsWith("/engineer/assigned-estimates") ||
    backHref === "/engineer/jobs" ||
    backHref.startsWith("/engineer/jobs")
  ) {
    return "Back to Assigned Estimates";
  }
  return "Back to Dashboard";
}

type QuoteReviewDetailProps = {
  sessionId: string;
  client: DashboardClient;
  backHref: string;
  listHref: string;
  backLabel?: string;
  onUnlockSuccess?: (reopened: ReopenQuoteResponse, quote: DashboardQuoteItem) => void;
  shell?: "dashboard" | "embedded";
  enableClientLink?: boolean;
  showClientAcceptance?: boolean;
};

export function QuoteReviewDetail({
  sessionId,
  client,
  backHref,
  listHref,
  backLabel,
  onUnlockSuccess,
  shell = "dashboard",
  enableClientLink = false,
  showClientAcceptance = false,
}: QuoteReviewDetailProps) {
  const resolvedBackLabel = backLabel ?? defaultBackLabel(backHref);
  const router = useRouter();
  const [quote, setQuote] = useState<DashboardQuoteItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [openWorks, setOpenWorks] = useState<Set<number>>(() => new Set());
  const [selectedWorks, setSelectedWorks] = useState<Set<number>>(() => new Set());
  const [showNotesModal, setShowNotesModal] = useState(false);
  const [combinedNotes, setCombinedNotes] = useState("");
  const [notesLoading, setNotesLoading] = useState(false);
  const [notesError, setNotesError] = useState<string | null>(null);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [downloadingClientPdf, setDownloadingClientPdf] = useState(false);
  const [downloadingOptimalPdf, setDownloadingOptimalPdf] = useState(false);
  const [downloadingFullEstimatePdf, setDownloadingFullEstimatePdf] = useState(false);
  const [downloadingAllTradesPdf, setDownloadingAllTradesPdf] = useState(false);
  const [combinedPdfError, setCombinedPdfError] = useState<string | null>(null);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const [refilling, setRefilling] = useState(false);
  const [refillError, setRefillError] = useState<string | null>(null);
  const [unlockMessage, setUnlockMessage] = useState<string | null>(null);
  const initializedOpenWorksSessionId = useRef<string | null>(null);

  const loadQuote = useCallback(async () => {
    setLoading(true);
    setError(null);
    setNotFound(false);
    try {
      const response = await client.fetchSubmittedQuotes();
      const match = response.quotes.find((item) => item.session_id === sessionId);
      if (!match) {
        setQuote(null);
        setNotFound(true);
        return;
      }
      setQuote(match);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load quote");
      setQuote(null);
    } finally {
      setLoading(false);
    }
  }, [client, sessionId]);

  useEffect(() => {
    void loadQuote();
  }, [loadQuote]);

  useEffect(() => {
    if (!quote) {
      initializedOpenWorksSessionId.current = null;
      setOpenWorks(new Set());
      return;
    }
    if (initializedOpenWorksSessionId.current === quote.session_id) {
      return;
    }
    initializedOpenWorksSessionId.current = quote.session_id;
    setOpenWorks(
      new Set(
        defaultOpenWorkIndexes(
          quote.works.map((work) => ({
            work_index: work.work_index,
            scope: work.scope ?? work.details?.scope ?? null,
          })),
        ),
      ),
    );
  }, [quote]);

  const handleCalculateNotes = async () => {
    if (!quote || selectedWorks.size === 0) return;
    setNotesLoading(true);
    setNotesError(null);
    try {
      const result = await client.fetchCombinedWorkNotes(
        quote.session_id,
        Array.from(selectedWorks).sort((a, b) => a - b),
      );
      setCombinedNotes(result.internal_notes);
      setShowNotesModal(true);
    } catch (err) {
      setNotesError(err instanceof Error ? err.message : "Failed to combine internal notes");
    } finally {
      setNotesLoading(false);
    }
  };

  const handleDownloadCombinedPdf = async (viewType: "client" | "optimal" | "all_trades") => {
    if (!quote || selectedWorks.size === 0) return;
    const setLoadingState =
      viewType === "client"
        ? setDownloadingClientPdf
        : viewType === "optimal"
          ? setDownloadingOptimalPdf
          : setDownloadingAllTradesPdf;
    setLoadingState(true);
    setCombinedPdfError(null);
    try {
      await client.downloadCombinedWorksPdf(
        quote.session_id,
        Array.from(selectedWorks).sort((a, b) => a - b),
        viewType,
        quote.quote_number,
      );
    } catch (err) {
      setCombinedPdfError(err instanceof Error ? err.message : "PDF download failed");
    } finally {
      setLoadingState(false);
    }
  };

  const handleDownloadFullEstimatePdf = async () => {
    if (!quote) return;
    setDownloadingFullEstimatePdf(true);
    setCombinedPdfError(null);
    try {
      if (client.mode === "role") {
        await downloadManagerQuotePdf(quote.session_id, "combined", quote.quote_number);
      } else {
        await downloadSessionPdf(quote.session_id, quote.session_token);
      }
    } catch (err) {
      setCombinedPdfError(err instanceof Error ? err.message : "PDF download failed");
    } finally {
      setDownloadingFullEstimatePdf(false);
    }
  };

  const toggleWork = (workIndex: number) => {
    setOpenWorks((prev) => {
      const next = new Set(prev);
      if (next.has(workIndex)) {
        next.delete(workIndex);
      } else {
        next.add(workIndex);
      }
      return next;
    });
  };

  const handleSelectWork = (workIndex: number, checked: boolean) => {
    setSelectedWorks((prev) => {
      const next = new Set(prev);
      if (checked) {
        next.add(workIndex);
      } else {
        next.delete(workIndex);
      }
      return next;
    });
  };

  const handleDownloadPdf = async () => {
    if (!quote) return;
    setDownloadingPdf(true);
    setPdfError(null);
    try {
      await downloadSessionPdf(quote.session_id, quote.session_token);
    } catch (err) {
      setPdfError(err instanceof Error ? err.message : "PDF download failed");
    } finally {
      setDownloadingPdf(false);
    }
  };

  const handleUnlockQuestionnaire = async () => {
    if (!quote) return;
    setRefilling(true);
    setRefillError(null);
    try {
      const reopened = await client.reopenQuoteForRefill(quote.session_id);
      if (onUnlockSuccess) {
        onUnlockSuccess(reopened, quote);
        return;
      }
      setUnlockMessage(`Quote ${quote.quote_number} is unlocked. Moving to dashboard.`);
      await new Promise((resolve) => window.setTimeout(resolve, 1500));
      const params = new URLSearchParams({
        unlocked: quote.quote_number,
        session_id: reopened.session_id,
        token: reopened.session_token,
      });
      router.push(`${listHref}?${params.toString()}`);
    } catch (err) {
      setUnlockMessage(null);
      setRefillError(err instanceof Error ? err.message : "Failed to unlock questionnaire");
    } finally {
      setRefilling(false);
    }
  };

  const content = (() => {
    if (unlockMessage) {
      return <LoadingState message={unlockMessage} />;
    }

    if (loading) {
      return <LoadingState message="Loading quote details…" />;
    }

    if (notFound) {
      return (
        <EmptyState
          title="Quote not found"
          description="The requested quote is not available or has been removed."
          action={<BackLink href={backHref} label={resolvedBackLabel} className="mb-0" />}
        />
      );
    }

    if (error || !quote) {
      return (
        <ErrorState
          message={error ?? "Failed to load quote"}
          onRetry={() => void loadQuote()}
        />
      );
    }

    return (
      <>
        <div className={cn("space-y-6", selectedWorks.size > 0 && "pb-20")}>
          {enableClientLink ? <ClientLinkPanel sessionId={quote.session_id} /> : null}
          {showClientAcceptance ? (
            <QuoteAcceptancePanel
              acceptance={normalizeQuoteAcceptance(quote.acceptance as Record<string, unknown> | undefined)}
              showEworksSync={enableClientLink}
              onRetryEworksSync={
                enableClientLink
                  ? async () => {
                      const sync = await retryEworksAcceptanceSync(quote.session_id);
                      setQuote((current) =>
                        current
                          ? {
                              ...current,
                              acceptance: {
                                ...(current.acceptance ?? { accepted: true, accepted_at: null, name: null }),
                                eworks_sync: sync,
                              },
                            }
                          : current,
                      );
                    }
                  : undefined
              }
            />
          ) : null}
          <SectionCard
            testId="quote-summary-card"
            title={formatQuoteSummaryTitle()}
            description={`Submitted ${formatSubmittedAt(quote.submitted_at)}`}
          >
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div className="space-y-1">
                <p className="text-sm text-slate-600">
                  Job {quote.job_number} · {quote.client_name}
                </p>
                {quote.trade_name ? (
                  <p className="text-sm text-slate-600" data-testid="quote-summary-trade">
                    Trade: {quote.trade_name}
                  </p>
                ) : null}
              </div>
              <div className="text-right">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Final total</p>
                <p className="text-2xl font-bold text-blue-700">
                  <MoneyText value={money(quote.final_total)} />
                </p>
              </div>
            </div>
            {pdfError ? <p className="mt-3 text-sm text-rose-600">{pdfError}</p> : null}
            {refillError ? <p className="mt-3 text-sm text-rose-600">{refillError}</p> : null}
            <QuoteSummaryBreakdown quote={quote} />
          </SectionCard>

          <div className="space-y-3">
            <EworksSectionTitle title="Works" />
            <p className="text-sm text-optimal-muted">Select works for combined notes.</p>
            {notesError && <p className="text-sm text-red-600">{notesError}</p>}
            {quote.works.map((work) => (
              <WorkSection
                key={work.work_index}
                work={work}
                quote={quote}
                open={openWorks.has(work.work_index)}
                onToggle={() => toggleWork(work.work_index)}
                selectable
                selected={selectedWorks.has(work.work_index)}
                onSelect={(checked) => handleSelectWork(work.work_index, checked)}
              />
            ))}
          </div>

          <QuoteAdditionalChargesSection lines={quote.additional_charges ?? []} />

          {quote.internal_notes ? (
            <SectionCard title="Internal notes (combined)">
              <pre className="whitespace-pre-wrap rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs leading-relaxed text-slate-800">
                {quote.internal_notes}
              </pre>
            </SectionCard>
          ) : null}
        </div>

        {selectedWorks.size > 0 && (
          <WorkSelectionBar
            selectedCount={selectedWorks.size}
            onCalculate={() => void handleCalculateNotes()}
            onClear={() => setSelectedWorks(new Set())}
            calculating={notesLoading}
          />
        )}

        {showNotesModal && (
          <CombinedNotesModal
            notesText={combinedNotes}
            title="Combined internal notes"
            onClose={() => setShowNotesModal(false)}
            onDownloadClient={() => handleDownloadCombinedPdf("client")}
            onDownloadOptimal={() => handleDownloadCombinedPdf("optimal")}
            onDownloadFullEstimate={() => void handleDownloadFullEstimatePdf()}
            onDownloadAllTrades={() => handleDownloadCombinedPdf("all_trades")}
            downloadingClient={downloadingClientPdf}
            downloadingOptimal={downloadingOptimalPdf}
            downloadingFullEstimate={downloadingFullEstimatePdf}
            downloadingAllTrades={downloadingAllTradesPdf}
            pdfError={combinedPdfError}
          />
        )}
      </>
    );
  })();

  const actionButtons =
    quote && !loading && !notFound && !error && !unlockMessage ? (
      <div className="flex flex-wrap items-center gap-2">
        <PrimaryButton disabled={refilling} onClick={() => void handleUnlockQuestionnaire()}>
          {refilling ? "Unlocking…" : "Unlock Estimating Questionnaire"}
        </PrimaryButton>
        <SecondaryButton disabled={downloadingPdf} onClick={() => void handleDownloadPdf()}>
          {downloadingPdf ? "Generating PDF…" : "Download PDF"}
        </SecondaryButton>
      </div>
    ) : null;

  const footer =
    quote && !loading && !notFound && !error && !unlockMessage && actionButtons ? (
      <div className="flex flex-wrap items-center justify-end gap-3">{actionButtons}</div>
    ) : undefined;

  const title =
    unlockMessage
      ? "Unlocking questionnaire"
      : loading
        ? "Quote details"
        : notFound
          ? "Quote not found"
          : error || !quote
            ? "Quote details"
            : `Quote ${quote.quote_number}`;

  const subtitle =
    unlockMessage ??
    (loading
      ? "Loading quote…"
      : notFound
        ? "This quote could not be found"
        : error || !quote
          ? "Unable to load quote"
          : `Job ${quote.job_number} · ${quote.client_name}`);

  if (shell === "embedded") {
    return (
      <div className="space-y-6" data-testid="manager-quote-review-detail">
        <PageHeader
          backHref={backHref}
          backLabel={resolvedBackLabel}
          title={title}
          subtitle={subtitle}
          actions={actionButtons ?? undefined}
        />
        {content}
      </div>
    );
  }

  return (
    <DashboardPageShell
      title={title}
      subtitle={subtitle}
      footer={footer}
      backLink={<BackLink href={backHref} label={resolvedBackLabel} />}
    >
      {content}
    </DashboardPageShell>
  );
}
