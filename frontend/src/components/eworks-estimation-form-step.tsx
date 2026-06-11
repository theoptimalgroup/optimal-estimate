"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Control, FieldErrors, UseFormRegister, UseFormSetValue, UseFormWatch } from "react-hook-form";
import type { FromLinkResponse } from "@/lib/eworks-session";
import { EworksAdditionalChargesForm } from "@/components/eworks-additional-charges-form";
import { EworksTextarea, cn } from "@/components/eworks-ui";
import { VoiceDictationButton } from "@/components/voice/VoiceDictationButton";
import { SafeRichText } from "@/components/ui/safe-rich-text";
import type { QuestionnaireFormValues } from "@/lib/eworks-calculate-schema";

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

function isUnknownCustomer(clientName?: string | null) {
  return (clientName ?? "").trim().toLowerCase() === "unknown customer";
}

function FormSectionCard({
  title,
  testId,
  children,
  className,
}: {
  title: string;
  testId: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section
      className={cn(
        "rounded-xl border border-slate-200 bg-white p-5 shadow-sm",
        className,
      )}
      data-testid={testId}
    >
      <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function SummaryField({
  label,
  value,
  className,
}: {
  label: string;
  value?: string | number | null;
  className?: string;
}) {
  return (
    <div className={className}>
      <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-1 text-sm font-medium text-slate-900">{displayValue(value)}</dd>
    </div>
  );
}

function QuoteDescriptionCard({ value }: { value?: string | null }) {
  const [expanded, setExpanded] = useState(false);
  const isLong = (value?.length ?? 0) > 480;

  return (
    <FormSectionCard title="Quote Description" testId="estimation-quote-description">
      <div
        className={cn(
          "rounded-lg border border-slate-100 bg-slate-50 px-3.5 py-3 text-slate-900",
          !expanded && isLong && "max-h-48 overflow-y-auto",
        )}
        data-testid="quote-description-rich-text"
      >
        <SafeRichText value={value} emptyText="—" variant="inline" />
      </div>
      {isLong ? (
        <button
          type="button"
          className="mt-3 text-sm font-medium text-blue-600 hover:text-blue-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/30"
          onClick={() => setExpanded((current) => !current)}
          data-testid="quote-description-toggle"
        >
          {expanded ? "Show less" : "Show more"}
        </button>
      ) : null}
    </FormSectionCard>
  );
}

type Props = {
  step1: FromLinkResponse["step1"];
  resolved: FromLinkResponse["resolved"];
  control: Control<QuestionnaireFormValues>;
  register: UseFormRegister<QuestionnaireFormValues>;
  watch: UseFormWatch<QuestionnaireFormValues>;
  setValue: UseFormSetValue<QuestionnaireFormValues>;
  errors: FieldErrors<QuestionnaireFormValues>;
  onFindingsReportChange?: (value: string) => void;
  findingsReportSaving?: boolean;
  submitted?: boolean;
};

export function EworksEstimationFormStep({
  step1,
  control,
  register,
  watch,
  setValue,
  errors,
  onFindingsReportChange,
  findingsReportSaving,
  submitted,
}: Props) {
  const chargeValues = watch();
  const [localFindings, setLocalFindings] = useState(step1.findings_report ?? "");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const findingsFieldId = "estimation-findings-report-input";

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

  const showUnknownCustomerBadge = isUnknownCustomer(step1.client_name);

  return (
    <section className="space-y-5">
      <FormSectionCard title="Quote Summary" testId="estimation-quote-summary">
        <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <SummaryField label="Quote Number" value={step1.quote_number} />
          <SummaryField label="Job Number" value={step1.job_number} />
          <SummaryField label="Client" value={step1.client_name} />
          <SummaryField label="Property Address" value={step1.property_address} />
        </dl>
      </FormSectionCard>

      <FormSectionCard title="Job Information" testId="estimation-job-information">
        <dl className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          <SummaryField label="Engineer Name" value={step1.engineer_name} />
          <SummaryField label="PM" value={step1.property_manager_name} />
          <SummaryField label="Date visited / Form completed" value={formatDateVisited(step1.date_visited)} />
          <SummaryField label="Quote Number" value={step1.quote_number} />
          <SummaryField label="Job Number" value={step1.job_number} />
        </dl>
      </FormSectionCard>

      <FormSectionCard title="Property & Client" testId="estimation-property-client">
        <div className="space-y-4">
          {showUnknownCustomerBadge ? (
            <span
              className="inline-flex items-center rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-800"
              data-testid="customer-not-matched-badge"
            >
              Customer not matched
            </span>
          ) : null}
          <dl className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <SummaryField label="Client" value={step1.client_name} />
            <SummaryField label="Property Address" value={step1.property_address} />
            <SummaryField label="Contact" value={step1.contact} />
            <SummaryField label="PM" value={step1.property_manager_name} />
          </dl>
        </div>
      </FormSectionCard>

      <QuoteDescriptionCard value={step1.quote_description} />

      <FormSectionCard title="Findings Report" testId="estimation-findings-report">
        <div className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <label htmlFor={findingsFieldId} className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Findings Report
            </label>
            <div className="flex flex-wrap items-center gap-2">
              <VoiceDictationButton
                context="engineer_findings"
                mode="append"
                disabled={submitted}
                onCleanText={(text) => {
                  const current = localFindings.trim();
                  const next = current ? `${current}\n\n${text}` : text;
                  setLocalFindings(next);
                  onFindingsReportChange?.(next);
                }}
              />
              {findingsReportSaving ? (
                <span className="text-xs font-medium text-slate-500" data-testid="findings-report-saving">
                  Saving…
                </span>
              ) : null}
            </div>
          </div>
          <EworksTextarea
            id={findingsFieldId}
            value={localFindings}
            onChange={handleFindingsChange}
            disabled={submitted}
            rows={8}
            placeholder="Enter findings report…"
            className="w-full"
            data-testid="findings-report-input"
          />
        </div>
      </FormSectionCard>

      <EworksAdditionalChargesForm
        control={control}
        register={register}
        setValue={setValue}
        errors={errors}
        values={chargeValues}
      />
    </section>
  );
}
