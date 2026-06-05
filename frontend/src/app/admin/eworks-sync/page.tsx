"use client";

import { useCallback, useEffect, useState } from "react";

import { AlertTriangle, CheckCircle, RefreshCw, XCircle } from "lucide-react";

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
  LoadingState,
  PageHeader,
  PaginationBar,
  PrimaryButton,
  SecondaryButton,
  SectionCard,
  StatCard,
  StatusBadge,
  filterInputClass,
} from "@/components/ui";
import {
  getEworksSyncStatus,
  getSyncRuns,
  listSyncedJobs,
  listSyncedQuotes,
  triggerAllSync,
  triggerJobsSync,
  triggerQuotesSync,
  type EworksSyncBucketSummary,
  type EworksSyncResult,
  type EworksSyncRunRecord,
  type EworksSyncStatus,
  type EworksJobRecord,
  type EworksQuoteRecord,
} from "@/lib/eworks-sync";

type TabId = "sync" | "quotes" | "jobs";
const PAGE_SIZE = 50;

// ---------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------

function syncStatusTone(status: string): "success" | "warning" | "danger" | "info" | "neutral" {
  if (status === "success") return "success";
  if (status === "partial") return "warning";
  if (status === "failed") return "danger";
  if (status === "running") return "info";
  return "neutral";
}

function fmtDate(val: string | null | undefined): string {
  if (!val) return "—";
  try {
    return new Date(val).toLocaleString();
  } catch {
    return val;
  }
}

function fmtMoney(val: number | null | undefined): string {
  if (val === null || val === undefined) return "—";
  return `£${val.toFixed(2)}`;
}

// ---------------------------------------------------------------------------
// Sync summary panel
// ---------------------------------------------------------------------------

