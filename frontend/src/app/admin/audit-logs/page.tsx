"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { EworksButton, EworksInput, EworksLabel, EworksLoadingScreen } from "@/components/eworks-ui";
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
  return (
    <span className="inline-flex rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-800">
      {action}
    </span>
  );
}

function EntityBadge({ entityType }: { entityType: string }) {
  return (
    <span className="inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
      {entityType}
    </span>
  );
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
      <div className="w-full max-w-3xl rounded-lg border border-gray-200 bg-white shadow-xl">
        <div className="flex items-start justify-between gap-4 border-b border-gray-200 px-6 py-4">
          <div>
            <h2 id="audit-detail-title" className="text-lg font-semibold text-gray-900">
              Audit Log Details
            </h2>
            <p className="mt-1 text-sm text-gray-600">{log.summary}</p>
          </div>
          <button type="button" onClick={onClose} className="rounded-md px-2 py-1 text-sm text-gray-500 hover:bg-gray-100">
            Close
          </button>
        </div>

        <div className="space-y-4 px-6 py-5">
          <dl className="grid gap-3 rounded-lg bg-gray-50 p-4 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">Time</dt>
              <dd className="mt-1 text-gray-900">{formatDate(log.created_at)}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">Actor</dt>
              <dd className="mt-1 text-gray-900">{log.actor_email ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">Action</dt>
              <dd className="mt-1">
                <ActionBadge action={log.action} />
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">Entity</dt>
              <dd className="mt-1 flex flex-wrap items-center gap-2">
                <EntityBadge entityType={log.entity_type} />
                <span className="font-mono text-xs text-gray-700">{log.entity_id ?? "—"}</span>
              </dd>
            </div>
          </dl>

          <div>
            <h3 className="text-sm font-semibold text-gray-900">Metadata</h3>
            <pre className="mt-2 max-h-40 overflow-auto rounded-lg bg-gray-900 p-3 text-xs text-gray-100" data-testid="audit-metadata">
              {formatJson(log.metadata)}
            </pre>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <h3 className="text-sm font-semibold text-gray-900">Before</h3>
              <pre className="mt-2 max-h-64 overflow-auto rounded-lg bg-gray-900 p-3 text-xs text-gray-100" data-testid="audit-before">
                {formatJson(log.before_snapshot)}
              </pre>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-900">After</h3>
              <pre className="mt-2 max-h-64 overflow-auto rounded-lg bg-gray-900 p-3 text-xs text-gray-100" data-testid="audit-after">
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
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Audit Logs</h1>
          <p className="mt-2 text-sm text-gray-600">
            Review configuration changes, admin updates, and dashboard actions.
          </p>
        </div>
        <EworksButton type="button" variant="secondary" onClick={() => void loadLogs()} disabled={loading}>
          Refresh
        </EworksButton>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <EworksLabel>
            Search
            <EworksInput
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Action, entity, actor"
              data-testid="audit-search"
            />
          </EworksLabel>
          <EworksLabel>
            Actor email
            <EworksInput value={actorEmail} onChange={(e) => setActorEmail(e.target.value)} placeholder="admin@example.com" />
          </EworksLabel>
          <EworksLabel>
            Action
            <select
              value={actionFilter}
              onChange={(e) => {
                setActionFilter(e.target.value);
                setOffset(0);
              }}
              className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3.5 py-2.5 text-sm text-gray-900 shadow-sm focus:border-optimal-orange focus:outline-none focus:ring-2 focus:ring-optimal-orange/30"
            >
              <option value="">All actions</option>
              {COMMON_ACTIONS.map((action) => (
                <option key={action} value={action}>
                  {action}
                </option>
              ))}
            </select>
          </EworksLabel>
          <EworksLabel>
            Entity type
            <select
              value={entityTypeFilter}
              onChange={(e) => {
                setEntityTypeFilter(e.target.value);
                setOffset(0);
              }}
              className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3.5 py-2.5 text-sm text-gray-900 shadow-sm focus:border-optimal-orange focus:outline-none focus:ring-2 focus:ring-optimal-orange/30"
            >
              <option value="">All entity types</option>
              {COMMON_ENTITY_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </EworksLabel>
          <EworksLabel>
            From
            <EworksInput type="datetime-local" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </EworksLabel>
          <EworksLabel>
            To
            <EworksInput type="datetime-local" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </EworksLabel>
        </div>
        <div className="mt-4">
          <EworksButton type="button" onClick={applyFilters}>
            Apply filters
          </EworksButton>
        </div>
      </div>

      {loading ? (
        <EworksLoadingScreen message="Loading audit logs…" />
      ) : error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      ) : logs.length === 0 ? (
        <div className="rounded-lg border border-gray-200 bg-white p-6 text-center">
          <p className="text-sm text-gray-600">No audit logs match your filters.</p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm" data-testid="audit-logs-table">
              <thead className="bg-gray-50">
                <tr>
                  {["Time", "Actor", "Action", "Entity Type", "Entity ID", "Summary", "Actions"].map((heading) => (
                    <th
                      key={heading}
                      scope="col"
                      className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500"
                    >
                      {heading}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {logs.map((log) => (
                  <tr key={log.id} data-testid={`audit-row-${log.id}`}>
                    <td className="px-4 py-3 text-gray-700">{formatDate(log.created_at)}</td>
                    <td className="px-4 py-3 text-gray-700">{log.actor_email ?? "—"}</td>
                    <td className="px-4 py-3">
                      <ActionBadge action={log.action} />
                    </td>
                    <td className="px-4 py-3">
                      <EntityBadge entityType={log.entity_type} />
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-700">{log.entity_id ?? "—"}</td>
                    <td className="px-4 py-3 text-gray-700">{log.summary}</td>
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        onClick={() => void openDetail(log.id)}
                        className="text-sm font-medium text-gray-900 underline-offset-2 hover:underline"
                        data-testid={`audit-view-${log.id}`}
                      >
                        View Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-gray-200 px-4 py-3 text-sm text-gray-600">
            <p>
              Page {currentPage} of {lastPage} · {total} total
            </p>
            <div className="flex gap-2">
              <EworksButton
                type="button"
                variant="secondary"
                disabled={offset <= 0 || loading}
                onClick={() => setOffset((c) => Math.max(0, c - PAGE_SIZE))}
              >
                Previous
              </EworksButton>
              <EworksButton
                type="button"
                variant="secondary"
                disabled={!hasMore || loading}
                onClick={() => setOffset((c) => c + PAGE_SIZE)}
                data-testid="audit-load-more"
              >
                Next
              </EworksButton>
            </div>
          </div>
        </div>
      )}

      {detailLoading && !selectedLog ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/20">
          <EworksLoadingScreen message="Loading audit log…" />
        </div>
      ) : null}

      {selectedLog ? <AuditDetailPanel log={selectedLog} onClose={() => setSelectedLog(null)} /> : null}
    </div>
  );
}
