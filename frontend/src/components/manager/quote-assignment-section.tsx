"use client";

import { useCallback, useEffect, useState } from "react";

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

export function QuoteAssignmentSection({ quoteId }: { quoteId: number | null }) {
  const [assignments, setAssignments] = useState<QuoteAssignment[]>([]);
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
      setAssignments(items);
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

  const filteredAssignees = assignees.filter((user) => user.role === assignmentType);

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

  const handleCopyLink = async (assignment: QuoteAssignment) => {
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
    <SectionCard title="Assign Estimator / Engineer" testId="quote-assignment-section">
      {loading ? (
        <LoadingState message="Loading assignments…" />
      ) : error ? (
        <ErrorState message={error} onRetry={() => void load()} />
      ) : (
        <div className="space-y-4">
          {assignments.length === 0 ? (
            <p className="text-sm text-slate-600" data-testid="assignments-empty">
              No assignments yet.
            </p>
          ) : (
            <DataTable testId="assignments-table">
              <DataTableHead>
                <DataTableRow>
                  <DataTableCell header>Type</DataTableCell>
                  <DataTableCell header>Assignee</DataTableCell>
                  <DataTableCell header>Status</DataTableCell>
                  <DataTableCell header>Assigned At</DataTableCell>
                  <DataTableCell header>Actions</DataTableCell>
                </DataTableRow>
              </DataTableHead>
              <DataTableBody>
                {assignments.map((assignment) => (
                  <DataTableRow key={assignment.id} data-testid={`assignment-row-${assignment.id}`}>
                    <DataTableCell>{assignmentTypeLabel(assignment.assignment_type)}</DataTableCell>
                    <DataTableCell>
                      {assignment.assigned_user_name || assignment.assigned_user_email || "—"}
                      {assignment.assignee_kind === "external" ? (
                        <StatusBadge tone="info">External</StatusBadge>
                      ) : null}
                    </DataTableCell>
                    <DataTableCell>
                      <StatusBadge tone="neutral">{assignment.status}</StatusBadge>
                    </DataTableCell>
                    <DataTableCell>{assignment.assigned_at ?? "—"}</DataTableCell>
                    <DataTableCell>
                      <div className="flex flex-wrap gap-2">
                        {assignment.assignee_kind === "external" && assignment.assignment_link ? (
                          <div className="flex flex-col gap-1">
                            <button
                              type="button"
                              className="text-sm font-medium text-blue-600 hover:text-blue-800"
                              onClick={() => void handleCopyLink(assignment)}
                              data-testid={`copy-assignment-link-${assignment.id}`}
                            >
                              {copiedId === assignment.id ? "Copied" : "Copy link"}
                            </button>
                          </div>
                        ) : null}
                        {assignment.status !== "cancelled" ? (
                          <button
                            type="button"
                            className="text-sm font-medium text-red-600 hover:text-red-800"
                            onClick={() => void handleRevoke(assignment.id)}
                            disabled={submitting}
                            data-testid={`revoke-assignment-${assignment.id}`}
                          >
                            Revoke
                          </button>
                        ) : null}
                      </div>
                    </DataTableCell>
                  </DataTableRow>
                ))}
              </DataTableBody>
            </DataTable>
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
                  Assign
                </PrimaryButton>
                <SecondaryButton onClick={() => setShowForm(false)} disabled={submitting}>
                  Cancel
                </SecondaryButton>
              </div>
            </div>
          ) : (
            <PrimaryButton onClick={() => setShowForm(true)} data-testid="open-assignment-form">
              Assign
            </PrimaryButton>
          )}
        </div>
      )}
    </SectionCard>
  );
}
