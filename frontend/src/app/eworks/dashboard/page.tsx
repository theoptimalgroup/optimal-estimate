"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { SubmittedQuotesList, SubmittedQuotesUnlockForm } from "@/components/dashboard/submitted-quotes-list";
import {
  EworksButton,
  EworksLoadingScreen,
  DashboardPageShell,
} from "@/components/eworks-ui";
import {
  clearDashboardPassword,
  readDashboardPassword,
  storeDashboardPassword,
  type DashboardQuoteItem,
} from "@/lib/dashboard";
import { createPasswordDashboardClient } from "@/lib/dashboard-client";

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
      const client = createPasswordDashboardClient(dashboardPassword);
      const response = await client.fetchSubmittedQuotes();
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
      <SubmittedQuotesUnlockForm
        password={password}
        onPasswordChange={setPassword}
        onSubmit={handleUnlock}
        loading={loading}
        error={error}
      />
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
          <p className="text-sm font-medium text-gray-900">Quote {unlockedQuote} is unlocked.</p>
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
      <SubmittedQuotesList
        quotes={quotes}
        loading={loading}
        error={error}
        detailHref={(sessionId) => `/eworks/dashboard/${sessionId}`}
      />
    </DashboardPageShell>
  );
}
