"use client";

import { useState } from "react";

import {
  DateText,
  SecondaryButton,
  SectionCard,
  StatusBadge,
  syncStatusTone,
} from "@/components/ui";
import { QuoteAcceptanceBadge } from "@/components/quote-acceptance-badge";
import { formatQuoteDate } from "@/lib/client-quotes";
import {
  canRetryEworksSync,
  eworksSyncLabel,
  type QuoteAcceptanceStatus,
} from "@/lib/quote-acceptance";

function EworksSyncBadge({ status }: { status: string | null | undefined }) {
  return (
    <span data-testid="eworks-sync-badge">
      <StatusBadge tone={syncStatusTone(status ?? "skipped")}>{eworksSyncLabel(status)}</StatusBadge>
    </span>
  );
}

type QuoteAcceptancePanelProps = {
  acceptance: QuoteAcceptanceStatus;
  showEworksSync?: boolean;
  onRetryEworksSync?: () => Promise<void>;
};

export function QuoteAcceptancePanel({
  acceptance,
  showEworksSync = false,
  onRetryEworksSync,
}: QuoteAcceptancePanelProps) {
  const [retrying, setRetrying] = useState(false);
  const [retryError, setRetryError] = useState<string | null>(null);

  const handleRetry = async () => {
    if (!onRetryEworksSync) return;
    setRetrying(true);
    setRetryError(null);
    try {
      await onRetryEworksSync();
    } catch (err) {
      setRetryError(err instanceof Error ? err.message : "Failed to retry eWorks sync");
    } finally {
      setRetrying(false);
    }
  };

  return (
    <div data-testid="quote-acceptance-panel">
      <SectionCard
        title="Client acceptance"
        description="Status of the client-facing quote acceptance."
        actions={<QuoteAcceptanceBadge accepted={acceptance.accepted} />}
      >
        {acceptance.accepted ? (
          <dl className="grid gap-3 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-slate-500">Accepted at</dt>
              <dd className="mt-0.5 font-medium text-slate-900">
                {acceptance.accepted_at ? (
                  <DateText value={acceptance.accepted_at} includeTime />
                ) : (
                  formatQuoteDate(acceptance.accepted_at)
                )}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Accepted by</dt>
              <dd className="mt-0.5 font-medium text-slate-900">{acceptance.name || "—"}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Email</dt>
              <dd className="mt-0.5 font-medium text-slate-900">{acceptance.email || "—"}</dd>
            </div>
            {acceptance.notes ? (
              <div className="sm:col-span-2">
                <dt className="text-slate-500">Notes</dt>
                <dd className="mt-1 whitespace-pre-wrap text-slate-900">{acceptance.notes}</dd>
              </div>
            ) : null}
          </dl>
        ) : (
          <p className="text-sm text-slate-600">The client has not accepted this quote yet.</p>
        )}

        {showEworksSync && acceptance.accepted ? (
          <div className="mt-5 border-t border-slate-100 pt-4" data-testid="eworks-sync-panel">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-slate-900">eWorks sync</h3>
                <p className="mt-1 text-sm text-slate-600">Acceptance note sync to eWorks custom field.</p>
              </div>
              <EworksSyncBadge status={acceptance.eworks_sync?.status} />
            </div>
            {acceptance.eworks_sync?.synced_at ? (
              <p className="mt-3 text-sm text-slate-700">
                Last synced: <DateText value={acceptance.eworks_sync.synced_at} includeTime />
              </p>
            ) : null}
            {acceptance.eworks_sync?.error ? (
              <p className="mt-3 text-sm text-rose-700" data-testid="eworks-sync-error">
                {acceptance.eworks_sync.error}
              </p>
            ) : null}
            {canRetryEworksSync(acceptance) && onRetryEworksSync ? (
              <div className="mt-4">
                <SecondaryButton
                  disabled={retrying}
                  onClick={() => void handleRetry()}
                  data-testid="eworks-sync-retry-button"
                >
                  {retrying ? "Retrying…" : "Retry Sync"}
                </SecondaryButton>
                {retryError ? <p className="mt-2 text-sm text-rose-600">{retryError}</p> : null}
              </div>
            ) : null}
          </div>
        ) : null}
      </SectionCard>
    </div>
  );
}

export function QuoteAcceptanceSummary({ acceptance }: { acceptance: QuoteAcceptanceStatus }) {
  if (!acceptance.accepted) return null;
  return (
    <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
      Accepted by {acceptance.name || "client"} on {formatQuoteDate(acceptance.accepted_at)}.
    </div>
  );
}
