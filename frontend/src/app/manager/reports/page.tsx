"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { QuoteAcceptanceBadge } from "@/components/quote-acceptance-badge";
import {
  DataTable,
  DataTableBody,
  DataTableCell,
  DataTableHead,
  DataTableRow,
  EmptyState,
  ErrorState,
  FilterBar,
  FilterField,
  filterInputClass,
  filterSelectClass,
  LoadingState,
  MoneyText,
  PageHeader,
  SecondaryButton,
  SectionCard,
  StatCard,
  StatusBadge,
  quoteStatusTone,
} from "@/components/ui";
import {
  formatMoney,
  formatPeriod,
  formatReportDate,
  getReportSummary,
  type ReportSummary,
} from "@/lib/reports";

function ReportKpiCard({ label, value }: { label: string; value: string }) {
  const testId = `kpi-${label.toLowerCase().replace(/\s+/g, "-")}`;
  return (
    <div data-testid={testId}>
      <StatCard label={label} value={value} />
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
    <div data-testid={testId}>
      <SectionCard title={title} padding="none">
        {rows.length === 0 ? (
          <EmptyState
            title="No data"
            description="No data for the selected filters."
            className="border-0 bg-transparent py-8"
          />
        ) : (
          <DataTable>
            <DataTableHead>
              {headers.map((header) => (
                <DataTableCell key={header} header>
                  {header}
                </DataTableCell>
              ))}
            </DataTableHead>
            <DataTableBody>
              {rows.map((row, index) => (
                <DataTableRow key={`${title}-${index}`}>
                  {row.map((cell, cellIndex) => (
                    <DataTableCell key={cellIndex} className={cellIndex === 0 ? "font-medium text-slate-900" : undefined}>
                      {cell}
                    </DataTableCell>
                  ))}
                </DataTableRow>
              ))}
            </DataTableBody>
          </DataTable>
        )}
      </SectionCard>
    </div>
  );
}

