"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  DataTable,
  DataTableBody,
  DataTableCell,
  DataTableHead,
  DataTableRow,
  ErrorState,
  LoadingState,
  PrimaryButton,
  SecondaryButton,
  SectionCard,
  StatusBadge,
} from "@/components/ui";
import type { QuoteAssignmentSafe } from "@/lib/eworks-sync";
import {
  buildAssignmentLink,
  createQuoteAssignment,
  listAssignees,
  listQuoteAssignments,
  revokeQuoteAssignment,
  type AssigneeUser,
  type AssignmentCreatePayload,
  type QuoteAssignment,
} from "@/lib/quote-assignments";

function assignmentTypeLabel(type: QuoteAssignment["assignment_type"]): string {
  return type === "estimator" ? "Estimator" : "Engineer";
}

function sourceLabel(source: string | null | undefined): string {
  if (source === "eworks_appointment") return "eWorks appointment";
  if (source === "manual") return "Manual";
  return source ?? "—";
}

function isActiveAssignment(status: QuoteAssignment["status"] | string | null | undefined): boolean {
  return status !== "cancelled" && status !== "revoked";
}

function formatAppointmentTime(assignment: QuoteAssignmentSafe | QuoteAssignment): string {
  const start = assignment.appointment_start_at ?? null;
  const end = assignment.appointment_end_at ?? null;
  if (start && end) return `${start} to ${end}`;
  return start ?? end ?? "—";
}

function mergeAssignmentLists(
  initialAssignments: QuoteAssignmentSafe[] | undefined,
  manualAssignments: QuoteAssignment[],
): Array<QuoteAssignmentSafe | QuoteAssignment> {
  const appointmentRows =
    initialAssignments?.filter(
      (item) => item.is_derived === true || item.source === "eworks_appointment",
    ) ?? [];
  if (appointmentRows.length > 0) {
    return [...appointmentRows, ...manualAssignments];
  }
  if (initialAssignments && initialAssignments.length > 0) {
    return initialAssignments;
  }
  return manualAssignments;
}

