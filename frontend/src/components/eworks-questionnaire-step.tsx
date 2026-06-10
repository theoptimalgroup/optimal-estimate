"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useFieldArray } from "react-hook-form";
import type { Control, FieldErrors, UseFormRegister, UseFormSetValue, UseFormWatch } from "react-hook-form";
import { EworksWorkBlockForm } from "@/components/eworks-work-block-form";
import { ScopeReplaceDialog } from "@/components/scope-replace-dialog";
import { WorkModeSwitchDialog } from "@/components/work-mode-switch-dialog";
import { shouldConfirmSwitchToCustom, shouldConfirmSwitchToProduct } from "@/lib/custom-scope";
import { EworksButton, cn } from "@/components/eworks-ui";
import {
  computeProductTotalPrice,
  defaultWorkBlockValues,
  type ProductOption,
  type QuestionnaireFormValues,
} from "@/lib/eworks-calculate-schema";
import type { SharedStep2Meta } from "@/lib/eworks-session";
import { stripHtmlFromLabel } from "@/lib/html-text";
import { canAutoFillScope, productScopeText, shouldPromptScopeReplace } from "@/lib/product-scope";
import { formatWorkCardTitle } from "@/lib/work-label";

export type QuestionnaireStepActions = {
  addWork: () => void;
};

type Props = {
  control: Control<QuestionnaireFormValues>;
  register: UseFormRegister<QuestionnaireFormValues>;
  watch: UseFormWatch<QuestionnaireFormValues>;
  setValue: UseFormSetValue<QuestionnaireFormValues>;
  errors: FieldErrors<QuestionnaireFormValues>;
  tradeName: string;
  skillOptions: string[];
  sessionId: string;
  sessionToken: string;
  onUploadFiles: (files: FileList | null, workIndex: number) => Promise<void>;
  onDeleteAttachment: (workIndex: number, attachmentId: string) => Promise<void>;
  uploading: boolean;
  deletingAttachmentId: string | null;
  focusWorkIndex?: number | null;
  onActionsReady?: (actions: QuestionnaireStepActions) => void;
  sharedStep2?: SharedStep2Meta | null;
};

type PendingScopeReplace = {
  workIndex: number;
  product: ProductOption;
};

type PendingModeSwitch = {
  workIndex: number;
  mode: "to-custom" | "to-product";
  product?: ProductOption;
};

