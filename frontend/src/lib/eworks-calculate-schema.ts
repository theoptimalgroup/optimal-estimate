import { z } from "zod";
import type { MaterialSupplier, Step2Snapshot, WorkBlockSnapshot } from "@/lib/eworks-session";
import { cleanRichTextForTextarea, stripHtmlFromLabel } from "@/lib/html-text";
import { formatProductLabel as formatProductLabelFromStrings } from "@/lib/work-label";

export const materialOrderRowSchema = z
  .object({
    link: z.string().optional(),
    quantity: z.number({ error: "Enter quantity" }).min(0, "Quantity must be 0 or greater"),
    cost: z.number({ error: "Enter cost" }).min(0, "Cost must be 0 or greater"),
  })
  .superRefine((row, ctx) => {
    const link = (row.link ?? "").trim();
    if (link && row.quantity <= 0) {
      ctx.addIssue({
        code: "custom",
        message: "Quantity must be greater than 0",
        path: ["quantity"],
      });
    }
  });

export const materialLinkRowSchema = materialOrderRowSchema;

export const materialSupplierSchema = z.object({
  links: z.array(materialLinkRowSchema).min(1, "Add at least one link"),
  delivery_charge: z.number({ error: "Enter delivery charge" }).min(0, "Delivery must be 0 or greater"),
  supplier_name: z.string().optional(),
});

export const attachmentMetaSchema = z.object({
  id: z.string(),
  file_name: z.string(),
  content_type: z.string(),
  size: z.number(),
  media_type: z.string(),
  stored_name: z.string(),
  uploaded_by_name: z.string().nullable().optional(),
  uploaded_by_email: z.string().nullable().optional(),
  uploaded_at: z.string().nullable().optional(),
  work_index: z.number().nullable().optional(),
  product_id: z.number().nullable().optional(),
  product_name: z.string().nullable().optional(),
  is_custom_scope: z.boolean().nullable().optional(),
  custom_scope_title: z.string().nullable().optional(),
  scope_snapshot: z.string().nullable().optional(),
  work_block_label: z.string().nullable().optional(),
});

export type TimeUnit = "hours" | "days";

function requiredNumber(label: string, min: number) {
  return z
    .number({ error: `Enter ${label}` })
    .min(min, min >= 1 ? `${label} must be at least ${min}` : `${label} is required`);
}

function normalizeMaterialRow(row: { link?: string | null; quantity?: unknown; cost?: unknown }) {
  const quantity = Number(row.quantity);
  const cost = Number(row.cost);
  const link = row.link ?? "";
  const hasLink = link.trim().length > 0;
  return {
    link,
    quantity: hasLink
      ? Number.isFinite(quantity) && quantity > 0
        ? quantity
        : 1
      : 0,
    cost: Number.isFinite(cost) && cost >= 0 ? cost : 0,
  };
}

function normalizeMaterialLinkRow(row: { link?: string | null; quantity?: unknown; cost?: unknown }) {
  return normalizeMaterialRow(row);
}

function normalizeMaterialSupplier(supplier: {
  links?: Array<{ link?: string | null; quantity?: unknown; cost?: unknown }>;
  delivery_charge?: unknown;
  supplier_name?: string | null;
}): MaterialSupplier {
  const links =
    supplier.links && supplier.links.length > 0
      ? supplier.links.map(normalizeMaterialLinkRow)
      : [{ link: "", quantity: 0, cost: 0 }];
  const delivery = Number(supplier.delivery_charge);
  const supplierName = toStringValue(supplier.supplier_name).trim();
  return {
    links,
    delivery_charge: Number.isFinite(delivery) && delivery >= 0 ? delivery : 0,
    supplier_name: supplierName,
  };
}

function isLegacyMaterialRow(row: unknown): boolean {
  return typeof row === "object" && row !== null && !("links" in row);
}

export function migrateLegacyMaterialRows(rows: unknown): MaterialSupplier[] {
  if (!Array.isArray(rows) || rows.length === 0) {
    return defaultMaterialSuppliers();
  }
  if (!isLegacyMaterialRow(rows[0])) {
    return rows.map((row) => normalizeMaterialSupplier(row as MaterialSupplier));
  }
  const links = (rows as Array<{ link?: string | null; quantity?: unknown; cost?: unknown }>).map((row) => {
    const normalized = normalizeMaterialRow(row);
    const qty = normalized.quantity > 0 ? normalized.quantity : 1;
    const costPerItem = normalized.cost > 0 ? normalized.cost / qty : 0;
    return { link: normalized.link, quantity: normalized.quantity, cost: costPerItem };
  });
  return [
    normalizeMaterialSupplier({
      links: links.length > 0 ? links : [{ link: "", quantity: 0, cost: 0 }],
      delivery_charge: 0,
    }),
  ];
}

export function defaultMaterialSuppliers(): MaterialSupplier[] {
  return [{ links: [{ link: "", quantity: 0, cost: 0 }], delivery_charge: 0, supplier_name: "" }];
}

export function formatSupplierDisplayName(
  supplier: { supplier_name?: string | null },
  index: number,
): string {
  const name = supplier.supplier_name?.trim();
  return name ? name : `Supplier ${index + 1}`;
}

export function supplierMaterialsTotal(supplier: MaterialSupplier): number {
  const linksTotal = supplier.links.reduce((sum, row) => {
    const qty = Number(row.quantity) || 0;
    const cost = Number(row.cost) || 0;
    return sum + qty * cost;
  }, 0);
  return linksTotal + (Number(supplier.delivery_charge) || 0);
}

