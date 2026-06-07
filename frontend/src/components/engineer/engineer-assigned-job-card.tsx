"use client";

import { StatusBadge } from "@/components/ui";
import { formatEstimateTotal, type EngineerAssignedJob } from "@/lib/engineer-jobs";

type EngineerAssignedJobCardProps = {
  job: EngineerAssignedJob;
};

export function EngineerAssignedJobCard({ job }: EngineerAssignedJobCardProps) {
  const quoteLabel = job.quote_ref ?? (job.eworks_quote_id != null ? String(job.eworks_quote_id) : "Quote");
  const statusLabel = job.status_name ?? job.status ?? "Assigned";

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
          {job.job_date ? (
            <p className="text-xs text-slate-500" data-testid={`engineer-assigned-job-date-${job.id}`}>
              Job date {job.job_date}
            </p>
          ) : null}
          {job.total != null ? (
            <p className="text-sm font-medium text-slate-900" data-testid={`engineer-assigned-job-total-${job.id}`}>
              {formatEstimateTotal(job.total)}
            </p>
          ) : null}
          {job.description ? <p className="text-sm text-slate-600">{job.description}</p> : null}
        </div>
        <StatusBadge tone="success" data-testid={`engineer-assigned-job-status-${job.id}`}>
          {statusLabel}
        </StatusBadge>
      </div>
      {/* TODO: Open Job deep-link once eWorks job navigation is integrated. */}
    </div>
  );
}
