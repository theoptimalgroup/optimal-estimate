"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { EworksButton, EworksInput, EworksLabel, EworksLoadingScreen } from "@/components/eworks-ui";
import {
  formatDate,
  getTrade,
  listTrades,
  updateTrade,
  type ManagedTrade,
  type TradeUpdatePayload,
} from "@/lib/trades";

const PAGE_SIZE = 25;

function StatusBadge({ active }: { active: boolean }) {
  return (
    <span
      className={
        active
          ? "inline-flex rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800"
          : "inline-flex rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700"
      }
    >
      {active ? "Active" : "Inactive"}
    </span>
  );
}

function TradeEditPanel({
  trade,
  onClose,
  onSaved,
}: {
  trade: ManagedTrade;
  onClose: () => void;
  onSaved: (trade: ManagedTrade) => void;
}) {
  const [name, setName] = useState(trade.name || "");
  const [description, setDescription] = useState(trade.description ?? "");
  const [isActive, setIsActive] = useState(trade.is_active);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    if (!name.trim()) {
      setError("Trade name is required");
      return;
    }
    setSaving(true);
    setError(null);
    const payload: TradeUpdatePayload = {
      name: name.trim(),
      description,
      is_active: isActive,
    };
    try {
      const updated = await updateTrade(trade.id, payload);
      onSaved(updated);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save trade");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-4 sm:p-8"
      role="dialog"
      aria-modal="true"
      aria-labelledby="trade-edit-title"
      data-testid="trade-edit-modal"
    >
      <div className="w-full max-w-2xl rounded-lg border border-gray-200 bg-white shadow-xl">
        <div className="flex items-start justify-between gap-4 border-b border-gray-200 px-6 py-4">
          <div>
            <h2 id="trade-edit-title" className="text-lg font-semibold text-gray-900">
              Edit Trade
            </h2>
            <p className="mt-1 text-sm text-gray-600">{trade.name}</p>
          </div>
          <button type="button" onClick={onClose} className="rounded-md px-2 py-1 text-sm text-gray-500 hover:bg-gray-100">
            Close
          </button>
        </div>

        <div className="space-y-4 px-6 py-5">
          <p className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            Trade changes may affect rate rule lookup and calculator dropdowns.
          </p>

          {error ? <p className="text-sm text-red-600">{error}</p> : null}

          <EworksLabel>
            Trade Name *
            <EworksInput value={name} onChange={(e) => setName(e.target.value)} data-testid="trade-name-input" />
          </EworksLabel>

          <EworksLabel>
            Description
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={4}
              className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3.5 py-2.5 text-sm text-gray-900 shadow-sm focus:border-optimal-orange focus:outline-none focus:ring-2 focus:ring-optimal-orange/30"
              data-testid="trade-description-input"
            />
          </EworksLabel>

          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-gray-900 focus:ring-optimal-orange"
              data-testid="trade-active-checkbox"
            />
            Active trade
          </label>

          <dl className="grid gap-3 rounded-lg bg-gray-50 p-4 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">Trade ID</dt>
              <dd className="mt-1 break-all font-mono text-xs text-gray-900">{trade.id}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">Rate Rules</dt>
              <dd className="mt-1 text-gray-900">{trade.rate_rules_count}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">Products (by category)</dt>
              <dd className="mt-1 text-gray-900">{trade.products_count}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">Created</dt>
              <dd className="mt-1 text-gray-900">{formatDate(trade.created_at)}</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">Updated</dt>
              <dd className="mt-1 text-gray-900">{formatDate(trade.updated_at)}</dd>
            </div>
          </dl>
        </div>

        <div className="flex flex-wrap items-center justify-end gap-3 border-t border-gray-200 px-6 py-4">
          <EworksButton type="button" variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </EworksButton>
          <EworksButton type="button" onClick={() => void handleSave()} disabled={saving} data-testid="trade-save">
            {saving ? "Saving…" : "Save Changes"}
          </EworksButton>
        </div>
      </div>
    </div>
  );
}

