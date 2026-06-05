"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { EworksInput, EworksLabel } from "@/components/eworks-ui";
import {
  ErrorState,
  PageHeader,
  PrimaryButton,
  SecondaryButton,
  SectionCard,
} from "@/components/ui";
import { buildEngineerJobDetailPath, storeEngineerSessionCredentials } from "@/lib/engineer-session";
import { createDevTestSession } from "@/lib/eworks-session";

const IS_DEV = process.env.NODE_ENV === "development";

export default function EngineerJobsPage() {
  const router = useRouter();
  const [sessionId, setSessionId] = useState("");
  const [sessionToken, setSessionToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isCreatingDev, setIsCreatingDev] = useState(false);

  const openSession = () => {
    const id = sessionId.trim();
    const token = sessionToken.trim();
    if (!id || !token) {
      setError("Session ID and session token are required.");
      return;
    }
    setError(null);
    storeEngineerSessionCredentials(id, token);
    router.push(buildEngineerJobDetailPath(id, token));
  };

  const handleDevBootstrap = async () => {
    setIsCreatingDev(true);
    setError(null);
    try {
      const { data } = await createDevTestSession();
      storeEngineerSessionCredentials(data.session_id, data.session_token);
      router.push(buildEngineerJobDetailPath(data.session_id, data.session_token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create dev session");
    } finally {
      setIsCreatingDev(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <PageHeader
        title="My Jobs"
        description="Open a site visit session using the session ID and token from your eWorks estimate link."
      />

      <div data-testid="engineer-open-session-card">
        <SectionCard
          title="Open site visit session"
          description="After opening an eWorks calculation link, copy the session ID and token from the link URL or from your estimator. Paste them below to continue the site visit on this device."
        >
        <div className="space-y-4">
          <EworksLabel>
            Session ID
            <EworksInput
              value={sessionId}
              onChange={(event) => setSessionId(event.target.value)}
              placeholder="e.g. 550e8400-e29b-41d4-a716-446655440000"
              data-testid="engineer-session-id-input"
            />
          </EworksLabel>
          <EworksLabel>
            Session token
            <EworksInput
              value={sessionToken}
              onChange={(event) => setSessionToken(event.target.value)}
              placeholder="Paste token from eWorks link"
              data-testid="engineer-session-token-input"
            />
          </EworksLabel>
          {error ? <ErrorState title="Unable to open session" message={error} className="py-3" /> : null}
          <PrimaryButton type="button" onClick={openSession} data-testid="engineer-open-session-button">
            Open site visit
          </PrimaryButton>
        </div>
        </SectionCard>
      </div>

      {IS_DEV ? (
        <SectionCard
          title="Development"
          description="Create a test calculation session without an eWorks signed link."
          className="border-dashed border-amber-300 bg-amber-50/60"
        >
          <SecondaryButton
            type="button"
            disabled={isCreatingDev}
            onClick={() => void handleDevBootstrap()}
            data-testid="engineer-dev-bootstrap-button"
          >
            {isCreatingDev ? "Creating…" : "Create dev test session"}
          </SecondaryButton>
        </SectionCard>
      ) : null}

      <SectionCard title="How to find your session" padding="sm">
        <ol className="list-decimal space-y-1.5 pl-5 text-sm text-slate-700">
          <li>Open the eWorks estimate link sent for the job (or ask your estimator).</li>
          <li>
            The URL contains <code className="rounded bg-slate-100 px-1">session_id</code> and{" "}
            <code className="rounded bg-slate-100 px-1">token</code> query parameters after the session loads.
          </li>
          <li>Paste both values above, or use the dev button in local development.</li>
        </ol>
        <p className="mt-3 text-sm text-slate-600">
          Need help? Contact your estimator — this page does not show pricing or approval controls.
        </p>
      </SectionCard>

      <p className="text-sm text-slate-500">
        <Link href="/engineer/submitted" className="font-medium text-blue-600 underline underline-offset-2 hover:text-blue-700">
          View submitted jobs
        </Link>{" "}
        (coming soon)
      </p>
    </div>
  );
}