export function QuoteAssignmentSection({
  quoteId,
  initialAssignments,
}: {
  quoteId: number | null;
  initialAssignments?: QuoteAssignmentSafe[] | null;
}) {
  const [manualAssignments, setManualAssignments] = useState<QuoteAssignment[]>([]);
  const [assignees, setAssignees] = useState<AssigneeUser[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<number | null>(null);

  const [assignmentType, setAssignmentType] = useState<"estimator" | "engineer">("estimator");
  const [assigneeKind, setAssigneeKind] = useState<"registered" | "external">("registered");
  const [assignedUserId, setAssignedUserId] = useState("");
  const [externalName, setExternalName] = useState("");
  const [externalEmail, setExternalEmail] = useState("");
  const [notes, setNotes] = useState("");

  const load = useCallback(async () => {
    if (!quoteId) return;
    setLoading(true);
    setError(null);
    try {
      const [items, users] = await Promise.all([listQuoteAssignments(quoteId), listAssignees()]);
      setManualAssignments(items);
      setAssignees(users);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load assignments");
    } finally {
      setLoading(false);
    }
  }, [quoteId]);

  useEffect(() => {
    void load();
  }, [load]);

  const assignments = useMemo(
    () => mergeAssignmentLists(initialAssignments ?? undefined, manualAssignments),
    [initialAssignments, manualAssignments],
  );

  const filteredAssignees = assignees.filter((user) =>
    assignmentType === "engineer"
      ? user.role === "engineer" || user.role === "manager"
      : user.role === "estimator",
  );

  const activeAssignments = assignments.filter((item) => isActiveAssignment(item.status));
  const cancelledAssignments = assignments.filter((item) => !isActiveAssignment(item.status));
  const sortedAssignments = [...activeAssignments, ...cancelledAssignments];

  const handleAssign = async () => {
    if (!quoteId) return;
    setSubmitting(true);
    setFormError(null);
    try {
      const payload: AssignmentCreatePayload = {
        assignment_type: assignmentType,
        assignee_kind: assigneeKind,
        notes: notes.trim() || undefined,
      };
      if (assigneeKind === "registered") {
        if (!assignedUserId) {
          setFormError("Select a registered user.");
          return;
        }
        payload.assigned_user_id = assignedUserId;
      } else {
        if (!externalName.trim() && !externalEmail.trim()) {
          setFormError("Enter a name or email for the external assignee.");
          return;
        }
        payload.assigned_user_name = externalName.trim() || undefined;
        payload.assigned_user_email = externalEmail.trim() || undefined;
      }
      await createQuoteAssignment(quoteId, payload);
      setShowForm(false);
      setAssignedUserId("");
      setExternalName("");
      setExternalEmail("");
      setNotes("");
      await load();
    } catch (e: unknown) {
      setFormError(e instanceof Error ? e.message : "Failed to create assignment");
    } finally {
      setSubmitting(false);
    }
  };

  const handleCopyLink = async (assignment: QuoteAssignment | QuoteAssignmentSafe) => {
    const url = buildAssignmentLink(assignment.assignment_link);
    if (!url) return;
    await navigator.clipboard.writeText(url);
    setCopiedId(assignment.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleRevoke = async (assignmentId: number) => {
    setSubmitting(true);
    try {
      await revokeQuoteAssignment(assignmentId);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to revoke assignment");
    } finally {
      setSubmitting(false);
    }
  };

  if (!quoteId) return null;

  return (
    <SectionCard title="Assigned Estimators / Engineers" testId="quote-assignment-section">
      {loading ? (
        <LoadingState message="Loading assignments…" />
      ) : error ? (
        <ErrorState message={error} onRetry={() => void load()} />
      ) : (
        <div className="space-y-4">
          {sortedAssignments.length > 0 ? (
            <DataTable testId="assignments-table">
              <DataTableHead>
                <DataTableRow>
                  <DataTableCell header>Source</DataTableCell>
                  <DataTableCell header>Role</DataTableCell>
                  <DataTableCell header>Name</DataTableCell>
                  <DataTableCell header>Email</DataTableCell>
                  <DataTableCell header>Appointment</DataTableCell>
                  <DataTableCell header>Status</DataTableCell>
                  <DataTableCell header>Actions</DataTableCell>
                </DataTableRow>
              </DataTableHead>
              <DataTableBody>
                {sortedAssignments.map((assignment) => {
                  const isReadOnly =
                    assignment.is_read_only === true ||
                    assignment.source === "eworks_appointment" ||
                    assignment.is_derived === true;
                  const rowKey =
                    assignment.source === "eworks_appointment"
                      ? `appt-${assignment.appointment_id ?? assignment.id}`
                      : `manual-${assignment.id}`;

                  return (
                    <DataTableRow key={rowKey} data-testid={`assignment-row-${assignment.id}`}>
                      <DataTableCell>
                        <StatusBadge tone={assignment.source === "eworks_appointment" ? "info" : "neutral"}>
                          {sourceLabel(assignment.source)}
                        </StatusBadge>
                      </DataTableCell>
                      <DataTableCell>{assignmentTypeLabel(assignment.assignment_type)}</DataTableCell>
                      <DataTableCell>
                        {assignment.assigned_user_name || assignment.assigned_user_email || "—"}
                        {assignment.assignee_kind === "external" ? (
                          <StatusBadge tone="info">External</StatusBadge>
                        ) : assignment.assignee_kind === "registered" ? (
                          <StatusBadge tone="success">Registered user</StatusBadge>
                        ) : null}
                      </DataTableCell>
                      <DataTableCell>{assignment.assigned_user_email || "—"}</DataTableCell>
                      <DataTableCell>{formatAppointmentTime(assignment)}</DataTableCell>
                      <DataTableCell>
                        <StatusBadge tone="neutral">
                          {assignment.source === "eworks_appointment"
                            ? assignment.appointment_status ?? assignment.status ?? "—"
                            : assignment.status ?? "—"}
                        </StatusBadge>
                      </DataTableCell>
                      <DataTableCell>
                        {isReadOnly ? (
                          <span className="text-sm text-slate-500" data-testid={`assignment-readonly-${assignment.id}`}>
                            Locked
                          </span>
                        ) : (
                          <div className="flex flex-wrap gap-2">
                            {assignment.assignee_kind === "external" && assignment.assignment_link ? (
                              <button
                                type="button"
                                className="text-sm font-medium text-blue-600 hover:text-blue-800"
                                onClick={() => void handleCopyLink(assignment)}
                                data-testid={`copy-assignment-link-${assignment.id}`}
                              >
                                {copiedId === assignment.id ? "Copied" : "Copy link"}
                              </button>
                            ) : null}
                            {assignment.status !== "cancelled" ? (
                              <button
                                type="button"
                                className="text-sm font-medium text-red-600 hover:text-red-800"
                                onClick={() => void handleRevoke(assignment.id)}
                                disabled={submitting}
                                data-testid={`revoke-assignment-${assignment.id}`}
                              >
                                Remove
                              </button>
                            ) : null}
                          </div>
                        )}
                      </DataTableCell>
                    </DataTableRow>
                  );
                })}
              </DataTableBody>
            </DataTable>
          ) : (
            <p className="text-sm text-slate-600" data-testid="assignments-empty">
              No assignments yet.
            </p>
          )}

          {showForm ? (
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4" data-testid="assignment-form">
              <div className="grid gap-4 md:grid-cols-2">
                <label className="block text-sm">
                  <span className="font-medium text-slate-700">Assignment type</span>
                  <select
                    className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2"
                    value={assignmentType}
                    onChange={(e) => {
                      setAssignmentType(e.target.value as "estimator" | "engineer");
                      setAssignedUserId("");
                    }}
                    data-testid="assignment-type-select"
                  >
                    <option value="estimator">Estimator</option>
                    <option value="engineer">Engineer</option>
                  </select>
                </label>
                <label className="block text-sm">
                  <span className="font-medium text-slate-700">Assignee type</span>
                  <select
                    className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2"
                    value={assigneeKind}
                    onChange={(e) => setAssigneeKind(e.target.value as "registered" | "external")}
                    data-testid="assignee-kind-select"
                  >
                    <option value="registered">Registered user</option>
                    <option value="external">External / not registered</option>
                  </select>
                </label>
              </div>

              {assigneeKind === "registered" ? (
                <label className="mt-4 block text-sm">
                  <span className="font-medium text-slate-700">Registered user</span>
                  <select
                    className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2"
                    value={assignedUserId}
                    onChange={(e) => setAssignedUserId(e.target.value)}
                    data-testid="assignee-user-select"
                  >
                    <option value="">Select user…</option>
                    {filteredAssignees.map((user) => (
                      <option key={user.id} value={user.id}>
                        {user.name} ({user.email}) — {user.role}
                      </option>
                    ))}
                  </select>
                </label>
              ) : (
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <label className="block text-sm">
                    <span className="font-medium text-slate-700">Name</span>
                    <input
                      className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2"
                      value={externalName}
                      onChange={(e) => setExternalName(e.target.value)}
                      data-testid="external-assignee-name"
                    />
                  </label>
                  <label className="block text-sm">
                    <span className="font-medium text-slate-700">Email</span>
                    <input
                      type="email"
                      className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2"
                      value={externalEmail}
                      onChange={(e) => setExternalEmail(e.target.value)}
                      data-testid="external-assignee-email"
                    />
                  </label>
                </div>
              )}

              <label className="mt-4 block text-sm">
                <span className="font-medium text-slate-700">Notes</span>
                <textarea
                  className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2"
                  rows={3}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  data-testid="assignment-notes"
                />
              </label>

              {formError ? <p className="mt-3 text-sm text-red-600">{formError}</p> : null}

              <div className="mt-4 flex flex-wrap gap-2">
                <PrimaryButton
                  onClick={() => void handleAssign()}
                  disabled={submitting}
                  data-testid="submit-assignment-button"
                >
                  Add assignee
                </PrimaryButton>
                <SecondaryButton onClick={() => setShowForm(false)} disabled={submitting}>
                  Cancel
                </SecondaryButton>
              </div>
            </div>
          ) : (
            <PrimaryButton onClick={() => setShowForm(true)} data-testid="open-assignment-form">
              Add assignee
            </PrimaryButton>
          )}
        </div>
      )}
    </SectionCard>
  );
}
