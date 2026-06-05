"use client";

import { useCallback, useEffect, useState } from "react";

import { EstimatorQuotesTable } from "@/components/estimator/estimator-quotes-table";
import {
  ErrorState,
  LoadingState,
  PageHeader,
  SecondaryButton,
  SectionCard,
} from "@/components/ui";
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
      <PageHeader
        title="Submitted for Review"
        description="Read-only view of quotes submitted to the manager review queue. Estimators cannot approve or reject quotes here."
        actions={
          <SecondaryButton onClick={() => void loadApprovals()} disabled={loading}>
            Refresh
          </SecondaryButton>
        }
      />

      {loading ? (
        <LoadingState message="Loading submitted quotes…" />
      ) : error ? (
        <ErrorState message={error} onRetry={() => void loadApprovals()} />
      ) : (
        <SectionCard>
          <EstimatorQuotesTable quotes={quotes} showSubmitted testId="estimator-approvals-table" />
        </SectionCard>
      )}
    </div>
  );
}
