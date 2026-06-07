"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useForm, type FieldErrors } from "react-hook-form";
import { questionnaireResolver } from "@/lib/eworks-questionnaire-resolver";
import { EworksInternalNavBar } from "@/components/eworks/eworks-internal-nav-bar";
import { EworksEstimationFormStep } from "@/components/eworks-estimation-form-step";
import { EworksQuestionnaireStep, type QuestionnaireStepActions } from "@/components/eworks-questionnaire-step";
import {
  EworksButton,
  EworksCard,
  EworksLoadingScreen,
  EworksPageShell,
  EworksSaveStatus,
  EworksSectionTitle,
  EworksStepIndicator,
  cn,
} from "@/components/eworks-ui";
import {
  createDevTestSession,
  createSessionFromLink,
  deleteSessionAttachment,
  EworksSessionError,
  fetchSession,
  patchFindingsReport,
  patchSession,
  storeSessionCredentials,
  submitSession,
  uploadSessionAttachment,
  type FromLinkResponse,
  type SessionUiState,
} from "@/lib/eworks-session";
import {
  coerceQuestionnaireValues,
  defaultQuestionnaireValues,
  EWORKS_STEPS,
  CHARGES_FIELDS,
  questionnaireToStep2,
  step2ToQuestionnaire,
  type QuestionnaireFormValues,
} from "@/lib/eworks-calculate-schema";
import { formatWorkLabel } from "@/lib/work-label";
import { fetchAllTrades } from "@/lib/trades";

