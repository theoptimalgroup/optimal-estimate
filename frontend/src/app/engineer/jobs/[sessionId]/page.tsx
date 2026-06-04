"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { SiteVisitForm } from "@/components/engineer/site-visit-form";
import { EworksButton, EworksInput, EworksLabel, EworksLoadingScreen } from "@/components/eworks-ui";
import {
  fetchEngineerSession,
  readEngineerSessionCredentials,
  storeEngineerSessionCredentials,
  type EngineerSession,
} from "@/lib/engineer-session";

export default function EngineerSiteVisitPage() {
  const params = useParams<{ sessionId: string }>();
  const searchParams = useSearchParams();
  const sessionId = params.sessionId;

  const [tokenInput, setTokenInput] = useState("");
  const [sessionToken, setSessionToken] = useState<string | null>(null);
  const [session, setSession] = useState<EngineerSession | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const resolveToken = useCallback(() => {
    const fromQuery = searchParams.get("token")?.trim();
    if (fromQuery) return fromQuery;
    return readEngineerSessionCredentials(sessionId);
  }, [searchParams, sessionId]);

  const loadSession = useCallback(
    async (token: string) => {
      setIsLoading(true);
      setLoadError(null);
      try {
        const data = await fetchEngineerSession(sessionId, token);
        storeEngineerSessionCredentials(sessionId, token);
        setSessionToken(token);
        setSession(data);
      } catch (err) {
        setSession(null);
        setLoadError(err instanceof Error ? err.message : "Failed to load session");
      } finally {
        setIsLoading(false);
      }
    },
    [sessionId],
  );

  useEffect(() => {
    const token = resolveToken();
    if (token) {
      setTokenInput(token);
      void loadSession(token);
    }
  }, [resolveToken, loadSession]);

  const handleConnect = () => {
    const token = tokenInput.trim();
    if (!token) {
      setLoadError("Session token is required.");
      return;
    }
    void loadSession(token);
  };

  if (!sessionToken && !isLoading) {
    return (
      <div className="mx-auto max-w-lg space-y-4 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <h1 className="text-xl font-semibold text-gray-900">Connect to site visit</h1>
        <p className="text-sm text-gray-600">
          Enter the session token for job <span className="font-mono text-xs">{sessionId}</span>.
        </p>
        <EworksLabel>
          Session token
          <EworksInput
            value={tokenInput}
            onChange={(event) => setTokenInput(event.target.value)}
            data-testid="engineer-detail-token-input"
          />
        </EworksLabel>
        {loadError && <p className="text-sm text-red-600">{loadError}</p>}
        <div className="flex gap-3">
          <EworksButton type="button" onClick={handleConnect} data-testid="engineer-detail-connect-button">
            Load session
          </EworksButton>
          <Link href="/engineer/jobs" className="text-sm text-gray-600 underline underline-offset-2">
            Back to jobs
          </Link>
        </div>
      </div>
    );
  }

  if (isLoading || !session || !sessionToken) {
    return <EworksLoadingScreen message="Loading site visit…" />;
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Site visit</h1>
          <p className="text-sm text-gray-600">
            {session.job.quote_number} · {session.job.client_name}
          </p>
        </div>
        <Link href="/engineer/jobs" className="text-sm text-gray-600 underline underline-offset-2">
          All jobs
        </Link>
      </div>
      {loadError && <p className="text-sm text-red-600">{loadError}</p>}
      <SiteVisitForm
        session={session}
        sessionToken={sessionToken}
        onSaved={() => void loadSession(sessionToken)}
      />
    </div>
  );
}
