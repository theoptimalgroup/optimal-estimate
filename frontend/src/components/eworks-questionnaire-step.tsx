"use client";

import { useEffect, useState } from "react";
import { useFieldArray } from "react-hook-form";
import type { Control, FieldErrors, UseFormRegister, UseFormSetValue, UseFormWatch } from "react-hook-form";
import { EworksWorkBlockForm } from "@/components/eworks-work-block-form";
import { EworksButton, cn } from "@/components/eworks-ui";
import { defaultWorkBlockValues, type QuestionnaireFormValues } from "@/lib/eworks-calculate-schema";

type Props = {
  control: Control<QuestionnaireFormValues>;
  register: UseFormRegister<QuestionnaireFormValues>;
  watch: UseFormWatch<QuestionnaireFormValues>;
  setValue: UseFormSetValue<QuestionnaireFormValues>;
  errors: FieldErrors<QuestionnaireFormValues>;
  tradeName: string;
  skillOptions: string[];
  onUploadFiles: (files: FileList | null, workIndex: number) => Promise<void>;
  uploading: boolean;
  focusWorkIndex?: number | null;
};

export function EworksQuestionnaireStep({
  control,
  register,
  watch,
  setValue,
  errors,
  tradeName,
  skillOptions,
  onUploadFiles,
  uploading,
  focusWorkIndex,
}: Props) {
  const { fields, append, remove } = useFieldArray({ name: "works", control });
  const values = watch();
  const [expandedIndex, setExpandedIndex] = useState(0);

  useEffect(() => {
    if (focusWorkIndex !== null && focusWorkIndex !== undefined && focusWorkIndex >= 0) {
      setExpandedIndex(focusWorkIndex);
    }
  }, [focusWorkIndex]);

  const handleAddWork = () => {
    const newIndex = fields.length;
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
      <p className="text-sm text-optimal-muted">Complete each work block below.</p>

      <div className="space-y-3">
        {fields.map((field, index) => {
          const isExpanded = expandedIndex === index;
          const scopePreview = values.works[index]?.scope?.trim();
          const hasErrors = !!errors.works?.[index];

          return (
            <div
              key={field.id}
              className={cn(
                "overflow-hidden rounded-lg border transition-all duration-300 ease-out",
                isExpanded ? "border-optimal-orange/40 bg-optimal-elevated shadow-lg shadow-black/20" : "border-white/10 bg-optimal-elevated/70",
                hasErrors && !isExpanded && "border-red-400/40 ring-1 ring-red-400/20",
              )}
            >
              <div className="flex items-center gap-2 p-2 pl-3">
                <button
                  type="button"
                  className="flex min-h-[44px] min-w-0 flex-1 items-center gap-3 rounded-lg px-2 py-2 text-left transition-colors duration-200 hover:bg-white/5 active:bg-white/10"
                  onClick={() => setExpandedIndex(isExpanded ? -1 : index)}
                  aria-expanded={isExpanded}
                >
                  <span
                    className={cn(
                      "flex size-8 shrink-0 items-center justify-center rounded-full text-xs font-bold transition-all duration-200",
                      isExpanded ? "bg-optimal-orange text-optimal-bg" : "bg-white/10 text-white",
                    )}
                  >
                    {index + 1}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-semibold text-white">Work {index + 1}</span>
                    {!isExpanded && scopePreview && (
                      <span className="block truncate text-xs text-optimal-muted">
                        {scopePreview.slice(0, 72)}
                        {scopePreview.length > 72 ? "…" : ""}
                      </span>
                    )}
                  </span>
                  <span className={cn("shrink-0 text-optimal-muted transition-transform duration-200", isExpanded && "rotate-180")}>
                    ▾
                  </span>
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
                <div className="overflow-hidden">
                  <div className="border-t border-white/10 px-4 pb-4 pt-2">
                    <EworksWorkBlockForm
                      workIndex={index}
                      control={control}
                      register={register}
                      watch={watch}
                      setValue={setValue}
                      errors={errors}
                      attachments={values.works[index]?.attachments ?? []}
                      skillOptions={skillOptions}
                      onUploadFiles={onUploadFiles}
                      uploading={uploading}
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
