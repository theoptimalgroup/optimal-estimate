"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  CombinedNotesModal,
  formatSubmittedAt,
  money,
  WorkSection,
  WorkSelectionBar,
} from "@/components/eworks-dashboard";
import { ClientLinkPanel } from "@/components/dashboard/client-link-panel";
import { QuoteAcceptancePanel } from "@/components/quote-acceptance-panel";
import { retryEworksAcceptanceSync } from "@/lib/client-quotes";
import { normalizeQuoteAcceptance } from "@/lib/quote-acceptance";
import {
  EworksButton,
  DashboardPageShell,
  EworksLoadingScreen,
  EworksSectionTitle,
  cn,
} from "@/components/eworks-ui";
import type { DashboardClient } from "@/lib/dashboard-client";
import type { DashboardQuoteItem, ReopenQuoteResponse } from "@/lib/dashboard";
import { downloadSessionPdf } from "@/lib/eworks-session";

type QuoteReviewDetailProps = {
  sessionId: string;
  client: DashboardClient;
  backHref: string;
  listHref: string;
  onUnlockSuccess?: (reopened: ReopenQuoteResponse, quote: DashboardQuoteItem) => void;
  shell?: "dashboard" | "embedded";
  enableClientLink?: boolean;
};

export function QuoteReviewDetail({
  sessionId,
  client,
  backHref,
  listHref,
  onUnlockSuccess,
  shell = "dashboard",
  enableClientLink = false,
}: QuoteReviewDetailProps) {
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
  const [combinedPdfError, setCombinedPdfError] = useState<string | null>(null);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const [refilling, setRefilling] = useState(false);
  const [refillError, setRefillError] = useState<string | null>(null);
  const [unlockMessage, setUnlockMessage] = useState<string | null>(null);

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

  const handleDownloadCombinedPdf = async (viewType: "client" | "optimal") => {
    if (!quote || selectedWorks.size === 0) return;
    const setLoadingState = viewType === "client" ? setDownloadingClientPdf : setDownloadingOptimalPdf;
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
      return <EworksLoadingScreen message={unlockMessage} />;
    }

    if (loading) {
      return <EworksLoadingScreen message="Loading quote details…" />;
    }

    if (notFound) {
      return (
        <div className="space-y-4 rounded-lg border border-gray-200 bg-optimal-elevated p-6 text-center">
          <p className="text-sm text-optimal-muted">The requested quote is not available or has been removed.</p>
          <Link href={backHref}>
            <EworksButton variant="secondary">Back to quotes</EworksButton>
          </Link>
        </div>
      );
    }

    if (error || !quote) {
      return (
        <div className="space-y-4 rounded-lg border border-gray-200 bg-optimal-elevated p-6 text-center">
          <p className="text-sm text-red-600">{error ?? "Failed to load quote"}</p>
          <Link href={backHref}>
            <EworksButton variant="secondary">Back to quotes</EworksButton>
          </Link>
        </div>
      );
    }

    return (
      <>
        <div className={cn("space-y-6", selectedWorks.size > 0 && "pb-20")}>
          {enableClientLink ? <ClientLinkPanel sessionId={quote.session_id} /> : null}
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
          <section className="rounded-lg border border-gray-200 bg-optimal-elevated p-5 lg:p-6">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-1">
                <p className="text-sm text-optimal-muted">{quote.trade_name}</p>
                <p className="text-xs text-optimal-muted">Submitted {formatSubmittedAt(quote.submitted_at)}</p>
              </div>
              <div className="text-right">
                <p className="text-xs uppercase tracking-wide text-optimal-muted">Final total</p>
                <p className="text-2xl font-bold text-optimal-orange">{money(quote.final_total)}</p>
              </div>
            </div>
            {pdfError && <p className="mt-3 text-sm text-red-600">{pdfError}</p>}
            {refillError && <p className="mt-3 text-sm text-red-600">{refillError}</p>}
          </section>

          <div className="space-y-3">
            <EworksSectionTitle title="Works" />
            <p className="text-sm text-optimal-muted">Select works to combine internal notes.</p>
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

          {quote.internal_notes && (
            <section className="rounded-lg border border-gray-200 bg-gray-50 p-4">
              <EworksSectionTitle title="Internal notes (combined)" />
              <pre className="mt-3 whitespace-pre-wrap rounded-lg bg-optimal-field p-3 text-xs leading-relaxed text-optimal-field-text">
                {quote.internal_notes}
              </pre>
            </section>
          )}
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
            downloadingClient={downloadingClientPdf}
            downloadingOptimal={downloadingOptimalPdf}
            pdfError={combinedPdfError}
          />
        )}
      </>
    );
  })();

  const actionButtons =
    quote && !loading && !notFound && !error && !unlockMessage ? (
      <div className="flex flex-wrap items-center gap-2">
        <EworksButton disabled={refilling} onClick={() => void handleUnlockQuestionnaire()}>
          {refilling ? "Unlocking…" : "Unlock Estimating Questionnaire"}
        </EworksButton>
        <EworksButton variant="secondary" disabled={downloadingPdf} onClick={() => void handleDownloadPdf()}>
          {downloadingPdf ? "Generating PDF…" : "Download PDF"}
        </EworksButton>
      </div>
    ) : null;

  const footer =
    quote && !loading && !notFound && !error && !unlockMessage ? (
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link href={backHref}>
          <EworksButton variant="secondary">Back to quotes</EworksButton>
        </Link>
        {actionButtons}
      </div>
    ) : undefined;

  if (shell === "embedded") {
    return (
      <div className="space-y-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <Link
              href={backHref}
              className="text-sm text-optimal-muted underline-offset-2 hover:text-gray-900 hover:underline"
            >
              ← Back to quotes
            </Link>
            {quote && !loading && !notFound && !error && (
              <h1 className="mt-2 text-2xl font-semibold text-gray-900">Quote {quote.quote_number}</h1>
            )}
            {quote && (
              <p className="mt-1 text-sm text-gray-600">
                Job {quote.job_number} · {quote.client_name}
              </p>
            )}
          </div>
          {actionButtons}
        </div>
        {content}
      </div>
    );
  }

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

  return (
    <DashboardPageShell title={title} subtitle={subtitle} footer={footer}>
      {content}
    </DashboardPageShell>
  );
}
