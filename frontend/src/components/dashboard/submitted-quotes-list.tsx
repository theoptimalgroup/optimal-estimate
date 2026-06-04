"use client";

import { EworksButton, EworksInput, EworksLabel, EworksLoadingScreen } from "@/components/eworks-ui";
import { QuotesTable } from "@/components/eworks-dashboard";
import type { DashboardQuoteItem } from "@/lib/dashboard";

type SubmittedQuotesListProps = {
  quotes: DashboardQuoteItem[];
  loading?: boolean;
  error?: string | null;
  detailHref: (sessionId: string) => string;
};

export function SubmittedQuotesList({ quotes, loading, error, detailHref }: SubmittedQuotesListProps) {
  if (loading) {
    return <EworksLoadingScreen message="Loading submitted quotes…" />;
  }

  if (error) {
    return (
      <div className="rounded-lg border border-gray-200 bg-optimal-elevated p-6 text-center">
        <p className="text-sm text-red-600">{error}</p>
      </div>
    );
  }

  if (quotes.length === 0) {
    return (
      <div className="rounded-lg border border-gray-200 bg-optimal-elevated p-6 text-center">
        <p className="text-sm text-optimal-muted">No submitted quotes yet.</p>
      </div>
    );
  }

  return <QuotesTable quotes={quotes} detailHref={detailHref} />;
}

export function SubmittedQuotesUnlockForm({
  password,
  onPasswordChange,
  onSubmit,
  loading,
  error,
}: {
  password: string;
  onPasswordChange: (value: string) => void;
  onSubmit: (event: React.FormEvent) => void;
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <div className="min-h-screen bg-gray-50 px-6 py-10 lg:px-8">
      <div className="mx-auto w-full max-w-lg space-y-6">
        <div className="space-y-2 text-center">
          <h1 className="text-2xl font-bold uppercase tracking-wide text-gray-900">Submitted Quotes</h1>
          <p className="text-sm text-optimal-muted">Enter the dashboard password to view submitted estimates.</p>
        </div>
        <form
          className="space-y-4 rounded-lg border border-gray-200 bg-optimal-elevated p-5"
          onSubmit={(event) => void onSubmit(event)}
        >
          <EworksLabel>
            Dashboard password
            <EworksInput
              type="password"
              value={password}
              onChange={(event) => onPasswordChange(event.target.value)}
              autoComplete="current-password"
            />
          </EworksLabel>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <EworksButton className="w-full" type="submit" disabled={loading || !password.trim()}>
            {loading ? "Checking…" : "Unlock dashboard"}
          </EworksButton>
        </form>
      </div>
    </div>
  );
}