export function formatCurrency(amount: number): string {
  return `£${amount.toFixed(2)}`;
}

export function supplierMaterialsSubtotal(suppliers: MaterialSupplier[] | undefined): number {
  return (suppliers ?? []).reduce((sum, supplier) => sum + supplierMaterialsTotal(supplier), 0);
}

export function shelfMaterialsTotal(rows: WorkBlockFormValues["shelf_materials_rows"] | undefined): number {
  return (rows ?? []).reduce((sum, row) => {
    const qty = Number(row.quantity) || 0;
    const cost = Number(row.cost) || 0;
    return sum + qty * cost;
  }, 0);
}

export function grandTotalMaterials(
  work: Pick<WorkBlockFormValues, "materials_to_order" | "shelf_materials_rows">,
): number {
  return supplierMaterialsSubtotal(work.materials_to_order) + shelfMaterialsTotal(work.shelf_materials_rows);
}

export function workMaterialsSummary(
  work: Pick<WorkBlockFormValues, "materials_to_order" | "shelf_materials_rows">,
) {
  const suppliers = work.materials_to_order ?? [];
  const orderTotal = suppliers.reduce((sum, supplier) => sum + supplierMaterialsTotal(supplier), 0);
  const shelfTotal = shelfMaterialsTotal(work.shelf_materials_rows);
  const total = orderTotal + shelfTotal;
  const hasSupplierContent = suppliers.some(
    (supplier) =>
      Boolean(supplier.supplier_name?.trim()) ||
      supplier.links.some((row) => Boolean(row.link?.trim()) || Number(row.cost) > 0),
  );
  const hasShelfContent = (work.shelf_materials_rows ?? []).some(
    (row) => Boolean(row.link?.trim()) || Number(row.cost) > 0,
  );

  return {
    supplierCount: suppliers.length,
    total,
    hasMaterials: total > 0 || hasSupplierContent || hasShelfContent,
  };
}

function toNumericValue(value: unknown): number | undefined {
  if (value === "" || value === null || value === undefined) return undefined;
  if (typeof value === "number") return Number.isNaN(value) ? undefined : value;
  const parsed = Number(value);
  return Number.isNaN(parsed) ? undefined : parsed;
}

function toStringValue(value: unknown): string {
  if (typeof value === "string") return value;
  if (value == null) return "";
  return String(value);
}

/** Combine legacy split notes or step1 link fields into one parking/access notes string. */
function mergeParkingAccessNotes(
  parkingNotes?: string | null,
  accessNotes?: string | null,
): string {
  const parking = parkingNotes?.trim() ?? "";
  const access = accessNotes?.trim() ?? "";
  if (parking && access) {
    if (parking.includes(access) || access.includes(parking)) {
      return parking.length >= access.length ? parking : access;
    }
    return `${parking}\n${access}`;
  }
  return parking || access;
}

function normalizeWorkBlockValues(work: WorkBlockFormValues): WorkBlockFormValues {
  const engineersRequired = work.engineers_required !== false;
  return {
    ...work,
    scope: toStringValue(work.scope),
    selected_product_id: toNumericValue(work.selected_product_id) ?? null,
    is_custom_scope: Boolean(work.is_custom_scope),
    custom_title: toStringValue(work.custom_title),
    eworks_item_id: toNumericValue(work.eworks_item_id) ?? null,
    product_name: toStringValue(work.product_name),
    product_code: toStringValue(work.product_code),
    product_quantity: Math.max(0.01, toNumericValue(work.product_quantity) ?? 1),
    product_unit_price: toNumericValue(work.product_unit_price) ?? 0,
    product_total_price: computeProductTotalPrice(
      Math.max(0.01, toNumericValue(work.product_quantity) ?? 1),
      toNumericValue(work.product_unit_price) ?? 0,
    ),
    scope_from_product: Boolean(work.scope_from_product),
    skill_required: toStringValue(work.skill_required),
    best_engineer: toStringValue(work.best_engineer),
    subcontractors: toStringValue(work.subcontractors),
    other_notes: toStringValue(work.other_notes),
    findings: toStringValue(work.findings),
    materials_to_order: migrateLegacyMaterialRows(work.materials_to_order),
    shelf_materials_rows:
      work.shelf_materials_rows?.length > 0
        ? work.shelf_materials_rows.map(normalizeMaterialRow)
        : [{ link: "", quantity: 0, cost: 0 }],
    engineers_required: engineersRequired,
    labour_required: Boolean(work.labour_required),
    engineers_needed: engineersRequired ? (toNumericValue(work.engineers_needed) as number) : 0,
    engineer_time_unit: work.engineer_time_unit === "days" ? "days" : "hours",
    engineer_time_value: toNumericValue(work.engineer_time_value) as number,
    labour_needed: work.labour_required ? (toNumericValue(work.labour_needed) as number) : 0,
    labour_time_value: work.labour_required ? (toNumericValue(work.labour_time_value) as number) : 0,
    markup_value: Number.isFinite(Number(work.markup_value)) ? Number(work.markup_value) : 20,
  };
}

