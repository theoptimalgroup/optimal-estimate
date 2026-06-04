"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { EworksButton, EworksInput, EworksLabel, EworksLoadingScreen } from "@/components/eworks-ui";
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
      <div className="w-full max-w-2xl rounded-lg border border-gray-200 bg-white shadow-xl">
        <div className="flex items-start justify-between gap-4 border-b border-gray-200 px-6 py-4">
          <div>
            <h2 id="client-edit-title" className="text-lg font-semibold text-gray-900">
              Edit Client
            </h2>
            <p className="mt-1 text-sm text-gray-600">{client.name}</p>
          </div>
          <button type="button" onClick={onClose} className="rounded-md px-2 py-1 text-sm text-gray-500 hover:bg-gray-100">
            Close
          </button>
        </div>

        <div className="space-y-4 px-6 py-5">
          <p className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            Changing client identity fields can affect rate rule matching. Edit with care.
          </p>

          {error ? <p className="text-sm text-red-600">{error}</p> : null}

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

          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-gray-900 focus:ring-optimal-orange"
              data-testid="client-active-checkbox"
            />
            Active client
          </label>

          <dl className="grid gap-3 rounded-lg bg-gray-50 p-4 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">Client ID</dt>
              <dd className="mt-1 break-all font-mono text-xs text-gray-900">{client.id}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">Aliases / eWorks names</dt>
              <dd className="mt-1 text-gray-900">{aliasDisplay(client.aliases)}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">Rate Rules</dt>
              <dd className="mt-1 text-gray-900">{client.rate_rules_count}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">Sessions / Quotes</dt>
              <dd className="mt-1 text-gray-900">{client.calculation_sessions_count}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">Created</dt>
              <dd className="mt-1 text-gray-900">{formatDate(client.created_at)}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">Updated</dt>
              <dd className="mt-1 text-gray-900">{formatDate(client.updated_at)}</dd>
            </div>
          </dl>
        </div>

        <div className="flex flex-wrap items-center justify-end gap-3 border-t border-gray-200 px-6 py-4">
          <EworksButton type="button" variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </EworksButton>
          <EworksButton type="button" onClick={() => void handleSave()} disabled={saving} data-testid="client-save">
            {saving ? "Saving…" : "Save Changes"}
          </EworksButton>
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
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Clients</h1>
          <p className="mt-2 text-sm text-gray-600">Manage client records used for rate rules and calculation sessions.</p>
        </div>
        <EworksButton type="button" variant="secondary" onClick={() => void loadClients()} disabled={loading}>
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
              placeholder="Name or alias"
              data-testid="clients-search"
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
              data-testid="clients-status-filter"
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
        <EworksLoadingScreen message="Loading clients…" />
      ) : error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      ) : clients.length === 0 ? (
        <div className="rounded-lg border border-gray-200 bg-white p-6 text-center">
          <p className="text-sm text-gray-600">No clients match your filters.</p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm" data-testid="clients-table">
              <thead className="bg-gray-50">
                <tr>
                  {[
                    "Client Name",
                    "Aliases",
                    "Status",
                    "Rate Rules",
                    "Sessions",
                    "Updated At",
                    "Actions",
                  ].map((heading) => (
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
                {clients.map((client) => (
                  <tr key={client.id} data-testid={`client-row-${client.id}`}>
                    <td className="px-4 py-3 font-medium text-gray-900">{client.name?.trim() || "—"}</td>
                    <td className="px-4 py-3 text-gray-700">{aliasDisplay(client.aliases)}</td>
                    <td className="px-4 py-3">
                      <StatusBadge active={client.is_active} />
                    </td>
                    <td className="px-4 py-3 text-gray-700">{client.rate_rules_count}</td>
                    <td className="px-4 py-3 text-gray-700">{client.calculation_sessions_count}</td>
                    <td className="px-4 py-3 text-gray-700">{formatDate(client.updated_at)}</td>
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        onClick={() => void openEdit(client.id)}
                        className="text-sm font-medium text-gray-900 underline-offset-2 hover:underline"
                        data-testid={`client-edit-${client.id}`}
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
                data-testid="clients-load-more"
              >
                Next
              </EworksButton>
            </div>
          </div>
        </div>
      )}

      {detailLoading && !selectedClient ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/20">
          <EworksLoadingScreen message="Loading client…" />
        </div>
      ) : null}

      {selectedClient ? (
        <ClientEditPanel client={selectedClient} onClose={() => setSelectedClient(null)} onSaved={handleSaved} />
      ) : null}
    </div>
  );
}
