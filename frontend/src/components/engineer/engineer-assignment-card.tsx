"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { ReviseEstimateModal } from "@/components/dashboard/revise-estimate-modal";
import { PrimaryButton, SecondaryButton, StatusBadge } from "@/components/ui";
import { reviseEstimate } from "@/lib/eworks-session";
import {
  assignmentStatusTone,
  formatAssignedAt,
  formatAssignmentStatusLabel,
  startAssignmentEstimate,
  type QuoteAssignment,
} from "@/lib/quote-assignments";
import { formatEstimateTotal } from "@/lib/engineer-jobs";

type EngineerAssignmentCardProps = {
  assignment: QuoteAssignment;
  variant: "active" | "submitted";
  testIdPrefix?: string;
};

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
  const customer = assignment.quote_summary?.customer_name ?? "Customer not available";
  const address = assignment.quote_summary?.site_address ?? "Address not available";
  const quoteLabel = assignment.quote_ref ?? String(assignment.eworks_quote_id);

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

  return (
    <>
      <div
        className="rounded-xl border border-slate-200 bg-white p-4 transition-colors hover:border-blue-300"
        data-testid={testId}
      >
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 flex-1 space-y-1">
            <p className="font-semibold text-slate-900">{quoteLabel}</p>
            <p className="text-sm text-slate-600">{customer}</p>
            <p className="text-sm text-slate-600">{address}</p>
            {variant === "active" ? (
              <p className="text-xs text-slate-500" data-testid={`${testIdPrefix}-date-${assignment.id}`}>
                Assigned {formatAssignedAt(assignment.assigned_at)}
              </p>
            ) : (
              <>
                <p className="text-xs text-slate-500" data-testid={`${testIdPrefix}-date-${assignment.id}`}>
                  Submitted {formatAssignedAt(assignment.submitted_at)}
                </p>
                {assignment.current_version_number ? (
                  <p className="text-xs text-slate-500" data-testid={`${testIdPrefix}-version-${assignment.id}`}>
                    Version {assignment.current_version_number}
                  </p>
                ) : null}
                {assignment.final_total != null ? (
                  <p
                    className="text-sm font-medium text-slate-900"
                    data-testid={`${testIdPrefix}-total-${assignment.id}`}
                  >
                    {formatEstimateTotal(assignment.final_total)}
                  </p>
                ) : null}
              </>
            )}
          </div>
          <StatusBadge
            tone={assignmentStatusTone(assignment.status)}
            data-testid={`${testIdPrefix}-status-${assignment.id}`}
          >
            {formatAssignmentStatusLabel(assignment.status)}
          </StatusBadge>
        </div>
        {variant === "active" ? (
          <PrimaryButton
            type="button"
            className="mt-4"
            disabled={loadingAction !== null || !assignment.can_start_estimate}
            onClick={() => void openEstimate("view")}
            data-testid={`${testIdPrefix}-action-${assignment.id}`}
          >
            {loadingAction ? "Opening…" : assignment.has_calculation_session ? "Continue Estimate" : "Start Estimate"}
          </PrimaryButton>
        ) : (
          <div className="mt-4 flex flex-wrap gap-2">
            <PrimaryButton
              type="button"
              disabled={loadingAction !== null || !assignment.calculation_session_id}
              onClick={() => void openEstimate("view")}
              data-testid={`${testIdPrefix}-view-${assignment.id}`}
            >
              {loadingAction === "view" ? "Opening…" : "View Submission"}
            </PrimaryButton>
            {assignment.can_continue_revision ? (
              <SecondaryButton
                type="button"
                disabled={loadingAction !== null}
                onClick={() => void openEstimate("continue")}
                data-testid={`${testIdPrefix}-continue-revision-${assignment.id}`}
              >
                {loadingAction === "continue" ? "Opening…" : "Continue Revision"}
              </SecondaryButton>
            ) : assignment.can_revise ? (
              <SecondaryButton
                type="button"
                disabled={loadingAction !== null}
                onClick={() => setShowReviseModal(true)}
                data-testid={`${testIdPrefix}-revise-${assignment.id}`}
              >
                Revise Estimate
              </SecondaryButton>
            ) : null}
          </div>
        )}
        {error ? <p className="mt-2 text-xs text-red-600">{error}</p> : null}
      </div>
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
