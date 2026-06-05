"use client";

import { useCallback, useEffect, useRef, useState } from "react";

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
  EWORKS_ACTIVE_SYNC_RUN_KEY,
  EWORKS_SYNC_DEFAULT_DAYS,
  buildDefaultSyncRequest,
  getEworksSyncStatus,
  getSyncRun,
  getSyncRuns,
  listSyncedJobs,
  listSyncedQuotes,
  runToSyncResult,
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
type SyncType = "quotes" | "jobs" | "all";

const PAGE_SIZE = 50;
const POLL_INTERVAL_MS = 2500;

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

function SyncSummaryPanel({ label, summary }: { label: string; summary: EworksSyncBucketSummary }) {
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
        ).map(([lbl, val, cls]) => (
          <div key={lbl}>
            <div className={`text-lg font-bold ${cls}`}>{val}</div>
            <div className="text-slate-500">{lbl}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ActiveSyncBanner({
  syncType,
  phase,
}: {
  syncType: SyncType;
  phase?: string | null;
}) {
  const label =
    syncType === "all"
      ? "Syncing quotes and jobs in the background"
      : syncType === "quotes"
        ? "Syncing quotes in the background"
        : "Syncing jobs in the background";

  return (
    <div
      className="flex items-start gap-3 rounded-lg border border-blue-200 bg-blue-50 p-4"
      data-testid="sync-active-banner"
    >
      <RefreshCw className="mt-0.5 h-5 w-5 flex-shrink-0 animate-spin text-blue-600" />
      <div>
        <p className="text-sm font-semibold text-blue-800">{label}</p>
        <p className="mt-0.5 text-xs text-blue-700">
          You can switch tabs or navigate away — sync continues on the server.
          {phase ? ` Current phase: ${phase}.` : ""}
        </p>
      </div>
    </div>
  );
}

type SyncTabProps = {
  status: EworksSyncStatus | null;
  statusError: string | null;
  runs: EworksSyncRunRecord[];
  syncing: SyncType | null;
  lastResult: EworksSyncResult | EworksSyncBucketSummary | null;
  syncError: string | null;
  fullSync: boolean;
  onFullSyncChange: (value: boolean) => void;
  onSync: (type: SyncType) => void;
};

function SyncTab({
  status,
  statusError,
  runs,
  syncing,
  lastResult,
  syncError,
  fullSync,
  onFullSyncChange,
  onSync,
}: SyncTabProps) {
  return (
    <div className="space-y-6">
      <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4">
        <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-600" />
        <div>
          <p className="text-sm font-semibold text-amber-800">Read-only from eWorks</p>
          <p className="mt-0.5 text-xs text-amber-700">
            This sync fetches eWorks data into the local database only. No records are modified in eWorks.
            By default, only the last {EWORKS_SYNC_DEFAULT_DAYS} days are synced.
          </p>
        </div>
      </div>

      {statusError ? (
        <ErrorState message={statusError} />
      ) : !status ? (
        <LoadingState />
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatCard label="Local Quotes" value={String(status.quotes_count)} data-testid="stat-quotes-count" />
          <StatCard label="Local Jobs" value={String(status.jobs_count)} data-testid="stat-jobs-count" />
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

      <SectionCard>
        <div className="space-y-4">
          <h2 className="text-sm font-semibold text-slate-700">Trigger Sync</h2>
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={fullSync}
              onChange={(e) => onFullSyncChange(e.target.checked)}
              data-testid="sync-full-toggle"
            />
            Full sync (all dates — slower; use for initial load)
          </label>
          {!fullSync ? (
            <p className="text-xs text-slate-500" data-testid="sync-date-window-note">
              Sync window: last {EWORKS_SYNC_DEFAULT_DAYS} days only.
            </p>
          ) : null}
          <div className="flex flex-wrap gap-3">
            <PrimaryButton onClick={() => onSync("all")} disabled={!!syncing} data-testid="btn-sync-all">
              {syncing === "all" ? (
                <span className="flex items-center gap-2">
                  <RefreshCw className="h-4 w-4 animate-spin" /> Starting…
                </span>
              ) : (
                "Sync All"
              )}
            </PrimaryButton>
            <SecondaryButton onClick={() => onSync("quotes")} disabled={!!syncing} data-testid="btn-sync-quotes">
              {syncing === "quotes" ? (
                <span className="flex items-center gap-2">
                  <RefreshCw className="h-4 w-4 animate-spin" /> Starting…
                </span>
              ) : (
                "Sync Quotes"
              )}
            </SecondaryButton>
            <SecondaryButton onClick={() => onSync("jobs")} disabled={!!syncing} data-testid="btn-sync-jobs">
              {syncing === "jobs" ? (
                <span className="flex items-center gap-2">
                  <RefreshCw className="h-4 w-4 animate-spin" /> Starting…
                </span>
              ) : (
                "Sync Jobs"
              )}
            </SecondaryButton>
          </div>
        </div>
      </SectionCard>

      {syncError && (
        <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4" data-testid="sync-error">
          <XCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" />
          <p className="text-sm text-red-700">{syncError}</p>
        </div>
      )}

      {lastResult && !syncError && (
        <div className="space-y-3 rounded-lg border border-emerald-200 bg-emerald-50 p-4" data-testid="sync-result">
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
                    <span className={run.failed_count > 0 ? "font-semibold text-red-600" : ""}>
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

function QuotesTab({ refreshKey }: { refreshKey: number }) {
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
  }, [load, refreshKey]);

  return (
    <div className="space-y-4">
      <FilterBar>
        <FilterField label="Search">
          <input
            className={filterInputClass}
            placeholder="Ref, customer, description…"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setOffset(0);
            }}
            data-testid="quotes-search"
          />
        </FilterField>
        <FilterField label="Customer">
          <input
            className={filterInputClass}
            placeholder="Customer name"
            value={customerFilter}
            onChange={(e) => {
              setCustomerFilter(e.target.value);
              setOffset(0);
            }}
          />
        </FilterField>
        <FilterField label="Status">
          <input
            className={filterInputClass}
            placeholder="Status"
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setOffset(0);
            }}
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
                    {q.status_name ? <StatusBadge tone="neutral">{q.status_name}</StatusBadge> : "—"}
                  </DataTableCell>
                  <DataTableCell>{q.quote_date ?? "—"}</DataTableCell>
                  <DataTableCell numeric>{fmtMoney(q.total)}</DataTableCell>
                  <DataTableCell>{fmtDate(q.synced_at)}</DataTableCell>
                </DataTableRow>
              ))}
            </DataTableBody>
          </DataTable>
          <PaginationBar total={total} limit={PAGE_SIZE} offset={offset} onOffsetChange={setOffset} />
        </>
      )}
    </div>
  );
}

