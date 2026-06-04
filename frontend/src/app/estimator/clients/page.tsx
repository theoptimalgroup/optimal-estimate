"use client";

import { useCallback, useEffect, useState } from "react";

import { EworksButton, EworksLoadingScreen } from "@/components/eworks-ui";
import { listEstimatorClients, type EstimatorClient } from "@/lib/estimator";

export default function EstimatorClientsPage() {
  const [clients, setClients] = useState<EstimatorClient[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadClients = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setClients(await listEstimatorClients());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load clients");
      setClients([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadClients();
  }, [loadClients]);

  return (
    <div className="space-y-6" data-testid="estimator-clients-page">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Clients</h1>
          <p className="mt-2 text-sm text-gray-600">Read-only list of active clients available for estimates</p>
        </div>
        <EworksButton type="button" onClick={() => void loadClients()} disabled={loading}>
          Refresh
        </EworksButton>
      </div>

      {loading ? (
        <EworksLoadingScreen message="Loading clients…" />
      ) : error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      ) : clients.length === 0 ? (
        <p className="text-sm text-gray-500">No active clients found.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-gray-200 text-sm" data-testid="estimator-clients-table">
            <thead className="bg-gray-50">
              <tr>
                {["Client", "Aliases", "Status"].map((header) => (
                  <th key={header} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {clients.map((client) => (
                <tr key={client.id}>
                  <td className="px-4 py-3 font-medium text-gray-900">{client.name}</td>
                  <td className="px-4 py-3 text-gray-700">{client.aliases.length ? client.aliases.join(", ") : "—"}</td>
                  <td className="px-4 py-3">
                    <span className="inline-flex rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800">
                      Active
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
