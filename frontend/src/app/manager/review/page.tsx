"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { SubmittedQuotesList } from "@/components/dashboard/submitted-quotes-list";
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
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Approvals & Quotes</h1>
        <p className="mt-2 text-sm text-gray-600">
          Review submitted estimates, reopen questionnaires, and download combined PDFs.
        </p>
      </div>
      <SubmittedQuotesList
        quotes={quotes}
        loading={loading}
        error={error}
        detailHref={(sessionId) => `/manager/review/${sessionId}`}
      />
    </div>
  );
}
