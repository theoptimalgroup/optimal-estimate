"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  EworksButton,
  DashboardPageShell,
  EworksLoadingScreen,
  EworksSectionTitle,
  cn,
} from "@/components/eworks-ui";
import {
  CombinedNotesModal,
  formatSubmittedAt,
  money,
  WorkSection,
  WorkSelectionBar,
} from "@/components/eworks-dashboard";
import {
  downloadCombinedWorksPdf,
  fetchCombinedWorkNotes,
  fetchSubmittedQuotes,
  readDashboardPassword,
  reopenQuoteForRefill,
  type DashboardQuoteItem,
} from "@/lib/dashboard";
import { downloadSessionPdf } from "@/lib/eworks-session";

export default function EworksDashboardQuotePage({
  params,
}: {
  params: { sessionId: string };
}) {
  const { sessionId } = params;
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
    const password = readDashboardPassword();
    if (!password) {
      router.replace("/eworks/dashboard");
      return;
    }

    setLoading(true);
    setError(null);
    setNotFound(false);
    try {
      const response = await fetchSubmittedQuotes(password);
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
  }, [router, sessionId]);

  useEffect(() => {
    void loadQuote();
  }, [loadQuote]);

  const handleCalculateNotes = async () => {
    if (!quote || selectedWorks.size === 0) return;
    const password = readDashboardPassword();
    if (!password) {
      router.replace("/eworks/dashboard");
      return;
    }
    setNotesLoading(true);
    setNotesError(null);
    try {
      const result = await fetchCombinedWorkNotes(
        password,
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
    const password = readDashboardPassword();
    if (!password) {
      router.replace("/eworks/dashboard");
      return;
    }
    const setLoading = viewType === "client" ? setDownloadingClientPdf : setDownloadingOptimalPdf;
    setLoading(true);
    setCombinedPdfError(null);
    try {
      await downloadCombinedWorksPdf(
        password,
        quote.session_id,
        Array.from(selectedWorks).sort((a, b) => a - b),
        viewType,
        quote.quote_number,
      );
    } catch (err) {
      setCombinedPdfError(err instanceof Error ? err.message : "PDF download failed");
    } finally {
      setLoading(false);
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
    const password = readDashboardPassword();
    if (!password) {
      router.replace("/eworks/dashboard");
      return;
    }
    setRefilling(true);
    setRefillError(null);
    try {
      const reopened = await reopenQuoteForRefill(password, quote.session_id);
      setUnlockMessage(`Quote ${quote.quote_number} is unlocked. Moving to dashboard.`);
      await new Promise((resolve) => window.setTimeout(resolve, 1500));
      const params = new URLSearchParams({
        unlocked: quote.quote_number,
        session_id: reopened.session_id,
        token: reopened.session_token,
      });
      router.push(`/eworks/dashboard?${params.toString()}`);
    } catch (err) {
      setUnlockMessage(null);
      setRefillError(err instanceof Error ? err.message : "Failed to unlock questionnaire");
    } finally {
      setRefilling(false);
    }
  };

  if (unlockMessage) {
    return (
      <DashboardPageShell title="Unlocking questionnaire" subtitle={unlockMessage}>
        <EworksLoadingScreen message={unlockMessage} />
      </DashboardPageShell>
    );
  }

  if (loading) {
    return (
      <DashboardPageShell title="Quote details" subtitle="Loading quote…">
        <EworksLoadingScreen message="Loading quote details…" />
      </DashboardPageShell>
    );
  }

  if (notFound) {
    return (
      <DashboardPageShell title="Quote not found" subtitle="This quote could not be found">
        <div className="space-y-4 rounded-lg border border-gray-200 bg-optimal-elevated p-6 text-center">
          <p className="text-sm text-optimal-muted">The requested quote is not available or has been removed.</p>
          <Link href="/eworks/dashboard">
            <EworksButton variant="secondary">Back to quotes</EworksButton>
          </Link>
        </div>
      </DashboardPageShell>
    );
  }

  if (error || !quote) {
    return (
      <DashboardPageShell title="Quote details" subtitle="Unable to load quote">
        <div className="space-y-4 rounded-lg border border-gray-200 bg-optimal-elevated p-6 text-center">
          <p className="text-sm text-red-600">{error ?? "Failed to load quote"}</p>
          <Link href="/eworks/dashboard">
            <EworksButton variant="secondary">Back to quotes</EworksButton>
          </Link>
        </div>
      </DashboardPageShell>
    );
  }

  return (
    <>
      <DashboardPageShell
        title={`Quote ${quote.quote_number}`}
        subtitle={`Job ${quote.job_number} · ${quote.client_name}`}
        footer={
          <div className="flex flex-wrap items-center justify-between gap-3">
            <Link href="/eworks/dashboard">
              <EworksButton variant="secondary">Back to quotes</EworksButton>
            </Link>
            <div className="flex flex-wrap items-center gap-2">
              <EworksButton disabled={refilling} onClick={() => void handleUnlockQuestionnaire()}>
                {refilling ? "Unlocking…" : "Unlock Estimating Questionnaire"}
              </EworksButton>
              <EworksButton variant="secondary" disabled={downloadingPdf} onClick={() => void handleDownloadPdf()}>
                {downloadingPdf ? "Generating PDF…" : "Download PDF"}
              </EworksButton>
            </div>
          </div>
        }
      >
        <div className={cn("space-y-6", selectedWorks.size > 0 && "pb-20")}>
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
      </DashboardPageShell>

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
}