function validateWorkBlock(data: z.infer<typeof workBlockFieldsSchema>, ctx: z.RefinementCtx, pathPrefix = "") {
  const path = (field: string) => (pathPrefix ? `${pathPrefix}.${field}` : field);
  const hasProduct = workBlockHasProductContext(data);
  const isCustomScope = Boolean(data.is_custom_scope);

  if (!hasProduct) {
    ctx.addIssue({
      code: "custom",
      message: "Select a product or add custom scope",
      path: [path("selected_product_id")],
    });
  }

  if (isCustomScope) {
    if (!data.custom_title?.trim()) {
      ctx.addIssue({
        code: "custom",
        message: "Custom product/scope title is required",
        path: [path("custom_title")],
      });
    }
    if (!data.scope?.trim()) {
      ctx.addIssue({
        code: "custom",
        message: "Scope of works is required",
        path: [path("scope")],
      });
    }
  } else if (hasProduct && !isCustomScope && !data.scope?.trim()) {
    ctx.addIssue({
      code: "custom",
      message: "Scope of works is required",
      path: [path("scope")],
    });
  }

  if (!data.engineers_required) {
    ctx.addIssue({
      code: "custom",
      message: "Engineer needed is required",
      path: [path("engineers_required")],
    });
  }
  if (data.engineers_required) {
    const engineersNeeded = toNumericValue(data.engineers_needed);
    if (engineersNeeded === undefined) {
      ctx.addIssue({
        code: "custom",
        message: "Number of engineers is required",
        path: [path("engineers_needed")],
      });
    } else if (engineersNeeded < 1) {
      ctx.addIssue({
        code: "custom",
        message: "Number of engineers must be at least 1",
        path: [path("engineers_needed")],
      });
    }
    const duration = toNumericValue(data.engineer_time_value);
    if (duration === undefined) {
      ctx.addIssue({
        code: "custom",
        message: "Duration is required",
        path: [path("engineer_time_value")],
      });
    } else if (duration < 0.5) {
      ctx.addIssue({
        code: "custom",
        message: "Duration must be at least 0.5",
        path: [path("engineer_time_value")],
      });
    }
  }
  if (data.labour_required && data.engineers_required && data.engineer_time_unit === "days") {
    const labourNeeded = toNumericValue(data.labour_needed);
    if (labourNeeded === undefined) {
      ctx.addIssue({
        code: "custom",
        message: "Number of labour is required",
        path: [path("labour_needed")],
      });
    } else if (labourNeeded < 1) {
      ctx.addIssue({
        code: "custom",
        message: "Number of labour must be at least 1",
        path: [path("labour_needed")],
      });
    }
    const labourDuration = toNumericValue(data.labour_time_value);
    if (labourDuration === undefined) {
      ctx.addIssue({
        code: "custom",
        message: "Labour duration is required",
        path: [path("labour_time_value")],
      });
    } else if (labourDuration < 0.5) {
      ctx.addIssue({
        code: "custom",
        message: "Labour duration must be at least 0.5",
        path: [path("labour_time_value")],
      });
    }
  }
}

function validateQuoteCharges(data: z.infer<typeof quoteChargesFieldsSchema>, ctx: z.RefinementCtx) {
  if (data.parking_required && data.parking_type === "hourly") {
    if (!data.parking_hours || data.parking_hours <= 0) {
      ctx.addIssue({ code: "custom", message: "Parking hours required for hourly parking", path: ["parking_hours"] });
    }
    if (!data.parking_rate_per_hour || data.parking_rate_per_hour <= 0) {
      ctx.addIssue({
        code: "custom",
        message: "Parking rate required for hourly parking",
        path: ["parking_rate_per_hour"],
      });
    }
  }
  if (data.parking_required) {
    const vehicles = toNumericValue(data.parking_vehicles);
    if (vehicles === undefined || vehicles < 1 || !Number.isInteger(vehicles)) {
      ctx.addIssue({
        code: "custom",
        message: "Number of vehicles must be at least 1",
        path: ["parking_vehicles"],
      });
    }
  }
  const lat = toNumericValue(data.parking_latitude);
  const lng = toNumericValue(data.parking_longitude);
  if (lat !== undefined && lat !== null && (lat < -90 || lat > 90)) {
    ctx.addIssue({ code: "custom", message: "Latitude must be between -90 and 90", path: ["parking_latitude"] });
  }
  if (lng !== undefined && lng !== null && (lng < -180 || lng > 180)) {
    ctx.addIssue({ code: "custom", message: "Longitude must be between -180 and 180", path: ["parking_longitude"] });
  }
  if (data.other_charge > 0 && !data.other_charge_reason?.trim()) {
    ctx.addIssue({
      code: "custom",
      message: "Notes required when other charge is greater than 0",
      path: ["other_charge_reason"],
    });
  }
}

export const workBlockFieldsSchema = z.object({
  scope: z.string().optional(),
  selected_product_id: z.number().nullable().optional(),
  is_custom_scope: z.boolean().optional(),
  custom_title: z.string().optional(),
  eworks_item_id: z.number().nullable().optional(),
  product_name: z.string().optional(),
  product_code: z.string().optional(),
  product_quantity: z.number().min(0.01),
  product_unit_price: z.number().min(0),
  product_total_price: z.number().min(0),
  scope_from_product: z.boolean().optional(),
  materials_to_order: z.array(materialSupplierSchema).min(1, "Add at least one supplier"),
  shelf_materials_rows: z.array(materialOrderRowSchema).min(1, "Add at least one shelf materials row"),
  skill_required: z.string().min(1, "Select a skill"),
  best_engineer: z.string().optional(),
  subcontractors: z.string().optional(),
  engineers_required: z.boolean({ error: "Engineer needed is required" }),
  engineers_needed: z.number({ error: "Enter number of engineers" }).int().min(0),
  engineer_time_unit: z.enum(["hours", "days"]),
  engineer_time_value: requiredNumber("duration", 0.5),
  labour_required: z.boolean(),
  labour_needed: z.number({ error: "Enter number of labour" }).int().min(0),
  labour_time_value: z.number().min(0),
  other_notes: z.string().optional(),
  findings: z.string().optional(),
  attachments: z.array(attachmentMetaSchema),
  markup_value: z.number({ error: "Enter markup percentage" }).min(0),
});

