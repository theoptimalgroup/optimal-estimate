"use client";

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useForm, type FieldErrors } from "react-hook-form";
import { questionnaireResolver } from "@/lib/eworks-questionnaire-resolver";
import { EworksEstimationFormStep } from "@/components/eworks-estimation-form-step";
import { EworksQuestionnaireStep } from "@/components/eworks-questionnaire-step";
import {
  EworksButton,
  EworksCard,
  EworksCheckbox,
  EworksFieldError,
  EworksInput,
  EworksLabel,
  EworksLoadingScreen,
  EworksPageShell,
  EworksSaveStatus,
  EworksSectionTitle,
  EworksStepIndicator,
  eworksInputClass,
} from "@/components/eworks-ui";
import {
  calculateSession,
  createDevTestSession,
  createSessionFromLink,
  downloadSessionPdf,
  patchSession,
  storeSessionCredentials,
  uploadSessionAttachment,
  type CalculateResponse,
  type FromLinkResponse,
  type SessionUiState,
} from "@/lib/eworks-session";
import {
  CHARGES_FIELDS,
  defaultQuestionnaireValues,
  EWORKS_STEPS,
  questionnaireToStep2,
  QUESTIONNAIRE_FIELDS,
  step2ToQuestionnaire,
  type QuestionnaireFormValues,
} from "@/lib/eworks-calculate-schema";
import { numberFieldOptions } from "@/lib/form-number";
import { fetchAllTrades } from "@/lib/trades";

type SaveStatus = "idle" | "saving" | "saved" | "error";

function money(value?: number | string | null) {
  if (value === undefined || value === null || value === "") return "—";
  return `£${Number(value).toFixed(2)}`;
}

function firstInvalidWorkIndex(errors: FieldErrors<QuestionnaireFormValues>): number | null {
  if (!Array.isArray(errors.works)) return null;
  const index = errors.works.findIndex((workErrors) => workErrors && Object.keys(workErrors).length > 0);
  return index >= 0 ? index : null;
}

function workFieldLabel(path: string[]): string | null {
  const field = path[path.length - 1];
  const rowIndex = path.findIndex((segment) => /^\d+$/.test(segment));
  const rowNumber = rowIndex >= 0 ? Number(path[rowIndex]) + 1 : null;
  const section = path.includes("materials_to_order")
    ? "Materials to order"
    : path.includes("shelf_materials_rows")
      ? "Shelf materials"
      : null;

  const labels: Record<string, string> = {
    scope: "Scope of works",
    skill_required: "Skill required",
    quantity: "quantity",
    cost: "cost",
    engineers_needed: "Number of engineers",
    engineer_time_value: "Duration",
    engineer_time_unit: "Hours or days",
    labour_needed: "Number of labour",
    labour_time_value: "Labour duration",
    engineers_required: "Engineer needed",
    markup_value: "Markup percentage",
    materials_to_order: "Materials to order",
    shelf_materials_rows: "Shelf materials",
  };

  if (section && rowNumber && field) {
    return `${section} row ${rowNumber} ${labels[field] ?? field}`;
  }
  return labels[field] ?? null;
}

function firstErrorMessage(error: unknown, path: string[] = []): string | null {
  if (!error || typeof error !== "object") return null;
  if ("message" in error && typeof (error as { message?: unknown }).message === "string") {
    const message = (error as { message: string }).message;
    if (message === "Invalid input" || message.startsWith("Invalid input:")) {
      const label = workFieldLabel(path);
      return label ? `Enter a valid ${label}` : "Complete all required fields";
    }
    if (message) return message;
  }
  if (Array.isArray(error)) {
    for (let index = 0; index < error.length; index += 1) {
      const nested = firstErrorMessage(error[index], [...path, String(index)]);
      if (nested) return nested;
    }
    return null;
  }
  for (const [key, value] of Object.entries(error)) {
    const nested = firstErrorMessage(value, [...path, key]);
    if (nested) return nested;
  }
  return null;
}

function questionnaireValidationMessage(errors: FieldErrors<QuestionnaireFormValues>): string | null {
  const workIndex = firstInvalidWorkIndex(errors);
  if (workIndex === null) return null;
  const workErrors = errors.works?.[workIndex];
  const message = firstErrorMessage(workErrors) ?? "complete all required fields";
  return `Work ${workIndex + 1}: ${message}`;
}

