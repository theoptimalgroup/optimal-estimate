"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { PrimaryButton } from "@/components/ui";
import { startAssignmentEstimate, type QuoteAssignment } from "@/lib/quote-assignments";

type AssignmentEstimateButtonProps = {
  assignment: QuoteAssignment;
  label?: string;
  className?: string;
  variant?: "link" | "button";
  testId?: string;
};

export function assignmentEstimateLabel(assignment: QuoteAssignment): string {
  return assignment.has_calculation_session ? "Continue Estimate" : "Start Estimate";
}

export function AssignmentEstimateButton({
  assignment,
  label,
  className,
  variant = "button",
  testId,
}: AssignmentEstimateButtonProps) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const text = label ?? assignmentEstimateLabel(assignment);

  const handleClick = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await startAssignmentEstimate(assignment.id);
      router.push(result.resume_url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to open estimate");
    } finally {
      setLoading(false);
    }
  };

  if (variant === "link") {
    return (
      <span className={className}>
        <button
          type="button"
          onClick={() => void handleClick()}
          disabled={loading || !assignment.can_start_estimate}
          className="shrink-0 text-sm font-medium text-blue-600 hover:text-blue-700 disabled:opacity-50"
          data-testid={testId}
        >
          {loading ? "Opening…" : text}
        </button>
        {error ? <span className="mt-1 block text-xs text-red-600">{error}</span> : null}
      </span>
    );
  }

  return (
    <div className={className}>
      <PrimaryButton
        type="button"
        onClick={() => void handleClick()}
        disabled={loading || !assignment.can_start_estimate}
        data-testid={testId}
      >
        {loading ? "Opening…" : text}
      </PrimaryButton>
      {error ? <p className="mt-2 text-xs text-red-600">{error}</p> : null}
    </div>
  );
}