export const quoteChargesFieldsSchema = z.object({
  parking_required: z.boolean(),
  parking_type: z.enum(["fixed", "hourly"]),
  parking_fixed_amount: z.number().min(0),
  parking_rate_per_hour: z.number().min(0),
  parking_hours: z.number().min(0),
  parking_vehicles: z.number().int().min(1),
  parking_latitude: z.number().min(-90).max(90).nullable().optional(),
  parking_longitude: z.number().min(-180).max(180).nullable().optional(),
  parking_notes: z.string().optional(),
  congestion_required: z.boolean(),
  congestion_amount: z.number({ error: "Enter congestion amount" }).min(0),
  ulez_required: z.boolean(),
  ulez_amount: z.number().min(0),
  waste_disposal_required: z.boolean(),
  waste_disposal_amount: z.number().min(0),
  travel_charge: z.number({ error: "Enter travel charge" }).min(0),
  other_charge: z.number({ error: "Enter other charge" }).min(0),
  other_charge_reason: z.string().optional(),
});

export const workBlockSchema = workBlockFieldsSchema.superRefine((data, ctx) => {
  validateWorkBlock(data, ctx);
});

export const questionnaireSchema = z
  .object({
    works: z.array(workBlockSchema).min(1, "At least one work block is required"),
  })
  .merge(quoteChargesFieldsSchema)
  .superRefine((data, ctx) => {
    data.works.forEach((work, index) => validateWorkBlock(work, ctx, `works.${index}`));
    validateQuoteCharges(data, ctx);
  });

export type WorkBlockFormValues = z.infer<typeof workBlockSchema>;
export type QuestionnaireFormValues = z.infer<typeof questionnaireSchema>;
export type MaterialOrderRow = z.infer<typeof materialOrderRowSchema>;
export type MaterialLinkRow = z.infer<typeof materialLinkRowSchema>;
export type MaterialSupplierFormValues = z.infer<typeof materialSupplierSchema>;
export type AttachmentMeta = z.infer<typeof attachmentMetaSchema>;

/** Stable numeric defaults for autosave while the user is mid-edit. */
function persistenceNumeric(value: unknown, fallback: number): number {
  const parsed = toNumericValue(value);
  if (parsed === undefined) return fallback;
  return parsed;
}

/** React Hook Form can store numeric inputs as strings; normalize before Zod validation. */
export function coerceQuestionnaireValues(values: QuestionnaireFormValues): QuestionnaireFormValues {
  return {
    works: values.works.map((work) => normalizeWorkBlockValues(work)),
    ...normalizeQuoteCharges(values),
  };
}

export const EWORKS_STEPS = ["Estimation Form", "Estimating Questionnaire", "Submitted"] as const;

export function formatTimeFrame(unit: TimeUnit, value: number): string {
  if (unit === "hours") {
    return value === 1 ? "1 hour" : `${value} hours`;
  }
  return value === 1 ? "1 day" : `${value} days`;
}

export function parseTimeFrame(timeFrame?: string | null): { time_unit: TimeUnit; time_value: number } {
  if (!timeFrame?.trim()) {
    return { time_unit: "hours", time_value: 1.5 };
  }
  const hourMatch = timeFrame.match(/([\d.]+)\s*(?:hours?|hrs?|hr)\b/i);
  const dayMatch = timeFrame.match(/([\d.]+)\s*(?:days?)\b/i);
  if (dayMatch && !hourMatch) {
    const value = parseFloat(dayMatch[1]);
    return { time_unit: "days", time_value: Number.isFinite(value) && value >= 0.5 ? value : 1.5 };
  }
  if (hourMatch) {
    const value = parseFloat(hourMatch[1]);
    return { time_unit: "hours", time_value: Number.isFinite(value) && value >= 0.5 ? value : 1.5 };
  }
  return { time_unit: "hours", time_value: 1.5 };
}

export function defaultWorkBlockValues(tradeName: string): WorkBlockFormValues {
  return normalizeWorkBlockValues({
    scope: "",
    selected_product_id: null,
    is_custom_scope: false,
    custom_title: "",
    eworks_item_id: null,
    product_name: "",
    product_code: "",
    product_quantity: 1,
    product_unit_price: 0,
    product_total_price: 0,
    scope_from_product: false,
    materials_to_order: defaultMaterialSuppliers(),
    shelf_materials_rows: [{ link: "", quantity: 0, cost: 0 }],
    skill_required: tradeName,
    best_engineer: "",
    subcontractors: "",
    engineers_required: true,
    engineers_needed: 1,
    engineer_time_unit: "hours",
    engineer_time_value: 1.5,
    labour_required: false,
    labour_needed: 0,
    labour_time_value: 1,
    other_notes: "",
    findings: "",
    attachments: [],
    markup_value: 20,
  });
}

