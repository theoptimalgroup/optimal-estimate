import { z } from "zod";
import type { Step2Snapshot, WorkBlockSnapshot } from "@/lib/eworks-session";

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

export const attachmentMetaSchema = z.object({
  id: z.string(),
  file_name: z.string(),
  content_type: z.string(),
  size: z.number(),
  media_type: z.string(),
  stored_name: z.string(),
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

function normalizeWorkBlockValues(work: WorkBlockFormValues): WorkBlockFormValues {
  const engineersRequired = work.engineers_required !== false;
  return {
    ...work,
    scope: toStringValue(work.scope),
    skill_required: toStringValue(work.skill_required),
    best_engineer: toStringValue(work.best_engineer),
    subcontractors: toStringValue(work.subcontractors),
    other_notes: toStringValue(work.other_notes),
    materials_to_order:
      work.materials_to_order?.length > 0
        ? work.materials_to_order.map(normalizeMaterialRow)
        : [{ link: "", quantity: 0, cost: 0 }],
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
    parking_required: Boolean(work.parking_required),
    parking_type: work.parking_type === "hourly" ? "hourly" : "fixed",
    parking_fixed_amount: toNumericValue(work.parking_fixed_amount) ?? 0,
    parking_rate_per_hour: toNumericValue(work.parking_rate_per_hour) ?? 0,
    parking_hours: toNumericValue(work.parking_hours) ?? 0,
    congestion_required: Boolean(work.congestion_required),
    congestion_amount: toNumericValue(work.congestion_amount) ?? 0,
    travel_charge: toNumericValue(work.travel_charge) ?? 0,
    other_charge: toNumericValue(work.other_charge) ?? 0,
    other_charge_reason: toStringValue(work.other_charge_reason),
  };
}

function validateWorkBlock(data: z.infer<typeof workBlockFieldsSchema>, ctx: z.RefinementCtx, pathPrefix = "") {
  const path = (field: string) => (pathPrefix ? `${pathPrefix}.${field}` : field);
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
  if (data.parking_required && data.parking_type === "hourly") {
    if (!data.parking_hours || data.parking_hours <= 0) {
      ctx.addIssue({ code: "custom", message: "Parking hours required for hourly parking", path: [path("parking_hours")] });
    }
    if (!data.parking_rate_per_hour || data.parking_rate_per_hour <= 0) {
      ctx.addIssue({ code: "custom", message: "Parking rate required for hourly parking", path: [path("parking_rate_per_hour")] });
    }
  }
  if (data.other_charge > 0 && !data.other_charge_reason?.trim()) {
    ctx.addIssue({
      code: "custom",
      message: "Reason required when other charge is greater than 0",
      path: [path("other_charge_reason")],
    });
  }
}

export const workBlockFieldsSchema = z.object({
  scope: z.string().min(1, "Scope of works is required"),
  materials_to_order: z.array(materialOrderRowSchema).min(1, "Add at least one materials row"),
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
  attachments: z.array(attachmentMetaSchema),
  markup_value: z.number({ error: "Enter markup percentage" }).min(0),
  // Per-work charges
  parking_required: z.boolean(),
  parking_type: z.enum(["fixed", "hourly"]),
  parking_fixed_amount: z.number().min(0),
  parking_rate_per_hour: z.number().min(0),
  parking_hours: z.number().min(0),
  congestion_required: z.boolean(),
  congestion_amount: z.number({ error: "Enter congestion amount" }).min(0),
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
  .superRefine((data, ctx) => {
    data.works.forEach((work, index) => validateWorkBlock(work, ctx, `works.${index}`));
  });

export type WorkBlockFormValues = z.infer<typeof workBlockSchema>;
export type QuestionnaireFormValues = z.infer<typeof questionnaireSchema>;
export type MaterialOrderRow = z.infer<typeof materialOrderRowSchema>;
export type AttachmentMeta = z.infer<typeof attachmentMetaSchema>;

function toNumericValueOr(value: unknown, fallback: number): number {
  return toNumericValue(value) ?? fallback;
}

/** React Hook Form can store numeric inputs as strings; normalize before Zod validation. */
export function coerceQuestionnaireValues(values: QuestionnaireFormValues): QuestionnaireFormValues {
  return {
    works: values.works.map((work) => normalizeWorkBlockValues(work)),
  };
}

export const EWORKS_STEPS = ["Estimation Form", "Estimating Questionnaire", "Results"] as const;

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
    materials_to_order: [{ link: "", quantity: 0, cost: 0 }],
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
    attachments: [],
    markup_value: 20,
    parking_required: false,
    parking_type: "fixed",
    parking_fixed_amount: 0,
    parking_rate_per_hour: 0,
    parking_hours: 0,
    congestion_required: false,
    congestion_amount: 0,
    travel_charge: 0,
    other_charge: 0,
    other_charge_reason: "",
  });
}

export const defaultQuestionnaireValues: QuestionnaireFormValues = {
  works: [defaultWorkBlockValues("")],
};

export const CHARGES_FIELDS: never[] = [];
export const QUESTIONNAIRE_FIELDS = ["works"] as const;

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

export function workBlockToSnapshot(work: WorkBlockFormValues): WorkBlockSnapshot {
  const labourActive = work.labour_required && work.engineers_required && work.engineer_time_unit === "days";
  const primaryUnit = work.engineers_required ? work.engineer_time_unit : "days";
  const primaryValue = work.engineers_required ? work.engineer_time_value : work.labour_time_value;
  return {
    scope: work.scope,
    materials_to_order: work.materials_to_order,
    shelf_materials_rows: work.shelf_materials_rows,
    shelf_materials: work.shelf_materials_rows
      .map((row) => row.link?.trim())
      .filter(Boolean)
      .join("\n") || null,
    shelf_materials_cost: shelfMaterialsCostTotal(work.shelf_materials_rows),
    skill_required: work.skill_required,
    best_engineer: work.best_engineer || null,
    subcontractors: work.subcontractors || null,
    engineers_required: work.engineers_required,
    engineers_needed: work.engineers_required ? work.engineers_needed : 0,
    engineer_time_unit: work.engineer_time_unit,
    engineer_time_value: work.engineer_time_value,
    labour_required: labourActive ? work.labour_required : false,
    labour_needed: labourActive ? work.labour_needed : 0,
    labour_time_value: work.labour_time_value,
    time_frame: formatTimeFrame(primaryUnit, primaryValue),
    other_notes: work.other_notes || null,
    attachments: work.attachments,
    markup_value: work.markup_value,
    engineers: work.engineers_required ? work.engineers_needed : 0,
    labourers: labourActive ? work.labour_needed : 0,
    labourer_days: labourActive ? work.labour_time_value : 0,
    labour_type: primaryUnit === "hours" ? "hourly" : "day",
    hours: primaryUnit === "hours" ? primaryValue : 0,
    days: primaryUnit === "days" ? primaryValue : 0,
    // Per-work charge fields (stored in snapshot for round-trip restore)
    parking_required: work.parking_required,
    parking_type: work.parking_type,
    parking_fixed_amount: work.parking_fixed_amount,
    parking_rate_per_hour: work.parking_rate_per_hour,
    parking_hours: work.parking_hours,
    congestion_required: work.congestion_required,
    congestion_amount: work.congestion_amount,
    travel_charge: work.travel_charge,
    other_charge: work.other_charge,
    other_charge_reason: work.other_charge_reason || null,
  };
}

/** Aggregate per-work charges into a single set of top-level charges for the backend. */
function aggregateCharges(works: WorkBlockFormValues[]) {
  const hasParking = works.some((w) => w.parking_required);
  const parkingTotal = works.reduce((sum, w) => {
    if (!w.parking_required) return sum;
    if (w.parking_type === "hourly") {
      return sum + (w.parking_rate_per_hour ?? 0) * (w.parking_hours ?? 0);
    }
    return sum + (w.parking_fixed_amount ?? 0);
  }, 0);

  const hasCongestion = works.some((w) => w.congestion_required);
  const congestionTotal = works.reduce((sum, w) => sum + (w.congestion_required ? (w.congestion_amount ?? 0) : 0), 0);
  const travelTotal = works.reduce((sum, w) => sum + toNumericValueOr(w.travel_charge, 0), 0);
  const otherTotal = works.reduce((sum, w) => sum + toNumericValueOr(w.other_charge, 0), 0);
  const otherReasons = works
    .map((w) => w.other_charge_reason?.trim() ?? "")
    .filter(Boolean)
    .join(" / ");

  return {
    parking_required: hasParking,
    parking_type: "fixed" as const,
    parking_fixed_amount: parkingTotal,
    parking_rate_per_hour: null as null,
    parking_hours: null as null,
    congestion_required: hasCongestion,
    congestion_amount: congestionTotal,
    travel_charge: travelTotal,
    other_charge: otherTotal,
    other_charge_reason: otherReasons || null,
  };
}

export function questionnaireToStep2(values: QuestionnaireFormValues): Step2Snapshot {
  const works = values.works.map(workBlockToSnapshot);
  const primary = works[0];
  const charges = aggregateCharges(values.works);
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
    ...charges,
  };
}

