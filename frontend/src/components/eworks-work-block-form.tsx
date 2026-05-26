"use client";

import { useEffect, useMemo, useRef } from "react";
import type { ChangeEvent } from "react";
import { Controller } from "react-hook-form";
import type { Control, FieldErrors, FieldPath, UseFormRegister, UseFormSetValue, UseFormWatch } from "react-hook-form";
import {
  EworksButton,
  EworksCheckbox,
  EworksFieldError,
  EworksInput,
  EworksLabel,
  EworksSectionTitle,
  EworksTableShell,
  EworksTextarea,
  eworksInputClass,
} from "@/components/eworks-ui";
import type { AttachmentMeta, QuestionnaireFormValues, WorkBlockFormValues } from "@/lib/eworks-calculate-schema";
import { numberFieldOptions } from "@/lib/form-number";
import { withRegisterChange } from "@/lib/form-register";

function numberInputValue(value: unknown): string | number {
  return typeof value === "number" && !Number.isNaN(value) ? value : "";
}

type Props = {
  workIndex: number;
  control: Control<QuestionnaireFormValues>;
  register: UseFormRegister<QuestionnaireFormValues>;
  watch: UseFormWatch<QuestionnaireFormValues>;
  setValue: UseFormSetValue<QuestionnaireFormValues>;
  errors: FieldErrors<QuestionnaireFormValues>;
  attachments: AttachmentMeta[];
  skillOptions: string[];
  onUploadFiles: (files: FileList | null, workIndex: number) => Promise<void>;
  uploading: boolean;
};

function fieldPath<T extends keyof WorkBlockFormValues>(workIndex: number, field: T) {
  return `works.${workIndex}.${field}` as FieldPath<QuestionnaireFormValues>;
}