export function defaultQuoteCharges(): z.infer<typeof quoteChargesFieldsSchema> {
  return {
    parking_required: false,
    parking_type: "fixed",
    parking_fixed_amount: 0,
    parking_rate_per_hour: 0,
    parking_hours: 0,
    parking_vehicles: 1,
    parking_latitude: null,
    parking_longitude: null,
    parking_notes: "",
    congestion_required: false,
    congestion_amount: 0,
    ulez_required: false,
    ulez_amount: 0,
    waste_disposal_required: false,
    waste_disposal_amount: 0,
    travel_charge: 0,
    other_charge: 0,
    other_charge_reason: "",
  };
}

function normalizeQuoteCharges(
  values: Partial<z.infer<typeof quoteChargesFieldsSchema>>,
): z.infer<typeof quoteChargesFieldsSchema> {
  const defaults = defaultQuoteCharges();
  return {
    parking_required: Boolean(values.parking_required),
    parking_type: values.parking_type === "hourly" ? "hourly" : "fixed",
    parking_fixed_amount: toNumericValue(values.parking_fixed_amount) ?? defaults.parking_fixed_amount,
    parking_rate_per_hour: toNumericValue(values.parking_rate_per_hour) ?? defaults.parking_rate_per_hour,
    parking_hours: toNumericValue(values.parking_hours) ?? defaults.parking_hours,
    parking_vehicles: Math.max(1, Math.floor(toNumericValue(values.parking_vehicles) ?? defaults.parking_vehicles)),
    parking_latitude: toNumericValue(values.parking_latitude) ?? null,
    parking_longitude: toNumericValue(values.parking_longitude) ?? null,
    parking_notes: toStringValue(values.parking_notes),
    congestion_required: Boolean(values.congestion_required),
    congestion_amount: toNumericValue(values.congestion_amount) ?? defaults.congestion_amount,
    // ULEZ and waste disposal are hidden from the UI; always zero for new calculations.
    ulez_required: false,
    ulez_amount: 0,
    waste_disposal_required: false,
    waste_disposal_amount: 0,
    travel_charge: toNumericValue(values.travel_charge) ?? defaults.travel_charge,
    other_charge: toNumericValue(values.other_charge) ?? defaults.other_charge,
    other_charge_reason: toStringValue(values.other_charge_reason),
  };
}

function quoteChargesFromStep2(
  step2: Step2Snapshot | null | undefined,
  step1?: { congestion_required?: boolean; congestion_amount?: number | string; travel?: number | string; parking_notes?: string | null; access_notes?: string | null } | null,
): z.infer<typeof quoteChargesFieldsSchema> {
  const defaults = defaultQuoteCharges();
  if (!step2) {
    const charges = { ...defaults };
    if (step1?.congestion_required) {
      charges.congestion_required = true;
      charges.congestion_amount = Number(step1.congestion_amount ?? 0);
    }
    if (Number(step1?.travel ?? 0) > 0) {
      charges.travel_charge = Number(step1?.travel ?? 0);
    }
    charges.parking_notes = mergeParkingAccessNotes(step1?.parking_notes, step1?.access_notes);
    return charges;
  }
  return normalizeQuoteCharges({
    parking_required: step2.parking_required ?? false,
    parking_type: (step2.parking_type as "fixed" | "hourly") ?? "fixed",
    parking_fixed_amount: step2.parking_fixed_amount ?? 0,
    parking_rate_per_hour: step2.parking_rate_per_hour ?? 0,
    parking_hours: step2.parking_hours ?? 0,
    parking_vehicles: Math.max(1, Number(step2.parking_vehicles ?? 1)),
    parking_latitude: step2.parking_latitude != null ? Number(step2.parking_latitude) : null,
    parking_longitude: step2.parking_longitude != null ? Number(step2.parking_longitude) : null,
    parking_notes: mergeParkingAccessNotes(step2.parking_notes as string | null | undefined, step1?.access_notes),
    congestion_required: step2.congestion_required ?? step1?.congestion_required ?? false,
    congestion_amount:
      Number(step2.congestion_amount ?? 0) > 0
        ? step2.congestion_amount
        : step1?.congestion_required
          ? step1.congestion_amount
          : 0,
    // Legacy step2 may contain ULEZ/waste; hidden from UI and excluded from new calculations.
    ulez_required: false,
    ulez_amount: 0,
    waste_disposal_required: false,
    waste_disposal_amount: 0,
    travel_charge: Number(step2.travel_charge ?? 0) > 0 ? step2.travel_charge : step1?.travel ?? 0,
    other_charge: step2.other_charge ?? 0,
    other_charge_reason: step2.other_charge_reason ?? "",
  });
}

export const defaultQuestionnaireValues: QuestionnaireFormValues = {
  works: [defaultWorkBlockValues("")],
  ...defaultQuoteCharges(),
};

export const CHARGES_FIELDS = [
  "parking_required",
  "parking_type",
  "parking_fixed_amount",
  "parking_rate_per_hour",
  "parking_hours",
  "parking_vehicles",
  "parking_latitude",
  "parking_longitude",
  "parking_notes",
  "congestion_required",
  "congestion_amount",
  "ulez_required",
  "ulez_amount",
  "waste_disposal_required",
  "waste_disposal_amount",
  "travel_charge",
  "other_charge",
  "other_charge_reason",
] as const satisfies ReadonlyArray<keyof QuestionnaireFormValues>;

export const QUESTIONNAIRE_FIELDS = ["works", ...CHARGES_FIELDS] as const;