function legacyBlockFromStep2(step2: Step2Snapshot, tradeName: string): WorkBlockFormValues {
  const parsedEngineerTime = parseTimeFrame(step2.time_frame);
  const hasEngineers = (step2.engineers_needed ?? step2.engineers ?? 0) > 0;
  const hasLabour = (step2.labourers ?? 0) > 0;
  const labourerDays = Number(step2.labourer_days ?? 0);
  return {
    scope: step2.scope ?? "",
    materials_to_order:
      step2.materials_to_order && step2.materials_to_order.length > 0
        ? step2.materials_to_order.map((row) => normalizeMaterialRow(row))
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
    // Restore charges from legacy top-level Step2Snapshot for first work block
    parking_required: step2.parking_required ?? false,
    parking_type: (step2.parking_type as "fixed" | "hourly") ?? "fixed",
    parking_fixed_amount: Number(step2.parking_fixed_amount ?? 0),
    parking_rate_per_hour: Number(step2.parking_rate_per_hour ?? 0),
    parking_hours: Number(step2.parking_hours ?? 0),
    congestion_required: step2.congestion_required ?? false,
    congestion_amount: Number(step2.congestion_amount ?? 0),
    travel_charge: Number(step2.travel_charge ?? 0),
    other_charge: Number(step2.other_charge ?? 0),
    other_charge_reason: step2.other_charge_reason ?? "",
  };
}

