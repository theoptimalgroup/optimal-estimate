"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { EworksInput, EworksLabel } from "@/components/eworks-ui";
import {
  BackLink,
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
  aliasDisplay,
  formatDate,
  getClient,
  listClients,
  updateClient,
  type ClientUpdatePayload,
  type ManagedClient,
} from "@/lib/clients";

const PAGE_SIZE = 25;

function ClientEditPanel({
  client,
  onClose,
  onSaved,
}: {
  client: ManagedClient;
  onClose: () => void;
  onSaved: (client: ManagedClient) => void;
}) {
  const [name, setName] = useState(client.name || "");
  const [billingEmail, setBillingEmail] = useState(client.billing_email ?? "");
  const [vatRate, setVatRate] = useState(String(client.default_vat_rate ?? "20"));
  const [isActive, setIsActive] = useState(client.is_active);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    if (!name.trim()) {
      setError("Client name is required");
      return;
    }
    setSaving(true);
    setError(null);
    const payload: ClientUpdatePayload = {
      name: name.trim(),
      billing_email: billingEmail.trim() || null,
      default_vat_rate: vatRate.trim() || undefined,
      is_active: isActive,
    };
    try {
      const updated = await updateClient(client.id, payload);
      onSaved(updated);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save client");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-4 sm:p-8"
      role="dialog"
      aria-modal="true"
      aria-labelledby="client-edit-title"
      data-testid="client-edit-modal"
    >
      <div className="w-full max-w-2xl rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-100 px-6 py-5">
          <BackLink
            href="/admin/clients"
            label="Back to Clients"
            onClick={(event) => {
              event.preventDefault();
              onClose();
            }}
          />
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 id="client-edit-title" className="text-lg font-semibold text-slate-900">
                Edit Client
              </h2>
              <p className="mt-1 text-sm text-slate-600">{client.name}</p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg px-2.5 py-1.5 text-sm text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900"
            >
              Close
            </button>
          </div>
        </div>

        <div className="space-y-5 px-6 py-6">
          <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            Changing client identity fields can affect rate rule matching. Edit with care.
          </p>

          {error ? <p className="text-sm text-rose-600">{error}</p> : null}

          <EworksLabel>
            Client Name *
            <EworksInput value={name} onChange={(e) => setName(e.target.value)} data-testid="client-name-input" />
          </EworksLabel>

          <EworksLabel>
            Billing Email
            <EworksInput
              value={billingEmail}
              onChange={(e) => setBillingEmail(e.target.value)}
              placeholder="billing@example.com"
            />
          </EworksLabel>

          <EworksLabel>
            Default VAT Rate (%)
            <EworksInput value={vatRate} onChange={(e) => setVatRate(e.target.value)} />
          </EworksLabel>

          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              data-testid="client-active-checkbox"
            />
            Active client
          </label>

          <dl className="grid gap-3 rounded-xl bg-slate-50 p-4 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Client ID</dt>
              <dd className="mt-1 break-all font-mono text-xs text-slate-900">{client.id}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Aliases / eWorks names</dt>
              <dd className="mt-1 text-slate-900">{aliasDisplay(client.aliases)}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Rate Rules</dt>
              <dd className="mt-1 text-slate-900">{client.rate_rules_count}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Sessions / Quotes</dt>
              <dd className="mt-1 text-slate-900">{client.calculation_sessions_count}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Created</dt>
              <dd className="mt-1 text-slate-900">{formatDate(client.created_at)}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Updated</dt>
              <dd className="mt-1 text-slate-900">{formatDate(client.updated_at)}</dd>
            </div>
          </dl>
        </div>

        <div className="flex flex-wrap items-center justify-end gap-3 border-t border-slate-100 px-6 py-5">
          <SecondaryButton onClick={onClose} disabled={saving}>
            Cancel
          </SecondaryButton>
          <PrimaryButton onClick={() => void handleSave()} disabled={saving} data-testid="client-save">
            {saving ? "Saving…" : "Save Changes"}
          </PrimaryButton>
        </div>
      </div>
    </div>
  );
}

