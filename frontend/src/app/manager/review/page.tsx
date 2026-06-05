"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { SubmittedQuotesList } from "@/components/dashboard/submitted-quotes-list";
import { ErrorState, LoadingState, PageHeader, SecondaryButton } from "@/components/ui";
import { createRoleDashboardClient } from "@/lib/dashboard-client";
import type { DashboardQuoteItem } from "@/lib/dashboard";

export default function ManagerReviewPage() {
  const client = useMemo(() => createRoleDashboardClient(), []);
  const [quotes, setQuotes] = useState<DashboardQuoteItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadQuotes = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await client.fetchSubmittedQuotes();
      setQuotes(response.quotes);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load quotes");
      setQuotes([]);
    } finally {
      setLoading(false);
    }
  }, [client]);

  useEffect(() => {
    void loadQuotes();
  }, [loadQuotes]);

  return (
    <div className="space-y-6" data-testid="manager-review-page">
      <PageHeader
        title="Approvals & Quotes"
        description="Review submitted estimates, reopen questionnaires, and download combined PDFs."
        actions={
          <SecondaryButton onClick={() => void loadQuotes()} disabled={loading}>
            Refresh
          </SecondaryButton>
        }
      />
      {loading ? (
        <LoadingState message="Loading submitted quotes…" />
      ) : error ? (
        <ErrorState message={error} onRetry={() => void loadQuotes()} />
      ) : (
        <SubmittedQuotesList quotes={quotes} detailHref={(sessionId) => `/manager/review/${sessionId}`} />
      )}
    </div>
  );
}
