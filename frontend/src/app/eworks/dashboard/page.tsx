"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import {
  EworksButton,
  EworksInput,
  EworksLabel,
  EworksLoadingScreen,
  DashboardPageShell,
} from "@/components/eworks-ui";
import { QuotesTable } from "@/components/eworks-dashboard";
import {
  clearDashboardPassword,
  fetchSubmittedQuotes,
  readDashboardPassword,
  storeDashboardPassword,
  type DashboardQuoteItem,
} from "@/lib/dashboard";

export default function EworksDashboardPage() {
  return (
    <Suspense fallback={<EworksLoadingScreen message="Loading dashboard…" />}>
      <EworksDashboardContent />
    </Suspense>
  );
}

function EworksDashboardContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const unlockedQuote = searchParams.get("unlocked");
  const unlockedSessionId = searchParams.get("session_id");
  const unlockedSessionToken = searchParams.get("token");

  const [password, setPassword] = useState("");
  const [authenticatedPassword, setAuthenticatedPassword] = useState<string | null>(null);
  const [quotes, setQuotes] = useState<DashboardQuoteItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadQuotes = useCallback(async (dashboardPassword: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchSubmittedQuotes(dashboardPassword);
      setQuotes(response.quotes);
      storeDashboardPassword(dashboardPassword);
      setAuthenticatedPassword(dashboardPassword);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load quotes");
      clearDashboardPassword();
      setAuthenticatedPassword(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const saved = readDashboardPassword();
    if (saved) {
      void loadQuotes(saved);
    }
  }, [loadQuotes]);

  const handleUnlock = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!password.trim()) return;
    await loadQuotes(password.trim());
  };

  const handleSignOut = () => {
    clearDashboardPassword();
    setAuthenticatedPassword(null);
    setQuotes([]);
    setPassword("");
  };

  if (!authenticatedPassword) {
    return (
      <div className="min-h-screen bg-gray-50 px-6 py-10 lg:px-8">
        <div className="mx-auto w-full max-w-lg space-y-6">
          <div className="space-y-2 text-center">
            <h1 className="text-2xl font-bold uppercase tracking-wide text-gray-900">Submitted Quotes</h1>
            <p className="text-sm text-optimal-muted">Enter the dashboard password to view submitted estimates.</p>
          </div>
          <form className="space-y-4 rounded-lg border border-gray-200 bg-optimal-elevated p-5" onSubmit={(event) => void handleUnlock(event)}>
            <EworksLabel>
              Dashboard password
              <EworksInput
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
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

  return (
    <DashboardPageShell
      title="Submitted Quotes"
      subtitle="Select a quote to view works, photos, and internal notes"
      footer={
        <div className="flex justify-end">
          <EworksButton variant="secondary" onClick={handleSignOut}>
            Lock dashboard
          </EworksButton>
        </div>
      }
    >
      {unlockedQuote && (
        <div className="mb-4 rounded-lg border border-optimal-orange/40 bg-optimal-orange/10 p-4">
          <p className="text-sm font-medium text-gray-900">
            Quote {unlockedQuote} is unlocked.
          </p>
          {unlockedSessionId && unlockedSessionToken ? (
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <Link
                href={`/eworks/calculate?session_id=${encodeURIComponent(unlockedSessionId)}&token=${encodeURIComponent(unlockedSessionToken)}`}
              >
                <EworksButton>Open estimating questionnaire</EworksButton>
              </Link>
              <button
                type="button"
                onClick={() => router.replace("/eworks/dashboard")}
                className="text-sm text-optimal-muted underline-offset-2 hover:text-gray-900 hover:underline"
              >
                Dismiss
              </button>
            </div>
          ) : null}
        </div>
      )}
      {loading ? (
        <EworksLoadingScreen message="Loading submitted quotes…" />
      ) : quotes.length === 0 ? (
        <div className="rounded-lg border border-gray-200 bg-optimal-elevated p-6 text-center">
          <p className="text-sm text-optimal-muted">No submitted quotes yet.</p>
        </div>
      ) : (
        <QuotesTable quotes={quotes} />
      )}
    </DashboardPageShell>
  );
}
