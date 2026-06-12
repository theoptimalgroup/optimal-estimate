"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
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
  EworksTableShell,
  EworksTextarea,
  cn,
  eworksInputClass,
} from "@/components/eworks-ui";
import { ProductCombobox } from "@/components/product-combobox";
import { fetchProduct } from "@/lib/products-api";
import {
  attachmentMediaContext,
  formatAttachmentProductLine,
  formatAttachmentScopeLine,
} from "@/lib/attachment-context";
import { cleanRichTextForTextarea } from "@/lib/html-text";
import type { AttachmentMeta, MaterialSupplierFormValues, ProductOption, QuestionnaireFormValues, WorkBlockFormValues } from "@/lib/eworks-calculate-schema";
import { defaultMaterialSuppliers, formatCurrency, formatDurationParts, formatSupplierDisplayName, grandTotalMaterials, computeProductTotalPrice, calculateWorkCcTotal, calculateWorkParkingTotal, shelfMaterialLineTotal, shelfMaterialsTotal, supplierMaterialsSubtotal, supplierMaterialsTotal, workBlockHasProductContext, workCcChargeableDays, workDurationComponents } from "@/lib/eworks-calculate-schema";
import { VoiceDictationButton } from "@/components/voice/VoiceDictationButton";
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
  onProductSelect: (product: ProductOption | null) => void;
  onAddCustomScope?: () => void;
  customScopeDraft?: boolean;
  onConfirmCustomScope?: (title: string, description?: string) => void;
  onCancelCustomScopeDraft?: () => void;
  changingProduct: boolean;
  onChangeProductClick: () => void;
  quoteCharges?: Pick<
    QuestionnaireFormValues,
    | "parking_required"
    | "parking_type"
    | "parking_fixed_amount"
    | "parking_rate_per_hour"
    | "parking_vehicles"
    | "congestion_required"
    | "congestion_amount"
  >;
};

const WORK_TABS = ["Product", "Scope", "Materials", "Labour"] as const;
type WorkTabId = (typeof WORK_TABS)[number];

