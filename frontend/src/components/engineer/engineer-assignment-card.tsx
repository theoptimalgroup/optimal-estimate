"use client";

import { CalendarClock, UserRound } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";

import { ReviseEstimateModal } from "@/components/dashboard/revise-estimate-modal";
import { PrimaryButton, SecondaryButton, StatusBadge } from "@/components/ui";
import { cn } from "@/lib/utils";
import { reviseEstimate } from "@/lib/eworks-session";
import {
  assignmentStatusTone,
  formatAppointmentWindow,
  formatAssignedAt,
  formatAssignmentStatusLabel,
  startAssignmentEstimate,
  type QuoteAssignment,
} from "@/lib/quote-assignments";
import { formatEstimateTotal } from "@/lib/engineer-jobs";
import { compactCardPreviewText } from "@/lib/html-text";

type EngineerAssignmentCardProps = {
  assignment: QuoteAssignment;
  variant: "active" | "submitted";
  testIdPrefix?: string;
};

const SCOPE_PREVIEW_MIN_EXPAND_CHARS = 180;

function MetadataChip({
  label,
  value,
  testId,
  icon,
}: {
  label: string;
  value: string;
  testId?: string;
  icon?: ReactNode;
}) {
  return (
    <div
      className="inline-flex min-w-0 max-w-full items-start gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs text-slate-600"
      data-testid={testId}
    >
      {icon ? <span className="mt-0.5 shrink-0 text-slate-400">{icon}</span> : null}
      <span className="min-w-0 break-words">
        <span className="font-medium text-slate-700">{label}:</span> {value}
      </span>
    </div>
  );
}