export function shelfRowsFromLegacy(
  rows: Array<{ link?: string | null; quantity: number | string; cost: number | string }> | undefined,
  shelfMaterials?: string | null,
  shelfMaterialsCost?: number | string | null,
): MaterialOrderRow[] {
  if (rows && rows.length > 0) {
    return rows.map((row) => normalizeMaterialRow(row));
  }
  const cost = Number(shelfMaterialsCost ?? 0);
  if (cost > 0 || shelfMaterials?.trim()) {
    return [normalizeMaterialRow({ link: shelfMaterials ?? "", quantity: 1, cost })];
  }
  return [{ link: "", quantity: 0, cost: 0 }];
}

export function shelfMaterialsCostTotal(rows: MaterialOrderRow[]): number {
  return rows.reduce((sum, row) => sum + Number(row.cost ?? 0), 0);
}

export type ProductOption = {
  id: number;
  eworks_item_id: number;
  product_name: string;
  product_code: string | null;
  scope_of_work: string | null;
  selling_price: number;
  category: string | null;
  type: string | null;
};

export function formatProductLabel(product: Pick<ProductOption, "product_name" | "product_code">): string {
  return formatProductLabelFromStrings(product.product_name, product.product_code ?? undefined);
}

export function computeProductTotalPrice(quantity: number, unitPrice: number): number {
  return Math.round(quantity * unitPrice * 100) / 100;
}

type WorkBlockProductContext = {
  selected_product_id?: number | null;
  is_custom_scope?: boolean;
  custom_title?: string | null;
  eworks_item_id?: number | null;
  product_name?: string | null;
  scope?: string | null;
};

const CUSTOM_SCOPE_TITLE_MAX = 80;

function collapseWhitespace(text: string): string {
  return text.replace(/\s+/g, " ").trim();
}

function workBlockMeaningfulScopeText(work: WorkBlockProductContext): string | null {
  for (const candidate of [work.scope, work.custom_title, work.product_name]) {
    const text = stripHtmlFromLabel(candidate ?? "").trim();
    if (text) return text;
  }
  return null;
}

function deriveCustomScopeTitle(scope: string): string {
  const collapsed = collapseWhitespace(scope);
  if (collapsed.length > CUSTOM_SCOPE_TITLE_MAX) {
    return `${collapsed.slice(0, CUSTOM_SCOPE_TITLE_MAX)}…`;
  }
  return collapsed;
}

function normalizeWorkBlockScopeToCustom<T extends WorkBlockProductContext>(work: T): T {
  if (workBlockHasProductContext(work) || !workBlockMeaningfulScopeText(work)) {
    return work;
  }
  const title = deriveCustomScopeTitle(workBlockMeaningfulScopeText(work) ?? "");
  return {
    ...work,
    is_custom_scope: true,
    custom_title: title,
    product_name: title,
    selected_product_id: null,
    eworks_item_id: null,
  };
}

export function normalizeSharedWorkBlocks(step2: Step2Snapshot | null | undefined): Step2Snapshot {
  if (!step2) {
    return { works: [] };
  }
  let works = step2.works ?? [];
  if (works.length === 0 && step2.scope?.trim()) {
    works = [{ scope: step2.scope } as WorkBlockSnapshot];
  }
  if (works.length === 0) {
    return step2;
  }
  return {
    ...step2,
    works: works.map((block) => normalizeWorkBlockScopeToCustom(block)),
  };
}

export function workBlockHasProductContext(work: WorkBlockProductContext): boolean {
  if (work.is_custom_scope) {
    return Boolean(work.custom_title?.trim());
  }
  return (
    work.selected_product_id != null ||
    work.eworks_item_id != null ||
    Boolean(work.product_name?.trim())
  );
}

export function mergeWorkBlockWithSharedContext(
  local: WorkBlockFormValues,
  shared: WorkBlockSnapshot,
  tradeName: string,
): WorkBlockFormValues {
  if (workBlockHasProductContext(local) || !workBlockHasProductContext(shared)) {
    return local;
  }
  const sharedForm = blockFromSnapshot(shared, tradeName);
  return {
    ...local,
    scope: local.scope?.trim() ? local.scope : sharedForm.scope,
    selected_product_id: sharedForm.selected_product_id,
    is_custom_scope: sharedForm.is_custom_scope,
    custom_title: sharedForm.custom_title,
    eworks_item_id: sharedForm.eworks_item_id,
    product_name: sharedForm.product_name,
    product_code: sharedForm.product_code,
    product_quantity: sharedForm.product_quantity,
    product_unit_price: sharedForm.product_unit_price,
    product_total_price: sharedForm.product_total_price,
    scope_from_product: sharedForm.scope_from_product,
  };
}

export function mergeQuestionnaireWithSessionStep2(
  values: QuestionnaireFormValues,
  sessionStep2: Step2Snapshot | null | undefined,
  tradeName: string,
): QuestionnaireFormValues {
  const shared = normalizeSharedWorkBlocks(sessionStep2);
  if (!shared.works?.length) {
    return values;
  }
  return {
    ...values,
    works: values.works.map((work, index) =>
      mergeWorkBlockWithSharedContext(work, shared.works![index] ?? {}, tradeName),
    ),
  };
}

