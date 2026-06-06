"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";

import { MAX_COMPARE, SubmissionComparePanel } from "@/components/dashboard/submission-compare-panel";
import {
  QuoteGroupAssignmentSubmissionsTable,
  groupReviewStatusLabel,
  groupReviewStatusTone,
} from "@/components/dashboard/quote-groups-table";
import { ErrorState, LoadingState, PageHeader, SectionCard, StatusBadge } from "@/components/ui";
import { money } from "@/components/eworks-dashboard";
import { createRoleDashboardClient } from "@/lib/dashboard-client";
import type { DashboardQuoteGroupAssignmentSubmissionRow, DashboardQuoteGroupDetailItem } from "@/lib/dashboard";
import { assignQuoteJob, fetchSubmittedQuoteGroupDetail } from "@/lib/dashboard-auth";
import { revokeQuoteAssignment } from "@/lib/quote-assignments";

function formatAssigneeSummary(
  assignments: DashboardQuoteGroupDetailItem["assignments"],
  assignmentType: "estimator" | "engineer",
): string {
  const matches = (assignments ?? []).filter((item) => item.assignment_type === assignmentType);
  if (matches.length === 0) {
    return "None assigned";
  }
  return matches
    .map((item) => {
      const name = item.assigned_user_name || item.assigned_user_email || "Unassigned";
      return `${name} (${item.status === "assigned" ? "Pending" : item.status.replace("_", " ")})`;
    })
    .join("; ");
}

function QuoteGroupReviewContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const quoteRef = searchParams.get("quote_ref") ?? undefined;
  const eworksQuoteIdRaw = searchParams.get("eworks_quote_id");
  const eworksQuoteId = eworksQuoteIdRaw ? Number(eworksQuoteIdRaw) : undefined;
  const groupKey = searchParams.get("group_key") ?? undefined;

  const client = useMemo(() => createRoleDashboardClient(), []);
  const [group, setGroup] = useState<DashboardQuoteGroupDetailItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reopeningSessionId, setReopeningSessionId] = useState<string | null>(null);
  const [revokingAssignmentId, setRevokingAssignmentId] = useState<number | null>(null);
  const [selectedSessionIds, setSelectedSessionIds] = useState<Set<string>>(new Set());
  const [selectionLimitMessage, setSelectionLimitMessage] = useState<string | null>(null);
  const [assigningSessionId, setAssigningSessionId] = useState<string | null>(null);
  const [assignmentSuccessMessage, setAssignmentSuccessMessage] = useState<string | null>(null);

  const loadGroup = useCallback(async () => {
    if (!quoteRef && eworksQuoteId == null && !groupKey) {
      setError("Quote reference is required.");
      setGroup(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await fetchSubmittedQuoteGroupDetail({
        quote_ref: quoteRef,
        eworks_quote_id: Number.isNaN(eworksQuoteId) ? undefined : eworksQuoteId,
        group_key: groupKey,
      });
      setGroup(response.group);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load quote submissions");
      setGroup(null);
    } finally {
      setLoading(false);
    }
  }, [quoteRef, eworksQuoteId, groupKey]);

  useEffect(() => {
    void loadGroup();
  }, [loadGroup]);

  const handleReopen = async (sessionId: string) => {
    setReopeningSessionId(sessionId);
    try {
      const result = await client.reopenQuoteForRefill(sessionId);
      const search = new URLSearchParams({
        session_id: result.session_id,
        token: result.session_token,
      });
      router.push(`/eworks/calculate?${search.toString()}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reopen quote");
    } finally {
      setReopeningSessionId(null);
    }
  };

  const handleRevoke = async (assignmentId: number) => {
    setRevokingAssignmentId(assignmentId);
    try {
      await revokeQuoteAssignment(assignmentId);
      await loadGroup();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to revoke assignment");
    } finally {
      setRevokingAssignmentId(null);
    }
  };

  const handleToggleSelect = (sessionId: string) => {
    setSelectionLimitMessage(null);
    setSelectedSessionIds((current) => {
      const next = new Set(current);
      if (next.has(sessionId)) {
        next.delete(sessionId);
        return next;
      }
      if (next.size >= MAX_COMPARE) {
        setSelectionLimitMessage("You can compare up to 3 submissions.");
        return current;
      }
      next.add(sessionId);
      return next;
    });
  };

  const handleAssignJob = async (row: DashboardQuoteGroupAssignmentSubmissionRow) => {
    const activeQuoteRef = group?.quote_ref ?? quoteRef;
    if (!activeQuoteRef || !row.linked_session_id) {
      setError("Quote reference is required to assign the job.");
      return;
    }
    setAssigningSessionId(row.linked_session_id);
    setError(null);
    try {
      const result = await assignQuoteJob(activeQuoteRef, {
        selected_session_id: row.linked_session_id,
        assignee_name: row.assignee_name,
        assignee_email: row.assignee_email,
        assignment_id: row.assignment_id,
      });
      setAssignmentSuccessMessage(`Job assigned to ${result?.decision?.assignee_name ?? row.assignee_name}.`);
      setSelectedSessionIds(new Set());
      await loadGroup();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to assign job");
    } finally {
      setAssigningSessionId(null);
    }
  };

  const pendingAssignments = group?.assignment_summary?.pending_assignments ?? 0;
  const hasSubmissions = (group?.submission_count ?? 0) > 0;
  const assignmentSubmissions = group?.assignment_submissions ?? [];
  const selectedRows = assignmentSubmissions.filter(
    (row) => row.linked_session_id != null && selectedSessionIds.has(row.linked_session_id),
  );
  const jobDecision = group?.job_assignment_decision;

  return (
    <div className="space-y-6" data-testid="manager-review-group-page">
      <PageHeader
        title={group?.quote_ref ? `Quote ${group.quote_ref}` : "Quote Submissions"}
        description="Review assignments, submitters, and all submitted estimate sessions for this quote."
        actions={
          <Link
            href="/manager/review"
            className="inline-flex items-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Back to Quote Review
          </Link>
        }
      />

      {loading ? (
        <LoadingState message="Loading quote submissions…" />
      ) : error ? (
        <ErrorState message={error} onRetry={() => void loadGroup()} />
      ) : group ? (
        <>
          {assignmentSuccessMessage ? (
            <div
              className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900"
              data-testid="job-assignment-success-banner"
              role="status"
            >
              {assignmentSuccessMessage}
            </div>
          ) : null}

          {pendingAssignments > 0 && !hasSubmissions ? (
            <div
              className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
              data-testid="quote-group-pending-notice"
            >
              Estimator/Engineer assignment is pending. No estimate has been submitted yet.
            </div>
          ) : null}

          {hasSubmissions ? (
            <div
              className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900"
              data-testid="quote-group-submissions-notice"
            >
              {group.submission_count} submission{group.submission_count === 1 ? "" : "s"} received. Latest
              submission is shown first.
            </div>
          ) : null}

          <SectionCard title="Quote Summary" testId="quote-group-summary">
            <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Quote</dt>
                <dd className="mt-1 text-sm font-medium text-slate-900">{group.quote_ref ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">eWorks Quote ID</dt>
                <dd className="mt-1 text-sm text-slate-900">{group.eworks_quote_id ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Client</dt>
                <dd className="mt-1 text-sm text-slate-900">{group.client_name}</dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Trade</dt>
                <dd className="mt-1 text-sm text-slate-900">{group.trade_name}</dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Submissions</dt>
                <dd className="mt-1 text-sm text-slate-900">{group.submission_count}</dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Latest Total</dt>
                <dd className="mt-1 text-sm font-medium text-slate-900">{money(group.latest_total)}</dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Review Status</dt>
                <dd className="mt-1">
                  <StatusBadge tone={groupReviewStatusTone(group.review_status)} data-testid="quote-group-review-status">
                    {groupReviewStatusLabel(group.review_status)}
                  </StatusBadge>
                </dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Accepted</dt>
                <dd className="mt-1">
                  {group.accepted ? (
                    <StatusBadge tone="success">Accepted</StatusBadge>
                  ) : (
                    <StatusBadge tone="neutral">Not accepted</StatusBadge>
                  )}
                </dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Job assignment</dt>
                <dd className="mt-1 flex flex-wrap items-center gap-3 text-sm text-slate-900" data-testid="quote-group-job-assignment">
                  {jobDecision ? (
                    <>
                      <span>Assigned to {jobDecision.assignee_name}</span>
                      <button
                        type="button"
                        className="text-sm font-medium text-blue-600 hover:text-blue-700 hover:underline"
                        onClick={() => {
                          setAssignmentSuccessMessage(null);
                          if (jobDecision.selected_session_id) {
                            setSelectedSessionIds(new Set([jobDecision.selected_session_id]));
                          }
                        }}
                        data-testid="change-job-assignment"
                      >
                        Change assignment
                      </button>
                    </>
                  ) : (
                    <span>Not assigned</span>
                  )}
                </dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Estimator Assignments</dt>
                <dd className="mt-1 text-sm text-slate-900" data-testid="quote-group-estimator-summary">
                  {formatAssigneeSummary(group.assignments, "estimator")}
                </dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Engineer Assignments</dt>
                <dd className="mt-1 text-sm text-slate-900" data-testid="quote-group-engineer-summary">
                  {formatAssigneeSummary(group.assignments, "engineer")}
                </dd>
              </div>
            </dl>
          </SectionCard>

          <SectionCard title="Assignment Submissions" testId="quote-group-assignment-submissions">
            <QuoteGroupAssignmentSubmissionsTable
              rows={assignmentSubmissions}
              onReopen={handleReopen}
              reopeningSessionId={reopeningSessionId}
              onRevoke={handleRevoke}
              revokingAssignmentId={revokingAssignmentId}
              selectedSessionIds={selectedSessionIds}
              onToggleSelect={handleToggleSelect}
              selectionLimitMessage={selectionLimitMessage}
            />
          </SectionCard>

          {selectedRows.length > 0 ? (
            <SectionCard title="Compare Submissions" testId="quote-group-compare-submissions">
              <SubmissionComparePanel
                rows={selectedRows}
                onAssign={handleAssignJob}
                assigningSessionId={assigningSessionId}
              />
            </SectionCard>
          ) : null}
        </>
      ) : null}
    </div>
  );
}

export default function ManagerReviewGroupPage() {
  return (
    <Suspense fallback={<LoadingState message="Loading quote submissions…" />}>
      <QuoteGroupReviewContent />
    </Suspense>
  );
}
