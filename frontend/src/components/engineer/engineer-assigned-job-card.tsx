"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { PrimaryButton, StatusBadge } from "@/components/ui";
import { formatAssignedAt } from "@/lib/quote-assignments";
import { formatEstimateTotal, type EngineerAssignedJob } from "@/lib/engineer-jobs";
import { startAssignmentEstimate } from "@/lib/quote-assignments";

type EngineerAssignedJobCardProps = {
  job: EngineerAssignedJob;
};

export function EngineerAssignedJobCard({ job }: EngineerAssignedJobCardProps) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const quoteLabel = job.quote_ref ?? (job.eworks_quote_id != null ? String(job.eworks_quote_id) : "Quote");

  const handleOpenJob = async () => {
    if (job.assignment_id == null) {
      setError("This job cannot be opened yet.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await startAssignmentEstimate(job.assignment_id);
      router.push(result.resume_url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to open job");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="rounded-xl border border-slate-200 bg-white p-4 transition-colors hover:border-blue-300"
      data-testid={`engineer-assigned-job-${job.id}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1 space-y-1">
          <p className="font-semibold text-slate-900">{quoteLabel}</p>
          {job.job_ref ? <p className="text-sm text-slate-600">Job {job.job_ref}</p> : null}
          <p className="text-sm text-slate-600">{job.customer_name ?? "Customer not available"}</p>
          <p className="text-sm text-slate-600">{job.address ?? "Address not available"}</p>
          <p className="text-xs text-slate-500" data-testid={`engineer-assigned-job-date-${job.id}`}>
            Selected {formatAssignedAt(job.selected_at)}
          </p>
          {job.selected_estimate_total != null ? (
            <p className="text-sm font-medium text-slate-900" data-testid={`engineer-assigned-job-total-${job.id}`}>
              {formatEstimateTotal(job.selected_estimate_total)}
            </p>
          ) : null}
        </div>
        <StatusBadge tone="success" data-testid={`engineer-assigned-job-status-${job.id}`}>
          Assigned
        </StatusBadge>
      </div>
      <PrimaryButton
        type="button"
        onClick={() => void handleOpenJob()}
        disabled={loading || job.assignment_id == null}
        className="mt-4"
        data-testid={`engineer-assigned-job-open-${job.id}`}
      >
        {loading ? "Opening…" : "Open Job"}
      </PrimaryButton>
      {error ? <p className="mt-2 text-xs text-red-600">{error}</p> : null}
    </div>
  );
}
