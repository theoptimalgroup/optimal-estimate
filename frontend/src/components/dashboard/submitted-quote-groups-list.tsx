"use client";

import { EmptyState, ErrorState, LoadingState } from "@/components/ui";
import { QuoteGroupsTable } from "@/components/dashboard/quote-groups-table";
import type { DashboardQuoteGroupItem } from "@/lib/dashboard";

type SubmittedQuoteGroupsListProps = {
  groups: DashboardQuoteGroupItem[];
  loading?: boolean;
  error?: string | null;
  groupHref?: (group: DashboardQuoteGroupItem) => string;
};

export function SubmittedQuoteGroupsList({
  groups,
  loading,
  error,
  groupHref,
}: SubmittedQuoteGroupsListProps) {
  if (loading) {
    return <LoadingState message="Loading submitted quotes…" />;
  }

  if (error) {
    return <ErrorState message={error} />;
  }

  if (groups.length === 0) {
    return (
      <EmptyState
        title="No submitted quotes"
        description="No submitted quotes yet."
      />
    );
  }

  return <QuoteGroupsTable groups={groups} groupHref={groupHref} />;
}