function SyncSummaryPanel({
  label,
  summary,
}: {
  label: string;
  summary: EworksSyncBucketSummary;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <p className="mb-2 text-sm font-semibold text-slate-700">{label}</p>
      <div className="grid grid-cols-4 gap-2 text-center text-xs">
        {(
          [
            ["Fetched", summary.fetched, "text-slate-600"],
            ["Created", summary.created, "text-emerald-600"],
            ["Updated", summary.updated, "text-blue-600"],
            ["Failed", summary.failed, summary.failed > 0 ? "text-red-600" : "text-slate-400"],
          ] as const
        ).map(([label, val, cls]) => (
          <div key={label}>
            <div className={`text-lg font-bold ${cls}`}>{val}</div>
            <div className="text-slate-500">{label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sync tab
// ---------------------------------------------------------------------------

function SyncTab() {
  const [status, setStatus] = useState<EworksSyncStatus | null>(null);
  const [runs, setRuns] = useState<EworksSyncRunRecord[]>([]);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState<"quotes" | "jobs" | "all" | null>(null);
  const [lastResult, setLastResult] = useState<EworksSyncResult | EworksSyncBucketSummary | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);

  const loadStatus = useCallback(async () => {
    try {
      const [s, r] = await Promise.all([getEworksSyncStatus(), getSyncRuns({ limit: 10 })]);
      setStatus(s);
      setRuns(r.items);
      setStatusError(null);
    } catch (e: unknown) {
      setStatusError(e instanceof Error ? e.message : "Failed to load sync status");
    }
  }, []);

  useEffect(() => {
    void loadStatus();
  }, [loadStatus]);

  const handleSync = useCallback(
    async (type: "quotes" | "jobs" | "all") => {
      setSyncing(type);
      setSyncError(null);
      setLastResult(null);
      try {
        if (type === "quotes") {
          const r = await triggerQuotesSync();
          setLastResult(r.summary);
        } else if (type === "jobs") {
          const r = await triggerJobsSync();
          setLastResult(r.summary);
        } else {
          const r = await triggerAllSync();
          setLastResult(r);
        }
        await loadStatus();
      } catch (e: unknown) {
        setSyncError(e instanceof Error ? e.message : "Sync failed");
      } finally {
        setSyncing(null);
      }
    },
    [loadStatus]
  );

  return (
    <div className="space-y-6">
      {/* Read-only warning */}
      <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4">
        <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-600" />
        <div>
          <p className="text-sm font-semibold text-amber-800">Read-only from eWorks</p>
          <p className="mt-0.5 text-xs text-amber-700">
            This sync fetches eWorks data into the local database only. No records are modified in eWorks.
          </p>
        </div>
      </div>

      {/* Status cards */}
      {statusError ? (
        <ErrorState message={statusError} />
      ) : !status ? (
        <LoadingState />
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatCard
            label="Local Quotes"
            value={String(status.quotes_count)}
            data-testid="stat-quotes-count"
          />
          <StatCard
            label="Local Jobs"
            value={String(status.jobs_count)}
            data-testid="stat-jobs-count"
          />
          <StatCard
            label="Last Quotes Sync"
            value={status.last_quotes_sync ? fmtDate(status.last_quotes_sync) : "Never"}
          />
          <StatCard
            label="Last Jobs Sync"
            value={status.last_jobs_sync ? fmtDate(status.last_jobs_sync) : "Never"}
          />
        </div>
      )}

      {!status?.eworks_api_enabled && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          eWorks API is disabled (<code>EWORKS_API_ENABLED=false</code>). Enable it to run syncs.
        </div>
      )}

      {/* Sync buttons */}
      <SectionCard>
        <div className="space-y-4">
          <h2 className="text-sm font-semibold text-slate-700">Trigger Sync</h2>
          <div className="flex flex-wrap gap-3">
            <PrimaryButton
              onClick={() => handleSync("all")}
              disabled={!!syncing}
              data-testid="btn-sync-all"
            >
              {syncing === "all" ? (
                <span className="flex items-center gap-2">
                  <RefreshCw className="h-4 w-4 animate-spin" /> Syncing All…
                </span>
              ) : (
                "Sync All"
              )}
            </PrimaryButton>
            <SecondaryButton
              onClick={() => handleSync("quotes")}
              disabled={!!syncing}
              data-testid="btn-sync-quotes"
            >
              {syncing === "quotes" ? (
                <span className="flex items-center gap-2">
                  <RefreshCw className="h-4 w-4 animate-spin" /> Syncing…
                </span>
              ) : (
                "Sync Quotes"
              )}
            </SecondaryButton>
            <SecondaryButton
              onClick={() => handleSync("jobs")}
              disabled={!!syncing}
              data-testid="btn-sync-jobs"
            >
              {syncing === "jobs" ? (
                <span className="flex items-center gap-2">
                  <RefreshCw className="h-4 w-4 animate-spin" /> Syncing…
                </span>
              ) : (
                "Sync Jobs"
              )}
            </SecondaryButton>
          </div>
        </div>
      </SectionCard>

      {/* Sync result */}
      {syncError && (
        <div
          className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4"
          data-testid="sync-error"
        >
          <XCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" />
          <p className="text-sm text-red-700">{syncError}</p>
        </div>
      )}

      {lastResult && !syncError && (
        <div
          className="space-y-3 rounded-lg border border-emerald-200 bg-emerald-50 p-4"
          data-testid="sync-result"
        >
          <div className="flex items-center gap-2">
            <CheckCircle className="h-5 w-5 text-emerald-600" />
            <p className="text-sm font-semibold text-emerald-800">Sync completed</p>
          </div>
          {"quotes" in lastResult ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <SyncSummaryPanel label="Quotes" summary={(lastResult as EworksSyncResult).quotes} />
              <SyncSummaryPanel label="Jobs" summary={(lastResult as EworksSyncResult).jobs} />
              {(lastResult as EworksSyncResult).errors.length > 0 && (
                <div className="col-span-2 text-xs text-red-600">
                  Errors: {(lastResult as EworksSyncResult).errors.join("; ")}
                </div>
              )}
            </div>
          ) : (
            <SyncSummaryPanel label="Result" summary={lastResult as EworksSyncBucketSummary} />
          )}
        </div>
      )}

      {/* Recent runs */}
      <SectionCard>
        <h2 className="mb-3 text-sm font-semibold text-slate-700">Recent Sync Runs</h2>
        {runs.length === 0 ? (
          <EmptyState message="No sync runs yet" />
        ) : (
          <DataTable data-testid="sync-runs-table">
            <DataTableHead>
              <DataTableRow>
                <DataTableCell header>Type</DataTableCell>
                <DataTableCell header>Status</DataTableCell>
                <DataTableCell header>Started</DataTableCell>
                <DataTableCell header>Finished</DataTableCell>
                <DataTableCell header numeric>Fetched</DataTableCell>
                <DataTableCell header numeric>Created</DataTableCell>
                <DataTableCell header numeric>Updated</DataTableCell>
                <DataTableCell header numeric>Failed</DataTableCell>
              </DataTableRow>
            </DataTableHead>
            <DataTableBody>
              {runs.map((run) => (
                <DataTableRow key={run.id}>
                  <DataTableCell>
                    <span className="text-xs font-mono">{run.sync_type}</span>
                  </DataTableCell>
                  <DataTableCell>
                    <StatusBadge tone={syncStatusTone(run.status)}>{run.status}</StatusBadge>
                  </DataTableCell>
                  <DataTableCell>{fmtDate(run.started_at)}</DataTableCell>
                  <DataTableCell>{fmtDate(run.finished_at)}</DataTableCell>
                  <DataTableCell numeric>{run.fetched_count}</DataTableCell>
                  <DataTableCell numeric>{run.created_count}</DataTableCell>
                  <DataTableCell numeric>{run.updated_count}</DataTableCell>
                  <DataTableCell numeric>
                    <span className={run.failed_count > 0 ? "text-red-600 font-semibold" : ""}>
                      {run.failed_count}
                    </span>
                  </DataTableCell>
                </DataTableRow>
              ))}
            </DataTableBody>
          </DataTable>
        )}
      </SectionCard>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Quotes tab
// ---------------------------------------------------------------------------

function QuotesTab() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [customerFilter, setCustomerFilter] = useState("");
  const [offset, setOffset] = useState(0);
  const [items, setItems] = useState<EworksQuoteRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listSyncedQuotes({
        search: search || undefined,
        status: statusFilter || undefined,
        customer_name: customerFilter || undefined,
        limit: PAGE_SIZE,
        offset,
      });
      setItems(result.items);
      setTotal(result.total);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load quotes");
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter, customerFilter, offset]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-4">
      <FilterBar>
        <FilterField label="Search">
          <input
            className={filterInputClass}
            placeholder="Ref, customer, description…"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setOffset(0); }}
            data-testid="quotes-search"
          />
        </FilterField>
        <FilterField label="Customer">
          <input
            className={filterInputClass}
            placeholder="Customer name"
            value={customerFilter}
            onChange={(e) => { setCustomerFilter(e.target.value); setOffset(0); }}
          />
        </FilterField>
        <FilterField label="Status">
          <input
            className={filterInputClass}
            placeholder="Status"
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setOffset(0); }}
          />
        </FilterField>
      </FilterBar>

      {error ? (
        <ErrorState message={error} />
      ) : loading ? (
        <LoadingState />
      ) : items.length === 0 ? (
        <EmptyState message="No quotes synced yet. Run 'Sync Quotes' from the Sync tab." />
      ) : (
        <>
          <DataTable data-testid="quotes-table">
            <DataTableHead>
              <DataTableRow>
                <DataTableCell header>Quote ID</DataTableCell>
                <DataTableCell header>Quote Ref</DataTableCell>
                <DataTableCell header>Customer</DataTableCell>
                <DataTableCell header>Status</DataTableCell>
                <DataTableCell header>Date</DataTableCell>
                <DataTableCell header numeric>Total</DataTableCell>
                <DataTableCell header>Synced At</DataTableCell>
              </DataTableRow>
            </DataTableHead>
            <DataTableBody>
              {items.map((q) => (
                <DataTableRow key={q.id}>
                  <DataTableCell>
                    <span className="font-mono text-xs">{q.eworks_quote_id}</span>
                  </DataTableCell>
                  <DataTableCell>{q.quote_ref ?? "—"}</DataTableCell>
                  <DataTableCell>{q.customer_name ?? "—"}</DataTableCell>
                  <DataTableCell>
                    {q.status_name ? (
                      <StatusBadge tone="neutral">{q.status_name}</StatusBadge>
                    ) : (
                      "—"
                    )}
                  </DataTableCell>
                  <DataTableCell>{q.quote_date ?? "—"}</DataTableCell>
                  <DataTableCell numeric>{fmtMoney(q.total)}</DataTableCell>
                  <DataTableCell>{fmtDate(q.synced_at)}</DataTableCell>
                </DataTableRow>
              ))}
            </DataTableBody>
          </DataTable>
          <PaginationBar
            total={total}
            limit={PAGE_SIZE}
            offset={offset}
            onOffsetChange={setOffset}
          />
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Jobs tab
// ---------------------------------------------------------------------------

function JobsTab() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [customerFilter, setCustomerFilter] = useState("");
  const [offset, setOffset] = useState(0);
  const [items, setItems] = useState<EworksJobRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listSyncedJobs({
        search: search || undefined,
        status: statusFilter || undefined,
        customer_name: customerFilter || undefined,
        limit: PAGE_SIZE,
        offset,
      });
      setItems(result.items);
      setTotal(result.total);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load jobs");
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter, customerFilter, offset]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-4">
      <FilterBar>
        <FilterField label="Search">
          <input
            className={filterInputClass}
            placeholder="Ref, customer, description…"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setOffset(0); }}
            data-testid="jobs-search"
          />
        </FilterField>
        <FilterField label="Customer">
          <input
            className={filterInputClass}
            placeholder="Customer name"
            value={customerFilter}
            onChange={(e) => { setCustomerFilter(e.target.value); setOffset(0); }}
          />
        </FilterField>
        <FilterField label="Status">
          <input
            className={filterInputClass}
            placeholder="Status"
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setOffset(0); }}
          />
        </FilterField>
      </FilterBar>

      {error ? (
        <ErrorState message={error} />
      ) : loading ? (
        <LoadingState />
      ) : items.length === 0 ? (
        <EmptyState message="No jobs synced yet. Run 'Sync Jobs' from the Sync tab." />
      ) : (
        <>
          <DataTable data-testid="jobs-table">
            <DataTableHead>
              <DataTableRow>
                <DataTableCell header>Job ID</DataTableCell>
                <DataTableCell header>Job Ref</DataTableCell>
                <DataTableCell header>Customer</DataTableCell>
                <DataTableCell header>Status</DataTableCell>
                <DataTableCell header>Date</DataTableCell>
                <DataTableCell header numeric>Total</DataTableCell>
                <DataTableCell header>Synced At</DataTableCell>
              </DataTableRow>
            </DataTableHead>
            <DataTableBody>
              {items.map((j) => (
                <DataTableRow key={j.id}>
                  <DataTableCell>
                    <span className="font-mono text-xs">{j.eworks_job_id}</span>
                  </DataTableCell>
                  <DataTableCell>{j.job_ref ?? "—"}</DataTableCell>
                  <DataTableCell>{j.customer_name ?? "—"}</DataTableCell>
                  <DataTableCell>
                    {j.status_name ? (
                      <StatusBadge tone="neutral">{j.status_name}</StatusBadge>
                    ) : (
                      "—"
                    )}
                  </DataTableCell>
                  <DataTableCell>{j.job_date ?? "—"}</DataTableCell>
                  <DataTableCell numeric>{fmtMoney(j.total)}</DataTableCell>
                  <DataTableCell>{fmtDate(j.synced_at)}</DataTableCell>
                </DataTableRow>
              ))}
            </DataTableBody>
          </DataTable>
          <PaginationBar
            total={total}
            limit={PAGE_SIZE}
            offset={offset}
            onOffsetChange={setOffset}
          />
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

const TABS: { id: TabId; label: string }[] = [
  { id: "sync", label: "Sync" },
  { id: "quotes", label: "Quotes" },
  { id: "jobs", label: "Jobs" },
];

export default function EworksSyncPage() {
  const [activeTab, setActiveTab] = useState<TabId>("sync");

  return (
    <div className="space-y-6" data-testid="eworks-sync-page">
      <PageHeader
        title="eWorks Sync"
        description="Sync Quotes and Jobs from eWorks Manager into the local database (read-only from eWorks)."
      />

      {/* Tab bar */}
      <div className="flex gap-1 border-b border-slate-200">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            data-testid={`tab-${tab.id}`}
            className={[
              "px-4 py-2 text-sm font-medium transition-colors",
              activeTab === tab.id
                ? "border-b-2 border-blue-600 text-blue-600"
                : "text-slate-500 hover:text-slate-700",
            ].join(" ")}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "sync" && <SyncTab />}
      {activeTab === "quotes" && <QuotesTab />}
      {activeTab === "jobs" && <JobsTab />}
    </div>
  );
}
