"use client";

import { useCallback, useEffect, useState } from "react";

import { EstimatorQuotesTable } from "@/components/estimator/estimator-quotes-table";
import { EworksButton, EworksLoadingScreen } from "@/components/eworks-ui";
import { listEstimatorApprovals, type EstimatorQuoteRow } from "@/lib/estimator";

export default function EstimatorApprovalsPage() {
  const [quotes, setQuotes] = useState<EstimatorQuoteRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadApprovals = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listEstimatorApprovals();
      setQuotes(result.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load approvals");
      setQuotes([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadApprovals();
  }, [loadApprovals]);

  return (
    <div className="space-y-6" data-testid="estimator-approvals-page">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Submitted for Review</h1>
          <p className="mt-2 text-sm text-gray-600">
            Read-only view of quotes submitted to the manager review queue. Estimators cannot approve or reject quotes here.
          </p>
        </div>
        <EworksButton type="button" onClick={() => void loadApprovals()} disabled={loading}>
          Refresh
        </EworksButton>
      </div>

      {loading ? (
        <EworksLoadingScreen message="Loading submitted quotes…" />
      ) : error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      ) : (
        <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <EstimatorQuotesTable quotes={quotes} showSubmitted testId="estimator-approvals-table" />
        </div>
      )}
    </div>
  );
}
