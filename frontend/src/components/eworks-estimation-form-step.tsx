"use client";

import type { FromLinkResponse } from "@/lib/eworks-session";
import { EworksSectionTitle, cn } from "@/components/eworks-ui";

function displayValue(value?: string | number | null) {
  if (value === undefined || value === null || value === "") return "—";
  return String(value);
}

function formatDateVisited(value?: string | null) {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

function ReadOnlyField({
  label,
  value,
  className,
}: {
  label: string;
  value?: string | number | null;
  className?: string;
}) {
  return (
    <div className={cn("space-y-2", className)}>
      <dt className="text-sm font-semibold text-optimal-orange">{label}</dt>
      <dd className="min-h-[44px] rounded-lg bg-optimal-field px-3.5 py-2.5 text-sm font-medium leading-relaxed text-optimal-field-text">
        {displayValue(value)}
      </dd>
    </div>
  );
}

function ReadOnlyTextBlock({
  label,
  value,
  className,
  rows = 6,
}: {
  label: string;
  value?: string | null;
  className?: string;
  rows?: number;
}) {
  return (
    <div className={cn("space-y-2", className)}>
      <dt className="text-sm font-semibold text-optimal-orange">{label}</dt>
      <dd
        className="whitespace-pre-wrap rounded-lg bg-optimal-field px-3.5 py-3 text-sm leading-relaxed text-optimal-field-text"
        style={{ minHeight: `${rows * 1.25}rem` }}
      >
        {displayValue(value)}
      </dd>
    </div>
  );
}

type Props = {
  step1: FromLinkResponse["step1"];
  resolved: FromLinkResponse["resolved"];
};

export function EworksEstimationFormStep({ step1, resolved }: Props) {
  return (
    <section className="space-y-6">
      <div className="rounded-lg border border-white/10 bg-white/5 px-4 py-3.5 text-sm leading-relaxed text-optimal-muted">
        This estimation form is supplied by your eWorks link and cannot be edited here.
      </div>

      <dl className="space-y-5">
        <div className="grid gap-5 sm:grid-cols-3">
          <ReadOnlyField label="Engineer Name" value={step1.engineer_name} className="sm:col-span-1" />
          <ReadOnlyField label="Quote Number" value={step1.quote_number} />
          <ReadOnlyField label="Job Number" value={step1.job_number} />
        </div>
        <ReadOnlyField label="Property Address" value={step1.property_address} />
        <div className="grid gap-5 sm:grid-cols-3">
          <ReadOnlyField label="Client" value={step1.client_name} />
          <ReadOnlyField label="PM" value={step1.property_manager_name} />
          <ReadOnlyField label="Date visited / Form completed" value={formatDateVisited(step1.date_visited)} />
        </div>
        <ReadOnlyTextBlock label="Description of what quoting for" value={step1.quote_description} rows={10} />
        <ReadOnlyTextBlock
          label="Findings Report for what has been requested"
          value={step1.findings_report}
          rows={8}
        />
      </dl>

      <div className="rounded-lg border border-white/10 bg-optimal-elevated px-4 py-3.5">
        <EworksSectionTitle title="Rate rule" />
        <p className="mt-2 text-xs leading-relaxed text-optimal-muted">
          Trade: {step1.trade_name} · Rule: {resolved.formula_source.toUpperCase()}
          {resolved.xlsx_client_name ? ` · ${resolved.xlsx_client_name}` : ""}
        </p>
      </div>
    </section>
  );
}
