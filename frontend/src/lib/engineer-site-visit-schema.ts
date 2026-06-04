import { z } from "zod";

export const MAX_ENGINEER_NOTE_LENGTH = 8000;

export const engineerDurationTypeSchema = z.enum([
  "hourly",
  "half_day",
  "day_up_to_2",
  "day_3_plus",
]);

export const engineerSiteVisitSchema = z
  .object({
    scope: z.string().max(MAX_ENGINEER_NOTE_LENGTH).optional(),
    site_notes: z.string().max(MAX_ENGINEER_NOTE_LENGTH).optional(),
    findings: z.string().max(MAX_ENGINEER_NOTE_LENGTH).optional(),
    engineer_count: z.number().min(0, "Engineer count must be 0 or greater"),
    labourer_count: z.number().min(0, "Labourer count must be 0 or greater"),
    duration_type: engineerDurationTypeSchema,
    hours: z.number().positive("Hours must be greater than 0").optional(),
    days: z.number().positive("Days must be greater than 0").optional(),
    materials_required: z.string().max(MAX_ENGINEER_NOTE_LENGTH).optional(),
    unit_cost: z.number().min(0, "Unit cost must be 0 or greater").optional(),
    parking_required: z.boolean(),
    parking_amount: z.number().min(0).optional(),
    congestion_required: z.boolean(),
    congestion_amount: z.number().min(0).optional(),
    ulez_required: z.boolean(),
    ulez_amount: z.number().min(0).optional(),
    waste_required: z.boolean(),
    waste_amount: z.number().min(0).optional(),
  })
  .superRefine((data, ctx) => {
    if (data.duration_type === "hourly") {
      if (data.hours === undefined || data.hours <= 0) {
        ctx.addIssue({ code: "custom", message: "Hours required for hourly duration", path: ["hours"] });
      }
    } else if (data.days === undefined || data.days <= 0) {
      ctx.addIssue({ code: "custom", message: "Days required for this duration type", path: ["days"] });
    }
    if (data.parking_required && (data.parking_amount === undefined || data.parking_amount < 0)) {
      ctx.addIssue({ code: "custom", message: "Enter parking amount", path: ["parking_amount"] });
    }
    if (data.congestion_required && (data.congestion_amount === undefined || data.congestion_amount < 0)) {
      ctx.addIssue({ code: "custom", message: "Enter congestion amount", path: ["congestion_amount"] });
    }
    if (data.ulez_required && (data.ulez_amount === undefined || data.ulez_amount < 0)) {
      ctx.addIssue({ code: "custom", message: "Enter ULEZ amount", path: ["ulez_amount"] });
    }
    if (data.waste_required && (data.waste_amount === undefined || data.waste_amount < 0)) {
      ctx.addIssue({ code: "custom", message: "Enter waste amount", path: ["waste_amount"] });
    }
  });

export type EngineerSiteVisitFormValues = z.infer<typeof engineerSiteVisitSchema>;

export function siteVisitToFormValues(siteVisit: {
  scope?: string | null;
  site_notes?: string | null;
  findings?: string | null;
  engineer_count: number;
  labourer_count: number;
  duration_type: string;
  hours?: number | string | null;
  days?: number | string | null;
  materials_required?: string | null;
  unit_cost?: number | string | null;
  parking_required: boolean;
  parking_amount?: number | string | null;
  congestion_required: boolean;
  congestion_amount?: number | string | null;
  ulez_required: boolean;
  ulez_amount?: number | string | null;
  waste_required: boolean;
  waste_amount?: number | string | null;
}): EngineerSiteVisitFormValues {
  const toNum = (value: number | string | null | undefined) => {
    if (value === null || value === undefined || value === "") return undefined;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : undefined;
  };

  return {
    scope: siteVisit.scope ?? "",
    site_notes: siteVisit.site_notes ?? "",
    findings: siteVisit.findings ?? "",
    engineer_count: siteVisit.engineer_count ?? 0,
    labourer_count: siteVisit.labourer_count ?? 0,
    duration_type: siteVisit.duration_type as EngineerSiteVisitFormValues["duration_type"],
    hours: toNum(siteVisit.hours),
    days: toNum(siteVisit.days),
    materials_required: siteVisit.materials_required ?? "",
    unit_cost: toNum(siteVisit.unit_cost),
    parking_required: siteVisit.parking_required,
    parking_amount: toNum(siteVisit.parking_amount),
    congestion_required: siteVisit.congestion_required,
    congestion_amount: toNum(siteVisit.congestion_amount),
    ulez_required: siteVisit.ulez_required,
    ulez_amount: toNum(siteVisit.ulez_amount),
    waste_required: siteVisit.waste_required,
    waste_amount: toNum(siteVisit.waste_amount),
  };
}
