"use client";

import { useCallback, useEffect, useState } from "react";

import { SubmittedQuoteGroupsList } from "@/components/dashboard/submitted-quote-groups-list";
import { ErrorState, PageHeader, SecondaryButton } from "@/components/ui";
import type { DashboardQuoteGroupItem } from "@/lib/dashboard";
import { fetchSubmittedQuoteGroups } from "@/lib/dashboard-auth";

export default function ManagerReviewPage() {
  const [groups, setGroups] = useState<DashboardQuoteGroupItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadGroups = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchSubmittedQuoteGroups();
      setGroups(response.groups);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load quotes");
      setGroups([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadGroups();
  }, [loadGroups]);

  return (
    <div className="space-y-6" data-testid="manager-review-page">
      <PageHeader
        title="Approvals & Quotes"
        actions={
          <SecondaryButton onClick={() => void loadGroups()} disabled={loading}>
            Refresh
          </SecondaryButton>
        }
      />
      {error ? (
        <ErrorState message={error} onRetry={() => void loadGroups()} />
      ) : (
        <SubmittedQuoteGroupsList groups={groups} loading={loading} error={null} />
      )}
    </div>
  );
}