function JobsTab({ refreshKey }: { refreshKey: number }) {
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
  }, [load, refreshKey]);

  return (
    <div className="space-y-4">
      <FilterBar>
        <FilterField label="Search">
          <input
            className={filterInputClass}
            placeholder="Ref, customer, description…"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setOffset(0);
            }}
            data-testid="jobs-search"
          />
        </FilterField>
        <FilterField label="Customer">
          <input
            className={filterInputClass}
            placeholder="Customer name"
            value={customerFilter}
            onChange={(e) => {
              setCustomerFilter(e.target.value);
              setOffset(0);
            }}
          />
        </FilterField>
        <FilterField label="Status">
          <input
            className={filterInputClass}
            placeholder="Status"
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setOffset(0);
            }}
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
                    {j.status_name ? <StatusBadge tone="neutral">{j.status_name}</StatusBadge> : "—"}
                  </DataTableCell>
                  <DataTableCell>{j.job_date ?? "—"}</DataTableCell>
                  <DataTableCell numeric>{fmtMoney(j.total)}</DataTableCell>
                  <DataTableCell>{fmtDate(j.synced_at)}</DataTableCell>
                </DataTableRow>
              ))}
            </DataTableBody>
          </DataTable>
          <PaginationBar total={total} limit={PAGE_SIZE} offset={offset} onOffsetChange={setOffset} />
        </>
      )}
    </div>
  );
}

const TABS: { id: TabId; label: string }[] = [
  { id: "sync", label: "Sync" },
  { id: "quotes", label: "Quotes" },
  { id: "jobs", label: "Jobs" },
];