function ScopePreview({
  rawText,
  testId,
}: {
  rawText: string;
  testId: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const preview = compactCardPreviewText(rawText);
  if (!preview) return null;

  const canExpand = preview.length > SCOPE_PREVIEW_MIN_EXPAND_CHARS;

  return (
    <section
      className="rounded-lg border border-slate-100 bg-slate-50/70 px-3 py-2.5"
      data-testid={testId}
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Scope Preview</p>
      <p
        className={cn(
          "mt-1 break-words text-sm leading-relaxed text-slate-600",
          !expanded && "line-clamp-3 overflow-hidden text-ellipsis",
          expanded && "max-h-32 overflow-y-auto",
        )}
        data-testid={`${testId}-text`}
      >
        {preview}
      </p>
      {canExpand ? (
        <button
          type="button"
          className="mt-1.5 text-xs font-medium text-blue-600 hover:text-blue-700"
          onClick={() => setExpanded((value) => !value)}
          data-testid={`${testId}-toggle`}
        >
          {expanded ? "Show less" : "View details"}
        </button>
      ) : null}
    </section>
  );
}

function formatAppointmentBadge(startAt: string | null | undefined): string | null {
  if (!startAt) return null;
  const date = new Date(startAt);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

export function EngineerAssignmentCard({
  assignment,
  variant,
  testIdPrefix = "engineer-assignment",
}: EngineerAssignmentCardProps) {
  const router = useRouter();
  const [loadingAction, setLoadingAction] = useState<"view" | "revise" | "continue" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showReviseModal, setShowReviseModal] = useState(false);
  const [reviseError, setReviseError] = useState<string | null>(null);

  const testId = `${testIdPrefix}-${assignment.id}`;
  const customer = assignment.quote_summary?.customer_name ?? assignment.customer_name ?? "Customer not available";
  const address = assignment.quote_summary?.site_address ?? assignment.site_address ?? "Address not available";
  const quoteLabel = assignment.quote_ref ?? String(assignment.eworks_quote_id);
  const appointmentWindow = formatAppointmentWindow(
    assignment.appointment_start_at,
    assignment.appointment_end_at,
  );
  const scopeSource = assignment.notes ?? assignment.quote_summary?.description ?? "";
  const assignedBy = assignment.assigned_by_email;
  const assignedAtLabel = formatAssignedAt(assignment.assigned_at);
  const appointmentBadge = formatAppointmentBadge(assignment.appointment_start_at);
  const statusLabel = assignment.revision_in_progress
    ? "Revision in Progress"
    : formatAssignmentStatusLabel(assignment.status);

  const openEstimate = async (mode: "view" | "continue") => {
    setLoadingAction(mode);
    setError(null);
    try {
      const result = await startAssignmentEstimate(assignment.id);
      router.push(result.resume_url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to open estimate");
    } finally {
      setLoadingAction(null);
    }
  };

  const handleReviseConfirm = async (reason: string) => {
    setLoadingAction("revise");
    setReviseError(null);
    try {
      const result = await startAssignmentEstimate(assignment.id);
      await reviseEstimate(result.session_id, result.session_token, reason);
      setShowReviseModal(false);
      router.push(result.resume_url);
    } catch (err) {
      setReviseError(err instanceof Error ? err.message : "Failed to start revision");
    } finally {
      setLoadingAction(null);
    }
  };

  const activeActionLabel = loadingAction
    ? "Opening…"
    : assignment.has_calculation_session
      ? "Resume Estimate"
      : "Start Estimate";

  const activeHelperText = assignment.has_calculation_session
    ? "Continue your estimate"
    : "Start your site estimate";

  return (
    <>
      <article
        className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm transition-colors hover:border-blue-200"
        data-testid={testId}
      >
        {/* Header */}
        <header className="border-b border-slate-100 px-4 py-3 sm:px-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0 flex-1">
              <h3 className="truncate text-base font-semibold text-slate-900">{quoteLabel}</h3>
              <p className="mt-0.5 truncate text-sm text-slate-700">{customer}</p>
              <p className="mt-0.5 truncate text-sm text-slate-500">{address}</p>
            </div>
            <div className="flex shrink-0 flex-wrap items-center gap-2 sm:justify-end">
              {appointmentBadge ? (
                <span
                  className="inline-flex items-center gap-1 rounded-md border border-blue-100 bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700"
                  data-testid={`${testIdPrefix}-appointment-badge-${assignment.id}`}
                >
                  <CalendarClock className="size-3.5" aria-hidden />
                  {appointmentBadge}
                </span>
              ) : null}
              <StatusBadge
                tone={assignmentStatusTone(
                  assignment.revision_in_progress ? "in_progress" : assignment.status,
                )}
                data-testid={`${testIdPrefix}-status-${assignment.id}`}
              >
                {statusLabel}
              </StatusBadge>
            </div>
          </div>
        </header>

        {/* Metadata */}
        <div className="grid gap-2 border-b border-slate-100 px-4 py-3 sm:grid-cols-2 sm:px-5">
          <MetadataChip
            label="Appointment"
            value={appointmentWindow}
            testId={`${testIdPrefix}-appointment-${assignment.id}`}
            icon={<CalendarClock className="size-3.5" aria-hidden />}
          />
          {assignment.assigned_user_name ? (
            <MetadataChip
              label="Engineer"
              value={assignment.assigned_user_name}
              testId={`${testIdPrefix}-assignee-${assignment.id}`}
              icon={<UserRound className="size-3.5" aria-hidden />}
            />
          ) : null}
          {variant === "active" && assignedAtLabel ? (
            <MetadataChip
              label="Assigned"
              value={assignedAtLabel}
              testId={`${testIdPrefix}-date-${assignment.id}`}
            />
          ) : null}
          {assignedBy ? (
            <MetadataChip
              label="Assigned by"
              value={assignedBy}
              testId={`${testIdPrefix}-assigned-by-${assignment.id}`}
            />
          ) : null}
          {variant === "submitted" ? (
            <>
              <MetadataChip
                label="Submitted"
                value={formatAssignedAt(assignment.submitted_at) || "—"}
                testId={`${testIdPrefix}-date-${assignment.id}`}
              />
              {assignment.current_version_number ? (
                <MetadataChip
                  label="Version"
                  value={String(assignment.current_version_number)}
                  testId={`${testIdPrefix}-version-${assignment.id}`}
                />
              ) : null}
              {assignment.final_total != null ? (
                <MetadataChip
                  label="Total"
                  value={formatEstimateTotal(assignment.final_total)}
                  testId={`${testIdPrefix}-total-${assignment.id}`}
                />
              ) : null}
            </>
          ) : null}
        </div>

        {/* Scope preview */}
        {scopeSource ? (
          <div className="px-4 py-3 sm:px-5">
            <ScopePreview
              rawText={scopeSource}
              testId={`${testIdPrefix}-description-${assignment.id}`}
            />
          </div>
        ) : null}

        {/* Footer */}
        <footer className="flex flex-col gap-3 border-t border-slate-100 bg-slate-50/40 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-5">
          {variant === "active" ? (
            <>
              <p className="text-xs text-slate-500">{activeHelperText}</p>
              <PrimaryButton
                type="button"
                className="w-full sm:w-auto"
                disabled={loadingAction !== null || !assignment.can_start_estimate}
                onClick={() => void openEstimate("view")}
                data-testid={`${testIdPrefix}-action-${assignment.id}`}
              >
                {activeActionLabel}
              </PrimaryButton>
            </>
          ) : (
            <>
              <p className="text-xs text-slate-500">Review your submitted estimate</p>
              <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
                <PrimaryButton
                  type="button"
                  className="w-full sm:w-auto"
                  disabled={
                    loadingAction !== null
                    || !assignment.calculation_session_id
                    || assignment.can_view_submission === false
                  }
                  onClick={() => void openEstimate("view")}
                  data-testid={`${testIdPrefix}-view-${assignment.id}`}
                >
                  {loadingAction === "view" ? "Opening…" : "View Submission"}
                </PrimaryButton>
                {assignment.can_continue_revision ? (
                  <SecondaryButton
                    type="button"
                    className="w-full sm:w-auto"
                    disabled={loadingAction !== null}
                    onClick={() => void openEstimate("continue")}
                    data-testid={`${testIdPrefix}-continue-revision-${assignment.id}`}
                  >
                    {loadingAction === "continue" ? "Opening…" : "Continue Revision"}
                  </SecondaryButton>
                ) : assignment.can_revise ? (
                  <SecondaryButton
                    type="button"
                    className="w-full sm:w-auto"
                    disabled={loadingAction !== null}
                    onClick={() => setShowReviseModal(true)}
                    data-testid={`${testIdPrefix}-revise-${assignment.id}`}
                  >
                    Revise Estimate
                  </SecondaryButton>
                ) : null}
              </div>
            </>
          )}
        </footer>

        {error ? <p className="px-4 pb-3 text-xs text-red-600 sm:px-5">{error}</p> : null}
      </article>
      <ReviseEstimateModal
        open={showReviseModal}
        loading={loadingAction === "revise"}
        error={reviseError}
        onCancel={() => {
          setShowReviseModal(false);
          setReviseError(null);
        }}
        onConfirm={handleReviseConfirm}
      />
    </>
  );
}
