"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { SiteVisitForm } from "@/components/engineer/site-visit-form";
import { EworksInput, EworksLabel } from "@/components/eworks-ui";
import {
  ErrorState,
  LoadingState,
  PageHeader,
  PrimaryButton,
  SectionCard,
} from "@/components/ui";
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
      <div className="mx-auto max-w-lg space-y-6">
        <PageHeader
          title="Connect to site visit"
          description={`Enter the session token for job ${sessionId}.`}
        />
        <SectionCard>
          <div className="space-y-4">
            <EworksLabel>
              Session token
              <EworksInput
                value={tokenInput}
                onChange={(event) => setTokenInput(event.target.value)}
                data-testid="engineer-detail-token-input"
              />
            </EworksLabel>
            {loadError ? <ErrorState title="Connection failed" message={loadError} className="py-3" /> : null}
            <div className="flex flex-wrap items-center gap-3">
              <PrimaryButton type="button" onClick={handleConnect} data-testid="engineer-detail-connect-button">
                Load session
              </PrimaryButton>
              <Link href="/engineer/jobs" className="text-sm font-medium text-slate-600 underline underline-offset-2 hover:text-slate-900">
                Back to jobs
              </Link>
            </div>
          </div>
        </SectionCard>
      </div>
    );
  }

  if (isLoading || !session || !sessionToken) {
    return <LoadingState message="Loading site visit…" className="min-h-[50vh]" />;
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PageHeader
        title="Site visit"
        description={`${session.job.quote_number} · ${session.job.client_name}`}
        actions={
          <Link href="/engineer/jobs" className="text-sm font-medium text-slate-600 underline underline-offset-2 hover:text-slate-900">
            All jobs
          </Link>
        }
      />
      {loadError ? <ErrorState message={loadError} onRetry={() => void loadSession(sessionToken)} /> : null}
      <SiteVisitForm
        session={session}
        sessionToken={sessionToken}
        onSaved={() => void loadSession(sessionToken)}
      />
    </div>
  );
}