export function EworksQuestionnaireStep({
  control,
  register,
  watch,
  setValue,
  errors,
  tradeName,
  skillOptions,
  sessionId,
  sessionToken,
  onUploadFiles,
  onDeleteAttachment,
  uploading,
  deletingAttachmentId,
  focusWorkIndex,
  onActionsReady,
  sharedStep2,
}: Props) {
  const { fields, append, remove } = useFieldArray({ name: "works", control });
  const values = watch();
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);
  const [changingProductIndex, setChangingProductIndex] = useState<number | null>(null);
  const workRefs = useRef<(HTMLDivElement | null)[]>([]);
  const scrollToNewRef = useRef<number | null>(null);
  const [scopeReplacePrompt, setScopeReplacePrompt] = useState<PendingScopeReplace | null>(null);
  const [modeSwitchPrompt, setModeSwitchPrompt] = useState<PendingModeSwitch | null>(null);
  const [customScopeDraftIndex, setCustomScopeDraftIndex] = useState<number | null>(null);

  useEffect(() => {
    if (focusWorkIndex !== null && focusWorkIndex !== undefined && focusWorkIndex >= 0) {
      setExpandedIndex(focusWorkIndex);
    }
  }, [focusWorkIndex]);

  useEffect(() => {
    if (scrollToNewRef.current === null) return;
    const targetIndex = scrollToNewRef.current;
    scrollToNewRef.current = null;
    const timer = window.setTimeout(() => {
      workRefs.current[targetIndex]?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 320);
    return () => window.clearTimeout(timer);
  }, [fields.length]);

  const applyProductSelection = useCallback(
    (workIndex: number, product: ProductOption, replaceScope: boolean) => {
      const work = values.works[workIndex];
      const base = `works.${workIndex}` as const;
      const unitPrice = Number(product.selling_price ?? 0);
      const quantity = work.product_quantity ?? 1;
      const newScope = productScopeText(product);

      setValue(`${base}.is_custom_scope`, false, { shouldValidate: true });
      setValue(`${base}.custom_title`, "", { shouldValidate: true });
      setValue(`${base}.selected_product_id`, product.id, { shouldValidate: true });
      setValue(`${base}.eworks_item_id`, product.eworks_item_id, { shouldValidate: true });
      setValue(`${base}.product_name`, stripHtmlFromLabel(product.product_name), { shouldValidate: true });
      setValue(`${base}.product_code`, product.product_code ?? "", { shouldValidate: true });
      setValue(`${base}.product_unit_price`, unitPrice, { shouldValidate: true });
      setValue(`${base}.product_total_price`, computeProductTotalPrice(quantity, unitPrice), { shouldValidate: true });

      if (replaceScope) {
        setValue(`${base}.scope`, newScope, { shouldValidate: true });
        setValue(`${base}.scope_from_product`, true, { shouldValidate: true });
      }
    },
    [setValue, values.works],
  );

  const clearProductSelection = useCallback(
    (workIndex: number) => {
      const base = `works.${workIndex}` as const;
      setValue(`${base}.is_custom_scope`, false, { shouldValidate: true });
      setValue(`${base}.custom_title`, "", { shouldValidate: true });
      setValue(`${base}.selected_product_id`, null, { shouldValidate: true });
      setValue(`${base}.eworks_item_id`, null, { shouldValidate: true });
      setValue(`${base}.product_name`, "", { shouldValidate: true });
      setValue(`${base}.product_code`, "", { shouldValidate: true });
      setValue(`${base}.product_unit_price`, 0, { shouldValidate: true });
      setValue(`${base}.product_total_price`, 0, { shouldValidate: true });
      setValue(`${base}.scope_from_product`, false, { shouldValidate: true });
    },
    [setValue],
  );

  const beginCustomScopeDraft = useCallback(
    (workIndex: number) => {
      const base = `works.${workIndex}` as const;
      setValue(`${base}.is_custom_scope`, false, { shouldValidate: true });
      setValue(`${base}.custom_title`, "", { shouldValidate: true });
      setValue(`${base}.selected_product_id`, null, { shouldValidate: true });
      setValue(`${base}.eworks_item_id`, null, { shouldValidate: true });
      setValue(`${base}.product_name`, "", { shouldValidate: true });
      setValue(`${base}.product_code`, "", { shouldValidate: true });
      setValue(`${base}.product_unit_price`, 0, { shouldValidate: true });
      setValue(`${base}.product_total_price`, 0, { shouldValidate: true });
      setValue(`${base}.scope_from_product`, false, { shouldValidate: true });
      setChangingProductIndex(null);
      setCustomScopeDraftIndex(workIndex);
    },
    [setValue],
  );

  const confirmCustomScope = useCallback(
    (workIndex: number, title: string, description?: string) => {
      const trimmedTitle = title.trim();
      if (!trimmedTitle) return;
      const base = `works.${workIndex}` as const;
      setValue(`${base}.is_custom_scope`, true, { shouldValidate: true });
      setValue(`${base}.custom_title`, trimmedTitle, { shouldValidate: true });
      setValue(`${base}.product_name`, trimmedTitle, { shouldValidate: true });
      setValue(`${base}.selected_product_id`, null, { shouldValidate: true });
      setValue(`${base}.eworks_item_id`, null, { shouldValidate: true });
      setValue(`${base}.product_code`, "", { shouldValidate: true });
      setValue(`${base}.product_unit_price`, 0, { shouldValidate: true });
      setValue(`${base}.product_total_price`, 0, { shouldValidate: true });
      setValue(`${base}.product_quantity`, 1, { shouldValidate: true });
      setValue(`${base}.scope_from_product`, false, { shouldValidate: true });
      const trimmedDescription = description?.trim();
      if (trimmedDescription) {
        setValue(`${base}.scope`, trimmedDescription, { shouldValidate: true });
      }
      setCustomScopeDraftIndex(null);
      setChangingProductIndex(null);
    },
    [setValue],
  );

  const cancelCustomScopeDraft = useCallback(
    (workIndex: number) => {
      setCustomScopeDraftIndex(null);
      const work = values.works[workIndex];
      if (!work?.is_custom_scope) {
        clearProductSelection(workIndex);
      }
    },
    [clearProductSelection, values.works],
  );

  const handleProductSelect = useCallback(
    (workIndex: number, product: ProductOption | null) => {
      if (customScopeDraftIndex === workIndex) {
        setCustomScopeDraftIndex(null);
      }
      if (!product) {
        clearProductSelection(workIndex);
        return;
      }

      const work = values.works[workIndex];
      if (work.is_custom_scope && shouldConfirmSwitchToProduct(work)) {
        setModeSwitchPrompt({ workIndex, mode: "to-product", product });
        return;
      }

      const newScope = productScopeText(product);

      if (canAutoFillScope(work)) {
        applyProductSelection(workIndex, product, true);
        setChangingProductIndex(null);
        return;
      }

      if (shouldPromptScopeReplace(work, newScope)) {
        setScopeReplacePrompt({ workIndex, product });
        return;
      }

      applyProductSelection(workIndex, product, false);
      setChangingProductIndex(null);
    },
    [applyProductSelection, clearProductSelection, customScopeDraftIndex, values.works],
  );

  const handleAddCustomScope = useCallback(
    (workIndex: number) => {
      const work = values.works[workIndex];
      if (shouldConfirmSwitchToCustom(work)) {
        setModeSwitchPrompt({ workIndex, mode: "to-custom" });
        return;
      }
      beginCustomScopeDraft(workIndex);
    },
    [beginCustomScopeDraft, values.works],
  );

  const handleChangeProductClick = useCallback(
    (workIndex: number) => {
      const work = values.works[workIndex];
      if (work.is_custom_scope && shouldConfirmSwitchToProduct(work)) {
        setModeSwitchPrompt({ workIndex, mode: "to-product" });
        return;
      }
      setChangingProductIndex(workIndex);
    },
    [values.works],
  );

  const handleAddWork = useCallback(() => {
    const newIndex = fields.length;
    scrollToNewRef.current = newIndex;
    append(defaultWorkBlockValues(tradeName));
    setExpandedIndex(newIndex);
    setChangingProductIndex(null);
  }, [append, fields.length, tradeName]);

  useEffect(() => {
    onActionsReady?.({ addWork: handleAddWork });
  }, [handleAddWork, onActionsReady]);

  const handleRemoveWork = (index: number) => {
    remove(index);
    setExpandedIndex((current) => {
      if (current === index) return null;
      if (current !== null && current > index) return current - 1;
      return current;
    });
    setChangingProductIndex((current) => {
      if (current === index) return null;
      if (current !== null && current > index) return current - 1;
      return current;
    });
  };

  return (
    <div className="space-y-3">
      {sharedStep2?.updated_by_name || sharedStep2?.updated_at ? (
        <div
          className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900"
          data-testid="shared-quote-work-plan"
        >
          <p className="font-semibold">Shared quote work plan</p>
          {sharedStep2.updated_by_name || sharedStep2.updated_at ? (
            <p className="mt-1 text-xs text-blue-800">
              Last updated by {sharedStep2.updated_by_name ?? "a colleague"}
              {sharedStep2.updated_at
                ? ` · ${new Date(sharedStep2.updated_at).toLocaleString("en-GB", {
                    day: "numeric",
                    month: "short",
                    year: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}`
                : ""}
            </p>
          ) : null}
        </div>
      ) : null}
      <WorkModeSwitchDialog
        open={modeSwitchPrompt !== null}
        title={
          modeSwitchPrompt?.mode === "to-custom" ? "Switch to custom scope?" : "Replace custom scope with product?"
        }
        message={
          modeSwitchPrompt?.mode === "to-custom"
            ? "Switching to a custom scope will clear the selected product. Existing scope, materials, and labour may need to be updated."
            : "Selecting a product will replace your custom scope text. Continue?"
        }
        confirmLabel={modeSwitchPrompt?.mode === "to-custom" ? "Use custom scope" : "Select product"}
        onCancel={() => setModeSwitchPrompt(null)}
        onConfirm={() => {
          if (!modeSwitchPrompt) return;
          if (modeSwitchPrompt.mode === "to-custom") {
            beginCustomScopeDraft(modeSwitchPrompt.workIndex);
          } else {
            setChangingProductIndex(modeSwitchPrompt.workIndex);
            if (modeSwitchPrompt.product) {
              const work = values.works[modeSwitchPrompt.workIndex];
              const newScope = productScopeText(modeSwitchPrompt.product);
              if (canAutoFillScope(work)) {
                applyProductSelection(modeSwitchPrompt.workIndex, modeSwitchPrompt.product, true);
                setChangingProductIndex(null);
              } else if (shouldPromptScopeReplace(work, newScope)) {
                setScopeReplacePrompt({
                  workIndex: modeSwitchPrompt.workIndex,
                  product: modeSwitchPrompt.product,
                });
              } else {
                applyProductSelection(modeSwitchPrompt.workIndex, modeSwitchPrompt.product, false);
                setChangingProductIndex(null);
              }
            }
          }
          setModeSwitchPrompt(null);
        }}
      />

      <ScopeReplaceDialog
        open={scopeReplacePrompt !== null}
        onKeep={() => {
          if (scopeReplacePrompt) {
            applyProductSelection(scopeReplacePrompt.workIndex, scopeReplacePrompt.product, false);
            setChangingProductIndex(null);
          }
          setScopeReplacePrompt(null);
        }}
        onReplace={() => {
          if (scopeReplacePrompt) {
            applyProductSelection(scopeReplacePrompt.workIndex, scopeReplacePrompt.product, true);
            setChangingProductIndex(null);
          }
          setScopeReplacePrompt(null);
        }}
      />

      {fields.map((field, index) => {
        const isExpanded = expandedIndex === index;
        const work = values.works[index];
        const headerTitle = formatWorkCardTitle(work);
        const hasErrors = !!errors.works?.[index];

        return (
          <div
            key={field.id}
            ref={(el) => {
              workRefs.current[index] = el;
            }}
            className={cn(
              "rounded-xl border border-slate-200 bg-white shadow-sm transition-all duration-300 ease-out",
              isExpanded ? "overflow-visible ring-1 ring-blue-100" : "overflow-hidden",
              hasErrors && !isExpanded && "border-red-300 ring-1 ring-red-100",
            )}
            data-testid={`work-block-${index}`}
          >
            <div className="flex items-center gap-3 p-4">
              <button
                type="button"
                className="flex min-w-0 flex-1 items-center gap-3 text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/30"
                onClick={() => setExpandedIndex(isExpanded ? null : index)}
                aria-expanded={isExpanded}
                aria-label={isExpanded ? `Collapse ${headerTitle}` : `Expand ${headerTitle}`}
                data-testid={`work-block-toggle-${index}`}
              >
                <span
                  className={cn(
                    "flex size-8 shrink-0 items-center justify-center rounded-full text-xs font-bold",
                    isExpanded ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-700",
                  )}
                  aria-hidden
                >
                  {index + 1}
                </span>
                <p className="min-w-0 flex-1 truncate text-sm font-semibold text-slate-900">{headerTitle}</p>
              </button>
              <div className="flex shrink-0 items-center gap-2">
                {hasErrors ? (
                  <span
                    className="inline-flex items-center rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-800"
                    data-testid={`work-required-badge-${index}`}
                  >
                    Required
                  </span>
                ) : null}
                <span
                  className={cn(
                    "flex size-8 items-center justify-center text-slate-500 transition-transform duration-200",
                    isExpanded && "rotate-180",
                  )}
                  aria-hidden
                >
                  ▾
                </span>
                {index > 0 ? (
                  <EworksButton
                    variant="danger"
                    className="min-h-[36px] px-3 py-1.5 text-xs"
                    onClick={() => handleRemoveWork(index)}
                  >
                    Remove
                  </EworksButton>
                ) : null}
              </div>
            </div>

            <div
              className={cn(
                "grid transition-all duration-300 ease-out",
                isExpanded ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0",
              )}
            >
              <div className="min-h-0 min-w-0">
                <div className="border-t border-slate-200 px-4 pb-4 pt-3">
                  <EworksWorkBlockForm
                    workIndex={index}
                    control={control}
                    register={register}
                    watch={watch}
                    setValue={setValue}
                    errors={errors}
                    attachments={values.works[index]?.attachments ?? []}
                    skillOptions={skillOptions}
                    sessionId={sessionId}
                    sessionToken={sessionToken}
                    onUploadFiles={onUploadFiles}
                    onDeleteAttachment={onDeleteAttachment}
                    uploading={uploading}
                    deletingAttachmentId={deletingAttachmentId}
                    onProductSelect={(product) => handleProductSelect(index, product)}
                    onAddCustomScope={() => handleAddCustomScope(index)}
                    customScopeDraft={customScopeDraftIndex === index}
                    onConfirmCustomScope={(title, description) => confirmCustomScope(index, title, description)}
                    onCancelCustomScopeDraft={() => cancelCustomScopeDraft(index)}
                    changingProduct={changingProductIndex === index}
                    onChangeProductClick={() => handleChangeProductClick(index)}
                  />
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
