"use client";

import { useEffect, useRef, useState } from "react";
import { useFieldArray } from "react-hook-form";
import type { Control, FieldErrors, UseFormRegister, UseFormSetValue, UseFormWatch } from "react-hook-form";
import { EworksWorkBlockForm } from "@/components/eworks-work-block-form";
import { ProductCombobox } from "@/components/product-combobox";
import { ScopeReplaceDialog } from "@/components/scope-replace-dialog";
import { EworksButton, cn } from "@/components/eworks-ui";
import {
  computeProductTotalPrice,
  defaultWorkBlockValues,
  formatProductLabel,
  type ProductOption,
  type QuestionnaireFormValues,
} from "@/lib/eworks-calculate-schema";
import { canAutoFillScope, productScopeText, shouldPromptScopeReplace } from "@/lib/product-scope";

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
};

type PendingScopeReplace = {
  workIndex: number;
  product: ProductOption;
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
}: Props) {
  const { fields, append, remove } = useFieldArray({ name: "works", control });
  const values = watch();
  const [expandedIndex, setExpandedIndex] = useState(0);
  const workRefs = useRef<(HTMLDivElement | null)[]>([]);
  const scrollToNewRef = useRef<number | null>(null);
  const [scopeReplacePrompt, setScopeReplacePrompt] = useState<PendingScopeReplace | null>(null);
  const [productScopeCache, setProductScopeCache] = useState<Record<number, string>>({});

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

  const applyProductSelection = (
    workIndex: number,
    product: ProductOption,
    replaceScope: boolean,
  ) => {
    const work = values.works[workIndex];
    const base = `works.${workIndex}` as const;
    const unitPrice = Number(product.selling_price ?? 0);
    const quantity = work.product_quantity ?? 1;
    const newScope = productScopeText(product);

    setProductScopeCache((current) => ({
      ...current,
      [product.id]: newScope,
    }));

    setValue(`${base}.selected_product_id`, product.id, { shouldValidate: true });
    setValue(`${base}.eworks_item_id`, product.eworks_item_id, { shouldValidate: true });
    setValue(`${base}.product_name`, product.product_name, { shouldValidate: true });
    setValue(`${base}.product_code`, product.product_code ?? "", { shouldValidate: true });
    setValue(`${base}.product_unit_price`, unitPrice, { shouldValidate: true });
    setValue(`${base}.product_total_price`, computeProductTotalPrice(quantity, unitPrice), { shouldValidate: true });

    if (replaceScope) {
      setValue(`${base}.scope`, newScope, { shouldValidate: true });
      setValue(`${base}.scope_from_product`, true, { shouldValidate: true });
    }
  };

  const clearProductSelection = (workIndex: number) => {
    const base = `works.${workIndex}` as const;
    setValue(`${base}.selected_product_id`, null, { shouldValidate: true });
    setValue(`${base}.eworks_item_id`, null, { shouldValidate: true });
    setValue(`${base}.product_name`, "", { shouldValidate: true });
    setValue(`${base}.product_code`, "", { shouldValidate: true });
    setValue(`${base}.product_unit_price`, 0, { shouldValidate: true });
    setValue(`${base}.product_total_price`, 0, { shouldValidate: true });
    setValue(`${base}.scope_from_product`, false, { shouldValidate: true });
  };

  const handleProductSelect = (workIndex: number, product: ProductOption | null) => {
    if (!product) {
      clearProductSelection(workIndex);
      return;
    }

    const work = values.works[workIndex];
    const newScope = productScopeText(product);

    if (canAutoFillScope(work)) {
      applyProductSelection(workIndex, product, true);
      return;
    }

    if (shouldPromptScopeReplace(work, newScope)) {
      setScopeReplacePrompt({ workIndex, product });
      return;
    }

    applyProductSelection(workIndex, product, false);
  };

  const handleAddWork = () => {
    const newIndex = fields.length;
    scrollToNewRef.current = newIndex;
    append(defaultWorkBlockValues(tradeName));
    setExpandedIndex(newIndex);
  };

  const handleRemoveWork = (index: number) => {
    remove(index);
    setExpandedIndex((current) => {
      if (current === index) return Math.max(0, index - 1);
      if (current > index) return current - 1;
      return current;
    });
  };

  return (
    <div className="space-y-5">
      <p className="text-sm text-optimal-muted">
        Complete each work block below. Select a product to auto-fill scope, then review and edit before submitting.
      </p>

      <ScopeReplaceDialog
        open={scopeReplacePrompt !== null}
        onKeep={() => {
          if (scopeReplacePrompt) {
            applyProductSelection(scopeReplacePrompt.workIndex, scopeReplacePrompt.product, false);
          }
          setScopeReplacePrompt(null);
        }}
        onReplace={() => {
          if (scopeReplacePrompt) {
            applyProductSelection(scopeReplacePrompt.workIndex, scopeReplacePrompt.product, true);
          }
          setScopeReplacePrompt(null);
        }}
      />

      <div className="space-y-4">
        {fields.map((field, index) => {
          const isExpanded = expandedIndex === index;
          const work = values.works[index];
          const scopePreview = work?.scope?.trim();
          const productPreview =
            work?.selected_product_id != null && work?.product_name
              ? formatProductLabel({ product_name: work.product_name, product_code: work.product_code ?? null })
              : null;
          const hasErrors = !!errors.works?.[index];
          const cachedProductScope =
            work?.selected_product_id != null ? productScopeCache[work.selected_product_id] : undefined;

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
                <span
                  className={cn(
                    "flex size-8 shrink-0 items-center justify-center rounded-full text-xs font-bold transition-all duration-200",
                    isExpanded ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-700",
                  )}
                  aria-label={`Work ${index + 1}`}
                >
                  {index + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Work {index + 1}
                    {productPreview ? ` · ${productPreview}` : scopePreview ? " · Scope entered" : ""}
                  </p>
                  <div
                    className="mt-1"
                    onMouseDown={(e) => e.stopPropagation()}
                    onClick={(e) => e.stopPropagation()}
                  >
                    <ProductCombobox
                      selectedProductId={work?.selected_product_id}
                      productName={work?.product_name}
                      productCode={work?.product_code}
                      onSelect={(product) => handleProductSelect(index, product)}
                    />
                  </div>
                  {!isExpanded && scopePreview && (
                    <span className="mt-1 block truncate text-xs text-optimal-muted">
                      {scopePreview.slice(0, 72)}
                      {scopePreview.length > 72 ? "…" : ""}
                    </span>
                  )}
                </div>
                <button
                  type="button"
                  className="flex min-h-[44px] shrink-0 items-center rounded-lg px-2 py-2 text-optimal-muted transition-colors hover:bg-gray-50"
                  onClick={() => setExpandedIndex(isExpanded ? -1 : index)}
                  aria-expanded={isExpanded}
                  aria-label={isExpanded ? `Collapse work ${index + 1}` : `Expand work ${index + 1}`}
                >
                  <span className={cn("transition-transform duration-200", isExpanded && "rotate-180")}>▾</span>
                </button>
                {index > 0 && (
                  <EworksButton variant="danger" className="min-h-[40px] px-3 py-2 text-xs" onClick={() => handleRemoveWork(index)}>
                    Remove
                  </EworksButton>
                )}
              </div>
              <div
                className={cn(
                  "grid transition-all duration-300 ease-out",
                  isExpanded ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0",
                )}
              >
                <div className="min-h-0 min-w-0">
                  <div className="border-t border-slate-200 px-5 pb-5 pt-4">
                    <EworksWorkBlockForm
                      workIndex={index}
                      workNumber={index + 1}
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
                      cachedProductScope={cachedProductScope}
                    />
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <EworksButton variant="secondary" className="w-full sm:w-auto" onClick={handleAddWork}>
        + Add more works
      </EworksButton>
    </div>
  );
}
