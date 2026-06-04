"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { EworksButton, EworksInput, EworksLabel, EworksLoadingScreen } from "@/components/eworks-ui";
import { QuoteAcceptanceBadge } from "@/components/quote-acceptance-badge";
import {
  formatMoney,
  formatPeriod,
  formatReportDate,
  getReportSummary,
  type ReportSummary,
} from "@/lib/reports";

function StatusBadge({ status }: { status: string }) {
  const tone =
    status === "submitted"
      ? "bg-emerald-100 text-emerald-800"
      : status === "in_progress"
        ? "bg-amber-100 text-amber-800"
        : "bg-slate-100 text-slate-700";
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${tone}`}>{status}</span>
  );
}

function KpiCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm" data-testid={`kpi-${label.toLowerCase().replace(/\s+/g, "-")}`}>
      <p className="text-sm font-medium text-gray-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-gray-900">{value}</p>
    </div>
  );
}

function BreakdownTable({
  title,
  headers,
  rows,
  testId,
}: {
  title: string;
  headers: string[];
  rows: Array<Array<string | number>>;
  testId: string;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white shadow-sm" data-testid={testId}>
      <div className="border-b border-gray-200 px-5 py-4">
        <h2 className="text-base font-semibold text-gray-900">{title}</h2>
      </div>
      {rows.length === 0 ? (
        <p className="px-5 py-8 text-sm text-gray-500">No data for the selected filters.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                {headers.map((header) => (
                  <th key={header} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {rows.map((row, index) => (
                <tr key={`${title}-${index}`}>
                  {row.map((cell, cellIndex) => (
                    <td key={cellIndex} className="px-4 py-3 text-gray-900">
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function TrendBars({ trend }: { trend: ReportSummary["trend"] }) {
  if (trend.length === 0) {
    return <p className="text-sm text-gray-500">No trend data for the selected filters.</p>;
  }

  const maxValue = Math.max(...trend.map((point) => point.value), 1);

  return (
    <div className="space-y-3" data-testid="reports-trend">
      {trend.map((point) => {
        const widthPct = Math.max(4, Math.round((point.value / maxValue) * 100));
        return (
          <div key={point.period} className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium text-gray-700">{formatPeriod(point.period)}</span>
              <span className="text-gray-600">
                {point.count} quotes · {formatMoney(point.value)}
              </span>
            </div>
            <div className="h-2 rounded-full bg-gray-100">
              <div className="h-2 rounded-full bg-indigo-500" style={{ width: `${widthPct}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function ManagerReportsPage() {
  const [summary, setSummary] = useState<ReportSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [clientId, setClientId] = useState("");
  const [tradeId, setTradeId] = useState("");
  const [status, setStatus] = useState("submitted");
  const [groupBy, setGroupBy] = useState<"day" | "week" | "month">("day");

  const filters = useMemo(
    () => ({
      date_from: dateFrom ? `${dateFrom}T00:00:00Z` : undefined,
      date_to: dateTo ? `${dateTo}T23:59:59Z` : undefined,
      client_id: clientId || undefined,
      trade_id: tradeId || undefined,
      status: status || undefined,
      group_by: groupBy,
    }),
    [dateFrom, dateTo, clientId, tradeId, status, groupBy],
  );

  const loadSummary = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getReportSummary(filters);
      setSummary(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load reports");
      setSummary(null);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    void loadSummary();
  }, [loadSummary]);

  const clientOptions = summary?.by_client ?? [];
  const tradeOptions = summary?.by_trade ?? [];

  return (
    <div className="space-y-6" data-testid="manager-reports-page">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Reports</h1>
        <p className="mt-2 text-sm text-gray-600">Submitted quote and estimation performance overview</p>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div>
            <EworksLabel htmlFor="reports-date-from">Date from</EworksLabel>
            <EworksInput id="reports-date-from" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </div>
          <div>
            <EworksLabel htmlFor="reports-date-to">Date to</EworksLabel>
            <EworksInput id="reports-date-to" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </div>
          <div>
            <EworksLabel htmlFor="reports-client">Client</EworksLabel>
            <select
              id="reports-client"
              value={clientId}
              onChange={(e) => setClientId(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value="">All clients</option>
              {clientOptions.map((client) => (
                <option key={client.client_id ?? client.client_name} value={client.client_id ?? ""}>
                  {client.client_name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <EworksLabel htmlFor="reports-trade">Trade</EworksLabel>
            <select
              id="reports-trade"
              value={tradeId}
              onChange={(e) => setTradeId(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value="">All trades</option>
              {tradeOptions.map((trade) => (
                <option key={trade.trade_id ?? trade.trade_name} value={trade.trade_id ?? ""}>
                  {trade.trade_name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <EworksLabel htmlFor="reports-status">Status</EworksLabel>
            <select
              id="reports-status"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value="submitted">Submitted</option>
              <option value="in_progress">In progress</option>
            </select>
          </div>
          <div>
            <EworksLabel htmlFor="reports-group-by">Group by</EworksLabel>
            <select
              id="reports-group-by"
              value={groupBy}
              onChange={(e) => setGroupBy(e.target.value as "day" | "week" | "month")}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value="day">Day</option>
              <option value="week">Week</option>
              <option value="month">Month</option>
            </select>
          </div>
        </div>
        <div className="mt-4 flex justify-end">
          <EworksButton type="button" onClick={() => void loadSummary()} disabled={loading}>
            Refresh
          </EworksButton>
        </div>
      </div>

      {loading ? (
        <EworksLoadingScreen message="Loading reports…" />
      ) : error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" data-testid="reports-error">
          {error}
        </div>
      ) : summary ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-6" data-testid="reports-kpi-cards">
            <KpiCard label="Submitted Quotes" value={String(summary.kpis.submitted_quotes)} />
            <KpiCard label="Total Quote Value" value={formatMoney(summary.kpis.total_value)} />
            <KpiCard label="Average Quote Value" value={formatMoney(summary.kpis.average_quote_value)} />
            <KpiCard label="Accepted Count" value={String(summary.kpis.accepted_count ?? 0)} />
            <KpiCard label="Accepted Value" value={formatMoney(summary.kpis.accepted_value ?? 0)} />
            <KpiCard label="Reopened Count" value={String(summary.kpis.reopened_count ?? 0)} />
          </div>

          <div className="grid gap-6 xl:grid-cols-3">
            <BreakdownTable
              title="By Status"
              testId="reports-by-status"
              headers={["Status", "Count", "Value"]}
              rows={summary.by_status.map((row) => [row.status, row.count, formatMoney(row.value)])}
            />
            <BreakdownTable
              title="By Client"
              testId="reports-by-client"
              headers={["Client", "Count", "Value"]}
              rows={summary.by_client.map((row) => [row.client_name, row.count, formatMoney(row.value)])}
            />
            <BreakdownTable
              title="By Trade"
              testId="reports-by-trade"
              headers={["Trade", "Count", "Value"]}
              rows={summary.by_trade.map((row) => [row.trade_name, row.count, formatMoney(row.value)])}
            />
          </div>

          <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
            <h2 className="text-base font-semibold text-gray-900">Trend</h2>
            <div className="mt-4">
              <TrendBars trend={summary.trend} />
            </div>
          </div>

          <div className="rounded-lg border border-gray-200 bg-white shadow-sm" data-testid="reports-recent-quotes">
            <div className="border-b border-gray-200 px-5 py-4">
              <h2 className="text-base font-semibold text-gray-900">Recent Quotes</h2>
            </div>
            {summary.recent_quotes.length === 0 ? (
              <p className="px-5 py-8 text-sm text-gray-500">No submitted quotes match the selected filters.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      {["Quote Ref", "Client", "Trade", "Status", "Total", "Submitted At", "Actions"].map((header) => (
                        <th
                          key={header}
                          className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500"
                        >
                          {header}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 bg-white">
                    {summary.recent_quotes.map((quote) => (
                      <tr key={quote.session_id}>
                        <td className="px-4 py-3 font-medium text-gray-900">{quote.quote_ref}</td>
                        <td className="px-4 py-3 text-gray-700">{quote.client_name || "—"}</td>
                        <td className="px-4 py-3 text-gray-700">{quote.trade_name || "—"}</td>
                        <td className="px-4 py-3">
                          <div className="flex flex-wrap items-center gap-2">
                            <StatusBadge status={quote.status} />
                            {quote.client_accepted ? <QuoteAcceptanceBadge accepted /> : null}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-gray-900">{formatMoney(quote.total)}</td>
                        <td className="px-4 py-3 text-gray-700">{formatReportDate(quote.submitted_at)}</td>
                        <td className="px-4 py-3">
                          <Link
                            href={`/manager/review/${quote.session_id}`}
                            className="text-sm font-medium text-indigo-600 hover:text-indigo-800"
                            data-testid={`report-view-${quote.session_id}`}
                          >
                            View
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      ) : (
        <p className="text-sm text-gray-500">No report data available.</p>
      )}
    </div>
  );
}