export function workBlockToSnapshot(work: WorkBlockFormValues): WorkBlockSnapshot {
  const labourActive = work.labour_required && work.engineers_required && work.engineer_time_unit === "days";
  const primaryUnit = work.engineers_required ? work.engineer_time_unit : "days";
  const primaryValue = work.engineers_required
    ? persistenceNumeric(work.engineer_time_value, 1.5)
    : persistenceNumeric(work.labour_time_value, 1);
  const engineersNeeded = work.engineers_required ? persistenceNumeric(work.engineers_needed, 1) : 0;
  const labourNeeded = labourActive ? persistenceNumeric(work.labour_needed, 1) : 0;
  const labourTimeValue = labourActive ? persistenceNumeric(work.labour_time_value, 1) : 0;
  const customTitle = work.is_custom_scope ? work.custom_title?.trim() || null : null;
  return {
    scope: work.scope,
    selected_product_id: work.is_custom_scope ? null : work.selected_product_id ?? null,
    is_custom_scope: Boolean(work.is_custom_scope),
    custom_title: customTitle,
    eworks_item_id: work.is_custom_scope ? null : work.eworks_item_id ?? null,
    product_name: work.is_custom_scope
      ? customTitle
      : work.product_name?.trim() || null,
    product_code: work.product_code?.trim() || null,
    product_quantity: persistenceNumeric(work.product_quantity, 1),
    product_unit_price: persistenceNumeric(work.product_unit_price, 0),
    product_total_price: computeProductTotalPrice(
      persistenceNumeric(work.product_quantity, 1),
      persistenceNumeric(work.product_unit_price, 0),
    ),
    scope_from_product: Boolean(work.scope_from_product),
    materials_to_order: work.materials_to_order.map(normalizeMaterialSupplier),
    shelf_materials_rows: work.shelf_materials_rows.map(normalizeMaterialRow),
    shelf_materials: work.shelf_materials_rows
      .map((row) => row.link?.trim())
      .filter(Boolean)
      .join("\n") || null,
    shelf_materials_cost: shelfMaterialsCostTotal(work.shelf_materials_rows),
    skill_required: work.skill_required,
    best_engineer: work.best_engineer || null,
    subcontractors: work.subcontractors || null,
    engineers_required: work.engineers_required,
    engineers_needed: engineersNeeded,
    engineer_time_unit: work.engineer_time_unit,
    engineer_time_value: persistenceNumeric(work.engineer_time_value, 1.5),
    labour_required: labourActive ? work.labour_required : false,
    labour_needed: labourNeeded,
    labour_time_value: labourTimeValue,
    time_frame: formatTimeFrame(primaryUnit, primaryValue),
    other_notes: work.other_notes || null,
    findings: work.findings?.trim() || null,
    attachments: work.attachments,
    markup_value: persistenceNumeric(work.markup_value, 20),
    engineers: engineersNeeded,
    labourers: labourNeeded,
    labourer_days: labourTimeValue,
    labour_type: primaryUnit === "hours" ? "hourly" : "day",
    hours: primaryUnit === "hours" ? primaryValue : 0,
    days: primaryUnit === "days" ? primaryValue : 0,
  };
}

export function questionnaireToStep2(values: QuestionnaireFormValues): Step2Snapshot {
  const works = values.works.map(workBlockToSnapshot);
  const primary = works[0];
  const charges = normalizeQuoteCharges(values);
  return {
    works,
    scope: primary.scope,
    materials_to_order: primary.materials_to_order,
    shelf_materials_rows: primary.shelf_materials_rows,
    shelf_materials: primary.shelf_materials,
    shelf_materials_cost: primary.shelf_materials_cost,
    skill_required: primary.skill_required,
    best_engineer: primary.best_engineer,
    subcontractors: primary.subcontractors,
    time_frame: primary.time_frame,
    engineers_needed: primary.engineers_needed,
    other_notes: primary.other_notes,
    attachments: primary.attachments,
    engineers: primary.engineers,
    labourers: primary.labourers,
    labourer_days: primary.labourer_days,
    hours: primary.hours,
    days: primary.days,
    markup_value: primary.markup_value,
    parking_required: charges.parking_required,
    parking_type: charges.parking_type,
    parking_fixed_amount: charges.parking_fixed_amount,
    parking_rate_per_hour: charges.parking_rate_per_hour,
    parking_hours: charges.parking_hours,
    parking_vehicles: charges.parking_vehicles,
    parking_latitude: charges.parking_latitude ?? null,
    parking_longitude: charges.parking_longitude ?? null,
    parking_notes: charges.parking_notes?.trim() || null,
    congestion_required: charges.congestion_required,
    congestion_amount: charges.congestion_amount,
    ulez_required: charges.ulez_required,
    ulez_amount: charges.ulez_amount,
    waste_disposal_required: charges.waste_disposal_required,
    waste_disposal_amount: charges.waste_disposal_amount,
    travel_charge: charges.travel_charge,
    other_charge: charges.other_charge,
    other_charge_reason: charges.other_charge_reason || null,
  };
}

function cleanEditableScope(value: string | null | undefined): string {
  return cleanRichTextForTextarea(value);
}

function cleanProductName(value: string | null | undefined): string {
  return stripHtmlFromLabel(value);
}

