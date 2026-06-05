"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { AssignmentEstimateButton } from "@/components/quote-assignment-estimate-button";
import {
  ErrorState,
  LoadingState,
  PageHeader,
  SectionCard,
  StatusBadge,
} from "@/components/ui";
import { listMyQuoteAssignments, type QuoteAssignment } from "@/lib/quote-assignments";

export default function EngineerAssignmentDetailPage({ params }: { params: { assignmentId: string } }) {
  const assignmentId = Number(params.assignmentId);
  const [assignment, setAssignment] = useState<QuoteAssignment | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!Number.isFinite(assignmentId)) {
      setError("Invalid assignment ID");
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const items = await listMyQuoteAssignments();
      const match = items.find((item) => item.id === assignmentId) ?? null;
      if (!match) {
        setError("Assignment not found or you do not have access.");
      }
      setAssignment(match);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load assignment");
      setAssignment(null);
    } finally {
      setLoading(false);
    }
  }, [assignmentId]);

  useEffect(() => {
    void load();
  }, [load]);

  const summary = useMemo(() => assignment?.quote_summary, [assignment]);

  return (
    <div className="mx-auto max-w-2xl space-y-6" data-testid="engineer-assignment-detail-page">
      <PageHeader
        title="Assignment Details"
        description="Review the quote assignment and open the estimate questionnaire."
      />

      {loading ? (
        <LoadingState message="Loading assignment…" />
      ) : error ? (
        <ErrorState message={error} onRetry={() => void load()} />
      ) : assignment ? (
        <>
          <SectionCard title="Quote Summary" testId="engineer-assignment-summary">
            <div className="space-y-3 text-sm text-slate-700">
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge tone="info">{assignment.assignment_type}</StatusBadge>
                <StatusBadge tone="neutral">{assignment.status}</StatusBadge>
              </div>
              <p>
                <span className="font-medium text-slate-900">Quote ref:</span>{" "}
                {assignment.quote_ref ?? assignment.eworks_quote_id}
              </p>
              <p>
                <span className="font-medium text-slate-900">Customer:</span>{" "}
                {summary?.customer_name ?? "Not available"}
              </p>
              <p>
                <span className="font-medium text-slate-900">Site / address:</span>{" "}
                {summary?.site_address ?? "Not available"}
              </p>
              {assignment.notes ? (
                <p>
                  <span className="font-medium text-slate-900">Assignment notes:</span> {assignment.notes}
                </p>
              ) : null}
            </div>
          </SectionCard>

          <SectionCard title="Next steps">
            <AssignmentEstimateButton
              assignment={assignment}
              label="Open Assignment"
              testId="engineer-assignment-open-estimate"
            />
          </SectionCard>
        </>
      ) : null}
    </div>
  );
}
