"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { ChangeEvent } from "react";
import type { ControllerRenderProps } from "react-hook-form";
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
  cn,
  eworksInputClass,
} from "@/components/eworks-ui";
import { fetchProduct } from "@/lib/products-api";
import type { AttachmentMeta, MaterialSupplierFormValues, QuestionnaireFormValues, WorkBlockFormValues } from "@/lib/eworks-calculate-schema";
import { defaultMaterialSuppliers, PARKING_COPY_FIELDS, computeProductTotalPrice, supplierMaterialsTotal } from "@/lib/eworks-calculate-schema";
import { getAttachmentUrl, rewordScope } from "@/lib/eworks-session";
import { withRegisterChange } from "@/lib/form-register";

// Uses type="text" to avoid browser number-input quirks (can't clear, intermediate
// decimals eaten, spinners fighting React). The `editing` state owns the display while
// the field is focused; field.value only drives the display when the field is blurred,
// which eliminates the stale-value race that would restore a just-deleted number.
function NumericInput({
  field,
  hasError,
  placeholder,
  className,
}: {
  field: ControllerRenderProps<QuestionnaireFormValues, FieldPath<QuestionnaireFormValues>>;
  hasError?: boolean;
  placeholder?: string;
  className?: string;
}) {
  // null  → field is not focused; displayValue is derived from field.value
  // string → user is actively editing; displayValue is this string
  const [editing, setEditing] = useState<string | null>(null);

  const numericValue = field.value as number | undefined;
  const displayValue =
    editing !== null
      ? editing
      : typeof numericValue === "number" && !Number.isNaN(numericValue)
        ? String(numericValue)
        : "";

  return (
    <EworksInput
      type="text"
      inputMode="decimal"
      placeholder={placeholder}
      hasError={hasError}
      className={className}
      name={field.name}
      ref={field.ref}
      value={displayValue}
      onChange={(e) => {
        const raw = e.target.value;
        if (raw !== "" && !/^\d*\.?\d*$/.test(raw)) return;
        setEditing(raw);
        const parsed = raw === "" ? undefined : Number(raw);
        field.onChange(Number.isNaN(parsed as number) ? undefined : parsed);
      }}
      onBlur={() => {
        setEditing(null); // hand display control back to field.value
        field.onBlur();
      }}
    />
  );
}

type Props = {
  workIndex: number;
  workNumber: number;
  control: Control<QuestionnaireFormValues>;
  register: UseFormRegister<QuestionnaireFormValues>;
  watch: UseFormWatch<QuestionnaireFormValues>;
  setValue: UseFormSetValue<QuestionnaireFormValues>;
  errors: FieldErrors<QuestionnaireFormValues>;
  attachments: AttachmentMeta[];
  skillOptions: string[];
  sessionId: string;
  sessionToken: string;
  onUploadFiles: (files: FileList | null, workIndex: number) => Promise<void>;
  onDeleteAttachment: (workIndex: number, attachmentId: string) => Promise<void>;
  uploading: boolean;
  deletingAttachmentId: string | null;
  cachedProductScope?: string;
};

function fieldPath<T extends keyof WorkBlockFormValues>(workIndex: number, field: T) {
  return `works.${workIndex}.${field}` as FieldPath<QuestionnaireFormValues>;
}

type MaterialRowsSectionProps = {
  workIndex: number;
  labelColumn: string;
  table: "shelf_materials_rows";
  rows: WorkBlockFormValues["shelf_materials_rows"];
  register: UseFormRegister<QuestionnaireFormValues>;
  control: Control<QuestionnaireFormValues>;
  onLinkChange: (index: number, value: string) => void;
  onRemove: (index: number) => void;
};

const materialRowGridClass =
  "lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)_4.5rem] lg:items-center lg:gap-3 lg:px-3 lg:py-2.5";

