"use client";

import { useState } from "react";

import { EworksButton } from "@/components/eworks-ui";
import { QuoteAcceptanceBadge } from "@/components/quote-acceptance-badge";
import { formatQuoteDate } from "@/lib/client-quotes";
import {
  canRetryEworksSync,
  eworksSyncLabel,
  type QuoteAcceptanceStatus,
} from "@/lib/quote-acceptance";

type QuoteAcceptancePanelProps = {
  acceptance: QuoteAcceptanceStatus;
  showEworksSync?: boolean;
  onRetryEworksSync?: () => Promise<void>;
};

function EworksSyncBadge({ status }: { status: string | null | undefined }) {
  const tone =
    status === "success"
      ? "bg-emerald-100 text-emerald-800"
      : status === "failed"
        ? "bg-red-100 text-red-800"
        : status === "pending"
          ? "bg-amber-100 text-amber-800"
          : "bg-slate-100 text-slate-700";
  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${tone}`}
      data-testid="eworks-sync-badge"
    >
      {eworksSyncLabel(status)}
    </span>
  );
}

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
    <section className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm" data-testid="quote-acceptance-panel">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-gray-900">Client acceptance</h2>
          <p className="mt-1 text-sm text-gray-600">Status of the client-facing quote acceptance.</p>
        </div>
        <QuoteAcceptanceBadge accepted={acceptance.accepted} />
      </div>
      {acceptance.accepted ? (
        <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-gray-500">Accepted at</dt>
            <dd className="font-medium text-gray-900">{formatQuoteDate(acceptance.accepted_at)}</dd>
          </div>
          <div>
            <dt className="text-gray-500">Accepted by</dt>
            <dd className="font-medium text-gray-900">{acceptance.name || "—"}</dd>
          </div>
          <div>
            <dt className="text-gray-500">Email</dt>
            <dd className="font-medium text-gray-900">{acceptance.email || "—"}</dd>
          </div>
          {acceptance.notes ? (
            <div className="sm:col-span-2">
              <dt className="text-gray-500">Notes</dt>
              <dd className="mt-1 whitespace-pre-wrap text-gray-900">{acceptance.notes}</dd>
            </div>
          ) : null}
        </dl>
      ) : (
        <p className="mt-4 text-sm text-gray-600">The client has not accepted this quote yet.</p>
      )}

      {showEworksSync && acceptance.accepted ? (
        <div className="mt-5 border-t border-gray-100 pt-4" data-testid="eworks-sync-panel">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold text-gray-900">eWorks sync</h3>
              <p className="mt-1 text-sm text-gray-600">Acceptance note sync to eWorks custom field.</p>
            </div>
            <EworksSyncBadge status={acceptance.eworks_sync?.status} />
          </div>
          {acceptance.eworks_sync?.synced_at ? (
            <p className="mt-3 text-sm text-gray-700">
              Last synced: {formatQuoteDate(acceptance.eworks_sync.synced_at)}
            </p>
          ) : null}
          {acceptance.eworks_sync?.error ? (
            <p className="mt-3 text-sm text-red-700" data-testid="eworks-sync-error">
              {acceptance.eworks_sync.error}
            </p>
          ) : null}
          {canRetryEworksSync(acceptance) && onRetryEworksSync ? (
            <div className="mt-4">
              <EworksButton
                type="button"
                variant="secondary"
                disabled={retrying}
                onClick={() => void handleRetry()}
                data-testid="eworks-sync-retry-button"
              >
                {retrying ? "Retrying…" : "Retry Sync"}
              </EworksButton>
              {retryError ? <p className="mt-2 text-sm text-red-600">{retryError}</p> : null}
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

export function QuoteAcceptanceSummary({ acceptance }: { acceptance: QuoteAcceptanceStatus }) {
  if (!acceptance.accepted) return null;
  return (
    <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
      Accepted by {acceptance.name || "client"} on {formatQuoteDate(acceptance.accepted_at)}.
    </div>
  );
}