function restoreUiState(
  uiState: SessionUiState | null | undefined,
  setters: {
    setStep: (value: number) => void;
    setMaxReachableStep: (value: number) => void;
    setResults: (value: CalculateResponse | null) => void;
  },
) {
  if (!uiState) return;
  setters.setStep(uiState.current_step ?? 0);
  setters.setMaxReachableStep(uiState.max_reachable_step ?? uiState.current_step ?? 0);
  if (uiState.last_result) {
    setters.setResults(uiState.last_result);
  }
}

function EworksCalculateContent() {
  const searchParams = useSearchParams();
  const payload = searchParams.get("payload");
  const sig = searchParams.get("sig");

  const [step, setStep] = useState(0);
  const [maxReachableStep, setMaxReachableStep] = useState(0);
  const [session, setSession] = useState<FromLinkResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [results, setResults] = useState<CalculateResponse | null>(null);
  const [calcError, setCalcError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [skillOptions, setSkillOptions] = useState<string[]>([]);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [focusWorkIndex, setFocusWorkIndex] = useState<number | null>(null);
  const autoSaveReady = useRef(false);
  const isDev = process.env.NODE_ENV === "development";

  const form = useForm<QuestionnaireFormValues>({
    resolver: questionnaireResolver,
    defaultValues: defaultQuestionnaireValues,
    mode: "onChange",
  });

  const {
    register,
    watch,
    reset,
    trigger,
    setValue,
    control,
    formState: { errors },
  } = form;

  const applySession = useCallback(
    (data: FromLinkResponse) => {
      setSession(data);
      storeSessionCredentials(
        data.step1.quote_number,
        data.step1.job_number,
        data.session_id,
        data.session_token,
      );
      reset(
        step2ToQuestionnaire(data.step2, data.step1.trade_name, {
          congestion_required: data.step1.congestion_required,
          congestion_amount: Number(data.step1.congestion_amount ?? 0),
          travel_charge: Number(data.step1.travel ?? 0),
        }),
      );
      restoreUiState(data.ui_state, { setStep, setMaxReachableStep, setResults });
      autoSaveReady.current = false;
      window.setTimeout(() => {
        autoSaveReady.current = true;
      }, 500);
    },
    [reset],
  );

  const values = watch();

  useEffect(() => {
    let cancelled = false;
    async function bootstrap() {
      if (!payload) {
        setLoadError("Invalid or missing calculation link");
        setLoading(false);
        return;
      }
      setLoading(true);
      setLoadError(null);
      try {
        const res = await createSessionFromLink(payload, sig);
        if (cancelled) return;
        applySession(res.data);
      } catch (error) {
        if (cancelled) return;
        const message = error instanceof Error ? error.message : "Failed to open calculation link";
        setLoadError(message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    bootstrap();
    return () => {
      cancelled = true;
    };
  }, [payload, sig, applySession]);

  const startDevTestSession = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const res = await createDevTestSession();
      applySession(res.data);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to start local test session";
      setLoadError(message);
    } finally {
      setLoading(false);
    }
  }, [applySession]);

  useEffect(() => {
    if (!session) return;
    const fallbackSkill = session.step1.trade_name;
    let cancelled = false;
    async function loadSkills() {
      try {
        const trades = await fetchAllTrades();
        if (cancelled) return;
        setSkillOptions(trades.map((trade) => trade.name).sort((a, b) => a.localeCompare(b)));
      } catch {
        if (cancelled) return;
        setSkillOptions([fallbackSkill]);
      }
    }
    void loadSkills();
    return () => {
      cancelled = true;
    };
  }, [session]);

  const autosave = useCallback(
    async (formValues: QuestionnaireFormValues) => {
      if (!session || !autoSaveReady.current || step === 0 || step === 3) return;
      setSaveStatus("saving");
      try {
        await patchSession(session.session_id, session.session_token, {
          step2: questionnaireToStep2(formValues),
          ui_state: {
            current_step: step,
            max_reachable_step: maxReachableStep,
            last_result: results,
          },
        });
        setSaveStatus("saved");
      } catch {
        setSaveStatus("error");
      }
    },
    [session, step, maxReachableStep, results],
  );

  const saveProgress = useCallback(async () => {
    if (!session || !autoSaveReady.current) return;
    try {
      await patchSession(session.session_id, session.session_token, {
        ui_state: {
          current_step: step,
          max_reachable_step: maxReachableStep,
          last_result: results,
        },
      });
    } catch {
      // ignore background progress save failures
    }
  }, [session, step, maxReachableStep, results]);

  useEffect(() => {
    if (!session || step === 0 || step === 3) return;
    const timer = window.setTimeout(() => {
      void autosave(values);
    }, 800);
    return () => window.clearTimeout(timer);
  }, [values, session, step, autosave]);

  useEffect(() => {
    if (!session || !autoSaveReady.current) return;
    const timer = window.setTimeout(() => {
      void saveProgress();
    }, 400);
    return () => window.clearTimeout(timer);
  }, [session, step, maxReachableStep, results, saveProgress]);

  const step1 = session?.step1;

  const handleUploadFiles = useCallback(
    async (files: FileList | null, workIndex: number) => {
      if (!session || !files?.length) return;
      setUploading(true);
      try {
        const uploaded = [];
        for (const file of Array.from(files)) {
          uploaded.push(await uploadSessionAttachment(session.session_id, session.session_token, file, workIndex));
        }
        const current = values.works[workIndex]?.attachments ?? [];
        setValue(`works.${workIndex}.attachments`, [...current, ...uploaded], { shouldValidate: true });
      } catch (error) {
        setCalcError(error instanceof Error ? error.message : "Upload failed");
      } finally {
        setUploading(false);
      }
    },
    [session, setValue, values.works],
  );

  const validateCurrentStep = useCallback(async () => {
    if (step === 0 || step === 3) return true;
    if (step === 1) {
      const valid = await trigger([...QUESTIONNAIRE_FIELDS]);
      if (!valid) {
        const currentErrors = form.formState.errors;
        setValidationError(
          questionnaireValidationMessage(currentErrors) ?? "Please complete all required fields in the questionnaire.",
        );
        setFocusWorkIndex(firstInvalidWorkIndex(currentErrors));
      }
      return valid;
    }
    if (step === 2) {
      const valid = await trigger([...CHARGES_FIELDS]);
      if (!valid) {
        const currentErrors = form.formState.errors;
        setValidationError(
          currentErrors.other_charge_reason?.message ?? "Please complete the required charge fields.",
        );
      }
      return valid;
    }
    return true;
  }, [step, trigger, form]);

  const goToStep = useCallback(
    (index: number) => {
      if (index <= maxReachableStep) {
        setStep(index);
      }
    },
    [maxReachableStep],
  );

  const goNext = async () => {
    setValidationError(null);
    setFocusWorkIndex(null);
    const valid = await validateCurrentStep();
    if (!valid) return;
    setStep((current) => {
      const next = Math.min(current + 1, EWORKS_STEPS.length - 1);
      setMaxReachableStep((max) => Math.max(max, next));
      return next;
    });
  };

  const goBack = () => setStep((current) => Math.max(current - 1, 0));

  const runCalculate = async () => {
    if (!session) return;
    setValidationError(null);
    setFocusWorkIndex(null);
    const valid = await trigger();
    if (!valid) {
      const currentErrors = form.formState.errors;
      const workIndex = firstInvalidWorkIndex(currentErrors);
      if (workIndex !== null) {
        setStep(1);
        setFocusWorkIndex(workIndex);
        setValidationError(
          questionnaireValidationMessage(currentErrors) ?? "Please complete all required questionnaire fields.",
        );
      } else {
        setValidationError(
          currentErrors.other_charge_reason?.message ?? "Please complete all required fields before calculating.",
        );
      }
      return;
    }
    setCalcError(null);
    try {
      const res = await calculateSession(
        session.session_id,
        session.session_token,
        questionnaireToStep2(values),
      );
      setResults(res);
      setMaxReachableStep(EWORKS_STEPS.length - 1);
      setStep(3);
    } catch (error) {
      setCalcError(error instanceof Error ? error.message : "Calculation failed");
    }
  };

  const copyNotes = useCallback(async () => {
    const notes = results?.internal_notes ?? results?.breakdown.internal_notes;
    if (!notes) return;
    await navigator.clipboard.writeText(notes);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  }, [results]);

  const handleDownloadPdf = useCallback(async () => {
    if (!session) return;
    setDownloadingPdf(true);
    setCalcError(null);
    try {
      await downloadSessionPdf(session.session_id, session.session_token);
    } catch (error) {
      setCalcError(error instanceof Error ? error.message : "PDF download failed");
    } finally {
      setDownloadingPdf(false);
    }
  }, [session]);

  const clientCalc = useMemo(() => {
    const calc = (results?.client_view?.calculation ?? {}) as Record<string, unknown>;
    return calc;
  }, [results]);

  if (loading) {
    return (
      <div className="min-h-screen bg-optimal-bg">
        <EworksLoadingScreen />
      </div>
    );
  }

  if (loadError || !session || !step1) {
    return (
      <div className="min-h-screen bg-optimal-bg px-4 py-8 sm:px-6">
        <div className="mx-auto max-w-lg animate-fade-in">
          <div className="rounded-lg border border-red-400/30 bg-red-500/10 p-6">
            <EworksSectionTitle title="Invalid calculation link" />
            <p className="mt-3 text-sm leading-relaxed text-red-200">{loadError ?? "This link could not be opened."}</p>
            {loadError?.includes("truncated") && (
              <p className="mt-2 text-sm leading-relaxed text-red-200">
                Copy the <strong>entire</strong> URL from the script output — do not use shortened links with{" "}
                <code className="rounded bg-red-500/20 px-1.5 py-0.5 text-xs">...</code>.
              </p>
            )}
            <div className="mt-4 space-y-2 text-sm leading-relaxed text-red-200/90">
              <p>
                The <code className="rounded bg-red-500/20 px-1.5 py-0.5 text-xs">payload</code> query parameter must be{" "}
                <strong>base64-encoded JSON</strong> with required fields.
              </p>
              <p>
                Generate a test link:{" "}
                <code className="rounded bg-red-500/20 px-1.5 py-0.5 text-xs">python3 scripts/generate_eworks_link.py</code>
              </p>
            </div>
            {isDev && (
              <EworksButton className="mt-5 w-full sm:w-auto" onClick={() => void startDevTestSession()}>
                Start local test session
              </EworksButton>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <EworksPageShell
      title="OPTIMAL ESTIMATE"
      subtitle={`Step ${step + 1} of ${EWORKS_STEPS.length}: ${EWORKS_STEPS[step]}`}
      meta={
        <>
          Job {step1.job_number} · Quote {step1.quote_number}
        </>
      }
      badge={
        session.resumed ? (
          <p className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-optimal-orange/15 px-3 py-1 text-xs font-medium text-optimal-orange">
            <span className="size-1.5 rounded-full bg-optimal-orange" />
            Previous progress restored
          </p>
        ) : undefined
      }
      saveStatus={step > 0 && step < 3 ? <EworksSaveStatus status={saveStatus} /> : undefined}
      stepIndicator={
        <EworksStepIndicator
          steps={EWORKS_STEPS}
          currentStep={step}
          maxReachableStep={maxReachableStep}
          onStepClick={goToStep}
        />
      }
      footer={
        <div className="space-y-3">
          {(validationError || calcError) && (
            <div className="rounded-lg border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm font-medium text-red-200 animate-fade-in">
              {validationError ?? calcError}
            </div>
          )}
          <div className="flex gap-3">
            <EworksButton variant="secondary" className="flex-1 sm:flex-none sm:min-w-[120px]" disabled={step === 0} onClick={goBack}>
              Back
            </EworksButton>
            {step < 2 && (
              <EworksButton className="flex-[2] sm:flex-1" onClick={() => void goNext()}>
                Continue
              </EworksButton>
            )}
            {step === 2 && (
              <EworksButton className="flex-[2] sm:flex-1" onClick={() => void runCalculate()}>
                Calculate
              </EworksButton>
            )}
          </div>
        </div>
      }
    >
      <EworksCard key={step}>
        {step === 0 && <EworksEstimationFormStep step1={step1} resolved={session.resolved} />}

        {step === 1 && (
          <EworksQuestionnaireStep
            control={control}
            register={register}
            watch={watch}
            setValue={setValue}
            errors={errors}
            tradeName={step1.trade_name}
            skillOptions={skillOptions}
            onUploadFiles={handleUploadFiles}
            uploading={uploading}
            focusWorkIndex={focusWorkIndex}
          />
        )}

        {step === 2 && (
          <div className="space-y-5">
            <p className="text-sm text-optimal-muted">Parking, congestion, and travel.</p>
            <div className="grid gap-4 sm:grid-cols-2">
            <EworksCheckbox label="Parking charge required" className="sm:col-span-2" {...register("parking_required")} />
            {values.parking_required && (
              <>
                <EworksLabel>
                  Parking type
                  <select className={eworksInputClass()} {...register("parking_type")}>
                    <option value="fixed">Fixed</option>
                    <option value="hourly">Hourly</option>
                  </select>
                </EworksLabel>
                {values.parking_type === "hourly" ? (
                  <>
                    <EworksLabel>
                      Rate per hour
                      <EworksInput type="number" {...register("parking_rate_per_hour", numberFieldOptions(0))} />
                    </EworksLabel>
                    <EworksLabel>
                      Hours
                      <EworksInput type="number" {...register("parking_hours", numberFieldOptions(0))} />
                    </EworksLabel>
                  </>
                ) : (
                  <EworksLabel>
                    Fixed amount
                    <EworksInput type="number" {...register("parking_fixed_amount", numberFieldOptions(0))} />
                  </EworksLabel>
                )}
              </>
            )}
            {!step1.congestion_required && (
              <EworksCheckbox
                label="Add congestion charge"
                className="sm:col-span-2"
                {...register("congestion_required", {
                  onChange: (event) => setValue("congestion_required", event.target.checked, { shouldValidate: true }),
                })}
              />
            )}
            {(values.congestion_required || step1.congestion_required) && (
              <EworksLabel>
                Congestion amount (£)
                <EworksInput type="number" {...register("congestion_amount", numberFieldOptions(0))} />
              </EworksLabel>
            )}
            <EworksLabel>
              Travel charge (£)
              <EworksInput type="number" {...register("travel_charge", numberFieldOptions(0))} />
            </EworksLabel>
            <EworksLabel>
              Other charge (£)
              <EworksInput type="number" {...register("other_charge", numberFieldOptions(0))} />
            </EworksLabel>
            <EworksLabel className="sm:col-span-2">
              Other charge reason
              <EworksInput hasError={!!errors.other_charge_reason} {...register("other_charge_reason")} />
              <EworksFieldError message={errors.other_charge_reason?.message} />
            </EworksLabel>
            </div>
          </div>
        )}

        {step === 3 && results && (
          <div className="space-y-6">
            <p className="text-sm text-optimal-muted">Combined estimate breakdown.</p>
            {results.work_breakdowns && results.work_breakdowns.length > 0 && (
              <section className="space-y-3">
                <EworksSectionTitle title="Per-work breakdown" />
                {results.work_breakdowns.map((work) => {
                  const labourTotal = work.breakdown.labour.reduce((sum, line) => sum + Number(line.total), 0);
                  const materialsTotal = work.breakdown.materials.reduce((sum, line) => sum + Number(line.total), 0);
                  return (
                    <details
                      key={work.work_index}
                      className="group overflow-hidden rounded-lg border border-white/10 bg-optimal-elevated open:shadow-lg open:shadow-black/20 transition-shadow duration-200"
                      open={work.work_index === 0}
                    >
                      <summary className="flex min-h-[44px] cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-semibold text-white marker:content-none">
                        <span>
                          Work {work.work_index + 1}
                          {work.scope ? `: ${work.scope.slice(0, 80)}${work.scope.length > 80 ? "…" : ""}` : ""}
                        </span>
                        <span className="text-optimal-muted transition-transform duration-200 group-open:rotate-180">▾</span>
                      </summary>
                      <div className="space-y-2 border-t border-white/10 px-4 py-3 text-sm text-white/90">
                        <p>Labour subtotal: <span className="font-semibold text-white">{money(labourTotal)}</span></p>
                        <p>Materials subtotal: <span className="font-semibold text-white">{money(materialsTotal)}</span></p>
                        {work.internal_notes && (
                          <pre className="whitespace-pre-wrap rounded-lg bg-optimal-field p-3 text-xs leading-relaxed text-optimal-field-text">
                            {work.internal_notes}
                          </pre>
                        )}
                      </div>
                    </details>
                  );
                })}
              </section>
            )}

            <section className="rounded-lg border border-optimal-orange/30 bg-optimal-elevated p-4 sm:p-5">
              <EworksSectionTitle title="Combined quote" />
              {results.aggregated_summary?.subtitle && (
                <p className="mt-2 text-sm text-optimal-muted">{results.aggregated_summary.subtitle}</p>
              )}
              <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                <p className="rounded-lg bg-optimal-field px-3 py-2 text-optimal-field-text">Labour charge: <span className="font-semibold">{money(results.breakdown.labour_charge_to_client)}</span></p>
                <p className="rounded-lg bg-optimal-field px-3 py-2 text-optimal-field-text">Materials / parking / CC: <span className="font-semibold">{money(results.breakdown.materials_parking_cc_charge)}</span></p>
                <p className="rounded-lg bg-optimal-field px-3 py-2 text-optimal-field-text">Profit: <span className="font-semibold">{money(results.breakdown.profit_gbp)}</span></p>
                <p className="rounded-lg bg-optimal-orange px-3 py-2.5 font-semibold text-optimal-bg sm:col-span-2">
                  Final total: <span className="text-lg font-bold">{money(results.breakdown.final_total)}</span>
                </p>
              </div>
              <div className="mt-4 space-y-1.5 text-sm text-optimal-muted">
                {results.breakdown.labour?.map((line) => (
                  <p key={line.label}>{line.label}: {money(line.total)}</p>
                ))}
                {results.breakdown.materials?.map((line) => (
                  <p key={line.label}>{line.label}: {money(line.total)}</p>
                ))}
                {results.breakdown.charges?.map((line) => (
                  <p key={line.label}>{line.label}: {money(line.total)}</p>
                ))}
              </div>
            </section>

            {(results.internal_notes || results.breakdown.internal_notes) && (
              <section className="rounded-lg border border-white/10 bg-optimal-elevated p-4">
                <div className="flex items-start justify-between gap-3">
                  <EworksSectionTitle title="Internal notes (combined)" />
                  <EworksButton variant="secondary" className="min-h-[36px] px-3 py-1.5 text-xs" onClick={() => void copyNotes()}>
                    {copied ? "Copied ✓" : "Copy notes"}
                  </EworksButton>
                </div>
                <pre className="mt-3 whitespace-pre-wrap rounded-lg bg-optimal-field p-3 text-xs leading-relaxed text-optimal-field-text">
                  {results.internal_notes ?? results.breakdown.internal_notes}
                </pre>
              </section>
            )}

            <section className="rounded-lg border border-white/10 bg-optimal-elevated p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <EworksSectionTitle title="Client-safe summary" />
                <EworksButton variant="secondary" className="min-h-[40px] text-xs" disabled={downloadingPdf} onClick={() => void handleDownloadPdf()}>
                  {downloadingPdf ? "Generating PDF…" : "Download PDF"}
                </EworksButton>
              </div>
              <p className="mt-3 text-sm leading-relaxed text-optimal-muted">
                Scope: {(results.client_view.scope as string) ?? values.works.map((work) => work.scope).join("\n\n")}
              </p>
              <div className="mt-4 grid gap-2 text-sm sm:grid-cols-2">
                <p className="text-white/90">Subtotal: <span className="font-semibold text-white">{money(clientCalc.subtotal as number | string)}</span></p>
                <p className="text-white/90">VAT: <span className="font-semibold text-white">{money(clientCalc.vat_total as number | string)}</span></p>
                <p className="font-bold text-optimal-orange sm:col-span-2">Final total: {money(clientCalc.final_total as number | string)}</p>
              </div>
              {"profit_gbp" in clientCalc && (
                <p className="mt-2 text-xs text-red-400">Unexpected profit field exposed in client view</p>
              )}
            </section>
          </div>
        )}
      </EworksCard>
    </EworksPageShell>
  );
}

export default function EworksCalculatePage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-optimal-bg">
          <EworksLoadingScreen />
        </div>
      }
    >
      <EworksCalculateContent />
    </Suspense>
  );
}