function TrendBars({ trend }: { trend: ReportSummary["trend"] }) {
  if (trend.length === 0) {
    return <EmptyState title="No trend data" description="No trend data for the selected filters." className="border-0 bg-transparent py-6" />;
  }

  const maxValue = Math.max(...trend.map((point) => point.value), 1);

  return (
    <div className="space-y-3" data-testid="reports-trend">
      {trend.map((point) => {
        const widthPct = Math.max(4, Math.round((point.value / maxValue) * 100));
        return (
          <div key={point.period} className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium text-slate-700">{formatPeriod(point.period)}</span>
              <span className="text-slate-600">
                {point.count} quotes · <MoneyText value={formatMoney(point.value)} />
              </span>
            </div>
            <div className="h-2 rounded-full bg-slate-100">
              <div className="h-2 rounded-full bg-blue-600" style={{ width: `${widthPct}%` }} />
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
      <PageHeader
        title="Reports"
        description="Submitted quote and estimation performance overview"
      />

      <FilterBar>
        <FilterField label="Date from">
          <input
            id="reports-date-from"
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className={filterInputClass}
          />
        </FilterField>
        <FilterField label="Date to">
          <input
            id="reports-date-to"
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className={filterInputClass}
          />
        </FilterField>
        <FilterField label="Client">
          <select
            id="reports-client"
            value={clientId}
            onChange={(e) => setClientId(e.target.value)}
            className={filterSelectClass}
          >
            <option value="">All clients</option>
            {clientOptions.map((client) => (
              <option key={client.client_id ?? client.client_name} value={client.client_id ?? ""}>
                {client.client_name}
              </option>
            ))}
          </select>
        </FilterField>
        <FilterField label="Trade">
          <select
            id="reports-trade"
            value={tradeId}
            onChange={(e) => setTradeId(e.target.value)}
            className={filterSelectClass}
          >
            <option value="">All trades</option>
            {tradeOptions.map((trade) => (
              <option key={trade.trade_id ?? trade.trade_name} value={trade.trade_id ?? ""}>
                {trade.trade_name}
              </option>
            ))}
          </select>
        </FilterField>
        <FilterField label="Status">
          <select
            id="reports-status"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className={filterSelectClass}
          >
            <option value="submitted">Submitted</option>
            <option value="in_progress">In progress</option>
          </select>
        </FilterField>
        <FilterField label="Group by">
          <select
            id="reports-group-by"
            value={groupBy}
            onChange={(e) => setGroupBy(e.target.value as "day" | "week" | "month")}
            className={filterSelectClass}
          >
            <option value="day">Day</option>
            <option value="week">Week</option>
            <option value="month">Month</option>
          </select>
        </FilterField>
        <div className="flex sm:pb-0.5">
          <SecondaryButton onClick={() => void loadSummary()} disabled={loading}>
            Refresh
          </SecondaryButton>
        </div>
      </FilterBar>

      {loading ? (
        <LoadingState message="Loading reports…" />
      ) : error ? (
        <div data-testid="reports-error">
          <ErrorState message={error} onRetry={() => void loadSummary()} />
        </div>
      ) : summary ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3" data-testid="reports-kpi-cards">
            <ReportKpiCard label="Submitted Quotes" value={String(summary.kpis.submitted_quotes)} />
            <ReportKpiCard label="Total Quote Value" value={formatMoney(summary.kpis.total_value)} />
            <ReportKpiCard label="Average Quote Value" value={formatMoney(summary.kpis.average_quote_value)} />
            <ReportKpiCard label="Accepted Count" value={String(summary.kpis.accepted_count ?? 0)} />
            <ReportKpiCard label="Accepted Value" value={formatMoney(summary.kpis.accepted_value ?? 0)} />
            <ReportKpiCard label="Reopened Count" value={String(summary.kpis.reopened_count ?? 0)} />
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

          <SectionCard title="Trend">
            <TrendBars trend={summary.trend} />
          </SectionCard>

          <div data-testid="reports-recent-quotes">
            <SectionCard title="Recent Quotes" padding="none">
              {summary.recent_quotes.length === 0 ? (
                <EmptyState
                  title="No quotes"
                  description="No submitted quotes match the selected filters."
                  className="border-0 bg-transparent py-8"
                />
              ) : (
                <DataTable>
                  <DataTableHead>
                    {["Quote Ref", "Client", "Trade", "Status", "Total", "Submitted At", "Actions"].map((header) => (
                      <DataTableCell key={header} header>
                        {header}
                      </DataTableCell>
                    ))}
                  </DataTableHead>
                  <DataTableBody>
                    {summary.recent_quotes.map((quote) => (
                      <DataTableRow key={quote.session_id}>
                        <DataTableCell className="font-medium text-slate-900">{quote.quote_ref}</DataTableCell>
                        <DataTableCell>{quote.client_name || "—"}</DataTableCell>
                        <DataTableCell>{quote.trade_name || "—"}</DataTableCell>
                        <DataTableCell>
                          <div className="flex flex-wrap items-center gap-2">
                            <StatusBadge tone={quoteStatusTone(quote.status)}>{quote.status}</StatusBadge>
                            {quote.client_accepted ? <QuoteAcceptanceBadge accepted /> : null}
                          </div>
                        </DataTableCell>
                        <DataTableCell>
                          <MoneyText value={formatMoney(quote.total)} />
                        </DataTableCell>
                        <DataTableCell>{formatReportDate(quote.submitted_at)}</DataTableCell>
                        <DataTableCell>
                          <Link
                            href={`/manager/review/${quote.session_id}`}
                            className="text-sm font-medium text-blue-600 hover:text-blue-700"
                            data-testid={`report-view-${quote.session_id}`}
                          >
                            View
                          </Link>
                        </DataTableCell>
                      </DataTableRow>
                    ))}
                  </DataTableBody>
                </DataTable>
              )}
            </SectionCard>
          </div>
        </>
      ) : (
        <EmptyState title="No report data" description="No report data available." />
      )}
    </div>
  );
}