function legacyBlockFromStep2(step2: Step2Snapshot, tradeName: string): WorkBlockFormValues {
  const parsedEngineerTime = parseTimeFrame(step2.time_frame);
  const hasEngineers = (step2.engineers_needed ?? step2.engineers ?? 0) > 0;
  const hasLabour = (step2.labourers ?? 0) > 0;
  const labourerDays = Number(step2.labourer_days ?? 0);
  return {
    scope: cleanEditableScope(step2.scope),
    selected_product_id: null,
    is_custom_scope: false,
    custom_title: "",
    eworks_item_id: null,
    product_name: "",
    product_code: "",
    product_quantity: 1,
    product_unit_price: 0,
    product_total_price: 0,
    scope_from_product: false,
    materials_to_order:
      step2.materials_to_order && step2.materials_to_order.length > 0
        ? migrateLegacyMaterialRows(step2.materials_to_order)
        : defaultWorkBlockValues(tradeName).materials_to_order,
    shelf_materials_rows: shelfRowsFromLegacy(
      step2.shelf_materials_rows,
      step2.shelf_materials,
      step2.shelf_materials_cost,
    ),
    skill_required: step2.skill_required?.trim() || tradeName,
    best_engineer: step2.best_engineer ?? "",
    subcontractors: step2.subcontractors ?? "",
    engineers_required: hasEngineers,
    engineers_needed: hasEngineers ? Math.max(1, Number(step2.engineers_needed ?? step2.engineers ?? 1)) : 0,
    engineer_time_unit: parsedEngineerTime.time_unit,
    engineer_time_value: parsedEngineerTime.time_value,
    labour_required: hasLabour,
    labour_needed: hasLabour ? Math.max(1, Number(step2.labourers ?? 0)) : 0,
    labour_time_value:
      labourerDays > 0 ? labourerDays : hasLabour ? parsedEngineerTime.time_value : defaultWorkBlockValues(tradeName).labour_time_value,
    other_notes: step2.other_notes ?? "",
    attachments: step2.attachments ?? [],
    markup_value: Number(step2.markup_value ?? defaultWorkBlockValues(tradeName).markup_value),
  };
}

function blockFromSnapshot(block: WorkBlockSnapshot, tradeName: string): WorkBlockFormValues {
  const parsedEngineerTime = block.engineer_time_unit
    ? {
        time_unit: (block.engineer_time_unit === "days" ? "days" : "hours") as TimeUnit,
        time_value: Number(block.engineer_time_value ?? 1.5),
      }
    : parseTimeFrame(block.time_frame);
  const engineersRequired = Boolean(block.engineers_required ?? (block.engineers_needed ?? block.engineers ?? 0) > 0);
  const hasLabour = Boolean(block.labour_required ?? (block.labourers ?? 0) > 0);
  const labourerDays = Number(block.labourer_days ?? 0);
  return {
    scope: cleanEditableScope(block.scope),
    selected_product_id:
      block.is_custom_scope || block.selected_product_id == null ? null : Number(block.selected_product_id),
    is_custom_scope: Boolean(block.is_custom_scope),
    custom_title: block.is_custom_scope ? cleanProductName(block.custom_title ?? block.product_name) : "",
    eworks_item_id:
      block.is_custom_scope || block.eworks_item_id == null ? null : Number(block.eworks_item_id),
    product_name: block.is_custom_scope
      ? cleanProductName(block.custom_title ?? block.product_name)
      : cleanProductName(block.product_name),
    product_code: block.product_code ?? "",
    product_quantity: Number(block.product_quantity ?? 1),
    product_unit_price: Number(block.product_unit_price ?? 0),
    product_total_price: Number(
      block.product_total_price ??
        computeProductTotalPrice(Number(block.product_quantity ?? 1), Number(block.product_unit_price ?? 0)),
    ),
    scope_from_product: Boolean(block.scope_from_product ?? false),
    materials_to_order:
      block.materials_to_order && block.materials_to_order.length > 0
        ? migrateLegacyMaterialRows(block.materials_to_order)
        : defaultWorkBlockValues(tradeName).materials_to_order,
    shelf_materials_rows: shelfRowsFromLegacy(
      block.shelf_materials_rows,
      block.shelf_materials,
      block.shelf_materials_cost,
    ),
    skill_required: block.skill_required?.trim() || tradeName,
    best_engineer: block.best_engineer ?? "",
    subcontractors: block.subcontractors ?? "",
    engineers_required: engineersRequired,
    engineers_needed: engineersRequired ? Math.max(1, Number(block.engineers_needed ?? block.engineers ?? 1)) : 0,
    engineer_time_unit: parsedEngineerTime.time_unit,
    engineer_time_value: parsedEngineerTime.time_value,
    labour_required: hasLabour,
    labour_needed: hasLabour ? Math.max(1, Number(block.labour_needed ?? block.labourers ?? 1)) : 0,
    labour_time_value: hasLabour
      ? Number(block.labour_time_value ?? 1)
      : labourerDays > 0
        ? labourerDays
        : defaultWorkBlockValues(tradeName).labour_time_value,
    other_notes: block.other_notes ?? "",
    findings: block.findings ?? "",
    attachments: block.attachments ?? [],
    markup_value: Number(block.markup_value ?? 20),
  };
}

export function step2ToQuestionnaire(
  step2: Step2Snapshot | null | undefined,
  tradeName: string,
  overrides?: Partial<QuestionnaireFormValues>,
  step1?: { parking_notes?: string | null; access_notes?: string | null } | null,
): QuestionnaireFormValues {
  if (!step2 && !overrides) {
    return {
      works: [defaultWorkBlockValues(tradeName)],
      ...quoteChargesFromStep2(null, step1),
    };
  }
  const normalizedStep2 = normalizeSharedWorkBlocks(step2);
  const works =
    normalizedStep2.works && normalizedStep2.works.length > 0
      ? normalizedStep2.works.map((block) => normalizeWorkBlockValues(blockFromSnapshot(block, tradeName)))
      : [normalizeWorkBlockValues(legacyBlockFromStep2(normalizedStep2 ?? {}, tradeName))];

  return {
    works,
    ...quoteChargesFromStep2(normalizedStep2, step1),
    ...overrides,
  };
}
