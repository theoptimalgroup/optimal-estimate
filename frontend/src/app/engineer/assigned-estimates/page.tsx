"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { EngineerAssignmentCard } from "@/components/engineer/engineer-assignment-card";
import { EworksInput, EworksLabel } from "@/components/eworks-ui";
import {
  ErrorState,
  LoadingState,
  PageHeader,
  PrimaryButton,
  SecondaryButton,
  SectionCard,
} from "@/components/ui";
import { buildEngineerJobDetailPath, storeEngineerSessionCredentials } from "@/lib/engineer-session";
import { createDevTestSession } from "@/lib/eworks-session";
import { listMyQuoteAssignments, type QuoteAssignment } from "@/lib/quote-assignments";

const IS_DEV = process.env.NODE_ENV === "development";
const ACTIVE_STATUSES = new Set(["assigned", "in_progress"]);

export default function EngineerAssignedEstimatesPage() {
  const router = useRouter();
  const [sessionId, setSessionId] = useState("");
  const [sessionToken, setSessionToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isCreatingDev, setIsCreatingDev] = useState(false);
  const [assignments, setAssignments] = useState<QuoteAssignment[]>([]);
  const [assignmentsLoading, setAssignmentsLoading] = useState(true);

  const loadAssignments = useCallback(async () => {
    setAssignmentsLoading(true);
    try {
      const items = await listMyQuoteAssignments();
      setAssignments(
        items.filter(
          (item) => item.assignment_type === "engineer" && ACTIVE_STATUSES.has(item.status),
        ),
      );
    } catch {
      setAssignments([]);
    } finally {
      setAssignmentsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadAssignments();
  }, [loadAssignments]);

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

  const emptyMessage = useMemo(
    () => (assignmentsLoading ? null : "No active assignments yet."),
    [assignmentsLoading],
  );

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <PageHeader
        title="Assigned Estimates"
        description="Review assigned estimates and continue your work."
      />

      <SectionCard title="Assigned Estimates" testId="engineer-assigned-quotes">
        {assignmentsLoading ? (
          <LoadingState message="Loading assignments…" />
        ) : assignments.length === 0 ? (
          <p className="text-sm text-slate-600" data-testid="engineer-no-assignments">
            {emptyMessage}
          </p>
        ) : (
          <div className="space-y-3">
            {assignments.map((item) => (
              <EngineerAssignmentCard
                key={item.id}
                assignment={item}
                variant="active"
                testIdPrefix="engineer-assignment"
              />
            ))}
          </div>
        )}
      </SectionCard>

      {IS_DEV ? (
        <>
          <details className="group" data-testid="engineer-advanced-session">
            <summary className="cursor-pointer list-none text-sm font-medium text-slate-700 marker:content-none [&::-webkit-details-marker]:hidden">
              <span className="inline-flex items-center gap-2">
                <span className="text-slate-400 transition-transform group-open:rotate-90">▸</span>
                Advanced: Open by session token
              </span>
            </summary>
            <div className="mt-3" data-testid="engineer-open-session-card">
              <SectionCard
                title="Open site visit session"
                description="Paste the session ID and token from an eWorks estimate link to continue on this device."
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
          </details>

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
        </>
      ) : null}

      <p className="text-sm text-slate-500">
        <Link
          href="/engineer/submitted-estimates"
          className="font-medium text-blue-600 underline underline-offset-2 hover:text-blue-700"
        >
          View submitted estimates
        </Link>
      </p>
    </div>
  );
}
