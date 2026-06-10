"use client";

import { StatusBadge } from "@/components/ui";
import { formatEstimateTotal, type EngineerAssignedJob } from "@/lib/engineer-jobs";
import { cleanHtmlToReadableText } from "@/lib/html-text";

type EngineerAssignedJobCardProps = {
  job: EngineerAssignedJob;
};

function formatAppointmentWindow(job: EngineerAssignedJob): string | null {
  if (job.appointment_start_at && job.appointment_end_at) {
    return `${job.appointment_start_at} – ${job.appointment_end_at}`;
  }
  return job.appointment_start_at ?? job.appointment_end_at ?? null;
}

export function EngineerAssignedJobCard({ job }: EngineerAssignedJobCardProps) {
  const jobLabel = job.job_ref ?? `Job ${job.eworks_job_id}`;
  const appointmentWindow = formatAppointmentWindow(job);
  const statusLabel = job.appointment_status ?? job.status_name ?? job.status ?? "Assigned";

  return (
    <div
      className="rounded-xl border border-slate-200 bg-white p-4 transition-colors hover:border-blue-300"
      data-testid={`engineer-assigned-job-${job.id}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1 space-y-1">
          <p className="font-semibold text-slate-900">{jobLabel}</p>
          {job.quote_ref ? <p className="text-sm text-slate-600">Quote {job.quote_ref}</p> : null}
          <p className="text-sm text-slate-600">{job.customer_name ?? "Customer not available"}</p>
          <p className="text-sm text-slate-600">{job.address ?? "Address not available"}</p>
          {appointmentWindow ? (
            <p className="text-sm text-slate-600" data-testid={`engineer-assigned-job-appointment-${job.id}`}>
              Appointment: {appointmentWindow}
            </p>
          ) : null}
          {job.appointment_user_name ? (
            <p className="text-sm text-slate-600" data-testid={`engineer-assigned-job-assignee-${job.id}`}>
              Assigned to: {job.appointment_user_name}
            </p>
          ) : null}
          {job.total != null ? (
            <p className="text-sm font-medium text-slate-900" data-testid={`engineer-assigned-job-total-${job.id}`}>
              {formatEstimateTotal(job.total)}
            </p>
          ) : null}
          {job.description ? (
            <p className="whitespace-pre-line text-sm text-slate-600">{cleanHtmlToReadableText(job.description)}</p>
          ) : null}
        </div>
        <StatusBadge tone="success" data-testid={`engineer-assigned-job-status-${job.id}`}>
          {statusLabel}
        </StatusBadge>
      </div>
    </div>
  );
}