function MaterialRowsSection({
  workIndex,
  labelColumn,
  table,
  rows,
  register,
  control,
  onLinkChange,
  onRemove,
}: MaterialRowsSectionProps) {
  return (
    <EworksTableShell>
      <div className="hidden bg-gray-100 px-3 py-2.5 text-left text-[11px] font-bold uppercase tracking-wide text-gray-700 lg:grid lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)_4.5rem] lg:gap-3">
        <span>{labelColumn}</span>
        <span>Quantity</span>
        <span>Cost</span>
        <span />
      </div>
      <div className="divide-y divide-black/10">
        {rows.map((_, index) => (
          <div key={index} className={cn("grid grid-cols-1 gap-3 p-3", materialRowGridClass)}>
            <div className="min-w-0 w-full">
              <span className="mb-1.5 block text-[11px] font-bold uppercase tracking-wide text-black lg:hidden">
                {labelColumn}
              </span>
              <EworksInput
                className="min-h-[44px] w-full min-w-0 bg-white text-base lg:min-h-[40px] lg:text-sm"
                {...withRegisterChange<HTMLInputElement>(
                  register(`works.${workIndex}.${table}.${index}.link`),
                  (event) => onLinkChange(index, event.target.value),
                )}
              />
            </div>
            <div className="grid min-w-0 grid-cols-2 gap-3 lg:contents">
              <div className="min-w-0">
                <span className="mb-1.5 block text-[11px] font-bold uppercase tracking-wide text-black lg:hidden">
                  Quantity
                </span>
                <Controller
                  name={`works.${workIndex}.${table}.${index}.quantity` as FieldPath<QuestionnaireFormValues>}
                  control={control}
                  render={({ field }) => (
                    <NumericInput
                      field={field}
                      placeholder="0"
                      className="min-h-[44px] w-full min-w-0 bg-white text-base lg:min-h-[40px] lg:text-sm"
                    />
                  )}
                />
              </div>
              <div className="min-w-0">
                <span className="mb-1.5 block text-[11px] font-bold uppercase tracking-wide text-black lg:hidden">
                  Cost
                </span>
                <Controller
                  name={`works.${workIndex}.${table}.${index}.cost` as FieldPath<QuestionnaireFormValues>}
                  control={control}
                  render={({ field }) => (
                    <NumericInput
                      field={field}
                      placeholder="0.00"
                      className="min-h-[44px] w-full min-w-0 bg-white text-base lg:min-h-[40px] lg:text-sm"
                    />
                  )}
                />
              </div>
            </div>
            <div className="flex items-center lg:justify-end">
              <button
                type="button"
                className="min-h-[44px] px-1 text-xs font-semibold text-red-500 active:opacity-70 lg:px-2"
                onClick={() => onRemove(index)}
              >
                Remove
              </button>
            </div>
          </div>
        ))}
      </div>
    </EworksTableShell>
  );
}

type SupplierMaterialsSectionProps = {
  workIndex: number;
  suppliers: MaterialSupplierFormValues[];
  register: UseFormRegister<QuestionnaireFormValues>;
  control: Control<QuestionnaireFormValues>;
  setValue: UseFormSetValue<QuestionnaireFormValues>;
  onAddSupplier: () => void;
  onRemoveSupplier: (supplierIndex: number) => void;
  onAddLink: (supplierIndex: number) => void;
  onRemoveLink: (supplierIndex: number, linkIndex: number) => void;
  onLinkChange: (supplierIndex: number, linkIndex: number, value: string) => void;
};

