"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { EstimatorQuotesTable } from "@/components/estimator/estimator-quotes-table";
import { AssignmentEstimateButton } from "@/components/quote-assignment-estimate-button";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  MoneyText,
  PageHeader,
  PrimaryButton,
  SecondaryButton,
  SectionCard,
  StatCard,
} from "@/components/ui";
import { formatMoney, getEstimatorDashboard, type EstimatorDashboard } from "@/lib/estimator";
import { listMyQuoteAssignments, type QuoteAssignment } from "@/lib/quote-assignments";

export default function EstimatorDashboardPage() {
  const [dashboard, setDashboard] = useState<EstimatorDashboard | null>(null);
  const [assignedQuotes, setAssignedQuotes] = useState<QuoteAssignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [dashboardData, assignments] = await Promise.all([
        getEstimatorDashboard(),
        listMyQuoteAssignments(),
      ]);
      setDashboard(dashboardData);
      setAssignedQuotes(assignments.filter((item) => item.assignment_type === "estimator"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
      setDashboard(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  return (
    <div className="space-y-6" data-testid="estimator-dashboard-page">
      <PageHeader
        title="Estimator Dashboard"
        description="Create and track estimates before manager review"
        actions={
          <>
            <Link href="/eworks/calculate">
              <PrimaryButton data-testid="new-estimate-button">New Estimate</PrimaryButton>
            </Link>
            <SecondaryButton onClick={() => void loadDashboard()} disabled={loading}>
              Refresh
            </SecondaryButton>
          </>
        }
      />

      {loading ? (
        <LoadingState message="Loading dashboard…" />
      ) : error ? (
        <ErrorState message={error} onRetry={() => void loadDashboard()} />
      ) : dashboard ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3" data-testid="estimator-kpi-cards">
            <div data-testid="kpi-in-progress">
              <StatCard label="In-progress" value={dashboard.kpis.draft_count} />
            </div>
            <div data-testid="kpi-submitted">
              <StatCard label="Submitted" value={dashboard.kpis.submitted_count} />
            </div>
            <div data-testid="kpi-needs-changes">
              <StatCard label="Needs Changes" value={dashboard.kpis.reopened_count} />
            </div>
            <div data-testid="kpi-accepted">
              <StatCard label="Accepted" value={dashboard.kpis.accepted_count ?? 0} />
            </div>
            <div data-testid="kpi-total-submitted-value">
              <StatCard
                label="Total Submitted Value"
                value={<MoneyText value={formatMoney(dashboard.kpis.total_submitted_value)} />}
              />
            </div>
            <div data-testid="kpi-average-quote-value">
              <StatCard
                label="Average Quote Value"
                value={<MoneyText value={formatMoney(dashboard.kpis.average_quote_value)} />}
              />
            </div>
          </div>

          <SectionCard title="Assigned Quotes" testId="estimator-assigned-quotes">
            {assignedQuotes.length === 0 ? (
              <EmptyState
                title="No assigned quotes"
                description="Quotes assigned to you by a manager will appear here."
                className="border-0 bg-transparent py-6"
              />
            ) : (
              <ul className="divide-y divide-slate-100">
                {assignedQuotes.map((item) => (
                  <li
                    key={item.id}
                    className="flex items-center justify-between gap-4 py-3 text-sm first:pt-0 last:pb-0"
                    data-testid={`assigned-quote-${item.id}`}
                  >
                    <div>
                      <span className="font-medium text-slate-900">{item.quote_ref ?? item.eworks_quote_id}</span>
                      <span className="ml-2 text-slate-600">
                        {item.quote_summary?.customer_name ?? "Customer not available"}
                      </span>
                    </div>
                    <AssignmentEstimateButton
                      assignment={item}
                      variant="link"
                      testId={`start-assignment-${item.id}`}
                    />
                  </li>
                ))}
              </ul>
            )}
          </SectionCard>

          <SectionCard title="Recent Quotes">
            <EstimatorQuotesTable quotes={dashboard.recent_quotes} testId="estimator-recent-quotes" />
          </SectionCard>

          <div data-testid="estimator-needs-attention">
            <SectionCard title="Needs Attention">
            {dashboard.needs_attention.length === 0 ? (
              <EmptyState
                title="All caught up"
                description="No quotes need attention right now."
                className="border-0 bg-transparent py-6"
              />
            ) : (
              <ul className="divide-y divide-slate-100">
                {dashboard.needs_attention.map((item) => (
                  <li
                    key={`${item.session_id}-${item.reason}`}
                    className="flex items-center justify-between gap-4 py-3 text-sm first:pt-0 last:pb-0"
                  >
                    <div>
                      <span className="font-medium text-slate-900">{item.quote_ref}</span>
                      <span className="ml-2 text-slate-600">{item.reason}</span>
                    </div>
                    <Link
                      href={`/estimator/quotes/${item.session_id}`}
                      className="shrink-0 text-sm font-medium text-blue-600 hover:text-blue-700"
                    >
                      Open
                    </Link>
                  </li>
                ))}
              </ul>
            )}
            </SectionCard>
          </div>
        </>
      ) : (
        <EmptyState title="No dashboard data" description="No dashboard data available." />
      )}
    </div>
  );
}
