"use client";

import Link from "next/link";
import { useState } from "react";

import { VersionHistoryModal } from "@/components/dashboard/version-history-modal";
import { StatusBadge } from "@/components/ui";
import { cn } from "@/lib/utils";
import {
  buildQuoteGroupHref,
  type DashboardQuoteGroupAssignmentItem,
  type DashboardQuoteGroupAssignmentSubmissionRow,
  type DashboardQuoteGroupDetailItem,
  type DashboardQuoteGroupItem,
  type DashboardQuoteGroupSessionDetailItem,
} from "@/lib/dashboard";

function money(value: number | string | null | undefined): string {
  if (value == null || value === "") return "—";
  const amount = Number(value);
  if (Number.isNaN(amount)) return String(value);
  return new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP" }).format(amount);
}

function formatRole(value: string | null | undefined): string {
  if (!value) return "—";
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function formatAssignmentType(value: string): string {
  if (value === "unknown") return "Unknown";
  if (value === "manual") return "Manual";
  return formatRole(value);
}

function assignmentSubmissionRowKey(row: DashboardQuoteGroupAssignmentSubmissionRow): string {
  if (row.assignment_id != null) {
    return `assignment-${row.assignment_id}`;
  }
  return `session-${row.linked_session_id ?? "unknown"}`;
}

function latestBadgeTone(): "info" | "neutral" {
  return "neutral";
}

function assignmentStatusTone(status: string): "warning" | "info" | "success" | "error" | "neutral" {
  switch (status) {
    case "assigned":
      return "warning";
    case "in_progress":
      return "info";
    case "submitted":
      return "success";
    case "cancelled":
      return "error";
    default:
      return "neutral";
  }
}

function assignmentStatusLabel(status: string): string {
  switch (status) {
    case "assigned":
      return "Assigned";
    case "in_progress":
      return "In Progress";
    case "submitted":
      return "Submitted";
    case "cancelled":
      return "Cancelled";
    default:
      return status;
  }
}

function formatAssigneeKindLine(row: DashboardQuoteGroupAssignmentSubmissionRow): string {
  const kind =
    row.assignee_kind === "unknown"
      ? "Unknown"
      : row.assignee_kind.charAt(0).toUpperCase() + row.assignee_kind.slice(1);
  return `${formatAssignmentType(row.assignment_type)} · ${kind}`;
}

function isSubmittedAssignmentRow(row: DashboardQuoteGroupAssignmentSubmissionRow): boolean {
  return row.assignment_status === "submitted" && row.linked_session_id != null;
}

function groupReviewStatusTone(
  status: string | undefined,
): "warning" | "info" | "success" | "error" | "neutral" {
  switch (status) {
    case "pending":
      return "warning";
    case "in_progress":
      return "info";
    case "ready_for_review":
      return "success";
    case "accepted":
      return "success";
    default:
      return "neutral";
  }
}

function groupReviewStatusLabel(status: string | undefined): string {
  switch (status) {
    case "pending":
      return "Pending";
    case "in_progress":
      return "In Progress";
    case "ready_for_review":
      return "Ready for Review";
    case "accepted":
      return "Accepted";
    default:
      return "Pending";
  }
}

function formatAssignee(assignment: DashboardQuoteGroupAssignmentItem): string {
  return assignment.assigned_user_name || assignment.assigned_user_email || "Unassigned";
}

function formatAssignmentTimeline(assignment: DashboardQuoteGroupAssignmentItem): string {
  if (assignment.submitted_at) {
    return `Submitted ${formatSubmittedAt(assignment.submitted_at)}`;
  }
  if (assignment.started_at) {
    return `Started ${formatSubmittedAt(assignment.started_at)}`;
  }
  return "—";
}

function formatSubmittedAt(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("en-GB");
}

function formatLinkedSubmission(assignment: DashboardQuoteGroupAssignmentItem): string {
  if (assignment.has_submission) {
    return "Submission linked";
  }
  if (assignment.calculation_session_id) {
    return "Session in progress";
  }
  return "No submission yet";
}

type QuoteGroupsTableProps = {
  groups: DashboardQuoteGroupItem[];
  groupHref?: (group: DashboardQuoteGroupItem) => string;
  sessionDetailHref?: (sessionId: string) => string;
};

export function QuoteGroupsTable({
  groups,
  groupHref = buildQuoteGroupHref,
  sessionDetailHref = (sessionId) => `/manager/review/${sessionId}`,
}: QuoteGroupsTableProps) {
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm" data-testid="quote-groups-table">
      <table className="min-w-full text-left text-sm">
        <thead className="sticky top-0 z-10 border-b border-slate-200 bg-slate-50 text-xs font-medium uppercase tracking-wide text-slate-600">
          <tr>
            <th className="px-4 py-3 lg:px-5">Quote</th>
            <th className="px-4 py-3 lg:px-5">Job / eWorks Quote ID</th>
            <th className="px-4 py-3 lg:px-5">Client</th>
            <th className="px-4 py-3 lg:px-5">Trade</th>
            <th className="px-4 py-3 lg:px-5">Submissions</th>
            <th className="px-4 py-3 lg:px-5">Latest Submitted</th>
            <th className="px-4 py-3 text-right lg:px-5">Latest Total</th>
            <th className="px-4 py-3 lg:px-5">Status / Accepted</th>
            <th className="px-4 py-3 lg:px-5">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200 bg-white">
          {groups.map((group) => (
            <tr key={group.group_key} className="transition-colors hover:bg-slate-50" data-testid={`quote-group-row-${group.group_key}`}>
              <td className="px-4 py-3 font-semibold text-slate-900 lg:px-5">{group.quote_ref ?? "—"}</td>
              <td className="px-4 py-3 text-slate-900 lg:px-5">{group.eworks_quote_id ?? "—"}</td>
              <td className="px-4 py-3 text-slate-900 lg:px-5">{group.client_name}</td>
              <td className="px-4 py-3 text-slate-600 lg:px-5">{group.trade_name}</td>
              <td className="px-4 py-3 text-slate-600 lg:px-5">{group.submission_count}</td>
              <td className="px-4 py-3 text-slate-600 lg:px-5">{formatSubmittedAt(group.latest_submitted_at)}</td>
              <td className="px-4 py-3 text-right font-semibold tabular-nums text-slate-900 lg:px-5">{money(group.latest_total)}</td>
              <td className="px-4 py-3 lg:px-5">
                {group.accepted ? (
                  <StatusBadge tone="success">Accepted</StatusBadge>
                ) : (
                  <StatusBadge tone="neutral">Submitted</StatusBadge>
                )}
              </td>
              <td className="px-4 py-3 lg:px-5">
                <Link
                  href={groupHref(group)}
                  className="text-sm font-medium text-blue-600 hover:text-blue-700"
                  data-testid={`view-quote-group-${group.group_key}`}
                >
                  View Submissions
                </Link>
                <span className="sr-only"> for {group.quote_ref ?? group.group_key}</span>
                <Link href={sessionDetailHref(group.latest_session_id)} className="sr-only">
                  Latest session detail
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function QuoteGroupAssignmentSubmissionsTable({
  rows,
  sessionDetailHref = (sessionId) => `/manager/review/${sessionId}`,
  quoteRef,
  onReopen,
  reopeningSessionId,
  onRevoke,
  revokingAssignmentId,
  selectedSessionIds,
  onToggleSelect,
  selectionLimitMessage,
  onDownloadVersionPdf,
}: {
  rows: DashboardQuoteGroupAssignmentSubmissionRow[];
  sessionDetailHref?: (sessionId: string) => string;
  quoteRef?: string | null;
  onReopen?: (sessionId: string) => Promise<void>;
  reopeningSessionId?: string | null;
  onRevoke?: (assignmentId: number) => Promise<void>;
  revokingAssignmentId?: number | null;
  selectedSessionIds?: Set<string>;
  onToggleSelect?: (sessionId: string) => void;
  selectionLimitMessage?: string | null;
  onDownloadVersionPdf?: (sessionId: string, versionNumber: number) => void | Promise<void>;
}) {
  const [versionHistoryRow, setVersionHistoryRow] = useState<DashboardQuoteGroupAssignmentSubmissionRow | null>(
    null,
  );

  if (rows.length === 0) {
    return <p className="text-sm text-slate-600">No assignments or submissions yet.</p>;
  }

  return (
    <>
      <div className="space-y-3">
        {selectionLimitMessage ? (
          <p className="text-sm text-amber-800" data-testid="submission-selection-limit-message" role="status">
            {selectionLimitMessage}
          </p>
        ) : null}
        <div className="space-y-2" data-testid="quote-group-assignment-submissions-table">
          {rows.map((row) => {
            const rowKey = assignmentSubmissionRowKey(row);
            const statusId = row.assignment_id ?? row.linked_session_id ?? rowKey;
            const isPendingOrInProgress =
              row.assignment_status === "assigned" || row.assignment_status === "in_progress";
            const sessionId = row.linked_session_id ?? null;
            const isSubmitted = isSubmittedAssignmentRow(row);
            const isSelectable =
              row.assignment_status === "submitted" && sessionId != null && row.assignment_status !== "cancelled";
            const isSelected = sessionId != null && (selectedSessionIds?.has(sessionId) ?? false);

            return (
              <article
                key={rowKey}
                className={cn(
                  "rounded-xl border px-3 py-2.5 transition-colors sm:px-4 sm:py-3",
                  row.is_selected_estimate
                    ? "border-l-4 border-emerald-500 bg-emerald-50/70"
                    : isSelected
                      ? "border-blue-200 bg-blue-50"
                      : "border-slate-200 bg-white hover:bg-slate-50/80",
                )}
                data-testid={`assignment-submission-row-${statusId}`}
              >
                <div className={cn("flex gap-3", isSelectable ? "items-center" : "items-start")}>
                  {onToggleSelect && isSelectable ? (
                    <input
                      type="checkbox"
                      className="shrink-0"
                      checked={isSelected}
                      onChange={() => onToggleSelect(sessionId!)}
                      aria-label={`Compare submission from ${row.assignee_name}`}
                      data-testid={`compare-select-${sessionId}`}
                    />
                  ) : null}

                  <div className="min-w-0 flex-1 space-y-1">
                    <div className="flex items-start justify-between gap-3">
                      <h3
                        className="text-sm font-semibold text-slate-900 sm:text-base"
                        title={row.assignee_email ?? undefined}
                      >
                        {row.assignee_name}
                      </h3>
                      {isSubmitted ? (
                        <span
                          className="shrink-0 text-sm font-semibold tabular-nums text-slate-900"
                          data-testid={sessionId ? `submission-total-${sessionId}` : undefined}
                        >
                          {money(row.final_total)}
                        </span>
                      ) : (
                        <StatusBadge
                          tone={assignmentStatusTone(row.assignment_status)}
                          data-testid={`assignment-submission-status-${statusId}`}
                        >
                          {assignmentStatusLabel(row.assignment_status)}
                        </StatusBadge>
                      )}
                    </div>

                    <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
                      <p className="text-xs text-slate-600 sm:text-sm">{formatAssigneeKindLine(row)}</p>
                      {isSubmitted ? (
                        <div className="flex flex-wrap items-center justify-end gap-1">
                          <StatusBadge
                            tone={assignmentStatusTone(row.assignment_status)}
                            data-testid={`assignment-submission-status-${statusId}`}
                          >
                            {assignmentStatusLabel(row.assignment_status)}
                          </StatusBadge>
                          {row.current_version_number && sessionId ? (
                            <StatusBadge tone="info" data-testid={`submission-version-${sessionId}`}>
                              v{row.current_version_number}
                            </StatusBadge>
                          ) : null}
                          {row.is_latest && sessionId ? (
                            <StatusBadge tone={latestBadgeTone()} data-testid={`submission-latest-${sessionId}`}>
                              Latest
                            </StatusBadge>
                          ) : null}
                          {(row.is_selected_estimate || row.is_job_assigned) && sessionId ? (
                            <StatusBadge tone="success" data-testid={`submission-assigned-job-${sessionId}`}>
                              Selected Estimate
                            </StatusBadge>
                          ) : null}
                        </div>
                      ) : (
                        <p className="text-xs text-slate-500 sm:text-sm">No submission yet</p>
                      )}
                    </div>

                    <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
                      {isSubmitted && row.submitted_at ? (
                        <p className="text-xs text-slate-500 sm:text-sm">{formatSubmittedAt(row.submitted_at)}</p>
                      ) : (
                        <span className="flex-1" />
                      )}
                      <div
                        className="flex flex-wrap items-center gap-3 text-sm"
                        data-testid={sessionId ? `submission-actions-${sessionId}` : undefined}
                      >
                        {row.can_view_details && sessionId ? (
                          <Link
                            href={sessionDetailHref(sessionId)}
                            className="font-medium text-blue-600 hover:text-blue-700"
                            data-testid={`view-session-detail-${sessionId}`}
                          >
                            View
                          </Link>
                        ) : null}
                        {row.can_view_details && sessionId ? (
                          <button
                            type="button"
                            className="font-medium text-blue-600 hover:text-blue-700"
                            onClick={() => setVersionHistoryRow(row)}
                            aria-label="Version History"
                            data-testid={`version-history-open-${sessionId}`}
                          >
                            History
                          </button>
                        ) : null}
                        {row.can_reopen && sessionId && onReopen ? (
                          <button
                            type="button"
                            className="font-medium text-blue-600 hover:text-blue-700 hover:underline disabled:opacity-50"
                            disabled={reopeningSessionId === sessionId}
                            onClick={() => void onReopen(sessionId)}
                            data-testid={`reopen-session-${sessionId}`}
                          >
                            {reopeningSessionId === sessionId ? "Reopening…" : "Reopen"}
                          </button>
                        ) : null}
                        {isPendingOrInProgress && row.assignment_id != null && sessionId ? (
                          <Link
                            href={sessionDetailHref(sessionId)}
                            className="font-medium text-blue-600 hover:text-blue-700"
                            data-testid={`open-assignment-${row.assignment_id}`}
                          >
                            Open Assignment
                          </Link>
                        ) : null}
                        {isPendingOrInProgress && row.assignment_id != null && onRevoke ? (
                          <button
                            type="button"
                            className="font-medium text-red-600 hover:text-red-700 hover:underline disabled:opacity-50"
                            disabled={revokingAssignmentId === row.assignment_id}
                            onClick={() => void onRevoke(row.assignment_id!)}
                            data-testid={`revoke-assignment-${row.assignment_id}`}
                          >
                            {revokingAssignmentId === row.assignment_id ? "Revoking…" : "Revoke"}
                          </button>
                        ) : null}
                      </div>
                    </div>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      </div>
      {versionHistoryRow?.linked_session_id ? (
        <VersionHistoryModal
          open
          assigneeName={versionHistoryRow.assignee_name}
          sessionId={versionHistoryRow.linked_session_id}
          quoteRef={quoteRef}
          versions={versionHistoryRow.versions ?? []}
          sessionDetailHref={sessionDetailHref}
          onClose={() => setVersionHistoryRow(null)}
          onDownloadPdf={onDownloadVersionPdf}
        />
      ) : null}
    </>
  );
}

export function QuoteGroupAssignmentsTable({
  assignments,
  sessionDetailHref = (sessionId) => `/manager/review/${sessionId}`,
}: {
  assignments: DashboardQuoteGroupAssignmentItem[];
  sessionDetailHref?: (sessionId: string) => string;
}) {
  if (assignments.length === 0) {
    return <p className="text-sm text-slate-600">No assignments linked to this quote.</p>;
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm" data-testid="quote-group-assignments-table">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-slate-200 bg-slate-50 text-xs font-medium uppercase tracking-wide text-slate-600">
          <tr>
            <th className="px-4 py-3 font-medium lg:px-5">Type</th>
            <th className="px-4 py-3 font-medium lg:px-5">Assignee</th>
            <th className="px-4 py-3 font-medium lg:px-5">Kind</th>
            <th className="px-4 py-3 font-medium lg:px-5">Status</th>
            <th className="px-4 py-3 font-medium lg:px-5">Assigned At</th>
            <th className="px-4 py-3 font-medium lg:px-5">Started / Submitted</th>
            <th className="px-4 py-3 font-medium lg:px-5">Linked Submission</th>
            <th className="px-4 py-3 font-medium lg:px-5">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200 bg-white">
          {assignments.map((assignment) => (
            <tr key={assignment.id} className="transition-colors hover:bg-slate-50" data-testid={`quote-group-assignment-${assignment.id}`}>
              <td className="px-4 py-3 text-slate-900 lg:px-5">{formatRole(assignment.assignment_type)}</td>
              <td className="px-4 py-3 text-slate-900 lg:px-5">
                <div>{formatAssignee(assignment)}</div>
                {assignment.assigned_user_email ? (
                  <div className="text-xs text-slate-500">{assignment.assigned_user_email}</div>
                ) : null}
              </td>
              <td className="px-4 py-3 capitalize text-slate-600 lg:px-5">{assignment.assignee_kind}</td>
              <td className="px-4 py-3 lg:px-5">
                <StatusBadge tone={assignmentStatusTone(assignment.status)} data-testid={`assignment-status-${assignment.id}`}>
                  {assignmentStatusLabel(assignment.status)}
                </StatusBadge>
              </td>
              <td className="px-4 py-3 text-slate-600 lg:px-5">{formatSubmittedAt(assignment.assigned_at)}</td>
              <td className="px-4 py-3 text-slate-600 lg:px-5">{formatAssignmentTimeline(assignment)}</td>
              <td className="px-4 py-3 text-slate-600 lg:px-5">{formatLinkedSubmission(assignment)}</td>
              <td className="px-4 py-3 lg:px-5">
                {assignment.calculation_session_id ? (
                  <Link
                    href={sessionDetailHref(assignment.calculation_session_id)}
                    className="text-sm font-medium text-blue-600 hover:text-blue-700"
                    data-testid={`view-assignment-session-${assignment.id}`}
                  >
                    View Session
                  </Link>
                ) : (
                  <span className="text-sm text-slate-500">—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function QuoteGroupSubmissionsTable({
  group,
  sessionDetailHref = (sessionId) => `/manager/review/${sessionId}`,
  onReopen,
  reopeningSessionId,
}: {
  group: Pick<DashboardQuoteGroupDetailItem, "sessions">;
  sessionDetailHref?: (sessionId: string) => string;
  onReopen?: (sessionId: string) => Promise<void>;
  reopeningSessionId?: string | null;
}) {
  const sessions = group.sessions as DashboardQuoteGroupSessionDetailItem[];

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm" data-testid="quote-group-submissions-table">
      <table className="min-w-full text-left text-sm">
        <thead className="sticky top-0 z-10 border-b border-slate-200 bg-slate-50 text-xs font-medium uppercase tracking-wide text-slate-600">
          <tr>
            <th className="px-4 py-3 lg:px-5">Submitted At</th>
            <th className="px-4 py-3 lg:px-5">Submitted By</th>
            <th className="px-4 py-3 lg:px-5">Role</th>
            <th className="px-4 py-3 text-right lg:px-5">Final Total</th>
            <th className="px-4 py-3 lg:px-5">Works</th>
            <th className="px-4 py-3 lg:px-5">Submission Status</th>
            <th className="px-4 py-3 lg:px-5">Latest</th>
            <th className="px-4 py-3 lg:px-5">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200 bg-white">
          {sessions.map((session) => (
            <tr key={session.session_id} className="transition-colors hover:bg-slate-50" data-testid={`quote-group-session-${session.session_id}`}>
              <td className="px-4 py-3 text-slate-900 lg:px-5">{formatSubmittedAt(session.submitted_at)}</td>
              <td className="px-4 py-3 text-slate-900 lg:px-5" data-testid={`submission-submitter-${session.session_id}`}>
                {session.submitted_by_name ?? "Unknown submitter"}
              </td>
              <td className="px-4 py-3 text-slate-600 lg:px-5">{formatRole(session.submitted_by_role)}</td>
              <td className="px-4 py-3 text-right font-semibold tabular-nums text-slate-900 lg:px-5">{money(session.final_total)}</td>
              <td className="px-4 py-3 text-slate-600 lg:px-5">{session.works_count}</td>
              <td className="px-4 py-3 lg:px-5">
                {session.accepted ? (
                  <StatusBadge tone="success">Accepted</StatusBadge>
                ) : (
                  <StatusBadge tone="neutral">{session.status}</StatusBadge>
                )}
              </td>
              <td className="px-4 py-3 lg:px-5">
                {session.is_latest ? (
                  <StatusBadge tone="info" data-testid={`submission-latest-${session.session_id}`}>
                    Latest
                  </StatusBadge>
                ) : (
                  <span className="text-sm text-slate-400">—</span>
                )}
              </td>
              <td className="px-4 py-3 lg:px-5">
                <div className="flex flex-wrap gap-3">
                  <Link
                    href={sessionDetailHref(session.session_id)}
                    className="text-sm font-medium text-blue-600 hover:text-blue-700"
                    data-testid={`view-session-detail-${session.session_id}`}
                  >
                    View Details
                  </Link>
                  {onReopen ? (
                    <button
                      type="button"
                      className="text-sm font-medium text-blue-600 hover:text-blue-700 hover:underline disabled:opacity-50"
                      disabled={reopeningSessionId === session.session_id}
                      onClick={() => void onReopen(session.session_id)}
                      data-testid={`reopen-session-${session.session_id}`}
                    >
                      {reopeningSessionId === session.session_id ? "Reopening…" : "Reopen"}
                    </button>
                  ) : null}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export {
  assignmentStatusLabel,
  formatSubmittedAt,
  groupReviewStatusLabel,
  groupReviewStatusTone,
  money,
};
