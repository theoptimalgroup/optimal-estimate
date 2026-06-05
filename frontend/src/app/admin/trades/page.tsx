"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { EworksInput, EworksLabel } from "@/components/eworks-ui";
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
  activeStatusTone,
  filterInputClass,
  filterSelectClass,
} from "@/components/ui";
import {
  formatDate,
  getTrade,
  listTrades,
  updateTrade,
  type ManagedTrade,
  type TradeUpdatePayload,
} from "@/lib/trades";

const PAGE_SIZE = 25;

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
      <div className="w-full max-w-2xl rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-5">
          <div>
            <h2 id="trade-edit-title" className="text-lg font-semibold text-slate-900">
              Edit Trade
            </h2>
            <p className="mt-1 text-sm text-slate-600">{trade.name}</p>
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
          <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            Trade changes may affect rate rule lookup and calculator dropdowns.
          </p>

          {error ? <p className="text-sm text-rose-600">{error}</p> : null}

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
              className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              data-testid="trade-description-input"
            />
          </EworksLabel>

          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              data-testid="trade-active-checkbox"
            />
            Active trade
          </label>

          <dl className="grid gap-3 rounded-xl bg-slate-50 p-4 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Trade ID</dt>
              <dd className="mt-1 break-all font-mono text-xs text-slate-900">{trade.id}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Rate Rules</dt>
              <dd className="mt-1 text-slate-900">{trade.rate_rules_count}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Products (by category)</dt>
              <dd className="mt-1 text-slate-900">{trade.products_count}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Created</dt>
              <dd className="mt-1 text-slate-900">{formatDate(trade.created_at)}</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Updated</dt>
              <dd className="mt-1 text-slate-900">{formatDate(trade.updated_at)}</dd>
            </div>
          </dl>
        </div>

        <div className="flex flex-wrap items-center justify-end gap-3 border-t border-slate-100 px-6 py-5">
          <SecondaryButton onClick={onClose} disabled={saving}>
            Cancel
          </SecondaryButton>
          <PrimaryButton onClick={() => void handleSave()} disabled={saving} data-testid="trade-save">
            {saving ? "Saving…" : "Save Changes"}
          </PrimaryButton>
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
      <PageHeader
        title="Trades"
        description="Maintain trade categories used in rate rules and the estimate calculator."
        actions={
          <SecondaryButton onClick={() => void loadTrades()} disabled={loading}>
            Refresh
          </SecondaryButton>
        }
      />

      <FilterBar>
        <FilterField label="Search">
          <input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Name or description"
            className={filterInputClass}
            data-testid="trades-search"
          />
        </FilterField>
        <FilterField label="Status">
          <select
            value={activeFilter}
            onChange={(e) => {
              setActiveFilter(e.target.value as "all" | "active" | "inactive");
              setOffset(0);
            }}
            className={filterSelectClass}
            data-testid="trades-status-filter"
          >
            <option value="all">All statuses</option>
            <option value="active">Active only</option>
            <option value="inactive">Inactive only</option>
          </select>
        </FilterField>
        <div className="flex shrink-0 items-end">
          <PrimaryButton onClick={applySearch}>Apply search</PrimaryButton>
        </div>
      </FilterBar>

      {loading ? (
        <LoadingState message="Loading trades…" />
      ) : error ? (
        <ErrorState message={error} />
      ) : trades.length === 0 ? (
        <EmptyState title="No trades found" description="No trades match your filters." />
      ) : (
        <SectionCard padding="none">
          <DataTable testId="trades-table" className="rounded-none border-0 shadow-none">
            <DataTableHead>
              {["Trade Name", "Status", "Rate Rules", "Products", "Updated At", "Actions"].map((heading) => (
                <DataTableCell key={heading} header>
                  {heading}
                </DataTableCell>
              ))}
            </DataTableHead>
            <DataTableBody>
              {trades.map((trade) => (
                <DataTableRow key={trade.id} data-testid={`trade-row-${trade.id}`}>
                  <DataTableCell className="font-medium text-slate-900">{trade.name?.trim() || "—"}</DataTableCell>
                  <DataTableCell>
                    <StatusBadge tone={activeStatusTone(trade.is_active)}>
                      {trade.is_active ? "Active" : "Inactive"}
                    </StatusBadge>
                  </DataTableCell>
                  <DataTableCell>{trade.rate_rules_count}</DataTableCell>
                  <DataTableCell>{trade.products_count}</DataTableCell>
                  <DataTableCell>
                    <DateText value={trade.updated_at} includeTime />
                  </DataTableCell>
                  <DataTableCell>
                    <button
                      type="button"
                      onClick={() => void openEdit(trade.id)}
                      className="text-sm font-medium text-blue-600 underline-offset-2 hover:text-blue-700 hover:underline"
                      data-testid={`trade-edit-${trade.id}`}
                    >
                      View / Edit
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
                data-testid="trades-load-more"
              >
                Next
              </SecondaryButton>
            </div>
          </div>
        </SectionCard>
      )}

      {detailLoading && !selectedTrade ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/20">
          <LoadingState message="Loading trade…" />
        </div>
      ) : null}

      {selectedTrade ? (
        <TradeEditPanel trade={selectedTrade} onClose={() => setSelectedTrade(null)} onSaved={handleSaved} />
      ) : null}
    </div>
  );
}