export default function AdminClientsPage() {
  const [clients, setClients] = useState<ManagedClient[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [activeFilter, setActiveFilter] = useState<"all" | "active" | "inactive">("all");

  const [selectedClient, setSelectedClient] = useState<ManagedClient | null>(null);
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

  const loadClients = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listClients(filters);
      setClients(result.items);
      setTotal(result.total);
    } catch (err) {
      setClients([]);
      setTotal(0);
      setError(err instanceof Error ? err.message : "Failed to load clients");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    void loadClients();
  }, [loadClients]);

  const applySearch = () => {
    setSearch(searchInput);
    setOffset(0);
  };

  const hasMore = offset + clients.length < total;
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;
  const lastPage = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const openEdit = async (clientId: string) => {
    setDetailLoading(true);
    setError(null);
    try {
      setSelectedClient(await getClient(clientId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load client details");
    } finally {
      setDetailLoading(false);
    }
  };

  const handleSaved = (updated: ManagedClient) => {
    setClients((current) => current.map((item) => (item.id === updated.id ? updated : item)));
  };

  return (
    <div className="space-y-6" data-testid="admin-clients-page">
      <PageHeader
        title="Clients"
        description="Manage client records used for rate rules and calculation sessions."
        actions={
          <SecondaryButton onClick={() => void loadClients()} disabled={loading}>
            Refresh
          </SecondaryButton>
        }
      />

      <FilterBar>
        <FilterField label="Search">
          <input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Name or alias"
            className={filterInputClass}
            data-testid="clients-search"
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
            data-testid="clients-status-filter"
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
        <LoadingState message="Loading clients…" />
      ) : error ? (
        <ErrorState message={error} />
      ) : clients.length === 0 ? (
        <EmptyState title="No clients found" description="No clients match your filters." />
      ) : (
        <SectionCard padding="none">
          <DataTable testId="clients-table" className="rounded-none border-0 shadow-none">
            <DataTableHead>
              {["Client Name", "Aliases", "Status", "Rate Rules", "Sessions", "Updated At", "Actions"].map(
                (heading) => (
                  <DataTableCell key={heading} header>
                    {heading}
                  </DataTableCell>
                ),
              )}
            </DataTableHead>
            <DataTableBody>
              {clients.map((client) => (
                <DataTableRow key={client.id} data-testid={`client-row-${client.id}`}>
                  <DataTableCell className="font-medium text-slate-900">{client.name?.trim() || "—"}</DataTableCell>
                  <DataTableCell>{aliasDisplay(client.aliases)}</DataTableCell>
                  <DataTableCell>
                    <StatusBadge tone={activeStatusTone(client.is_active)}>
                      {client.is_active ? "Active" : "Inactive"}
                    </StatusBadge>
                  </DataTableCell>
                  <DataTableCell>{client.rate_rules_count}</DataTableCell>
                  <DataTableCell>{client.calculation_sessions_count}</DataTableCell>
                  <DataTableCell>
                    <DateText value={client.updated_at} includeTime />
                  </DataTableCell>
                  <DataTableCell>
                    <button
                      type="button"
                      onClick={() => void openEdit(client.id)}
                      className="text-sm font-medium text-blue-600 underline-offset-2 hover:text-blue-700 hover:underline"
                      data-testid={`client-edit-${client.id}`}
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
                data-testid="clients-load-more"
              >
                Next
              </SecondaryButton>
            </div>
          </div>
        </SectionCard>
      )}

      {detailLoading && !selectedClient ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/20">
          <LoadingState message="Loading client…" />
        </div>
      ) : null}

      {selectedClient ? (
        <ClientEditPanel client={selectedClient} onClose={() => setSelectedClient(null)} onSaved={handleSaved} />
      ) : null}
    </div>
  );
}
