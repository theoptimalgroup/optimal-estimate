"use client";

import { useCallback, useEffect, useState } from "react";

import {
  ErrorState,
  LoadingState,
  PrimaryButton,
  SectionCard,
  StatusBadge,
} from "@/components/ui";
import { getPublicAssignment, submitPublicAssignment, type PublicAssignment } from "@/lib/quote-assignments";

export default function PublicAssignmentPage({ params }: { params: { assignmentToken: string } }) {
  const { assignmentToken } = params;
  const [assignment, setAssignment] = useState<PublicAssignment | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setAssignment(await getPublicAssignment(assignmentToken));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load assignment");
      setAssignment(null);
    } finally {
      setLoading(false);
    }
  }, [assignmentToken]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const updated = await submitPublicAssignment(assignmentToken, notes.trim() || undefined);
      setAssignment(updated);
      setSubmitted(true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to submit assignment");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50" data-testid="public-assignment-page">
      <header className="border-b border-slate-200 bg-white shadow-sm">
        <div className="mx-auto max-w-3xl px-6 py-6">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">The Optimal Group</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">Quote Assignment</h1>
          <p className="mt-1 text-sm text-slate-600">Review your assigned quote details</p>
        </div>
      </header>

      <main className="mx-auto max-w-3xl space-y-6 px-6 py-8">
        {loading ? (
          <LoadingState message="Loading assignment…" />
        ) : error ? (
          <ErrorState message={error} onRetry={() => void load()} />
        ) : assignment ? (
          <>
            <SectionCard title="Assignment Summary" testId="assignment-summary-section">
              <div className="space-y-3 text-sm text-slate-700">
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge tone="info">{assignment.assignment_type}</StatusBadge>
                  <StatusBadge tone="neutral">{assignment.status}</StatusBadge>
                </div>
                <p>
                  <span className="font-medium text-slate-900">Quote ref:</span> {assignment.quote_ref ?? "—"}
                </p>
                <p>
                  <span className="font-medium text-slate-900">Customer:</span>{" "}
                  {assignment.customer_name ?? "Not available"}
                </p>
                <p>
                  <span className="font-medium text-slate-900">Site / address:</span>{" "}
                  {assignment.site_address ?? "Not available"}
                </p>
                <p>
                  <span className="font-medium text-slate-900">Quote date:</span> {assignment.quote_date ?? "—"}
                </p>
                <p>
                  <span className="font-medium text-slate-900">Expiry date:</span> {assignment.expiry_date ?? "—"}
                </p>
                {assignment.description ? (
                  <p>
                    <span className="font-medium text-slate-900">Description:</span> {assignment.description}
                  </p>
                ) : null}
                {assignment.notes ? (
                  <p>
                    <span className="font-medium text-slate-900">Assignment notes:</span> {assignment.notes}
                  </p>
                ) : null}
                {assignment.assigned_by_name ? (
                  <p>
                    <span className="font-medium text-slate-900">Assigned by:</span> {assignment.assigned_by_name}
                  </p>
                ) : null}
              </div>
            </SectionCard>

            {submitted || assignment.status === "submitted" ? (
              <SectionCard title="Next steps">
                <p className="text-sm text-slate-700">
                  Thank you. Your assignment has been submitted. Please contact the office if you need further
                  assistance.
                </p>
              </SectionCard>
            ) : (
              <SectionCard title="Confirm review" testId="assignment-submit-section">
                <p className="text-sm text-slate-600">
                  This link is for reviewing assignment details only. To begin an estimate, please contact the office.
                </p>
                <p className="mt-3 text-sm text-slate-600">
                  Add any notes about your review, then submit to confirm you have received this assignment.
                </p>
                <textarea
                  className="mt-4 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                  rows={4}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Optional notes"
                  data-testid="public-assignment-notes"
                />
                <div className="mt-4">
                  <PrimaryButton
                    onClick={() => void handleSubmit()}
                    disabled={submitting}
                    data-testid="public-assignment-submit"
                  >
                    Submit review
                  </PrimaryButton>
                </div>
              </SectionCard>
            )}
          </>
        ) : null}
      </main>
    </div>
  );
}