export default function AdminTradesPage() {
  const [trades, setTrades] = useState<ManagedTrade[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [activeFilter, setActiveFilter] = useState<"all" | "active" | "inactive">("all");

  const [selectedTrade, setSelectedTrade] = useState<ManagedTrade | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const filters = useMemo(
    () => ({
      search: search || undefined,
      active: activeFilter === "all" ? undefined : activeFilter === "active",
      limit: PAGE_SIZE,
      offset,
    }),
    [search, activeFilter, offset],
  );

  const loadTrades = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listTrades(filters);
      setTrades(result.items);
      setTotal(result.total);
    } catch (err) {
      setTrades([]);
      setTotal(0);
      setError(err instanceof Error ? err.message : "Failed to load trades");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    void loadTrades();
  }, [loadTrades]);

  const applySearch = () => {
    setSearch(searchInput);
    setOffset(0);
  };

  const hasMore = offset + trades.length < total;
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;
  const lastPage = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const openEdit = async (tradeId: string) => {
    setDetailLoading(true);
    setError(null);
    try {
      setSelectedTrade(await getTrade(tradeId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load trade details");
    } finally {
      setDetailLoading(false);
    }
  };

  const handleSaved = (updated: ManagedTrade) => {
    setTrades((current) => current.map((item) => (item.id === updated.id ? updated : item)));
  };

  return (
    <div className="space-y-6" data-testid="admin-trades-page">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Trades</h1>
          <p className="mt-2 text-sm text-gray-600">Maintain trade categories used in rate rules and the estimate calculator.</p>
        </div>
        <EworksButton type="button" variant="secondary" onClick={() => void loadTrades()} disabled={loading}>
          Refresh
        </EworksButton>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <div className="grid gap-4 md:grid-cols-3">
          <EworksLabel>
            Search
            <EworksInput
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Name or description"
              data-testid="trades-search"
            />
          </EworksLabel>
          <EworksLabel>
            Status
            <select
              value={activeFilter}
              onChange={(e) => {
                setActiveFilter(e.target.value as "all" | "active" | "inactive");
                setOffset(0);
              }}
              className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3.5 py-2.5 text-sm text-gray-900 shadow-sm focus:border-optimal-orange focus:outline-none focus:ring-2 focus:ring-optimal-orange/30"
              data-testid="trades-status-filter"
            >
              <option value="all">All statuses</option>
              <option value="active">Active only</option>
              <option value="inactive">Inactive only</option>
            </select>
          </EworksLabel>
          <div className="flex flex-col justify-end">
            <EworksButton type="button" onClick={applySearch}>
              Apply search
            </EworksButton>
          </div>
        </div>
      </div>

      {loading ? (
        <EworksLoadingScreen message="Loading trades…" />
      ) : error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      ) : trades.length === 0 ? (
        <div className="rounded-lg border border-gray-200 bg-white p-6 text-center">
          <p className="text-sm text-gray-600">No trades match your filters.</p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm" data-testid="trades-table">
              <thead className="bg-gray-50">
                <tr>
                  {["Trade Name", "Status", "Rate Rules", "Products", "Updated At", "Actions"].map((heading) => (
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
                {trades.map((trade) => (
                  <tr key={trade.id} data-testid={`trade-row-${trade.id}`}>
                    <td className="px-4 py-3 font-medium text-gray-900">{trade.name?.trim() || "—"}</td>
                    <td className="px-4 py-3">
                      <StatusBadge active={trade.is_active} />
                    </td>
                    <td className="px-4 py-3 text-gray-700">{trade.rate_rules_count}</td>
                    <td className="px-4 py-3 text-gray-700">{trade.products_count}</td>
                    <td className="px-4 py-3 text-gray-700">{formatDate(trade.updated_at)}</td>
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        onClick={() => void openEdit(trade.id)}
                        className="text-sm font-medium text-gray-900 underline-offset-2 hover:underline"
                        data-testid={`trade-edit-${trade.id}`}
                      >
                        View / Edit
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
                data-testid="trades-load-more"
              >
                Next
              </EworksButton>
            </div>
          </div>
        </div>
      )}

      {detailLoading && !selectedTrade ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/20">
          <EworksLoadingScreen message="Loading trade…" />
        </div>
      ) : null}

      {selectedTrade ? (
        <TradeEditPanel trade={selectedTrade} onClose={() => setSelectedTrade(null)} onSaved={handleSaved} />
      ) : null}
    </div>
  );
}