function formatAttachmentUploadedBy(file: AttachmentMeta): string | null {
  const name = file.uploaded_by_name?.trim();
  const when = file.uploaded_at
    ? new Date(file.uploaded_at).toLocaleString("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      })
    : null;
  if (name && when) return `Uploaded by ${name} · ${when}`;
  if (name) return `Uploaded by ${name}`;
  if (when) return `Uploaded ${when}`;
  return null;
}


function workPanelTestId(tab: WorkTabId, workIndex: number) {
  return `work-panel-${tab.toLowerCase()}-${workIndex}`;
}

function workTabTestId(tab: WorkTabId, workIndex: number) {
  return `work-tab-${tab.toLowerCase()}-${workIndex}`;
}

function tabTestId(tab: WorkTabId) {
  return `tab-${tab.toLowerCase()}`;
}

function fieldPath<T extends keyof WorkBlockFormValues>(workIndex: number, field: T) {
  return `works.${workIndex}.${field}` as FieldPath<QuestionnaireFormValues>;
}

function WorkTabBar({
  workIndex,
  activeTab,
  onChange,
}: {
  workIndex: number;
  activeTab: WorkTabId;
  onChange: (tab: WorkTabId) => void;
}) {
  return (
    <div
      role="tablist"
      aria-label={`Sections for item ${workIndex + 1}`}
      className="flex flex-wrap gap-1 border-b border-slate-200 pb-2"
      data-testid={`work-tabs-${workIndex}`}
    >
      {WORK_TABS.map((tab) => (
        <button
          key={tab}
          type="button"
          role="tab"
          aria-selected={activeTab === tab}
          data-testid={workTabTestId(tab, workIndex)}
          className={cn(
            "rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/30",
            activeTab === tab
              ? "border-blue-200 bg-blue-50 text-blue-700"
              : "border-transparent text-slate-600 hover:bg-slate-50",
          )}
          onClick={() => onChange(tab)}
        >
          <span data-testid={tabTestId(tab)} className="contents">
            {tab}
          </span>
        </button>
      ))}
    </div>
  );
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
  "lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_4.5rem] lg:items-center lg:gap-3 lg:px-3 lg:py-2.5";

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
      <div className="hidden bg-slate-100 px-3 py-2.5 text-left text-[11px] font-bold uppercase tracking-wide text-slate-700 lg:grid lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_4.5rem] lg:gap-3">
        <span>{labelColumn}</span>
        <span>Quantity</span>
        <span>Cost per item</span>
        <span>Line total</span>
        <span />
      </div>
      <div className="divide-y divide-black/10">
        {rows.map((row, index) => (
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
                  Cost per item
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
              <div className="min-w-0">
                <span className="mb-1.5 block text-[11px] font-bold uppercase tracking-wide text-black lg:hidden">
                  Line total
                </span>
                <p
                  className="min-h-[44px] rounded-lg bg-slate-50 px-3 py-2.5 text-sm font-semibold tabular-nums text-slate-900 lg:min-h-[40px] lg:py-2"
                  data-testid={`shelf-line-total-${workIndex}-${index}`}
                >
                  {formatCurrency(shelfMaterialLineTotal(row))}
                </p>
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
  onRemoveSupplier: (supplierIndex: number) => void;
  onAddLink: (supplierIndex: number) => void;
  onRemoveLink: (supplierIndex: number, linkIndex: number) => void;
  onLinkChange: (supplierIndex: number, linkIndex: number, value: string) => void;
};

function supplierHeaderName(supplier: MaterialSupplierFormValues): string {
  const name = supplier.supplier_name?.trim();
  return name ? name : "Supplier";
}

type MaterialsSubsectionId = "supplier" | "shelf";

function MaterialsSubsectionAccordion({
  title,
  testId,
  expanded,
  onToggle,
  actionLabel,
  onAction,
  actionTestId,
  children,
}: {
  title: string;
  testId: string;
  expanded: boolean;
  onToggle: () => void;
  actionLabel?: string;
  onAction?: () => void;
  actionTestId?: string;
  children: ReactNode;
}) {
  return (
    <section
      className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm"
      data-testid={testId}
    >
      <div className="flex w-full items-center">
        <button
          type="button"
          className="flex min-w-0 flex-1 items-center gap-3 px-3 py-2.5 text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/30"
          onClick={onToggle}
          aria-expanded={expanded}
          data-testid={`${testId}-toggle`}
        >
          <span
            className={cn("shrink-0 text-slate-500 transition-transform duration-200", expanded && "rotate-180")}
            aria-hidden
          >
            ▾
          </span>
          <span className="min-w-0 flex-1 truncate text-sm font-medium text-slate-900">{title}</span>
        </button>
        {actionLabel && onAction ? (
          <button
            type="button"
            className="shrink-0 px-3 py-2.5 text-xs font-medium text-blue-600 hover:text-blue-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/30"
            onClick={(event) => {
              event.stopPropagation();
              onAction();
            }}
            data-testid={actionTestId}
          >
            {actionLabel}
          </button>
        ) : null}
      </div>
      {expanded ? <div className="space-y-3 border-t border-slate-100 p-3">{children}</div> : null}
    </section>
  );
}

function MaterialsSummaryRow({
  label,
  amount,
  testId,
  emphasized = false,
}: {
  label: string;
  amount: number;
  testId: string;
  emphasized?: boolean;
}) {
  return (
    <div
      className={cn(
        "flex items-center justify-between gap-3 rounded-lg px-3 py-2.5",
        emphasized ? "border border-slate-200 bg-slate-50" : "bg-slate-50",
      )}
      data-testid={testId}
    >
      <span className={cn("text-sm", emphasized ? "font-semibold text-slate-900" : "font-medium text-slate-700")}>
        {label}
      </span>
      <span className={cn("text-sm tabular-nums", emphasized ? "font-bold text-slate-900" : "font-semibold text-slate-900")}>
        {formatCurrency(amount)}
      </span>
    </div>
  );
}

function SupplierMaterialsSection({
  workIndex,
  suppliers,
  register,
  control,
  onRemoveSupplier,
  onAddLink,
  onRemoveLink,
  onLinkChange,
}: SupplierMaterialsSectionProps) {
  const [expandedSuppliers, setExpandedSuppliers] = useState<Set<number>>(() => new Set());

  const toggleSupplier = (supplierIndex: number) => {
    setExpandedSuppliers((current) => {
      const next = new Set(current);
      if (next.has(supplierIndex)) {
        next.delete(supplierIndex);
      } else {
        next.add(supplierIndex);
      }
      return next;
    });
  };

  const handleRemoveSupplier = (supplierIndex: number) => {
    onRemoveSupplier(supplierIndex);
    setExpandedSuppliers((current) => {
      const next = new Set<number>();
      for (const index of current) {
        if (index === supplierIndex) continue;
        next.add(index > supplierIndex ? index - 1 : index);
      }
      return next;
    });
  };

  return (
    <div className="space-y-3">
      {suppliers.map((supplier, supplierIndex) => {
        const supplierFallback = `Supplier ${supplierIndex + 1}`;
        const isExpanded = expandedSuppliers.has(supplierIndex);
        const subtotal = supplierMaterialsTotal(supplier);
        const headerName = supplierHeaderName(supplier);
        const linkCount = supplier.links.length;

        return (
          <div
            key={supplierIndex}
            className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm"
            data-testid={`supplier-card-${supplierIndex}`}
          >
            <div className="flex items-center gap-2 border-b border-slate-100 px-3 py-2.5">
              <button
                type="button"
                className="flex min-w-0 flex-1 items-center gap-3 text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/30"
                onClick={() => toggleSupplier(supplierIndex)}
                aria-expanded={isExpanded}
                data-testid={`supplier-toggle-${supplierIndex}`}
              >
                <span
                  className={cn(
                    "shrink-0 text-slate-500 transition-transform duration-200",
                    isExpanded && "rotate-180",
                  )}
                  aria-hidden
                >
                  ▾
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-slate-900">{headerName}</p>
                  <p className="text-xs text-slate-500">
                    {linkCount} {linkCount === 1 ? "link" : "links"}
                  </p>
                </div>
                <span
                  className="shrink-0 text-sm font-semibold tabular-nums text-slate-900"
                  data-testid={`supplier-subtotal-${supplierIndex}`}
                >
                  {formatCurrency(subtotal)}
                </span>
              </button>
              <button
                type="button"
                className="shrink-0 rounded-lg px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-50 disabled:opacity-40"
                disabled={suppliers.length <= 1}
                onClick={() => handleRemoveSupplier(supplierIndex)}
                aria-label={`Remove ${formatSupplierDisplayName(supplier, supplierIndex)}`}
                data-testid={`supplier-remove-${supplierIndex}`}
              >
                Remove
              </button>
            </div>

            {isExpanded ? (
              <div className="space-y-3 border-t border-slate-100 p-3">
                <EworksLabel className="text-sm font-medium">
                  Supplier name
                  <EworksInput
                    className="min-h-[44px] rounded-lg border-slate-300 bg-white text-base lg:min-h-[40px] lg:text-sm"
                    placeholder={supplierFallback}
                    data-testid={`supplier-name-${supplierIndex}`}
                    {...register(`works.${workIndex}.materials_to_order.${supplierIndex}.supplier_name`)}
                  />
                </EworksLabel>
                  <EworksTableShell>
                    <div className="hidden bg-slate-100 px-3 py-2.5 text-left text-[11px] font-bold uppercase tracking-wide text-slate-700 lg:grid lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)_4.5rem] lg:gap-3">
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
                      <span className="text-xs font-medium text-slate-500">Supplier total</span>
                      <p
                        className="mt-1.5 rounded-lg bg-slate-50 px-3.5 py-2.5 text-sm font-semibold tabular-nums text-slate-900"
                        data-testid={`supplier-total-${supplierIndex}`}
                      >
                        {formatCurrency(subtotal)}
                      </p>
                    </div>
                  </div>
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
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
  sessionId,
  sessionToken,
  onUploadFiles,
  onDeleteAttachment,
  uploading,
  deletingAttachmentId,
  onProductSelect,
  onAddCustomScope,
  customScopeDraft = false,
  onConfirmCustomScope,
  onCancelCustomScopeDraft,
  changingProduct,
  onChangeProductClick,
  quoteCharges,
}: Props) {
  const values = watch(`works.${workIndex}`);
  const workDuration = workDurationComponents(values);
  const workParkingTotal =
    quoteCharges?.parking_required ? calculateWorkParkingTotal(values, quoteCharges) : 0;
  const workCcTotal = quoteCharges?.congestion_required ? calculateWorkCcTotal(values, quoteCharges) : 0;
  const workCcDays = quoteCharges?.congestion_required ? workCcChargeableDays(values) : 0;
  const showWorkChargeSummary =
    quoteCharges != null &&
    (quoteCharges.parking_required || quoteCharges.congestion_required) &&
    values.engineers_required;
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
  const [draftTitle, setDraftTitle] = useState("");
  const [draftDescription, setDraftDescription] = useState("");
  const hasProductContext = workBlockHasProductContext(values);
  const [activeTab, setActiveTab] = useState<WorkTabId>(() =>
    hasProductContext ? "Scope" : "Product",
  );
  const [expandedMaterialsSections, setExpandedMaterialsSections] = useState<Set<MaterialsSubsectionId>>(
    () => new Set(),
  );
  const prevProductIdRef = useRef<number | null>(values.selected_product_id ?? null);

  useEffect(() => {
    if (customScopeDraft) {
      setDraftTitle("");
      setDraftDescription("");
    }
  }, [customScopeDraft]);

  useEffect(() => {
    const current = values.selected_product_id ?? null;
    if (current != null && prevProductIdRef.current == null) {
      setActiveTab("Scope");
    }
    prevProductIdRef.current = current;
  }, [values.selected_product_id]);

  const hasSelectedProduct = values.selected_product_id != null;
  const isCustomScope = Boolean(values.is_custom_scope);
  const hasSharedProductName = !isCustomScope && Boolean(values.product_name?.trim());
  const customScopeTitle = values.custom_title?.trim() ?? "";
  const showProductCombobox =
    changingProduct || customScopeDraft || (!hasProductContext && !isCustomScope);
  const showConfirmedCustom = isCustomScope && !changingProduct && !customScopeDraft;
  const showConfirmedProduct =
    (hasSelectedProduct || hasSharedProductName) && !isCustomScope && !changingProduct && !customScopeDraft;
  const scopeText = values.scope?.trim() ?? "";
  const engineerNotes = values.other_notes?.trim() ?? "";
  const engineerFindings = values.findings?.trim() ?? "";

  const handleResetScopeFromProduct = async () => {
    if (values.selected_product_id == null) return;
    setResettingScope(true);
    setResetScopeError(null);
    try {
      const product = await fetchProduct(values.selected_product_id);
      const scope = cleanRichTextForTextarea(product.scope_of_work);
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
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setValue(`works.${workIndex}.${table}.${index}.quantity` as any, 0, { shouldValidate: true });
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
    setExpandedMaterialsSections((current) => new Set([...current, "supplier"]));
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    setValue(`works.${workIndex}.materials_to_order` as any, [...suppliers, ...defaultMaterialSuppliers()] as any, {
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
    setExpandedMaterialsSections((current) => new Set([...current, "shelf"]));
    setValue(`works.${workIndex}.shelf_materials_rows`, [...shelfRows, { link: "", quantity: 0, cost: 0 }], {
      shouldValidate: true,
    });
  };

  const toggleMaterialsSection = (section: MaterialsSubsectionId) => {
    setExpandedMaterialsSections((current) => {
      const next = new Set(current);
      if (next.has(section)) {
        next.delete(section);
      } else {
        next.add(section);
      }
      return next;
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

  const appendScopeText = useCallback(
    (text: string) => {
      const current = values.scope?.trim() ?? "";
      const next = current ? `${current}\n\n${text}` : text;
      setRewordError(null);
      setValue(fieldPath(workIndex, "scope"), next, { shouldDirty: true, shouldValidate: true });
      setValue(fieldPath(workIndex, "scope_from_product"), false, { shouldValidate: false });
    },
    [setValue, values.scope, workIndex],
  );

  const appendOtherNotes = useCallback(
    (text: string) => {
      const current = values.other_notes?.trim() ?? "";
      const next = current ? `${current}\n\n${text}` : text;
      setValue(fieldPath(workIndex, "other_notes"), next, { shouldDirty: true, shouldValidate: true });
    },
    [setValue, values.other_notes, workIndex],
  );

  const appendDraftDescription = useCallback((text: string) => {
    setDraftDescription((current) => {
      const trimmed = current.trim();
      return trimmed ? `${trimmed}\n\n${text}` : text;
    });
  }, []);

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

  const handleContinueCustomScope = () => {
    const title = draftTitle.trim();
    if (!title) return;
    onConfirmCustomScope?.(title, draftDescription.trim() || undefined);
    setActiveTab("Scope");
  };

  const handleCancelCustomScopeDraft = () => {
    setDraftTitle("");
    setDraftDescription("");
    onCancelCustomScopeDraft?.();
  };

  return (
    <div className="space-y-4">
      <WorkTabBar workIndex={workIndex} activeTab={activeTab} onChange={setActiveTab} />

      {activeTab === "Product" && (
        <div className="space-y-4 pt-2" role="tabpanel" data-testid={workPanelTestId("Product", workIndex)}>
          {showConfirmedCustom ? (
            <div className="space-y-3" data-testid={`custom-scope-summary-${workIndex}`}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-slate-900">Custom: {customScopeTitle}</p>
                  <p className="mt-1 text-xs text-slate-500">Custom scope (not in catalog)</p>
                </div>
                <button
                  type="button"
                  className="text-sm font-medium text-blue-600 hover:text-blue-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/30"
                  onClick={onChangeProductClick}
                  data-testid={`change-product-${workIndex}`}
                >
                  Change
                </button>
              </div>
            </div>
          ) : null}
          {showConfirmedProduct ? (
            <div className="space-y-3">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-slate-900">{values.product_name}</p>
                  {values.product_code ? (
                    <p className="mt-1 text-xs text-slate-500">{values.product_code}</p>
                  ) : null}
                </div>
                <button
                  type="button"
                  className="text-sm font-medium text-blue-600 hover:text-blue-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/30"
                  onClick={onChangeProductClick}
                  data-testid={`change-product-${workIndex}`}
                >
                  Change product
                </button>
              </div>
              <EworksLabel className="flex-row items-center gap-2 space-y-0">
                <span className="shrink-0 text-xs font-medium text-slate-500">Qty</span>
                <Controller
                  name={fieldPath(workIndex, "product_quantity")}
                  control={control}
                  render={({ field }) => (
                    <NumericInput field={field} className="w-20 min-h-[36px] text-sm" />
                  )}
                />
              </EworksLabel>
            </div>
          ) : null}
          {showProductCombobox ? (
            <div className="space-y-4">
              <ProductCombobox
                selectedProductId={values.selected_product_id}
                productName={values.product_name}
                productCode={values.product_code}
                customScopeLabel={
                  customScopeDraft
                    ? draftTitle.trim() || null
                    : isCustomScope
                      ? customScopeTitle || null
                      : null
                }
                onSelect={onProductSelect}
                onAddCustomScope={onAddCustomScope}
              />
              {customScopeDraft ? (
                <div className="space-y-4 rounded-lg border border-blue-100 bg-blue-50/40 p-4" data-testid={`custom-scope-draft-${workIndex}`}>
                  <EworksLabel>
                    Custom product / scope title
                    <EworksInput
                      value={draftTitle}
                      onChange={(event) => setDraftTitle(event.target.value)}
                      data-testid="custom-scope-title-input"
                    />
                  </EworksLabel>
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <EworksLabel className="space-y-0 text-sm font-medium text-slate-900">
                        Description (optional)
                      </EworksLabel>
                      <VoiceDictationButton
                        key={`voice-client-description-${workIndex}`}
                        context="client_description"
                        mode="append"
                        workIndex={workIndex}
                        onCleanText={appendDraftDescription}
                      />
                    </div>
                    <EworksTextarea
                      rows={3}
                      value={draftDescription}
                      onChange={(event) => setDraftDescription(event.target.value)}
                      data-testid="custom-scope-description-input"
                    />
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <EworksButton
                      type="button"
                      variant="secondary"
                      className="min-h-[40px]"
                      onClick={handleCancelCustomScopeDraft}
                      data-testid="custom-scope-cancel-button"
                    >
                      Cancel
                    </EworksButton>
                    <EworksButton
                      type="button"
                      className="min-h-[40px]"
                      disabled={!draftTitle.trim()}
                      onClick={handleContinueCustomScope}
                      data-testid="custom-scope-continue-button"
                    >
                      Continue to Scope
                    </EworksButton>
                  </div>
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      )}

      {activeTab === "Scope" && (
        <div className="space-y-3 pt-2" role="tabpanel" data-testid={workPanelTestId("Scope", workIndex)}>
          {(engineerNotes || engineerFindings) && (
            <div className="space-y-2 rounded-lg border border-blue-200 bg-blue-50/80 p-3">
              {engineerFindings ? (
                <pre className="whitespace-pre-wrap text-xs text-blue-950">{engineerFindings}</pre>
              ) : null}
              {engineerNotes ? (
                <pre className="whitespace-pre-wrap text-xs text-blue-950">{engineerNotes}</pre>
              ) : null}
            </div>
          )}
          <div className="flex flex-wrap items-center justify-between gap-2">
            <EworksLabel className="space-y-0 text-sm font-medium text-slate-900">Scope of Works</EworksLabel>
            <div className="flex flex-wrap items-center gap-2">
              <VoiceDictationButton
                key={`voice-scope-${workIndex}`}
                context="scope_of_work"
                mode="append"
                disabled={rewordingScope}
                label="Dictate Scope"
                fieldLabel="Scope of Works"
                workIndex={workIndex}
                onCleanText={appendScopeText}
              />
              {hasSelectedProduct ? (
                <EworksButton
                  type="button"
                  variant="secondary"
                  className="min-h-[36px] px-3 text-xs"
                  disabled={resettingScope}
                  onClick={() => void handleResetScopeFromProduct()}
                  data-testid={`reset-scope-work-${workIndex}`}
                >
                  {resettingScope ? "Resetting…" : "Reset from product"}
                </EworksButton>
              ) : null}
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
          {resetScopeError ? <EworksFieldError message={resetScopeError} /> : null}
          <Controller
            name={fieldPath(workIndex, "scope")}
            control={control}
            render={({ field, fieldState }) => (
              <>
                <EworksTextarea
                  rows={6}
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
                  className="min-h-[160px] resize-y"
                  data-testid={`work-scope-${workIndex}`}
                />
                <EworksFieldError message={rewordError ?? fieldState.error?.message} />
              </>
            )}
          />
          <div className="space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <EworksLabel className="space-y-0 text-sm font-medium text-slate-900">Notes</EworksLabel>
              <VoiceDictationButton
                key={`voice-notes-${workIndex}`}
                context="internal_notes"
                mode="append"
                label="Dictate Notes"
                fieldLabel="Notes"
                workIndex={workIndex}
                onCleanText={appendOtherNotes}
              />
            </div>
            <EworksTextarea rows={3} {...register(fieldPath(workIndex, "other_notes"))} />
          </div>
          <div className="space-y-3">
            <p className="text-sm font-medium text-slate-900">Photos &amp; Videos</p>
            {attachments.length > 0 && (() => {
              const firstContext = attachmentMediaContext(attachments[0], values);
              return (
                <>
                  {firstContext.productLine ? (
                    <p className="text-xs text-slate-600" data-testid={`attachment-product-context-${workIndex}`}>
                      {firstContext.productLine}
                    </p>
                  ) : null}
                  {firstContext.scopeLine ? (
                    <p className="text-xs text-slate-600" data-testid={`attachment-scope-context-${workIndex}`}>
                      {firstContext.scopeLine}
                    </p>
                  ) : null}
                </>
              );
            })()}
            <input ref={photoInputRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={handleAttachmentChange} disabled={uploading} />
            <input ref={videoInputRef} type="file" accept="video/*" capture="environment" className="hidden" onChange={handleAttachmentChange} disabled={uploading} />
            <input ref={fileInputRef} type="file" accept="image/*,video/*" multiple className="hidden" onChange={handleAttachmentChange} disabled={uploading} />
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
            {uploading && <p className="text-xs font-medium text-blue-600 animate-pulse-soft">Uploading…</p>}
            {attachments.length > 0 && (
              <ul className="space-y-2">
                {attachments.map((file) => {
                  const viewUrl = getAttachmentUrl(sessionId, sessionToken, file.id);
                  const isPhoto = file.media_type === "photo";
                  const isDeleting = deletingAttachmentId === file.id;
                  const mediaContext = attachmentMediaContext(file, values);
                  const showPerFileContext =
                    attachments.length > 1 &&
                    (mediaContext.productLine !== formatAttachmentProductLine(attachments[0], values) ||
                      mediaContext.scopeLine !== formatAttachmentScopeLine(attachments[0]));
                  return (
                    <li key={file.id} className="flex min-h-[44px] items-center gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2.5">
                      <a href={viewUrl} target="_blank" rel="noopener noreferrer" className="flex min-w-0 flex-1 items-center gap-3 active:opacity-80">
                        {isPhoto ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={viewUrl} alt={file.file_name} className="size-12 shrink-0 rounded-md border border-black/10 bg-white object-cover" />
                        ) : (
                          <span className="flex size-12 shrink-0 items-center justify-center rounded-md border border-black/10 bg-white text-lg text-slate-900">▶</span>
                        )}
                        <span className="min-w-0">
                          <span className="block truncate text-sm font-medium text-slate-900">{file.file_name}</span>
                          {showPerFileContext && mediaContext.productLine ? (
                            <span className="block truncate text-xs text-slate-600">{mediaContext.productLine}</span>
                          ) : null}
                          {showPerFileContext && mediaContext.scopeLine ? (
                            <span className="block truncate text-xs text-slate-600">{mediaContext.scopeLine}</span>
                          ) : null}
                          {(() => {
                            const uploadedBy = formatAttachmentUploadedBy(file);
                            return uploadedBy ? (
                              <span className="block truncate text-xs text-slate-500">{uploadedBy}</span>
                            ) : null;
                          })()}
                        </span>
                      </a>
                      <button type="button" className="min-h-[44px] shrink-0 px-1 text-xs font-semibold text-red-500 active:opacity-70 disabled:opacity-50" disabled={isDeleting} onClick={() => void onDeleteAttachment(workIndex, file.id)}>
                        {isDeleting ? "Removing…" : "Remove"}
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>
      )}

      {activeTab === "Materials" && (
        <div className="space-y-4 pt-2" role="tabpanel" data-testid={workPanelTestId("Materials", workIndex)}>
          <MaterialsSubsectionAccordion
            title="Supplier materials"
            testId={`supplier-materials-section-${workIndex}`}
            expanded={expandedMaterialsSections.has("supplier")}
            onToggle={() => toggleMaterialsSection("supplier")}
            actionLabel="+ Add supplier"
            onAction={addSupplier}
            actionTestId={`supplier-materials-add-${workIndex}`}
          >
            <SupplierMaterialsSection
              workIndex={workIndex}
              suppliers={suppliers}
              register={register}
              control={control}
              onRemoveSupplier={removeSupplier}
              onAddLink={addSupplierLink}
              onRemoveLink={removeSupplierLink}
              onLinkChange={clearSupplierLinkQuantity}
            />
            <EworksFieldError message={workErrors?.materials_to_order?.message as string | undefined} />
          </MaterialsSubsectionAccordion>

          <MaterialsSubsectionAccordion
            title="Shelf materials"
            testId={`shelf-materials-section-${workIndex}`}
            expanded={expandedMaterialsSections.has("shelf")}
            onToggle={() => toggleMaterialsSection("shelf")}
            actionLabel="+ Add material"
            onAction={addShelfRow}
            actionTestId={`shelf-materials-add-${workIndex}`}
          >
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
            <EworksFieldError message={workErrors?.shelf_materials_rows?.message as string | undefined} />
          </MaterialsSubsectionAccordion>

          <div className="space-y-2 border-t border-slate-200 pt-3" data-testid={`materials-summary-${workIndex}`}>
            <MaterialsSummaryRow
              label="Supplier Materials Subtotal"
              amount={supplierMaterialsSubtotal(suppliers)}
              testId={`supplier-materials-subtotal-${workIndex}`}
            />
            <MaterialsSummaryRow
              label="Off-shelf materials total"
              amount={shelfMaterialsTotal(shelfRows)}
              testId={`shelf-materials-subtotal-${workIndex}`}
            />
            <MaterialsSummaryRow
              label="Grand Total Materials"
              amount={grandTotalMaterials(values)}
              testId={`grand-total-materials-${workIndex}`}
              emphasized
            />
          </div>
        </div>
      )}

      {activeTab === "Labour" && (
        <div className="space-y-4 pt-2" role="tabpanel" data-testid={workPanelTestId("Labour", workIndex)}>
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
          <div className="space-y-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
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
                      if (!checked) clearLabour();
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
                        <NumericInput field={field} hasError={!!fieldState.error} placeholder="Required" />
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
                      if (event.target.value === "hours") clearLabour();
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
                          <NumericInput field={field} hasError={!!fieldState.error} placeholder="Required" />
                          <span className="shrink-0 text-sm text-slate-600">
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
            {showWorkChargeSummary && (
              <div
                className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700"
                data-testid={`work-charge-summary-${workIndex}`}
              >
                <p data-testid={`work-duration-${workIndex}`}>
                  Work duration: {formatDurationParts(workDuration.days, workDuration.hours)}
                </p>
                {quoteCharges?.parking_required ? (
                  <p data-testid={`work-parking-total-${workIndex}`}>Parking: {formatCurrency(workParkingTotal)}</p>
                ) : null}
                {quoteCharges?.congestion_required ? (
                  <p data-testid={`work-cc-total-${workIndex}`}>
                    CC: {formatCurrency(workCcTotal)} ({workCcDays} chargeable day{workCcDays === 1 ? "" : "s"})
                  </p>
                ) : null}
              </div>
            )}
          </div>
          {showLabour && (
            <div className="space-y-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
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
                      onChange={(event) => field.onChange(event.target.checked)}
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
                          <NumericInput field={field} hasError={!!fieldState.error} placeholder="Required" />
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
                            <NumericInput field={field} hasError={!!fieldState.error} placeholder="Required" />
                            <span className="shrink-0 text-sm text-slate-600">
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
        </div>
      )}
    </div>
  );
}
