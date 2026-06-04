"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { EworksButton, EworksInput, EworksLabel } from "@/components/eworks-ui";
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
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">My Jobs</h1>
        <p className="mt-2 text-sm text-gray-600">
          Open a site visit session using the session ID and token from your eWorks estimate link.
        </p>
      </div>

      <div
        className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm"
        data-testid="engineer-open-session-card"
      >
        <h2 className="text-lg font-semibold text-gray-900">Open site visit session</h2>
        <p className="mt-2 text-sm text-gray-600">
          After opening an eWorks calculation link, copy the session ID and token from the link URL or from your
          estimator. Paste them below to continue the site visit on this device.
        </p>
        <div className="mt-4 space-y-4">
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
          {error && <p className="text-sm font-medium text-red-600">{error}</p>}
          <EworksButton type="button" onClick={openSession} data-testid="engineer-open-session-button">
            Open site visit
          </EworksButton>
        </div>
      </div>

      {IS_DEV && (
        <div className="rounded-lg border border-dashed border-amber-300 bg-amber-50 p-5">
          <h3 className="text-sm font-semibold text-amber-900">Development</h3>
          <p className="mt-1 text-sm text-amber-800">
            Create a test calculation session without an eWorks signed link.
          </p>
          <EworksButton
            type="button"
            variant="secondary"
            className="mt-3"
            disabled={isCreatingDev}
            onClick={() => void handleDevBootstrap()}
            data-testid="engineer-dev-bootstrap-button"
          >
            {isCreatingDev ? "Creating…" : "Create dev test session"}
          </EworksButton>
        </div>
      )}

      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm text-gray-700">
        <p className="font-semibold text-gray-900">How to find your session</p>
        <ol className="mt-2 list-decimal space-y-1 pl-5">
          <li>Open the eWorks estimate link sent for the job (or ask your estimator).</li>
          <li>
            The URL contains <code className="rounded bg-white px-1">session_id</code> and{" "}
            <code className="rounded bg-white px-1">token</code> query parameters after the session loads.
          </li>
          <li>Paste both values above, or use the dev button in local development.</li>
        </ol>
        <p className="mt-3">
          Need help? Contact your estimator — this page does not show pricing or approval controls.
        </p>
      </div>

      <p className="text-sm text-gray-500">
        <Link href="/engineer/submitted" className="text-optimal-orange underline underline-offset-2">
          View submitted jobs
        </Link>{" "}
        (coming soon)
      </p>
    </div>
  );
}
