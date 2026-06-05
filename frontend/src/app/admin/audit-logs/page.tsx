"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { EworksInput } from "@/components/eworks-ui";
import {
  DataTable,
  DataTableBody,
  DataTableCell,
  DataTableHead,
  DataTableRow,
  DateText,
  EmptyState,
  ErrorState,
  FilterBar,
  FilterField,
  LoadingState,
  PageHeader,
  PrimaryButton,
  SecondaryButton,
  SectionCard,
  StatusBadge,
  filterInputClass,
  filterSelectClass,
} from "@/components/ui";
import {
  COMMON_ACTIONS,
  COMMON_ENTITY_TYPES,
  formatDate,
  formatJson,
  getAuditLog,
  listAuditLogs,
  type AuditLog,
  type AuditLogDetail,
} from "@/lib/audit-logs";

const PAGE_SIZE = 25;

function ActionBadge({ action }: { action: string }) {
  return <StatusBadge tone="info">{action}</StatusBadge>;
}

function EntityBadge({ entityType }: { entityType: string }) {
  return <StatusBadge tone="neutral">{entityType}</StatusBadge>;
}

function AuditDetailPanel({
  log,
  onClose,
}: {
  log: AuditLogDetail;
  onClose: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-4 sm:p-8"
      role="dialog"
      aria-modal="true"
      aria-labelledby="audit-detail-title"
      data-testid="audit-detail-modal"
    >
      <div className="w-full max-w-3xl rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-5">
          <div>
            <h2 id="audit-detail-title" className="text-lg font-semibold text-slate-900">
              Audit Log Details
            </h2>
            <p className="mt-1 text-sm text-slate-600">{log.summary}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-2.5 py-1.5 text-sm text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900"
          >
            Close
          </button>
        </div>

        <div className="space-y-5 px-6 py-6">
          <dl className="grid gap-3 rounded-xl bg-slate-50 p-4 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Time</dt>
              <dd className="mt-1 text-slate-900">{formatDate(log.created_at)}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Actor</dt>
              <dd className="mt-1 text-slate-900">{log.actor_email ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Action</dt>
              <dd className="mt-1">
                <ActionBadge action={log.action} />
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Entity</dt>
              <dd className="mt-1 flex flex-wrap items-center gap-2">
                <EntityBadge entityType={log.entity_type} />
                <span className="font-mono text-xs text-slate-700">{log.entity_id ?? "—"}</span>
              </dd>
            </div>
          </dl>

          <div>
            <h3 className="text-sm font-semibold text-slate-900">Metadata</h3>
            <pre
              className="mt-2 max-h-40 overflow-auto rounded-xl bg-slate-900 p-4 text-xs text-slate-100"
              data-testid="audit-metadata"
            >
              {formatJson(log.metadata)}
            </pre>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">Before</h3>
              <pre
                className="mt-2 max-h-64 overflow-auto rounded-xl bg-slate-900 p-4 text-xs text-slate-100"
                data-testid="audit-before"
              >
                {formatJson(log.before_snapshot)}
              </pre>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-900">After</h3>
              <pre
                className="mt-2 max-h-64 overflow-auto rounded-xl bg-slate-900 p-4 text-xs text-slate-100"
                data-testid="audit-after"
              >
                {formatJson(log.after_snapshot)}
              </pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function AdminAuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [actorEmail, setActorEmail] = useState("");
  const [actionFilter, setActionFilter] = useState("");
  const [entityTypeFilter, setEntityTypeFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const [selectedLog, setSelectedLog] = useState<AuditLogDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const filters = useMemo(
    () => ({
      search: search || undefined,
      actor_email: actorEmail || undefined,
      action: actionFilter || undefined,
      entity_type: entityTypeFilter || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      limit: PAGE_SIZE,
      offset,
    }),
    [search, actorEmail, actionFilter, entityTypeFilter, dateFrom, dateTo, offset],
  );

  const loadLogs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listAuditLogs(filters);
      setLogs(result.items);
      setTotal(result.total);
    } catch (err) {
      setLogs([]);
      setTotal(0);
      setError(err instanceof Error ? err.message : "Failed to load audit logs");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    void loadLogs();
  }, [loadLogs]);

  const applyFilters = () => {
    setSearch(searchInput);
    setOffset(0);
  };

  const hasMore = offset + logs.length < total;
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;
  const lastPage = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const openDetail = async (logId: string) => {
    setDetailLoading(true);
    setError(null);
    try {
      setSelectedLog(await getAuditLog(logId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load audit log details");
    } finally {
      setDetailLoading(false);
    }
  };

  return (
    <div className="space-y-6" data-testid="admin-audit-logs-page">
      <PageHeader
        title="Audit Logs"
        description="Review configuration changes, admin updates, and dashboard actions."
        actions={
          <SecondaryButton onClick={() => void loadLogs()} disabled={loading}>
            Refresh
          </SecondaryButton>
        }
      />

      <FilterBar className="flex-col sm:flex-col sm:items-stretch">
        <div className="grid w-full gap-3 md:grid-cols-2 lg:grid-cols-3">
          <FilterField label="Search">
            <input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Action, entity, actor"
              className={filterInputClass}
              data-testid="audit-search"
            />
          </FilterField>
          <FilterField label="Actor email">
            <input
              value={actorEmail}
              onChange={(e) => setActorEmail(e.target.value)}
              placeholder="admin@example.com"
              className={filterInputClass}
            />
          </FilterField>
          <FilterField label="Action">
            <select
              value={actionFilter}
              onChange={(e) => {
                setActionFilter(e.target.value);
                setOffset(0);
              }}
              className={filterSelectClass}
            >
              <option value="">All actions</option>
              {COMMON_ACTIONS.map((action) => (
                <option key={action} value={action}>
                  {action}
                </option>
              ))}
            </select>
          </FilterField>
          <FilterField label="Entity type">
            <select
              value={entityTypeFilter}
              onChange={(e) => {
                setEntityTypeFilter(e.target.value);
                setOffset(0);
              }}
              className={filterSelectClass}
            >
              <option value="">All entity types</option>
              {COMMON_ENTITY_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </FilterField>
          <FilterField label="From">
            <EworksInput type="datetime-local" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </FilterField>
          <FilterField label="To">
            <EworksInput type="datetime-local" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </FilterField>
        </div>
        <div>
          <PrimaryButton onClick={applyFilters}>Apply filters</PrimaryButton>
        </div>
      </FilterBar>

      {loading ? (
        <LoadingState message="Loading audit logs…" />
      ) : error ? (
        <ErrorState message={error} />
      ) : logs.length === 0 ? (
        <EmptyState title="No audit logs found" description="No audit logs match your filters." />
      ) : (
        <SectionCard padding="none">
          <DataTable testId="audit-logs-table" className="rounded-none border-0 shadow-none">
            <DataTableHead>
              {["Time", "Actor", "Action", "Entity Type", "Entity ID", "Summary", "Actions"].map((heading) => (
                <DataTableCell key={heading} header>
                  {heading}
                </DataTableCell>
              ))}
            </DataTableHead>
            <DataTableBody>
              {logs.map((log) => (
                <DataTableRow key={log.id} data-testid={`audit-row-${log.id}`}>
                  <DataTableCell>
                    <DateText value={log.created_at} includeTime />
                  </DataTableCell>
                  <DataTableCell>{log.actor_email ?? "—"}</DataTableCell>
                  <DataTableCell>
                    <ActionBadge action={log.action} />
                  </DataTableCell>
                  <DataTableCell>
                    <EntityBadge entityType={log.entity_type} />
                  </DataTableCell>
                  <DataTableCell className="font-mono text-xs">{log.entity_id ?? "—"}</DataTableCell>
                  <DataTableCell>{log.summary}</DataTableCell>
                  <DataTableCell>
                    <button
                      type="button"
                      onClick={() => void openDetail(log.id)}
                      className="text-sm font-medium text-blue-600 underline-offset-2 hover:text-blue-700 hover:underline"
                      data-testid={`audit-view-${log.id}`}
                    >
                      View Details
                    </button>
                  </DataTableCell>
                </DataTableRow>
              ))}
            </DataTableBody>
          </DataTable>

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 px-4 py-3 text-sm text-slate-600">
            <p>
              Page {currentPage} of {lastPage} · {total} total
            </p>
            <div className="flex gap-2">
              <SecondaryButton
                disabled={offset <= 0 || loading}
                onClick={() => setOffset((c) => Math.max(0, c - PAGE_SIZE))}
              >
                Previous
              </SecondaryButton>
              <SecondaryButton
                disabled={!hasMore || loading}
                onClick={() => setOffset((c) => c + PAGE_SIZE)}
                data-testid="audit-load-more"
              >
                Next
              </SecondaryButton>
            </div>
          </div>
        </SectionCard>
      )}

      {detailLoading && !selectedLog ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/20">
          <LoadingState message="Loading audit log…" />
        </div>
      ) : null}

      {selectedLog ? <AuditDetailPanel log={selectedLog} onClose={() => setSelectedLog(null)} /> : null}
    </div>
  );
}