function SupplierMaterialsSection({
  workIndex,
  suppliers,
  register,
  control,
  onAddSupplier,
  onRemoveSupplier,
  onAddLink,
  onRemoveLink,
  onLinkChange,
}: SupplierMaterialsSectionProps) {
  return (
    <div className="space-y-4">
      {suppliers.map((supplier, supplierIndex) => (
        <div key={supplierIndex} className="rounded-lg border border-gray-200 bg-white">
          <div className="flex items-center justify-between border-b border-gray-200 bg-gray-50 px-3 py-2.5">
            <span className="text-sm font-semibold text-gray-900">Supplier {supplierIndex + 1}</span>
            <button
              type="button"
              className="flex size-8 items-center justify-center rounded border border-gray-300 text-lg leading-none text-gray-600 hover:bg-gray-100 disabled:opacity-40"
              disabled={suppliers.length <= 1}
              onClick={() => onRemoveSupplier(supplierIndex)}
              aria-label={`Remove supplier ${supplierIndex + 1}`}
            >
              −
            </button>
          </div>
          <div className="space-y-3 p-3">
            <EworksTableShell>
              <div className="hidden bg-gray-100 px-3 py-2.5 text-left text-[11px] font-bold uppercase tracking-wide text-gray-700 lg:grid lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)_4.5rem] lg:gap-3">
                <span>Link</span>
                <span>Quantity</span>
                <span>Cost per item</span>
                <span />
              </div>
              <div className="divide-y divide-black/10">
                {supplier.links.map((_, linkIndex) => (
                  <div key={linkIndex} className={cn("grid grid-cols-1 gap-3 p-3", materialRowGridClass)}>
                    <div className="min-w-0 w-full">
                      <span className="mb-1.5 block text-[11px] font-bold uppercase tracking-wide text-black lg:hidden">
                        Link
                      </span>
                      <EworksInput
                        className="min-h-[44px] w-full min-w-0 bg-white text-base lg:min-h-[40px] lg:text-sm"
                        {...withRegisterChange<HTMLInputElement>(
                          register(`works.${workIndex}.materials_to_order.${supplierIndex}.links.${linkIndex}.link`),
                          (event) => onLinkChange(supplierIndex, linkIndex, event.target.value),
                        )}
                      />
                    </div>
                    <div className="grid min-w-0 grid-cols-2 gap-3 lg:contents">
                      <div className="min-w-0">
                        <span className="mb-1.5 block text-[11px] font-bold uppercase tracking-wide text-black lg:hidden">
                          Quantity
                        </span>
                        <Controller
                          name={`works.${workIndex}.materials_to_order.${supplierIndex}.links.${linkIndex}.quantity` as FieldPath<QuestionnaireFormValues>}
                          control={control}
                          render={({ field }) => (
                            <NumericInput
                              field={field}
                              placeholder="0"
                              className="min-h-[44px] w-full min-w-0 bg-white text-base lg:min-h-[40px] lg:text-sm"
                            />
                          )}
                        />
                      </div>
                      <div className="min-w-0">
                        <span className="mb-1.5 block text-[11px] font-bold uppercase tracking-wide text-black lg:hidden">
                          Cost per item
                        </span>
                        <Controller
                          name={`works.${workIndex}.materials_to_order.${supplierIndex}.links.${linkIndex}.cost` as FieldPath<QuestionnaireFormValues>}
                          control={control}
                          render={({ field }) => (
                            <NumericInput
                              field={field}
                              placeholder="0.00"
                              className="min-h-[44px] w-full min-w-0 bg-white text-base lg:min-h-[40px] lg:text-sm"
                            />
                          )}
                        />
                      </div>
                    </div>
                    <div className="flex items-center lg:justify-end">
                      <button
                        type="button"
                        className="min-h-[44px] px-1 text-xs font-semibold text-red-500 active:opacity-70 lg:px-2"
                        disabled={supplier.links.length <= 1}
                        onClick={() => onRemoveLink(supplierIndex, linkIndex)}
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </EworksTableShell>
            <EworksButton variant="ghost" className="min-h-[40px] px-3 text-xs" onClick={() => onAddLink(supplierIndex)}>
              + Add link
            </EworksButton>
            <div className="grid gap-3 sm:grid-cols-2">
              <EworksLabel>
                Delivery charges
                <Controller
                  name={`works.${workIndex}.materials_to_order.${supplierIndex}.delivery_charge` as FieldPath<QuestionnaireFormValues>}
                  control={control}
                  render={({ field }) => (
                    <NumericInput
                      field={field}
                      placeholder="0.00"
                      className="min-h-[44px] w-full bg-white text-base lg:min-h-[40px] lg:text-sm"
                    />
                  )}
                />
              </EworksLabel>
              <div className="flex flex-col justify-end">
                <span className="text-[11px] font-bold uppercase tracking-wide text-gray-600">Total</span>
                <p className="mt-1.5 min-h-[44px] rounded-lg bg-optimal-field px-3.5 py-2.5 text-sm font-semibold text-optimal-field-text lg:min-h-[40px]">
                  £{supplierMaterialsTotal(supplier).toFixed(2)}
                </p>
              </div>
            </div>
          </div>
        </div>
      ))}
      <EworksButton variant="ghost" className="min-h-[40px] px-3 text-xs" onClick={onAddSupplier}>
        + Add supplier
      </EworksButton>
    </div>
  );
}

export function EworksWorkBlockForm({
  workIndex,
  workNumber,
  control,
  register,
  watch,
  setValue,
  errors,
  attachments,
  skillOptions,
  sessionId,
  sessionToken,
  onUploadFiles,
  onDeleteAttachment,
  uploading,
  deletingAttachmentId,
  cachedProductScope,
}: Props) {
  const values = watch(`works.${workIndex}`);
  const work1Parking = watch("works.0");
  const workErrors = errors.works?.[workIndex];
  const suppliers = values.materials_to_order;
  const shelfRows = values.shelf_materials_rows;
  const photoInputRef = useRef<HTMLInputElement>(null);
  const videoInputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [rewordingScope, setRewordingScope] = useState(false);
  const [rewordError, setRewordError] = useState<string | null>(null);
  const [resettingScope, setResettingScope] = useState(false);
  const [resetScopeError, setResetScopeError] = useState<string | null>(null);
  const [gpsError, setGpsError] = useState<string | null>(null);
  const [capturingGps, setCapturingGps] = useState(false);

  const scopeText = values.scope?.trim() ?? "";
  const hasSelectedProduct = values.selected_product_id != null;
  const productScopeAvailable = Boolean((cachedProductScope ?? "").trim());
  const showMissingScopeWarning = hasSelectedProduct && !productScopeAvailable && !scopeText;
  const engineerNotes = values.other_notes?.trim() ?? "";
  const engineerFindings = values.findings?.trim() ?? "";

  const handleResetScopeFromProduct = async () => {
    if (values.selected_product_id == null) return;
    setResettingScope(true);
    setResetScopeError(null);
    try {
      const product = await fetchProduct(values.selected_product_id);
      const scope = product.scope_of_work?.trim() ?? "";
      setValue(fieldPath(workIndex, "scope"), scope, { shouldValidate: true });
      setValue(fieldPath(workIndex, "scope_from_product"), true, { shouldValidate: false });
    } catch (error) {
      setResetScopeError(error instanceof Error ? error.message : "Failed to load product scope");
    } finally {
      setResettingScope(false);
    }
  };

  useEffect(() => {
    if (values.markup_value === undefined || Number.isNaN(Number(values.markup_value))) {
      setValue(`works.${workIndex}.markup_value`, 20, { shouldValidate: false });
    }
  }, [setValue, values.markup_value, workIndex]);

  useEffect(() => {
    if (values.selected_product_id == null) return;
    const total = computeProductTotalPrice(values.product_quantity ?? 1, values.product_unit_price ?? 0);
    if (values.product_total_price !== total) {
      setValue(fieldPath(workIndex, "product_total_price"), total, { shouldValidate: false });
    }
  }, [
    values.selected_product_id,
    values.product_quantity,
    values.product_unit_price,
    values.product_total_price,
    workIndex,
    setValue,
  ]);

  const handleAttachmentChange = (event: ChangeEvent<HTMLInputElement>) => {
    void onUploadFiles(event.target.files, workIndex);
    event.target.value = "";
  };

  const clearMaterialQuantity = (table: "materials_to_order" | "shelf_materials_rows", index: number, link: string) => {
    if (!link.trim()) {
      setValue(`works.${workIndex}.${table}.${index}.quantity`, 0, { shouldValidate: true });
    }
  };

  const clearSupplierLinkQuantity = (supplierIndex: number, linkIndex: number, link: string) => {
    if (!link.trim()) {
      setValue(`works.${workIndex}.materials_to_order.${supplierIndex}.links.${linkIndex}.quantity`, 0, {
        shouldValidate: true,
      });
    }
  };

  const addSupplier = () => {
    setValue(`works.${workIndex}.materials_to_order`, [...suppliers, ...defaultMaterialSuppliers()], {
      shouldValidate: true,
    });
  };

  const removeSupplier = (supplierIndex: number) => {
    if (suppliers.length <= 1) return;
    setValue(
      `works.${workIndex}.materials_to_order`,
      suppliers.filter((_, index) => index !== supplierIndex),
      { shouldValidate: true },
    );
  };

  const addSupplierLink = (supplierIndex: number) => {
    const next = suppliers.map((supplier, index) =>
      index === supplierIndex
        ? { ...supplier, links: [...supplier.links, { link: "", quantity: 0, cost: 0 }] }
        : supplier,
    );
    setValue(`works.${workIndex}.materials_to_order`, next, { shouldValidate: true });
  };

  const removeSupplierLink = (supplierIndex: number, linkIndex: number) => {
    const supplier = suppliers[supplierIndex];
    if (!supplier || supplier.links.length <= 1) return;
    const next = suppliers.map((item, index) =>
      index === supplierIndex
        ? { ...item, links: item.links.filter((_, rowIndex) => rowIndex !== linkIndex) }
        : item,
    );
    setValue(`works.${workIndex}.materials_to_order`, next, { shouldValidate: true });
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

  const copyParkingFromPreviousWork = () => {
    if (workIndex === 0) return;
    const source = watch(`works.${workIndex - 1}`);
    for (const field of PARKING_COPY_FIELDS) {
      setValue(fieldPath(workIndex, field), source[field] as WorkBlockFormValues[typeof field], {
        shouldValidate: true,
      });
    }
    setGpsError(null);
  };

  const captureParkingGps = () => {
    setGpsError(null);
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      setGpsError("Geolocation is not supported in this browser.");
      return;
    }
    setCapturingGps(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const lat = Math.round(position.coords.latitude * 1_000_000) / 1_000_000;
        const lng = Math.round(position.coords.longitude * 1_000_000) / 1_000_000;
        setValue(fieldPath(workIndex, "parking_latitude"), lat, { shouldValidate: true });
        setValue(fieldPath(workIndex, "parking_longitude"), lng, { shouldValidate: true });
        setCapturingGps(false);
      },
      (error) => {
        setCapturingGps(false);
        if (error.code === error.PERMISSION_DENIED) {
          setGpsError("Location permission denied. Allow location access and try again.");
        } else {
          setGpsError("Could not capture location. Try again or enter coordinates manually.");
        }
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 },
    );
  };

  const clearParkingGps = () => {
    setValue(fieldPath(workIndex, "parking_latitude"), null, { shouldValidate: true });
    setValue(fieldPath(workIndex, "parking_longitude"), null, { shouldValidate: true });
    setGpsError(null);
  };

  const openParkingInGoogleMaps = () => {
    const lat = values.parking_latitude;
    const lng = values.parking_longitude;
    if (lat == null || lng == null) return;
    window.open(`https://www.google.com/maps?q=${lat},${lng}`, "_blank", "noopener,noreferrer");
  };

  const hasParkingGps = values.parking_latitude != null && values.parking_longitude != null;
  const usesWork1ParkingLocation = workIndex > 0 && values.parking_same_location_as_work1 === true;
  const work1HasParkingGps =
    work1Parking.parking_latitude != null && work1Parking.parking_longitude != null;

  useEffect(() => {
    if (!usesWork1ParkingLocation) return;
    const lat = work1Parking.parking_latitude;
    const lng = work1Parking.parking_longitude;
    if (lat == null || lng == null) return;
    if (values.parking_latitude !== lat) {
      setValue(fieldPath(workIndex, "parking_latitude"), lat, { shouldValidate: true });
    }
    if (values.parking_longitude !== lng) {
      setValue(fieldPath(workIndex, "parking_longitude"), lng, { shouldValidate: true });
    }
  }, [
    usesWork1ParkingLocation,
    work1Parking.parking_latitude,
    work1Parking.parking_longitude,
    values.parking_latitude,
    values.parking_longitude,
    workIndex,
    setValue,
  ]);

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

  const handleRewordScope = async () => {
    if (!scopeText) {
      setRewordError("Enter scope text first");
      return;
    }
    setRewordError(null);
    setRewordingScope(true);
    try {
      const result = await rewordScope(sessionId, sessionToken, scopeText);
      setValue(`works.${workIndex}.scope`, result.reworded_text, { shouldValidate: true });
    } catch (error) {
      setRewordError(error instanceof Error ? error.message : "Failed to reword scope");
    } finally {
      setRewordingScope(false);
    }
  };

  return (
    <div className="space-y-6">
      <p className="text-sm font-medium text-gray-900">Work {workNumber} details</p>

      {(engineerNotes || engineerFindings) && (
        <div className="space-y-3 rounded-lg border border-blue-200 bg-blue-50 p-4">
          <EworksSectionTitle title="Site visit information" subtitle="From engineer site visit — preserved for estimator review" />
          {engineerFindings ? (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-blue-800">Engineer findings</p>
              <pre className="mt-1 whitespace-pre-wrap text-sm text-blue-950">{engineerFindings}</pre>
            </div>
          ) : null}
          {engineerNotes ? (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-blue-800">Site notes</p>
              <pre className="mt-1 whitespace-pre-wrap text-sm text-blue-950">{engineerNotes}</pre>
            </div>
          ) : null}
        </div>
      )}

      <div className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <EworksSectionTitle title="Scope of Works" />
          <div className="flex flex-wrap items-center gap-2">
            {values.selected_product_id != null && (
              <>
                <EworksLabel className="flex-row items-center gap-2 space-y-0">
                  <span className="shrink-0 text-xs text-optimal-muted">Qty</span>
                  <Controller
                    name={fieldPath(workIndex, "product_quantity")}
                    control={control}
                    render={({ field }) => (
                      <NumericInput
                        field={field}
                        className="w-20 min-h-[36px] text-sm"
                      />
                    )}
                  />
                </EworksLabel>
                <EworksButton
                  type="button"
                  variant="secondary"
                  className="min-h-[36px] px-3 text-xs"
                  disabled={resettingScope || !hasSelectedProduct}
                  onClick={() => void handleResetScopeFromProduct()}
                  data-testid={`reset-scope-work-${workIndex}`}
                >
                  {resettingScope ? "Resetting…" : "Reset from Product Scope"}
                </EworksButton>
              </>
            )}
            <EworksButton
              variant="secondary"
              className="min-h-[36px] px-3 text-xs"
              disabled={rewordingScope || !scopeText}
              onClick={() => void handleRewordScope()}
            >
              {rewordingScope ? "Rewording…" : "Reword with AI"}
            </EworksButton>
          </div>
        </div>
        <p className="text-xs text-optimal-muted">
          Auto-filled from selected product. You can edit before generating the quote.
        </p>
        {showMissingScopeWarning ? (
          <p className="text-xs text-amber-700" data-testid={`missing-product-scope-work-${workIndex}`}>
            No default scope configured for this product. Admin can add it in Products / Scope.
          </p>
        ) : null}
        {values.scope_from_product && scopeText ? (
          <p className="text-xs text-green-700">Scope linked to selected product.</p>
        ) : null}
        {resetScopeError ? <EworksFieldError message={resetScopeError} /> : null}
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
                onChange={(event) => {
                  setRewordError(null);
                  field.onChange(event);
                  setValue(fieldPath(workIndex, "scope_from_product"), false, { shouldValidate: false });
                }}
                data-testid={`work-scope-${workIndex}`}
              />
              <EworksFieldError message={rewordError ?? fieldState.error?.message} />
            </>
          )}
        />
      </div>

      <div className="space-y-3">
        <EworksSectionTitle title="Materials to Order and Cost" subtitle="Optional. Add suppliers when materials need ordering." />
        <SupplierMaterialsSection
          workIndex={workIndex}
          suppliers={suppliers}
          register={register}
          control={control}
          setValue={setValue}
          onAddSupplier={addSupplier}
          onRemoveSupplier={removeSupplier}
          onAddLink={addSupplierLink}
          onRemoveLink={removeSupplierLink}
          onLinkChange={clearSupplierLinkQuantity}
        />
        <EworksFieldError message={workErrors?.materials_to_order?.message as string | undefined} />
      </div>

      <div className="space-y-3">
        <EworksSectionTitle title="Materials bought off the Shelf and Cost" subtitle="Optional. Add shelf items only when needed." />
        <MaterialRowsSection
          workIndex={workIndex}
          labelColumn="Item"
          table="shelf_materials_rows"
          rows={shelfRows}
          register={register}
          control={control}
          onLinkChange={(index, value) => clearMaterialQuantity("shelf_materials_rows", index, value)}
          onRemove={removeShelfRow}
        />
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

      <div className="space-y-3 rounded-lg border border-gray-200 bg-gray-50 p-3">
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
                    <NumericInput
                      field={field}
                      hasError={!!fieldState.error}
                      placeholder="Required"
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
                      <NumericInput
                        field={field}
                        hasError={!!fieldState.error}
                        placeholder="Required"
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
        <div className="space-y-3 rounded-lg border border-gray-200 bg-gray-50 p-3">
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
                      <NumericInput
                        field={field}
                        hasError={!!fieldState.error}
                        placeholder="Required"
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
                        <NumericInput
                          field={field}
                          hasError={!!fieldState.error}
                          placeholder="Required"
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

      <div className="space-y-4 rounded-lg border border-gray-200 bg-gray-50 p-4">
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
              {workIndex > 0 && (
                <div className="sm:col-span-2">
                  <EworksButton
                    type="button"
                    variant="ghost"
                    className="min-h-[40px] px-3 text-xs"
                    onClick={copyParkingFromPreviousWork}
                  >
                    Use parking from Work {workIndex}
                  </EworksButton>
                </div>
              )}
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
                    <Controller
                      name={fieldPath(workIndex, "parking_rate_per_hour")}
                      control={control}
                      render={({ field }) => (
                        <NumericInput field={field} />
                      )}
                    />
                  </EworksLabel>
                  <EworksLabel>
                    Hours
                    <Controller
                      name={fieldPath(workIndex, "parking_hours")}
                      control={control}
                      render={({ field }) => (
                        <NumericInput field={field} />
                      )}
                    />
                  </EworksLabel>
                </>
              ) : (
                <EworksLabel>
                  Fixed amount (£)
                  <Controller
                    name={fieldPath(workIndex, "parking_fixed_amount")}
                    control={control}
                    render={({ field }) => (
                      <NumericInput field={field} />
                    )}
                  />
                </EworksLabel>
              )}
              <EworksLabel>
                Number of vehicles
                <Controller
                  name={fieldPath(workIndex, "parking_vehicles")}
                  control={control}
                  render={({ field, fieldState }) => (
                    <>
                      <EworksInput
                        type="text"
                        inputMode="numeric"
                        hasError={!!fieldState.error}
                        name={field.name}
                        ref={field.ref}
                        value={String(field.value ?? 1)}
                        onChange={(e) => {
                          const raw = e.target.value.replace(/\D/g, "");
                          const parsed = raw === "" ? 1 : Math.max(1, parseInt(raw, 10));
                          field.onChange(parsed);
                        }}
                        onBlur={field.onBlur}
                      />
                      <EworksFieldError message={fieldState.error?.message} />
                    </>
                  )}
                />
              </EworksLabel>
              <EworksLabel className="sm:col-span-2">
                Parking and access notes
                <EworksTextarea
                  rows={3}
                  placeholder="Parking bays, permits, site access, gates, contact on arrival…"
                  {...register(fieldPath(workIndex, "parking_notes"))}
                />
              </EworksLabel>
              <div className="space-y-3 sm:col-span-2">
                <p className="text-sm font-semibold text-optimal-orange">Parking GPS location</p>
                {workIndex > 0 && (
                  <Controller
                    name={fieldPath(workIndex, "parking_same_location_as_work1")}
                    control={control}
                    render={({ field }) => (
                      <EworksCheckbox
                        label="Same parking location as Work 1"
                        name={field.name}
                        ref={field.ref}
                        checked={field.value === true}
                        onBlur={field.onBlur}
                        onChange={(e) => {
                          const checked = e.target.checked;
                          field.onChange(checked);
                          if (checked) {
                            const lat = work1Parking.parking_latitude;
                            const lng = work1Parking.parking_longitude;
                            if (lat != null && lng != null) {
                              setValue(fieldPath(workIndex, "parking_latitude"), lat, { shouldValidate: true });
                              setValue(fieldPath(workIndex, "parking_longitude"), lng, { shouldValidate: true });
                              setGpsError(null);
                            }
                          }
                        }}
                      />
                    )}
                  />
                )}
                {usesWork1ParkingLocation && !work1HasParkingGps && (
                  <p className="text-xs text-amber-700">Set parking location on Work 1 first.</p>
                )}
                {usesWork1ParkingLocation && work1HasParkingGps && (
                  <p className="text-xs text-optimal-muted">
                    Using Work 1 location: {work1Parking.parking_latitude}, {work1Parking.parking_longitude}
                  </p>
                )}
                <div className="flex flex-wrap gap-2">
                  <EworksButton
                    type="button"
                    variant="secondary"
                    className="min-h-[40px] text-xs"
                    disabled={capturingGps || usesWork1ParkingLocation}
                    onClick={captureParkingGps}
                  >
                    {capturingGps ? "Capturing…" : "Capture location"}
                  </EworksButton>
                  <EworksButton
                    type="button"
                    variant="secondary"
                    className="min-h-[40px] text-xs"
                    disabled={!hasParkingGps}
                    onClick={openParkingInGoogleMaps}
                  >
                    Open in Google Maps
                  </EworksButton>
                  {hasParkingGps && !usesWork1ParkingLocation && (
                    <EworksButton type="button" variant="ghost" className="min-h-[40px] text-xs" onClick={clearParkingGps}>
                      Clear location
                    </EworksButton>
                  )}
                </div>
                {!usesWork1ParkingLocation && hasParkingGps && (
                  <p className="text-xs text-optimal-muted">
                    {values.parking_latitude}, {values.parking_longitude}
                  </p>
                )}
                {gpsError && !usesWork1ParkingLocation && <EworksFieldError message={gpsError} />}
              </div>
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
              <Controller
                name={fieldPath(workIndex, "congestion_amount")}
                control={control}
                render={({ field }) => (
                  <NumericInput field={field} />
                )}
              />
            </EworksLabel>
          )}
          <EworksLabel>
            Travel charge (£)
            <Controller
              name={fieldPath(workIndex, "travel_charge")}
              control={control}
              render={({ field }) => (
                <NumericInput field={field} />
              )}
            />
          </EworksLabel>
          <EworksLabel>
            Other charge (£)
            <Controller
              name={fieldPath(workIndex, "other_charge")}
              control={control}
              render={({ field }) => (
                <NumericInput field={field} />
              )}
            />
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
            {attachments.map((file) => {
              const viewUrl = getAttachmentUrl(sessionId, sessionToken, file.id);
              const isPhoto = file.media_type === "photo";
              const isDeleting = deletingAttachmentId === file.id;

              return (
                <li
                  key={file.id}
                  className="flex min-h-[44px] items-center gap-3 rounded-lg border border-gray-200 bg-optimal-field px-3 py-2.5"
                >
                  <a
                    href={viewUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex min-w-0 flex-1 items-center gap-3 active:opacity-80"
                  >
                    {isPhoto ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={viewUrl}
                        alt={file.file_name}
                        className="size-12 shrink-0 rounded-md border border-black/10 bg-white object-cover"
                      />
                    ) : (
                      <span className="flex size-12 shrink-0 items-center justify-center rounded-md border border-black/10 bg-white text-lg text-optimal-field-text">
                        ▶
                      </span>
                    )}
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-medium text-optimal-field-text">
                        {isPhoto ? "Photo" : file.media_type === "video" ? "Video" : "File"}
                      </span>
                      <span className="block truncate text-xs text-optimal-muted">{file.file_name}</span>
                    </span>
                  </a>
                  <button
                    type="button"
                    className="min-h-[44px] shrink-0 px-1 text-xs font-semibold text-red-500 active:opacity-70 disabled:opacity-50"
                    disabled={isDeleting}
                    onClick={() => void onDeleteAttachment(workIndex, file.id)}
                  >
                    {isDeleting ? "Removing…" : "Remove"}
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