type SaveStatus = "idle" | "saving" | "saved" | "error";

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
    ? path.includes("links")
      ? "Materials link"
      : "Materials supplier"
    : path.includes("shelf_materials_rows")
      ? "Shelf materials"
      : null;

  const labels: Record<string, string> = {
    scope: "Scope of works",
    skill_required: "Skill required",
    quantity: "quantity",
    cost: "cost per item",
    delivery_charge: "delivery charge",
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

function questionnaireValidationMessage(
  errors: FieldErrors<QuestionnaireFormValues>,
  works: QuestionnaireFormValues["works"],
): string | null {
  const workIndex = firstInvalidWorkIndex(errors);
  if (workIndex === null) return null;
  const workErrors = errors.works?.[workIndex];
  const message = firstErrorMessage(workErrors) ?? "complete all required fields";
  const label = formatWorkLabel(works[workIndex]);
  return `${label}: ${message}`;
}

function restoreUiState(
  uiState: SessionUiState | null | undefined,
  sessionMeta: Pick<FromLinkResponse, "revision_in_progress" | "locked" | "status"> | null | undefined,
  setters: {
    setStep: (value: number) => void;
    setMaxReachableStep: (value: number) => void;
    setSubmitted: (value: boolean) => void;
  },
) {
  if (sessionMeta?.revision_in_progress) {
    setters.setStep(Math.min(uiState?.current_step ?? 1, EWORKS_STEPS.length - 2));
    setters.setMaxReachableStep(Math.max(uiState?.max_reachable_step ?? 1, 1));
    setters.setSubmitted(false);
    return;
  }
  if (!uiState) return;
  const hasSubmitted =
    !!uiState.last_result || sessionMeta?.status === "submitted" || sessionMeta?.locked === true;
  const restoredStep = hasSubmitted ? EWORKS_STEPS.length - 1 : Math.min(uiState.current_step ?? 0, EWORKS_STEPS.length - 1);
  setters.setStep(restoredStep);
  setters.setMaxReachableStep(
    hasSubmitted ? EWORKS_STEPS.length - 1 : Math.min(uiState.max_reachable_step ?? uiState.current_step ?? 0, EWORKS_STEPS.length - 1),
  );
  setters.setSubmitted(hasSubmitted);
}

function loadErrorTitle(code: string | null | undefined) {
  switch (code) {
    case "EWORKS_CUSTOMER_NOT_FOUND":
      return "Customer not found in eWorks";
    case "EWORKS_API_UNAVAILABLE":
      return "eWorks is temporarily unavailable";
    default:
      return "Invalid calculation link";
  }
}

function loadErrorHint(code: string | null | undefined) {
  switch (code) {
    case "EWORKS_CUSTOMER_NOT_FOUND":
      return "The client on this link is not registered in eWorks. Check the customer name in the link payload matches eWorks exactly, or ask an administrator to add the customer.";
    case "EWORKS_API_UNAVAILABLE":
      return "We could not reach eWorks to verify the customer. Try again in a few minutes. If the problem continues, contact support.";
    default:
      return null;
  }
}

function EworksCalculateContent() {
  const searchParams = useSearchParams();
  const payload = searchParams.get("payload");
  const sig = searchParams.get("sig");
  const sessionIdParam = searchParams.get("session_id");
  const sessionTokenParam = searchParams.get("token");

  const [step, setStep] = useState(0);
  const [maxReachableStep, setMaxReachableStep] = useState(0);
  const [session, setSession] = useState<FromLinkResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loadErrorCode, setLoadErrorCode] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [calcError, setCalcError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [deletingAttachmentId, setDeletingAttachmentId] = useState<string | null>(null);
  const [skillOptions, setSkillOptions] = useState<string[]>([]);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [focusWorkIndex, setFocusWorkIndex] = useState<number | null>(null);
  const [findingsReportSaving, setFindingsReportSaving] = useState(false);
  const autoSaveReady = useRef(false);
  const autosaveInFlightRef = useRef<Promise<void> | null>(null);
  const autosaveInFlightKeyRef = useRef<string | null>(null);
  const lastSavedStep2Ref = useRef<string | null>(null);
  const lastSavedUiRef = useRef<string | null>(null);
  const questionnaireActionsRef = useRef<QuestionnaireStepActions | null>(null);
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
    getValues,
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
      const questionnaire = step2ToQuestionnaire(data.step2, data.step1.trade_name, undefined, data.step1);
      reset(questionnaire);
      restoreUiState(data.ui_state, data, { setStep, setMaxReachableStep, setSubmitted });
      autoSaveReady.current = false;
      lastSavedStep2Ref.current = null;
      lastSavedUiRef.current = null;
      window.setTimeout(() => {
        autoSaveReady.current = true;
      }, 500);
    },
    [reset],
  );

  const revisionInProgress = session?.revision_in_progress === true;
  const isLockedSubmitted = submitted && !revisionInProgress;

  const values = watch();

  useEffect(() => {
    let cancelled = false;
    async function bootstrap() {
      setLoading(true);
      setLoadError(null);
      setLoadErrorCode(null);
      try {
        if (sessionIdParam && sessionTokenParam) {
          const data = await fetchSession(sessionIdParam, sessionTokenParam);
          if (cancelled) return;
          applySession(data);
          return;
        }
        if (!payload) {
          setLoadError("Invalid or missing calculation link");
          return;
        }
        const res = await createSessionFromLink(payload, sig);
        if (cancelled) return;
        applySession(res.data);
      } catch (error) {
        if (cancelled) return;
        if (error instanceof EworksSessionError) {
          setLoadError(error.message);
          setLoadErrorCode(error.code ?? null);
        } else {
          const message = error instanceof Error ? error.message : "Failed to open calculation session";
          setLoadError(message);
          setLoadErrorCode(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    bootstrap();
    return () => {
      cancelled = true;
    };
  }, [sessionIdParam, sessionTokenParam, payload, sig, applySession]);

  const startDevTestSession = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    setLoadErrorCode(null);
    try {
      const res = await createDevTestSession();
      applySession(res.data);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to start local test session";
      setLoadError(message);
      setLoadErrorCode(error instanceof EworksSessionError ? error.code ?? null : null);
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
      if (!session || !autoSaveReady.current || step === 2 || submitting) return;
      const step2 = questionnaireToStep2(coerceQuestionnaireValues(formValues));
      const step2Key = JSON.stringify(step2);
      if (step2Key === lastSavedStep2Ref.current) return;
      if (autosaveInFlightKeyRef.current === step2Key && autosaveInFlightRef.current) {
        return autosaveInFlightRef.current;
      }
      setSaveStatus("saving");
      autosaveInFlightKeyRef.current = step2Key;
      const savePromise = (async () => {
        try {
          await patchSession(
            session.session_id,
            session.session_token,
            {
              step2,
              ui_state: {
                current_step: step,
                max_reachable_step: maxReachableStep,
              },
            },
            { idempotency: false },
          );
          lastSavedStep2Ref.current = step2Key;
          setSaveStatus("saved");
        } catch {
          setSaveStatus("error");
        } finally {
          autosaveInFlightRef.current = null;
          autosaveInFlightKeyRef.current = null;
        }
      })();
      autosaveInFlightRef.current = savePromise;
      await savePromise;
    },
    [session, step, maxReachableStep, submitting],
  );

  const saveProgress = useCallback(async () => {
    if (!session || !autoSaveReady.current || isLockedSubmitted || step === 2) return;
    const uiState = { current_step: step, max_reachable_step: maxReachableStep };
    const uiKey = JSON.stringify(uiState);
    if (uiKey === lastSavedUiRef.current) return;
    try {
      await patchSession(session.session_id, session.session_token, { ui_state: uiState }, { idempotency: false });
      lastSavedUiRef.current = uiKey;
    } catch {
      // ignore background progress save failures
    }
  }, [session, step, maxReachableStep, isLockedSubmitted]);

  useEffect(() => {
    if (!session || step === 2 || submitting) return;
    const timer = window.setTimeout(() => {
      void autosave(getValues());
    }, 800);
    return () => window.clearTimeout(timer);
  }, [values, session, step, autosave, submitting, getValues]);

  useEffect(() => {
    if (!session || !autoSaveReady.current) return;
    const timer = window.setTimeout(() => {
      void saveProgress();
    }, 400);
    return () => window.clearTimeout(timer);
  }, [session, step, maxReachableStep, saveProgress]);

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

  const handleDeleteAttachment = useCallback(
    async (workIndex: number, attachmentId: string) => {
      if (!session) return;
      setDeletingAttachmentId(attachmentId);
      setCalcError(null);
      try {
        await deleteSessionAttachment(session.session_id, session.session_token, attachmentId);
        const current = values.works[workIndex]?.attachments ?? [];
        setValue(
          `works.${workIndex}.attachments`,
          current.filter((item) => item.id !== attachmentId),
          { shouldValidate: true },
        );
      } catch (error) {
        setCalcError(error instanceof Error ? error.message : "Delete failed");
      } finally {
        setDeletingAttachmentId(null);
      }
    },
    [session, setValue, values.works],
  );

  const handleFindingsReportChange = useCallback(
    async (value: string) => {
      if (!session) return;
      setFindingsReportSaving(true);
      try {
        await patchFindingsReport(session.session_id, session.session_token, value);
        setSession((prev) =>
          prev
            ? { ...prev, step1: { ...prev.step1, findings_report: value } }
            : prev,
        );
      } catch {
        // non-critical — user can still continue
      } finally {
        setFindingsReportSaving(false);
      }
    },
    [session],
  );

  const validateCurrentStep = useCallback(async () => {
    if (step === 2) return true;
    if (step === 0) {
      const valid = await trigger([...CHARGES_FIELDS]);
      if (!valid) {
        setValidationError(
          firstErrorMessage(form.formState.errors) ?? "Please complete all required additional charge fields.",
        );
      }
      return valid;
    }
    if (step === 1) {
      const valid = await trigger(["works"]);
      if (!valid) {
        const currentErrors = form.formState.errors;
        setValidationError(
          questionnaireValidationMessage(currentErrors, getValues().works) ??
            "Please complete all required fields in the questionnaire.",
        );
        setFocusWorkIndex(firstInvalidWorkIndex(currentErrors));
      }
      return valid;
    }
    return true;
  }, [step, trigger, form, getValues]);

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
    if (step === 0) {
      await autosave(getValues());
    }
    setStep((current) => {
      const next = Math.min(current + 1, EWORKS_STEPS.length - 1);
      setMaxReachableStep((max) => Math.max(max, next));
      return next;
    });
  };

  const goBack = () => setStep((current) => Math.max(current - 1, 0));

  const runSubmit = async () => {
    if (!session) return;
    setValidationError(null);
    setFocusWorkIndex(null);
    const valid = await trigger();
    if (!valid) {
      const currentErrors = form.formState.errors;
      const workIndex = firstInvalidWorkIndex(currentErrors);
      setStep(1);
      setFocusWorkIndex(workIndex);
      setValidationError(
        questionnaireValidationMessage(currentErrors, getValues().works) ??
          "Please complete all required fields before submitting.",
      );
      return;
    }

    setCalcError(null);
    setSubmitting(true);
    autoSaveReady.current = false;
    try {
      if (autosaveInFlightRef.current) {
        await autosaveInFlightRef.current;
      }

      if (document.activeElement instanceof HTMLElement) {
        document.activeElement.blur();
      }
      await new Promise<void>((resolve) => {
        window.requestAnimationFrame(() => resolve());
      });

      const latestValues = getValues();
      const step2 = questionnaireToStep2(latestValues);

      await patchSession(session.session_id, session.session_token, {
        step2,
        ui_state: {
          current_step: step,
          max_reachable_step: maxReachableStep,
        },
      });
      lastSavedStep2Ref.current = JSON.stringify(step2);

      await submitSession(session.session_id, session.session_token, step2);
      setSubmitted(true);
      setMaxReachableStep(EWORKS_STEPS.length - 1);
      setStep(2);
    } catch (error) {
      autoSaveReady.current = true;
      setCalcError(error instanceof Error ? error.message : "Submit failed");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50">
        <EworksLoadingScreen />
      </div>
    );
  }

  if (loadError || !session || !step1) {
    return (
      <div className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6">
        <div className="mx-auto max-w-lg animate-fade-in">
          <div className="rounded-xl border border-red-300 bg-red-50 p-6 shadow-sm">
            <EworksSectionTitle title={loadErrorTitle(loadErrorCode)} />
            <p className="mt-3 text-sm leading-relaxed text-red-800">{loadError ?? "This link could not be opened."}</p>
            {loadErrorHint(loadErrorCode) && (
              <p className="mt-2 text-sm leading-relaxed text-red-800">{loadErrorHint(loadErrorCode)}</p>
            )}
            {loadError?.includes("truncated") && (
              <p className="mt-2 text-sm leading-relaxed text-red-800">
                Copy the <strong>entire</strong> URL from the script output — do not use shortened links with{" "}
                <code className="rounded bg-red-100 px-1.5 py-0.5 text-xs text-red-900">...</code>.
              </p>
            )}
            {!loadErrorCode && (
              <div className="mt-4 space-y-2 text-sm leading-relaxed text-red-700">
                <p>
                  The <code className="rounded bg-red-100 px-1.5 py-0.5 text-xs text-red-900">payload</code> query parameter must be{" "}
                  <strong>base64-encoded JSON</strong> with required fields.
                </p>
                <p>
                  Generate a test link:{" "}
                  <code className="rounded bg-red-100 px-1.5 py-0.5 text-xs text-red-900">python3 scripts/generate_eworks_link.py</code>
                </p>
              </div>
            )}
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
        revisionInProgress ? (
          <p
            className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900"
            data-testid="revision-in-progress-banner"
          >
            Revision in progress — Reason: {session.active_revision_reason ?? "Not specified"}
          </p>
        ) : session.resumed ? (
          <p className="mt-2 inline-flex items-center gap-1.5 rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700">
            <span className="size-1.5 rounded-full bg-blue-600" />
            Previous progress restored
          </p>
        ) : undefined
      }
      saveStatus={undefined}
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
            <div className="rounded-xl border border-red-300 bg-red-50 px-4 py-3 text-sm font-medium text-red-800 shadow-sm animate-fade-in">
              {validationError ?? calcError}
            </div>
          )}
          {step === 0 || step === 1 ? (
            <div className={cn("flex items-center justify-between gap-3", step === 1 && "border-b border-slate-100 pb-3")}>
              {step === 1 ? (
                <EworksButton
                  variant="secondary"
                  className="min-h-[44px] flex-1 sm:flex-none"
                  onClick={() => questionnaireActionsRef.current?.addWork()}
                  data-testid="add-work-button"
                >
                  + Add Work
                </EworksButton>
              ) : (
                <span />
              )}
              <EworksSaveStatus status={saveStatus} />
            </div>
          ) : null}
          <div className="flex gap-3">
            <EworksButton variant="secondary" className="flex-1 sm:flex-none sm:min-w-[120px]" disabled={step === 0} onClick={goBack}>
              {step === 1 ? "Previous" : "Back"}
            </EworksButton>
            {step < 1 && (
              <EworksButton className="flex-[2] sm:flex-1" onClick={() => void goNext()}>
                Continue
              </EworksButton>
            )}
            {step === 1 && (
              <EworksButton className="flex-[2] sm:flex-1" disabled={submitting} onClick={() => void runSubmit()}>
                {submitting ? "Submitting…" : revisionInProgress ? "Submit Revised Estimate" : "Submit"}
              </EworksButton>
            )}
          </div>
        </div>
      }
    >
      <EworksCard key={step}>
        {step === 0 && (
          <EworksEstimationFormStep
            step1={step1}
            resolved={session.resolved}
            control={control}
            register={register}
            watch={watch}
            setValue={setValue}
            errors={errors}
            onFindingsReportChange={handleFindingsReportChange}
            findingsReportSaving={findingsReportSaving}
            submitted={isLockedSubmitted}
          />
        )}

        {step === 1 && (
          <EworksQuestionnaireStep
            control={control}
            register={register}
            watch={watch}
            setValue={setValue}
            errors={errors}
            tradeName={step1.trade_name}
            skillOptions={skillOptions}
            sessionId={session.session_id}
            sessionToken={session.session_token}
            onUploadFiles={handleUploadFiles}
            onDeleteAttachment={handleDeleteAttachment}
            uploading={uploading}
            deletingAttachmentId={deletingAttachmentId}
            focusWorkIndex={focusWorkIndex}
            onActionsReady={(actions) => {
              questionnaireActionsRef.current = actions;
            }}
          />
        )}

        {step === 2 && isLockedSubmitted && (
          <div className="space-y-4 rounded-lg border border-emerald-300 bg-emerald-50 p-6 text-center">
            <div className="mx-auto flex size-14 items-center justify-center rounded-full bg-emerald-100 text-2xl text-emerald-700">
              ✓
            </div>
            <div className="space-y-2">
              <EworksSectionTitle title="Quote submitted" />
              <p className="text-sm text-emerald-800">Estimate submitted.</p>
            </div>
          </div>
        )}
      </EworksCard>
    </EworksPageShell>
  );
}

export default function EworksCalculatePage() {
  return (
    <>
      <EworksInternalNavBar />
      <Suspense
        fallback={
          <div className="min-h-screen bg-slate-50">
            <EworksLoadingScreen />
          </div>
        }
      >
        <EworksCalculateContent />
      </Suspense>
    </>
  );
}
