"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";

import {
  QuoteGroupAssignmentsTable,
  QuoteGroupSubmissionsTable,
  groupReviewStatusLabel,
  groupReviewStatusTone,
} from "@/components/dashboard/quote-groups-table";
import { ErrorState, LoadingState, PageHeader, SectionCard, StatusBadge } from "@/components/ui";
import { money } from "@/components/eworks-dashboard";
import { createRoleDashboardClient } from "@/lib/dashboard-client";
import type { DashboardQuoteGroupDetailItem } from "@/lib/dashboard";
import { fetchSubmittedQuoteGroupDetail } from "@/lib/dashboard-auth";

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

  const pendingAssignments = group?.assignment_summary?.pending_assignments ?? 0;
  const hasSubmissions = (group?.submission_count ?? 0) > 0;

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

          <SectionCard title="Assignments" testId="quote-group-assignments">
            <QuoteGroupAssignmentsTable assignments={group.assignments ?? []} />
          </SectionCard>

          <SectionCard title="Submissions" testId="quote-group-submissions">
            <QuoteGroupSubmissionsTable
              group={group}
              onReopen={handleReopen}
              reopeningSessionId={reopeningSessionId}
            />
          </SectionCard>
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
