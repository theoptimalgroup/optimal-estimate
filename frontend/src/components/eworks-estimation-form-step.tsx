"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { FromLinkResponse } from "@/lib/eworks-session";
import { EworksSectionTitle, EworksTextarea, cn } from "@/components/eworks-ui";
import { SafeRichText } from "@/components/ui/safe-rich-text";

function displayValue(value?: string | number | null) {
  if (value === undefined || value === null || value === "") return "—";
  return String(value);
}

function formatCommissionPct(value?: number | string | null) {
  const pct = Number(value ?? 0);
  if (!Number.isFinite(pct) || pct <= 0) return null;
  const display = pct <= 1 ? Math.round(pct * 100) : Math.round(pct);
  return `${display}%`;
}

function rateRuleLabel(resolved: FromLinkResponse["resolved"]) {
  if (resolved.formula_source === "none") {
    const commission = formatCommissionPct(resolved.client_fee_pct);
    return commission ? `EWORKS (${commission} COMMISSION)` : "DEFAULT (0% COMMISSION)";
  }
  return resolved.formula_source.toUpperCase();
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
  testId,
}: {
  label: string;
  value?: string | null;
  className?: string;
  rows?: number;
  testId?: string;
}) {
  return (
    <div className={cn("space-y-2", className)}>
      <dt className="text-sm font-semibold text-optimal-orange">{label}</dt>
      <dd
        className="rounded-lg bg-optimal-field px-3.5 py-3 text-optimal-field-text"
        style={{ minHeight: `${rows * 1.25}rem` }}
        data-testid={testId}
      >
        <SafeRichText value={value} emptyText="—" variant="inline" />
      </dd>
    </div>
  );
}

type Props = {
  step1: FromLinkResponse["step1"];
  resolved: FromLinkResponse["resolved"];
  onFindingsReportChange?: (value: string) => void;
  findingsReportSaving?: boolean;
  submitted?: boolean;
};

export function EworksEstimationFormStep({ step1, resolved, onFindingsReportChange, findingsReportSaving, submitted }: Props) {
  const [localFindings, setLocalFindings] = useState(step1.findings_report ?? "");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setLocalFindings(step1.findings_report ?? "");
  }, [step1.findings_report]);

  const handleFindingsChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const value = e.target.value;
      setLocalFindings(value);
      if (!onFindingsReportChange) return;
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        onFindingsReportChange(value);
      }, 800);
    },
    [onFindingsReportChange],
  );

  return (
    <section className="space-y-6">
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
        <ReadOnlyTextBlock
          label="Description of what quoting for"
          value={step1.quote_description}
          rows={10}
          testId="quote-description-rich-text"
        />

        <div className="space-y-2">
          <dt className="flex items-center gap-2 text-sm font-semibold text-optimal-orange">
            Findings Report for what has been requested
            {findingsReportSaving && (
              <span className="text-xs font-normal text-optimal-muted">Saving…</span>
            )}
          </dt>
          <EworksTextarea
            value={localFindings}
            onChange={handleFindingsChange}
            disabled={submitted}
            rows={8}
            placeholder="Enter findings report…"
            className="w-full"
          />
        </div>
      </dl>

      <div className="rounded-lg border border-gray-200 bg-optimal-elevated px-4 py-3.5">
        <EworksSectionTitle title="Rate rule" />
        <p className="mt-2 text-xs leading-relaxed text-optimal-muted">
          Trade: {step1.trade_name} · Rule: {rateRuleLabel(resolved)}
          {resolved.xlsx_client_name ? ` · ${resolved.xlsx_client_name}` : ""}
        </p>
      </div>
    </section>
  );
}
