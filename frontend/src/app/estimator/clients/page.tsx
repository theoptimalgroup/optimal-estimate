"use client";

import { useCallback, useEffect, useState } from "react";

import {
  activeStatusTone,
  DataTable,
  DataTableBody,
  DataTableCell,
  DataTableHead,
  DataTableRow,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  SecondaryButton,
  SectionCard,
  StatusBadge,
} from "@/components/ui";
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
      <PageHeader
        title="Clients"
        description="Read-only list of active clients available for estimates"
        actions={
          <SecondaryButton onClick={() => void loadClients()} disabled={loading}>
            Refresh
          </SecondaryButton>
        }
      />

      {loading ? (
        <LoadingState message="Loading clients…" />
      ) : error ? (
        <ErrorState message={error} onRetry={() => void loadClients()} />
      ) : clients.length === 0 ? (
        <EmptyState title="No clients" description="No active clients found." />
      ) : (
        <SectionCard padding="none">
          <DataTable testId="estimator-clients-table">
            <DataTableHead>
              <DataTableCell header>Client</DataTableCell>
              <DataTableCell header>Aliases</DataTableCell>
              <DataTableCell header>Status</DataTableCell>
            </DataTableHead>
            <DataTableBody>
              {clients.map((client) => (
                <DataTableRow key={client.id}>
                  <DataTableCell className="font-medium text-slate-900">{client.name}</DataTableCell>
                  <DataTableCell>{client.aliases.length ? client.aliases.join(", ") : "—"}</DataTableCell>
                  <DataTableCell>
                    <StatusBadge tone={activeStatusTone(true)}>Active</StatusBadge>
                  </DataTableCell>
                </DataTableRow>
              ))}
            </DataTableBody>
          </DataTable>
        </SectionCard>
      )}
    </div>
  );
}