export default function EworksSyncPage() {
  const [activeTab, setActiveTab] = useState<TabId>("sync");
  const [status, setStatus] = useState<EworksSyncStatus | null>(null);
  const [runs, setRuns] = useState<EworksSyncRunRecord[]>([]);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [activeRun, setActiveRun] = useState<EworksSyncRunRecord | null>(null);
  const [syncing, setSyncing] = useState<SyncType | null>(null);
  const [lastResult, setLastResult] = useState<EworksSyncResult | EworksSyncBucketSummary | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);
  const [fullSync, setFullSync] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const clearPollTimer = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  const loadOverview = useCallback(async () => {
    try {
      const [s, r] = await Promise.all([getEworksSyncStatus(), getSyncRuns({ limit: 10 })]);
      setStatus(s);
      setRuns(r.items);
      setStatusError(null);
      return s;
    } catch (e: unknown) {
      setStatusError(e instanceof Error ? e.message : "Failed to load sync status");
      return null;
    }
  }, []);

  const finishTracking = useCallback(
    (run: EworksSyncRunRecord) => {
      clearPollTimer();
      sessionStorage.removeItem(EWORKS_ACTIVE_SYNC_RUN_KEY);
      setActiveRunId(null);
      setActiveRun(null);
      setSyncing(null);

      const result = runToSyncResult(run);
      if (run.status === "failed") {
        setSyncError(run.error_message ?? "Sync failed");
        setLastResult(null);
      } else if (result) {
        setSyncError(null);
        setLastResult(result);
      }
      setRefreshKey((k) => k + 1);
      void loadOverview();
    },
    [clearPollTimer, loadOverview]
  );

  const pollRun = useCallback(
    async (runId: string) => {
      try {
        const run = await getSyncRun(runId);
        setActiveRun(run);
        if (run.status !== "running") {
          finishTracking(run);
        }
      } catch {
        // Keep polling — transient network errors should not stop tracking
      }
    },
    [finishTracking]
  );

  const startTracking = useCallback(
    (runId: string, syncType: SyncType) => {
      sessionStorage.setItem(EWORKS_ACTIVE_SYNC_RUN_KEY, runId);
      setActiveRunId(runId);
      setSyncing(syncType);
      setSyncError(null);
      setLastResult(null);
      clearPollTimer();
      void pollRun(runId);
      pollTimerRef.current = setInterval(() => {
        void pollRun(runId);
      }, POLL_INTERVAL_MS);
    },
    [clearPollTimer, pollRun]
  );

  useEffect(() => {
    void (async () => {
      const s = await loadOverview();
      const storedRunId = sessionStorage.getItem(EWORKS_ACTIVE_SYNC_RUN_KEY);
      const runId = s?.active_sync?.run_id ?? storedRunId;
      if (runId) {
        try {
          const run = await getSyncRun(runId);
          if (run.status === "running") {
            startTracking(runId, run.sync_type as SyncType);
          } else {
            sessionStorage.removeItem(EWORKS_ACTIVE_SYNC_RUN_KEY);
          }
        } catch {
          sessionStorage.removeItem(EWORKS_ACTIVE_SYNC_RUN_KEY);
        }
      }
    })();

    return () => clearPollTimer();
  }, [clearPollTimer, loadOverview, startTracking]);

  const handleSync = useCallback(
    async (type: SyncType) => {
      setSyncing(type);
      setSyncError(null);
      setLastResult(null);
      const req = buildDefaultSyncRequest(fullSync);
      try {
        const started =
          type === "quotes"
            ? await triggerQuotesSync(req)
            : type === "jobs"
              ? await triggerJobsSync(req)
              : await triggerAllSync(req);
        startTracking(started.run_id, type);
        void loadOverview();
      } catch (e: unknown) {
        setSyncError(e instanceof Error ? e.message : "Sync failed");
        setSyncing(null);
      }
    },
    [fullSync, loadOverview, startTracking]
  );

  const isRunning = !!activeRunId && activeRun?.status === "running";

  return (
    <div className="space-y-6" data-testid="eworks-sync-page">
      <PageHeader
        title="eWorks Sync"
        description="Sync Quotes and Jobs from eWorks Manager into the local database (read-only from eWorks)."
      />

      {isRunning && (
        <ActiveSyncBanner
          syncType={(activeRun?.sync_type as SyncType) ?? syncing ?? "all"}
          phase={activeRun?.metadata?.phase}
        />
      )}

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

      <div className={activeTab === "sync" ? "block" : "hidden"}>
        <SyncTab
          status={status}
          statusError={statusError}
          runs={runs}
          syncing={syncing}
          lastResult={lastResult}
          syncError={syncError}
          fullSync={fullSync}
          onFullSyncChange={setFullSync}
          onSync={handleSync}
        />
      </div>
      <div className={activeTab === "quotes" ? "block" : "hidden"}>
        <QuotesTab refreshKey={refreshKey} />
      </div>
      <div className={activeTab === "jobs" ? "block" : "hidden"}>
        <JobsTab refreshKey={refreshKey} />
      </div>
    </div>
  );
}