export function EworksWorkBlockForm({
  workIndex,
  control,
  register,
  watch,
  setValue,
  errors,
  attachments,
  skillOptions,
  onUploadFiles,
  uploading,
}: Props) {
  const values = watch(`works.${workIndex}`);
  const workErrors = errors.works?.[workIndex];
  const rows = values.materials_to_order;
  const shelfRows = values.shelf_materials_rows;
  const photoInputRef = useRef<HTMLInputElement>(null);
  const videoInputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (values.markup_value === undefined || Number.isNaN(Number(values.markup_value))) {
      setValue(`works.${workIndex}.markup_value`, 20, { shouldValidate: false });
    }
  }, [setValue, values.markup_value, workIndex]);

  const handleAttachmentChange = (event: ChangeEvent<HTMLInputElement>) => {
    void onUploadFiles(event.target.files, workIndex);
    event.target.value = "";
  };

  const clearMaterialQuantity = (table: "materials_to_order" | "shelf_materials_rows", index: number, link: string) => {
    if (!link.trim()) {
      setValue(`works.${workIndex}.${table}.${index}.quantity`, 0, { shouldValidate: true });
    }
  };

  const addRow = () => {
    setValue(`works.${workIndex}.materials_to_order`, [...rows, { link: "", quantity: 0, cost: 0 }], {
      shouldValidate: true,
    });
  };

  const removeRow = (index: number) => {
    if (rows.length <= 1) return;
    setValue(
      `works.${workIndex}.materials_to_order`,
      rows.filter((_, rowIndex) => rowIndex !== index),
      { shouldValidate: true },
    );
  };

  const addShelfRow = () => {
    setValue(`works.${workIndex}.shelf_materials_rows`, [...shelfRows, { link: "", quantity: 0, cost: 0 }], {
      shouldValidate: true,
    });
  };

  const removeShelfRow = (index: number) => {
    if (shelfRows.length <= 1) return;
    setValue(
      `works.${workIndex}.shelf_materials_rows`,
      shelfRows.filter((_, rowIndex) => rowIndex !== index),
      { shouldValidate: true },
    );
  };

  const showLabour = values.engineers_required && values.engineer_time_unit === "days";

  const engineerTimeUnitField = register(fieldPath(workIndex, "engineer_time_unit"));

  const skillChoices = useMemo(() => {
    const choices = new Set(skillOptions);
    if (values.skill_required?.trim()) {
      choices.add(values.skill_required.trim());
    }
    return Array.from(choices).sort((a, b) => a.localeCompare(b));
  }, [skillOptions, values.skill_required]);

  const clearLabour = () => {
    setValue(`works.${workIndex}.labour_required`, false, { shouldValidate: true });
    setValue(`works.${workIndex}.labour_needed`, 0, { shouldValidate: true });
  };

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <EworksSectionTitle title="Scope of Works" />
        <Controller
          name={fieldPath(workIndex, "scope")}
          control={control}
          render={({ field, fieldState }) => (
            <>
              <EworksTextarea
                rows={8}
                hasError={!!fieldState.error}
                name={field.name}
                ref={field.ref}
                value={typeof field.value === "string" ? field.value : ""}
                onBlur={field.onBlur}
                onChange={field.onChange}
              />
              <EworksFieldError message={fieldState.error?.message} />
            </>
          )}
        />
      </div>

      <div className="space-y-3">
        <EworksSectionTitle title="Materials to Order and Cost" subtitle="Optional. Add rows only when materials need ordering." />
        <EworksTableShell>
          <table className="min-w-full text-sm">
            <thead className="bg-optimal-field text-left text-[11px] font-bold uppercase tracking-wide text-black">
              <tr>
                <th className="px-3 py-2.5">Link</th>
                <th className="w-28 px-3 py-2.5">Quantity</th>
                <th className="w-32 px-3 py-2.5">Cost</th>
                <th className="w-16 px-3 py-2.5" />
              </tr>
            </thead>
            <tbody>
              {rows.map((_, index) => (
                <tr key={index} className="border-t border-black/10">
                  <td className="px-3 py-2.5">
                    <EworksInput
                      className="min-h-[40px] bg-white text-sm"
                      {...withRegisterChange<HTMLInputElement>(register(`works.${workIndex}.materials_to_order.${index}.link`), (event) =>
                        clearMaterialQuantity("materials_to_order", index, event.target.value),
                      )}
                    />
                  </td>
                  <td className="px-3 py-2.5">
                    <EworksInput
                      type="number"
                      min="0"
                      step="1"
                      placeholder="0"
                      className="min-h-[40px] bg-white text-sm"
                      {...register(`works.${workIndex}.materials_to_order.${index}.quantity`, numberFieldOptions(0))}
                    />
                  </td>
                  <td className="px-3 py-2.5">
                    <EworksInput
                      type="number"
                      step="0.01"
                      min="0"
                      placeholder="0.00"
                      className="min-h-[40px] bg-white text-sm"
                      {...register(`works.${workIndex}.materials_to_order.${index}.cost`, numberFieldOptions(0))}
                    />
                  </td>
                  <td className="px-3 py-2.5">
                    <button type="button" className="min-h-[44px] px-2 text-xs font-semibold text-red-500 active:opacity-70" onClick={() => removeRow(index)}>
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </EworksTableShell>
        <EworksButton variant="ghost" className="min-h-[40px] px-3 text-xs" onClick={addRow}>
          + Add material row
        </EworksButton>
        <EworksFieldError message={workErrors?.materials_to_order?.message as string | undefined} />
      </div>

      <div className="space-y-3">
        <EworksSectionTitle title="Materials bought off the Shelf and Cost" subtitle="Optional. Add shelf items only when needed." />
        <EworksTableShell>
          <table className="min-w-full text-sm">
            <thead className="bg-optimal-field text-left text-[11px] font-bold uppercase tracking-wide text-black">
              <tr>
                <th className="px-3 py-2.5">Item</th>
                <th className="w-28 px-3 py-2.5">Quantity</th>
                <th className="w-32 px-3 py-2.5">Cost</th>
                <th className="w-16 px-3 py-2.5" />
              </tr>
            </thead>
            <tbody>
              {shelfRows.map((_, index) => (
                <tr key={index} className="border-t border-black/10">
                  <td className="px-3 py-2.5">
                    <EworksInput
                      className="min-h-[40px] bg-white text-sm"
                      {...withRegisterChange<HTMLInputElement>(register(`works.${workIndex}.shelf_materials_rows.${index}.link`), (event) =>
                        clearMaterialQuantity("shelf_materials_rows", index, event.target.value),
                      )}
                    />
                  </td>
                  <td className="px-3 py-2.5">
                    <EworksInput
                      type="number"
                      min="0"
                      step="1"
                      placeholder="0"
                      className="min-h-[40px] bg-white text-sm"
                      {...register(`works.${workIndex}.shelf_materials_rows.${index}.quantity`, numberFieldOptions(0))}
                    />
                  </td>
                  <td className="px-3 py-2.5">
                    <EworksInput
                      type="number"
                      step="0.01"
                      min="0"
                      placeholder="0.00"
                      className="min-h-[40px] bg-white text-sm"
                      {...register(`works.${workIndex}.shelf_materials_rows.${index}.cost`, numberFieldOptions(0))}
                    />
                  </td>
                  <td className="px-3 py-2.5">
                    <button type="button" className="min-h-[44px] px-2 text-xs font-semibold text-red-500 active:opacity-70" onClick={() => removeShelfRow(index)}>
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </EworksTableShell>
        <EworksButton variant="ghost" className="min-h-[40px] px-3 text-xs" onClick={addShelfRow}>
          + Add material row
        </EworksButton>
        <EworksFieldError message={workErrors?.shelf_materials_rows?.message as string | undefined} />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <EworksLabel>
          Skill Required
          <select className={eworksInputClass(!!workErrors?.skill_required)} {...register(fieldPath(workIndex, "skill_required"))}>
            <option value="">{skillChoices.length === 0 ? "Loading skills…" : "Select skill"}</option>
            {skillChoices.map((skill) => (
              <option key={skill} value={skill}>
                {skill}
              </option>
            ))}
          </select>
          <EworksFieldError message={workErrors?.skill_required?.message} />
        </EworksLabel>
        <EworksLabel>
          Best Engineer
          <EworksInput {...register(fieldPath(workIndex, "best_engineer"))} />
        </EworksLabel>
        <EworksLabel>
          Subcontractors
          <EworksInput {...register(fieldPath(workIndex, "subcontractors"))} />
        </EworksLabel>
      </div>

      <div className="space-y-3 rounded-lg border border-white/10 bg-white/5 p-3">
        <Controller
          name={fieldPath(workIndex, "engineers_required")}
          control={control}
          render={({ field, fieldState }) => (
            <>
              <EworksCheckbox
                label="Engineer needed"
                name={field.name}
                ref={field.ref}
                checked={field.value === true}
                onBlur={field.onBlur}
                onChange={(event) => {
                  const checked = event.target.checked;
                  field.onChange(checked);
                  if (!checked) {
                    clearLabour();
                  }
                }}
              />
              <EworksFieldError message={fieldState.error?.message} />
            </>
          )}
        />
        {values.engineers_required && (
          <div className="grid gap-4 sm:grid-cols-3">
            <EworksLabel>
              Number of engineers
              <Controller
                name={fieldPath(workIndex, "engineers_needed")}
                control={control}
                render={({ field, fieldState }) => (
                  <>
                    <EworksInput
                      type="number"
                      min="1"
                      step="1"
                      placeholder="Required"
                      hasError={!!fieldState.error}
                      name={field.name}
                      ref={field.ref}
                      value={numberInputValue(field.value)}
                      onBlur={field.onBlur}
                      onChange={(event) => field.onChange(numberFieldOptions().setValueAs(event.target.value))}
                    />
                    <EworksFieldError message={fieldState.error?.message} />
                  </>
                )}
              />
            </EworksLabel>
            <EworksLabel>
              Hours or Days
              <select
                className={eworksInputClass(!!workErrors?.engineer_time_unit)}
                {...withRegisterChange<HTMLSelectElement>(engineerTimeUnitField, (event) => {
                  if (event.target.value === "hours") {
                    clearLabour();
                  }
                })}
              >
                <option value="hours">Hours</option>
                <option value="days">Days</option>
              </select>
              <EworksFieldError message={workErrors?.engineer_time_unit?.message} />
            </EworksLabel>
            <EworksLabel>
              Duration
              <Controller
                name={fieldPath(workIndex, "engineer_time_value")}
                control={control}
                render={({ field, fieldState }) => (
                  <>
                    <div className="flex items-center gap-2">
                      <EworksInput
                        type="number"
                        step="0.5"
                        min="0.5"
                        placeholder="Required"
                        hasError={!!fieldState.error}
                        name={field.name}
                        ref={field.ref}
                        value={numberInputValue(field.value)}
                        onBlur={field.onBlur}
                        onChange={(event) => field.onChange(numberFieldOptions().setValueAs(event.target.value))}
                      />
                      <span className="shrink-0 text-sm text-optimal-muted">
                        {values.engineer_time_unit === "hours"
                          ? values.engineer_time_value === 1
                            ? "hour"
                            : "hours"
                          : values.engineer_time_value === 1
                            ? "day"
                            : "days"}
                      </span>
                    </div>
                    <EworksFieldError message={fieldState.error?.message} />
                  </>
                )}
              />
            </EworksLabel>
          </div>
        )}
      </div>

      {showLabour && (
        <div className="space-y-3 rounded-lg border border-white/10 bg-white/5 p-3">
          <Controller
            name={fieldPath(workIndex, "labour_required")}
            control={control}
            render={({ field, fieldState }) => (
              <>
                <EworksCheckbox
                  label="Labour needed"
                  name={field.name}
                  ref={field.ref}
                  checked={field.value === true}
                  onBlur={field.onBlur}
                  onChange={(event) => {
                    const checked = event.target.checked;
                    field.onChange(checked);
                  }}
                />
                <EworksFieldError message={fieldState.error?.message} />
              </>
            )}
          />
          {values.labour_required && (
            <div className="grid gap-4 sm:grid-cols-2">
              <EworksLabel>
                Number of labour
                <Controller
                  name={fieldPath(workIndex, "labour_needed")}
                  control={control}
                  render={({ field, fieldState }) => (
                    <>
                      <EworksInput
                        type="number"
                        min="1"
                        placeholder="Required"
                        hasError={!!fieldState.error}
                        name={field.name}
                        ref={field.ref}
                        value={numberInputValue(field.value)}
                        onBlur={field.onBlur}
                        onChange={(event) => field.onChange(numberFieldOptions().setValueAs(event.target.value))}
                      />
                      <EworksFieldError message={fieldState.error?.message} />
                    </>
                  )}
                />
              </EworksLabel>
              <EworksLabel>
                Duration
                <Controller
                  name={fieldPath(workIndex, "labour_time_value")}
                  control={control}
                  render={({ field, fieldState }) => (
                    <>
                      <div className="flex items-center gap-2">
                        <EworksInput
                          type="number"
                          step="0.5"
                          min="0.5"
                          placeholder="Required"
                          hasError={!!fieldState.error}
                          name={field.name}
                          ref={field.ref}
                          value={numberInputValue(field.value)}
                          onBlur={field.onBlur}
                          onChange={(event) => field.onChange(numberFieldOptions().setValueAs(event.target.value))}
                        />
                        <span className="shrink-0 text-sm text-optimal-muted">
                          {values.labour_time_value === 1 ? "day" : "days"}
                        </span>
                      </div>
                      <EworksFieldError message={fieldState.error?.message} />
                    </>
                  )}
                />
              </EworksLabel>
            </div>
          )}
        </div>
      )}

      <div className="space-y-4 rounded-lg border border-white/10 bg-white/5 p-4">
        <EworksSectionTitle title="Charges" />
        <div className="grid gap-4 sm:grid-cols-2">
          <Controller
            name={fieldPath(workIndex, "parking_required")}
            control={control}
            render={({ field }) => (
              <EworksCheckbox
                label="Parking charge required"
                className="sm:col-span-2"
                name={field.name}
                ref={field.ref}
                checked={field.value === true}
                onBlur={field.onBlur}
                onChange={(e) => field.onChange(e.target.checked)}
              />
            )}
          />
          {values.parking_required && (
            <>
              <EworksLabel>
                Parking type
                <select className={eworksInputClass()} {...register(fieldPath(workIndex, "parking_type"))}>
                  <option value="fixed">Fixed</option>
                  <option value="hourly">Hourly</option>
                </select>
              </EworksLabel>
              {values.parking_type === "hourly" ? (
                <>
                  <EworksLabel>
                    Rate per hour
                    <EworksInput type="number" min="0" step="0.01" {...register(fieldPath(workIndex, "parking_rate_per_hour"), numberFieldOptions(0))} />
                  </EworksLabel>
                  <EworksLabel>
                    Hours
                    <EworksInput type="number" min="0" step="0.5" {...register(fieldPath(workIndex, "parking_hours"), numberFieldOptions(0))} />
                  </EworksLabel>
                </>
              ) : (
                <EworksLabel>
                  Fixed amount (£)
                  <EworksInput type="number" min="0" step="0.01" {...register(fieldPath(workIndex, "parking_fixed_amount"), numberFieldOptions(0))} />
                </EworksLabel>
              )}
            </>
          )}
          <Controller
            name={fieldPath(workIndex, "congestion_required")}
            control={control}
            render={({ field }) => (
              <EworksCheckbox
                label="Add congestion charge"
                className="sm:col-span-2"
                name={field.name}
                ref={field.ref}
                checked={field.value === true}
                onBlur={field.onBlur}
                onChange={(e) => field.onChange(e.target.checked)}
              />
            )}
          />
          {values.congestion_required && (
            <EworksLabel>
              Congestion amount (£)
              <EworksInput type="number" min="0" step="0.01" {...register(fieldPath(workIndex, "congestion_amount"), numberFieldOptions(0))} />
            </EworksLabel>
          )}
          <EworksLabel>
            Travel charge (£)
            <EworksInput type="number" min="0" step="0.01" {...register(fieldPath(workIndex, "travel_charge"), numberFieldOptions(0))} />
          </EworksLabel>
          <EworksLabel>
            Other charge (£)
            <EworksInput type="number" min="0" step="0.01" {...register(fieldPath(workIndex, "other_charge"), numberFieldOptions(0))} />
          </EworksLabel>
          {values.other_charge > 0 && (
            <EworksLabel className="sm:col-span-2">
              Other charge reason
              <EworksInput
                hasError={!!workErrors?.other_charge_reason}
                {...register(fieldPath(workIndex, "other_charge_reason"))}
              />
              <EworksFieldError message={workErrors?.other_charge_reason?.message} />
            </EworksLabel>
          )}
        </div>
      </div>

      <div className="space-y-2">
        <EworksSectionTitle title="Any Other Notes" />
        <EworksTextarea rows={4} {...register(fieldPath(workIndex, "other_notes"))} />
      </div>

      <div className="space-y-3">
        <EworksSectionTitle title="Photos / Videos" subtitle="Capture on site or choose from library" />
        <input
          ref={photoInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={handleAttachmentChange}
          disabled={uploading}
        />
        <input
          ref={videoInputRef}
          type="file"
          accept="video/*"
          capture="environment"
          className="hidden"
          onChange={handleAttachmentChange}
          disabled={uploading}
        />
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*,video/*"
          multiple
          className="hidden"
          onChange={handleAttachmentChange}
          disabled={uploading}
        />
        <div className="flex flex-wrap gap-2">
          <EworksButton variant="secondary" className="flex-1 sm:flex-none" onClick={() => photoInputRef.current?.click()} disabled={uploading}>
            Take photo
          </EworksButton>
          <EworksButton variant="secondary" className="flex-1 sm:flex-none" onClick={() => videoInputRef.current?.click()} disabled={uploading}>
            Record video
          </EworksButton>
          <EworksButton variant="secondary" className="flex-1 sm:flex-none" onClick={() => fileInputRef.current?.click()} disabled={uploading}>
            Choose files
          </EworksButton>
        </div>
        <p className="text-xs leading-relaxed text-optimal-muted">
          Use the camera on your phone or choose existing photos and videos (max 50MB each).
        </p>
        {uploading && <p className="text-xs font-medium text-optimal-orange animate-pulse-soft">Uploading…</p>}
        {attachments.length > 0 && (
          <ul className="space-y-2">
            {attachments.map((file) => (
              <li key={file.id} className="flex min-h-[44px] items-center rounded-lg border border-white/10 bg-optimal-field px-3.5 py-2.5 text-sm">
                <span className="font-medium text-optimal-field-text">
                  {file.media_type === "photo" ? "Photo" : file.media_type === "video" ? "Video" : "File"}: {file.file_name}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
