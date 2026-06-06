"use client";

import Link from "next/link";

import { StatusBadge } from "@/components/ui";
import {
  buildQuoteGroupHref,
  type DashboardQuoteGroupAssignmentItem,
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
    <div className="overflow-x-auto rounded-lg border border-gray-200" data-testid="quote-groups-table">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase tracking-wide text-optimal-muted">
          <tr>
            <th className="px-4 py-3 font-medium lg:px-5">Quote</th>
            <th className="px-4 py-3 font-medium lg:px-5">Job / eWorks Quote ID</th>
            <th className="px-4 py-3 font-medium lg:px-5">Client</th>
            <th className="px-4 py-3 font-medium lg:px-5">Trade</th>
            <th className="px-4 py-3 font-medium lg:px-5">Submissions</th>
            <th className="px-4 py-3 font-medium lg:px-5">Latest Submitted</th>
            <th className="px-4 py-3 text-right font-medium lg:px-5">Latest Total</th>
            <th className="px-4 py-3 font-medium lg:px-5">Status / Accepted</th>
            <th className="px-4 py-3 font-medium lg:px-5">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {groups.map((group) => (
            <tr key={group.group_key} className="transition-colors hover:bg-gray-50" data-testid={`quote-group-row-${group.group_key}`}>
              <td className="px-4 py-3 font-semibold text-gray-900 lg:px-5">{group.quote_ref ?? "—"}</td>
              <td className="px-4 py-3 text-gray-900 lg:px-5">{group.eworks_quote_id ?? "—"}</td>
              <td className="px-4 py-3 text-gray-900 lg:px-5">{group.client_name}</td>
              <td className="px-4 py-3 text-optimal-muted lg:px-5">{group.trade_name}</td>
              <td className="px-4 py-3 text-optimal-muted lg:px-5">{group.submission_count}</td>
              <td className="px-4 py-3 text-optimal-muted lg:px-5">{formatSubmittedAt(group.latest_submitted_at)}</td>
              <td className="px-4 py-3 text-right font-semibold text-gray-900 lg:px-5">{money(group.latest_total)}</td>
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
    <div className="overflow-x-auto rounded-lg border border-gray-200" data-testid="quote-group-assignments-table">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase tracking-wide text-optimal-muted">
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
        <tbody className="divide-y divide-gray-200">
          {assignments.map((assignment) => (
            <tr key={assignment.id} data-testid={`quote-group-assignment-${assignment.id}`}>
              <td className="px-4 py-3 text-gray-900 lg:px-5">{formatRole(assignment.assignment_type)}</td>
              <td className="px-4 py-3 text-gray-900 lg:px-5">
                <div>{formatAssignee(assignment)}</div>
                {assignment.assigned_user_email ? (
                  <div className="text-xs text-slate-500">{assignment.assigned_user_email}</div>
                ) : null}
              </td>
              <td className="px-4 py-3 capitalize text-optimal-muted lg:px-5">{assignment.assignee_kind}</td>
              <td className="px-4 py-3 lg:px-5">
                <StatusBadge tone={assignmentStatusTone(assignment.status)} data-testid={`assignment-status-${assignment.id}`}>
                  {assignmentStatusLabel(assignment.status)}
                </StatusBadge>
              </td>
              <td className="px-4 py-3 text-optimal-muted lg:px-5">{formatSubmittedAt(assignment.assigned_at)}</td>
              <td className="px-4 py-3 text-optimal-muted lg:px-5">{formatAssignmentTimeline(assignment)}</td>
              <td className="px-4 py-3 text-optimal-muted lg:px-5">{formatLinkedSubmission(assignment)}</td>
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
    <div className="overflow-x-auto rounded-lg border border-gray-200" data-testid="quote-group-submissions-table">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase tracking-wide text-optimal-muted">
          <tr>
            <th className="px-4 py-3 font-medium lg:px-5">Submitted At</th>
            <th className="px-4 py-3 font-medium lg:px-5">Submitted By</th>
            <th className="px-4 py-3 font-medium lg:px-5">Role</th>
            <th className="px-4 py-3 text-right font-medium lg:px-5">Final Total</th>
            <th className="px-4 py-3 font-medium lg:px-5">Works</th>
            <th className="px-4 py-3 font-medium lg:px-5">Submission Status</th>
            <th className="px-4 py-3 font-medium lg:px-5">Latest</th>
            <th className="px-4 py-3 font-medium lg:px-5">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {sessions.map((session) => (
            <tr key={session.session_id} data-testid={`quote-group-session-${session.session_id}`}>
              <td className="px-4 py-3 text-gray-900 lg:px-5">{formatSubmittedAt(session.submitted_at)}</td>
              <td className="px-4 py-3 text-gray-900 lg:px-5" data-testid={`submission-submitter-${session.session_id}`}>
                {session.submitted_by_name ?? "Unknown submitter"}
              </td>
              <td className="px-4 py-3 text-optimal-muted lg:px-5">{formatRole(session.submitted_by_role)}</td>
              <td className="px-4 py-3 text-right font-semibold text-gray-900 lg:px-5">{money(session.final_total)}</td>
              <td className="px-4 py-3 text-optimal-muted lg:px-5">{session.works_count}</td>
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
                      className="text-sm font-medium text-optimal-orange hover:underline disabled:opacity-50"
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
