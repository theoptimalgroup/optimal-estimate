"use client";

import Link from "next/link";

import { StatusBadge } from "@/components/ui";
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
      return "Pending";
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
  onReopen,
  reopeningSessionId,
  onRevoke,
  revokingAssignmentId,
  selectedSessionIds,
  onToggleSelect,
  selectionLimitMessage,
}: {
  rows: DashboardQuoteGroupAssignmentSubmissionRow[];
  sessionDetailHref?: (sessionId: string) => string;
  onReopen?: (sessionId: string) => Promise<void>;
  reopeningSessionId?: string | null;
  onRevoke?: (assignmentId: number) => Promise<void>;
  revokingAssignmentId?: number | null;
  selectedSessionIds?: Set<string>;
  onToggleSelect?: (sessionId: string) => void;
  selectionLimitMessage?: string | null;
}) {
  if (rows.length === 0) {
    return <p className="text-sm text-slate-600">No assignments or submissions yet.</p>;
  }

  return (
    <div className="space-y-3">
      {selectionLimitMessage ? (
        <p className="text-sm text-amber-800" data-testid="submission-selection-limit-message" role="status">
          {selectionLimitMessage}
        </p>
      ) : null}
      <div
        className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm"
        data-testid="quote-group-assignment-submissions-table"
      >
        <table className="min-w-full text-left text-sm">
          <thead className="sticky top-0 z-10 border-b border-slate-200 bg-slate-50 text-xs font-medium uppercase tracking-wide text-slate-600">
            <tr>
              {onToggleSelect ? <th className="px-4 py-3 lg:px-5">Compare</th> : null}
              <th className="px-4 py-3 lg:px-5">Type</th>
            <th className="px-4 py-3 lg:px-5">Assignee</th>
            <th className="px-4 py-3 lg:px-5">Kind</th>
            <th className="px-4 py-3 lg:px-5">Status</th>
            <th className="px-4 py-3 lg:px-5">Submitted At</th>
            <th className="px-4 py-3 lg:px-5">Submitted By</th>
            <th className="px-4 py-3 text-right lg:px-5">Final Total</th>
            <th className="px-4 py-3 lg:px-5">Latest</th>
            <th className="px-4 py-3 lg:px-5">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200 bg-white">
          {rows.map((row) => {
            const rowKey = assignmentSubmissionRowKey(row);
            const statusId = row.assignment_id ?? row.linked_session_id ?? rowKey;
            const isPendingOrInProgress =
              row.assignment_status === "assigned" || row.assignment_status === "in_progress";
            const sessionId = row.linked_session_id ?? null;
            const isSelectable =
              row.assignment_status === "submitted" && sessionId != null && row.assignment_status !== "cancelled";
            const isSelected = sessionId != null && (selectedSessionIds?.has(sessionId) ?? false);

            return (
              <tr
                key={rowKey}
                className="transition-colors hover:bg-slate-50"
                data-testid={`assignment-submission-row-${statusId}`}
              >
                {onToggleSelect ? (
                  <td className="px-4 py-3 lg:px-5">
                    {isSelectable ? (
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => onToggleSelect(sessionId!)}
                        aria-label={`Compare submission from ${row.assignee_name}`}
                        data-testid={`compare-select-${sessionId}`}
                      />
                    ) : (
                      <span className="text-sm text-slate-300">—</span>
                    )}
                  </td>
                ) : null}
                <td className="px-4 py-3 text-slate-900 lg:px-5">{formatAssignmentType(row.assignment_type)}</td>
                <td className="px-4 py-3 text-slate-900 lg:px-5">
                  <div>{row.assignee_name}</div>
                  {row.assignee_email ? <div className="text-xs text-slate-500">{row.assignee_email}</div> : null}
                </td>
                <td className="px-4 py-3 capitalize text-slate-600 lg:px-5">{row.assignee_kind}</td>
                <td className="px-4 py-3 lg:px-5">
                  <StatusBadge
                    tone={assignmentStatusTone(row.assignment_status)}
                    data-testid={`assignment-submission-status-${statusId}`}
                  >
                    {assignmentStatusLabel(row.assignment_status)}
                  </StatusBadge>
                </td>
                <td className="px-4 py-3 text-slate-600 lg:px-5">
                  {row.submitted_at ? formatSubmittedAt(row.submitted_at) : "—"}
                </td>
                <td
                  className="px-4 py-3 text-slate-900 lg:px-5"
                  data-testid={sessionId ? `submission-submitter-${sessionId}` : undefined}
                >
                  {row.submitted_by_name ?? "—"}
                </td>
                <td className="px-4 py-3 text-right font-semibold tabular-nums text-slate-900 lg:px-5">
                  {money(row.final_total)}
                </td>
                <td className="px-4 py-3 lg:px-5">
                  {row.is_latest && sessionId ? (
                    <StatusBadge tone={latestBadgeTone()} data-testid={`submission-latest-${sessionId}`}>
                      Latest
                    </StatusBadge>
                  ) : (
                    <span className="text-sm text-slate-400">—</span>
                  )}
                  {row.is_job_assigned ? (
                    <div className="mt-1">
                      <StatusBadge tone="info" data-testid={`submission-assigned-job-${sessionId}`}>
                        Assigned Job
                      </StatusBadge>
                    </div>
                  ) : null}
                </td>
                <td className="px-4 py-3 lg:px-5">
                  <div className="flex flex-wrap gap-3">
                    {row.can_view_details && sessionId ? (
                      <Link
                        href={sessionDetailHref(sessionId)}
                        className="text-sm font-medium text-blue-600 hover:text-blue-700"
                        data-testid={`view-session-detail-${sessionId}`}
                      >
                        View Details
                      </Link>
                    ) : null}
                    {row.can_reopen && sessionId && onReopen ? (
                      <button
                        type="button"
                        className="text-sm font-medium text-blue-600 hover:text-blue-700 hover:underline disabled:opacity-50"
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
                        className="text-sm font-medium text-blue-600 hover:text-blue-700"
                        data-testid={`open-assignment-${row.assignment_id}`}
                      >
                        Open Assignment
                      </Link>
                    ) : null}
                    {isPendingOrInProgress && row.assignment_id != null && onRevoke ? (
                      <button
                        type="button"
                        className="text-sm font-medium text-red-600 hover:text-red-700 hover:underline disabled:opacity-50"
                        disabled={revokingAssignmentId === row.assignment_id}
                        onClick={() => void onRevoke(row.assignment_id!)}
                        data-testid={`revoke-assignment-${row.assignment_id}`}
                      >
                        {revokingAssignmentId === row.assignment_id ? "Revoking…" : "Revoke"}
                      </button>
                    ) : null}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      </div>
    </div>
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