function blockFromSnapshot(block: WorkBlockSnapshot, tradeName: string): WorkBlockFormValues {
  if (block.engineer_time_unit) {
    return {
      scope: block.scope ?? "",
      materials_to_order:
        block.materials_to_order && block.materials_to_order.length > 0
          ? block.materials_to_order.map((row) => normalizeMaterialRow(row))
          : defaultWorkBlockValues(tradeName).materials_to_order,
      shelf_materials_rows: shelfRowsFromLegacy(
        block.shelf_materials_rows,
        block.shelf_materials,
        block.shelf_materials_cost,
      ),
      skill_required: block.skill_required?.trim() || tradeName,
      best_engineer: block.best_engineer ?? "",
      subcontractors: block.subcontractors ?? "",
      engineers_required: Boolean(block.engineers_required ?? (block.engineers_needed ?? 0) > 0),
      engineers_needed:
        (block.engineers_required ?? (block.engineers_needed ?? 0) > 0)
          ? Math.max(1, Number(block.engineers_needed ?? block.engineers ?? 1))
          : 0,
      engineer_time_unit: (block.engineer_time_unit as TimeUnit) ?? "hours",
      engineer_time_value: Number(block.engineer_time_value ?? 1.5),
      labour_required: Boolean(block.labour_required ?? (block.labourers ?? 0) > 0),
      labour_needed:
        (block.labour_required ?? (block.labourers ?? 0) > 0)
          ? Math.max(1, Number(block.labour_needed ?? block.labourers ?? 1))
          : 0,
      labour_time_value: Number(block.labour_time_value ?? 1),
      other_notes: block.other_notes ?? "",
      attachments: block.attachments ?? [],
      markup_value: Number(block.markup_value ?? 20),
      // Per-work charges — restore from snapshot if present
      parking_required: Boolean((block as WorkBlockSnapshot & Record<string, unknown>).parking_required ?? false),
      parking_type: ((block as WorkBlockSnapshot & Record<string, unknown>).parking_type as "fixed" | "hourly") ?? "fixed",
      parking_fixed_amount: Number((block as WorkBlockSnapshot & Record<string, unknown>).parking_fixed_amount ?? 0),
      parking_rate_per_hour: Number((block as WorkBlockSnapshot & Record<string, unknown>).parking_rate_per_hour ?? 0),
      parking_hours: Number((block as WorkBlockSnapshot & Record<string, unknown>).parking_hours ?? 0),
      congestion_required: Boolean((block as WorkBlockSnapshot & Record<string, unknown>).congestion_required ?? false),
      congestion_amount: Number((block as WorkBlockSnapshot & Record<string, unknown>).congestion_amount ?? 0),
      travel_charge: Number((block as WorkBlockSnapshot & Record<string, unknown>).travel_charge ?? 0),
      other_charge: Number((block as WorkBlockSnapshot & Record<string, unknown>).other_charge ?? 0),
      other_charge_reason: String((block as WorkBlockSnapshot & Record<string, unknown>).other_charge_reason ?? ""),
    };
  }
  return legacyBlockFromStep2(block as Step2Snapshot, tradeName);
}

export function step2ToQuestionnaire(
  step2: Step2Snapshot | null | undefined,
  tradeName: string,
  overrides?: Partial<QuestionnaireFormValues>,
): QuestionnaireFormValues {
  if (!step2 && !overrides) {
    return { works: [defaultWorkBlockValues(tradeName)] };
  }
  const works =
    step2?.works && step2.works.length > 0
      ? step2.works.map((block) => normalizeWorkBlockValues(blockFromSnapshot(block, tradeName)))
      : [normalizeWorkBlockValues(legacyBlockFromStep2(step2 ?? {}, tradeName))];

  return {
    works,
    ...overrides,
  };
}
