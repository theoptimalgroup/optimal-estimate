"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { EstimatorKpiCard, EstimatorQuotesTable } from "@/components/estimator/estimator-quotes-table";
import { EworksButton, EworksLoadingScreen } from "@/components/eworks-ui";
import { formatMoney, getEstimatorDashboard, type EstimatorDashboard } from "@/lib/estimator";

export default function EstimatorDashboardPage() {
  const [dashboard, setDashboard] = useState<EstimatorDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setDashboard(await getEstimatorDashboard());
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
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Estimator Dashboard</h1>
          <p className="mt-2 text-sm text-gray-600">Create and track estimates before manager review</p>
        </div>
        <div className="flex gap-2">
          <Link href="/eworks/calculate">
            <EworksButton type="button" data-testid="new-estimate-button">
              New Estimate
            </EworksButton>
          </Link>
          <EworksButton type="button" onClick={() => void loadDashboard()} disabled={loading}>
            Refresh
          </EworksButton>
        </div>
      </div>

      {loading ? (
        <EworksLoadingScreen message="Loading dashboard…" />
      ) : error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      ) : dashboard ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5" data-testid="estimator-kpi-cards">
            <EstimatorKpiCard label="In-progress" value={String(dashboard.kpis.draft_count)} />
            <EstimatorKpiCard label="Submitted" value={String(dashboard.kpis.submitted_count)} />
            <EstimatorKpiCard label="Needs Changes" value={String(dashboard.kpis.reopened_count)} />
            <EstimatorKpiCard label="Accepted" value={String(dashboard.kpis.accepted_count ?? 0)} />
            <EstimatorKpiCard label="Total Submitted Value" value={formatMoney(dashboard.kpis.total_submitted_value)} />
            <EstimatorKpiCard label="Average Quote Value" value={formatMoney(dashboard.kpis.average_quote_value)} />
          </div>

          <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
            <div className="border-b border-gray-200 px-5 py-4">
              <h2 className="text-base font-semibold text-gray-900">Recent Quotes</h2>
            </div>
            <div className="p-5">
              <EstimatorQuotesTable quotes={dashboard.recent_quotes} testId="estimator-recent-quotes" />
            </div>
          </div>

          <div className="rounded-lg border border-gray-200 bg-white shadow-sm" data-testid="estimator-needs-attention">
            <div className="border-b border-gray-200 px-5 py-4">
              <h2 className="text-base font-semibold text-gray-900">Needs Attention</h2>
            </div>
            {dashboard.needs_attention.length === 0 ? (
              <p className="px-5 py-8 text-sm text-gray-500">No quotes need attention right now.</p>
            ) : (
              <ul className="divide-y divide-gray-100">
                {dashboard.needs_attention.map((item) => (
                  <li key={`${item.session_id}-${item.reason}`} className="flex items-center justify-between px-5 py-3 text-sm">
                    <div>
                      <span className="font-medium text-gray-900">{item.quote_ref}</span>
                      <span className="ml-2 text-gray-600">{item.reason}</span>
                    </div>
                    <Link href={`/estimator/quotes/${item.session_id}`} className="text-indigo-600 hover:text-indigo-800">
                      Open
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      ) : (
        <p className="text-sm text-gray-500">No dashboard data available.</p>
      )}
    </div>
  );
}
