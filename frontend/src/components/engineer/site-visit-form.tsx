"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Image from "next/image";
import { useCallback, useMemo, useState } from "react";
import { useForm } from "react-hook-form";

import {
  EworksFieldError,
  EworksInput,
  EworksLabel,
  EworksTextarea,
  eworksInputClass,
} from "@/components/eworks-ui";
import {
  PrimaryButton,
  SecondaryButton,
  SectionCard,
  StatusBadge,
  quoteStatusTone,
} from "@/components/ui";
import type { AttachmentMeta } from "@/lib/eworks-calculate-schema";
import {
  deleteSessionAttachment,
  getAttachmentUrl,
  saveEngineerSiteVisit,
  uploadSessionAttachment,
  type EngineerSession,
  type EngineerSiteVisitPayload,
} from "@/lib/engineer-session";
import {
  engineerSiteVisitSchema,
  siteVisitToFormValues,
  type EngineerSiteVisitFormValues,
} from "@/lib/engineer-site-visit-schema";

type SiteVisitFormProps = {
  session: EngineerSession;
  sessionToken: string;
  onSaved?: (message: string) => void;
};

function toPayload(values: EngineerSiteVisitFormValues): EngineerSiteVisitPayload {
  return {
    scope: values.scope?.trim() || null,
    site_notes: values.site_notes?.trim() || null,
    findings: values.findings?.trim() || null,
    engineer_count: values.engineer_count,
    labourer_count: values.labourer_count,
    duration_type: values.duration_type,
    hours: values.duration_type === "hourly" ? values.hours ?? null : null,
    days: values.duration_type !== "hourly" ? values.days ?? null : null,
    materials_required: values.materials_required?.trim() || null,
    unit_cost: values.unit_cost ?? null,
    parking_required: values.parking_required,
    parking_amount: values.parking_required ? values.parking_amount ?? 0 : null,
    congestion_required: values.congestion_required,
    congestion_amount: values.congestion_required ? values.congestion_amount ?? 0 : null,
    ulez_required: values.ulez_required,
    ulez_amount: values.ulez_required ? values.ulez_amount ?? 0 : null,
    waste_required: values.waste_required,
    waste_amount: values.waste_required ? values.waste_amount ?? 0 : null,
  };
}

const checkboxClass =
  "size-5 shrink-0 rounded border-slate-300 text-blue-600 focus:ring-blue-500/40";

export function SiteVisitForm({ session, sessionToken, onSaved }: SiteVisitFormProps) {
  const [attachments, setAttachments] = useState<AttachmentMeta[]>(session.site_visit.attachments ?? []);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const defaultValues = useMemo(
    () => siteVisitToFormValues(session.site_visit),
    [session.site_visit],
  );

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<EngineerSiteVisitFormValues>({
    resolver: zodResolver(engineerSiteVisitSchema),
    defaultValues,
  });

  const durationType = watch("duration_type");
  const parkingRequired = watch("parking_required");
  const congestionRequired = watch("congestion_required");
  const ulezRequired = watch("ulez_required");
  const wasteRequired = watch("waste_required");

  const onSubmit = handleSubmit(async (values) => {
    setIsSaving(true);
    setSaveError(null);
    setSaveMessage(null);
    try {
      const result = await saveEngineerSiteVisit(session.session_id, sessionToken, toPayload(values));
      setSaveMessage(result.message);
      onSaved?.(result.message);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Failed to save site visit");
    } finally {
      setIsSaving(false);
    }
  });

  const handlePhotoUpload = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (!file) return;
      setUploadError(null);
      try {
        const meta = await uploadSessionAttachment(session.session_id, sessionToken, file, 0);
        setAttachments((prev) => [...prev, meta]);
      } catch (err) {
        setUploadError(err instanceof Error ? err.message : "Upload failed");
      } finally {
        event.target.value = "";
      }
    },
    [session.session_id, sessionToken],
  );

  const handleDeleteAttachment = useCallback(
    async (attachmentId: string) => {
      try {
        await deleteSessionAttachment(session.session_id, sessionToken, attachmentId);
        setAttachments((prev) => prev.filter((item) => item.id !== attachmentId));
      } catch (err) {
        setUploadError(err instanceof Error ? err.message : "Delete failed");
      }
    },
    [session.session_id, sessionToken],
  );

  return (
    <form onSubmit={onSubmit} className="space-y-6" data-testid="engineer-site-visit-form">
      <SectionCard title="Job summary" description="Read-only details from eWorks">
        <dl className="grid gap-4 sm:grid-cols-2">
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Quote ref</dt>
            <dd className="mt-1 text-sm font-medium text-slate-900">{session.job.quote_number}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Job number</dt>
            <dd className="mt-1 text-sm font-medium text-slate-900">{session.job.job_number}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Client</dt>
            <dd className="mt-1 text-sm font-medium text-slate-900">{session.job.client_name}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Trade</dt>
            <dd className="mt-1 text-sm font-medium text-slate-900">{session.job.trade_name}</dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Property</dt>
            <dd className="mt-1 text-sm text-slate-900">{session.job.property_address}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Status</dt>
            <dd className="mt-1">
              <StatusBadge tone={quoteStatusTone(session.status)}>
                {session.status.replace(/_/g, " ")}
              </StatusBadge>
            </dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Session ID</dt>
            <dd className="mt-1 break-all font-mono text-xs text-slate-600">{session.session_id}</dd>
          </div>
        </dl>
      </SectionCard>

      <SectionCard title="Work" description="Scope and on-site notes for the estimator">
        <div className="space-y-4">
          <EworksLabel>
            Scope of works
            <EworksTextarea {...register("scope")} placeholder="Describe the work required on site" />
            <EworksFieldError message={errors.scope?.message} />
          </EworksLabel>
          <EworksLabel>
            Site notes
            <EworksTextarea {...register("site_notes")} placeholder="Access, hazards, or other on-site observations" />
            <EworksFieldError message={errors.site_notes?.message} />
          </EworksLabel>
        </div>
      </SectionCard>

      <SectionCard title="Photos" description="Upload site photos for the estimator">
        <div className="space-y-4">
          <input
            type="file"
            accept="image/*"
            capture="environment"
            onChange={handlePhotoUpload}
            className="block w-full cursor-pointer rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-sm text-slate-600 file:mr-4 file:rounded-md file:border-0 file:bg-blue-600 file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:border-slate-400"
            data-testid="engineer-photo-upload"
          />
          <EworksFieldError message={uploadError ?? undefined} />
          {attachments.length > 0 ? (
            <ul className="grid gap-3 sm:grid-cols-2">
              {attachments.map((attachment) => (
                <li key={attachment.id} className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
                  <div className="relative aspect-video overflow-hidden bg-slate-100">
                    <Image
                      src={getAttachmentUrl(session.session_id, sessionToken, attachment.id)}
                      alt={attachment.file_name}
                      fill
                      className="object-cover"
                      unoptimized
                    />
                  </div>
                  <div className="flex items-center justify-between gap-2 px-3 py-2">
                    <span className="truncate text-xs text-slate-600">{attachment.file_name}</span>
                    <SecondaryButton
                      type="button"
                      variant="ghost"
                      className="min-h-[36px] px-2 text-xs"
                      onClick={() => void handleDeleteAttachment(attachment.id)}
                    >
                      Remove
                    </SecondaryButton>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">No photos uploaded yet.</p>
          )}
        </div>
      </SectionCard>

      <SectionCard title="Labour" description="Engineers and labourers on site">
        <div className="grid gap-4 sm:grid-cols-2">
          <EworksLabel>
            Engineers on site
            <EworksInput type="number" min={0} step={1} {...register("engineer_count", { valueAsNumber: true })} />
            <EworksFieldError message={errors.engineer_count?.message} />
          </EworksLabel>
          <EworksLabel>
            Labourers on site
            <EworksInput type="number" min={0} step={1} {...register("labourer_count", { valueAsNumber: true })} />
            <EworksFieldError message={errors.labourer_count?.message} />
          </EworksLabel>
          <EworksLabel className="sm:col-span-2">
            Duration type
            <select className={eworksInputClass(!!errors.duration_type)} {...register("duration_type")}>
              <option value="hourly">Hourly</option>
              <option value="half_day">Half day</option>
              <option value="day_up_to_2">Day (up to 2 days)</option>
              <option value="day_3_plus">Day (3+ days)</option>
            </select>
            <EworksFieldError message={errors.duration_type?.message} />
          </EworksLabel>
          {durationType === "hourly" ? (
            <EworksLabel>
              Hours on site
              <EworksInput type="number" min={0.5} step={0.5} {...register("hours", { valueAsNumber: true })} />
              <EworksFieldError message={errors.hours?.message} />
            </EworksLabel>
          ) : (
            <EworksLabel>
              Days on site
              <EworksInput type="number" min={0.5} step={0.5} {...register("days", { valueAsNumber: true })} />
              <EworksFieldError message={errors.days?.message} />
            </EworksLabel>
          )}
        </div>
      </SectionCard>

      <SectionCard title="Materials" description="Materials required on site (no markup shown)">
        <div className="space-y-4">
          <EworksLabel>
            Materials required
            <EworksTextarea {...register("materials_required")} placeholder="List materials needed" />
            <EworksFieldError message={errors.materials_required?.message} />
          </EworksLabel>
          <EworksLabel>
            Unit cost (optional)
            <EworksInput type="number" min={0} step={0.01} {...register("unit_cost", { valueAsNumber: true })} />
            <EworksFieldError message={errors.unit_cost?.message} />
          </EworksLabel>
        </div>
      </SectionCard>

      <SectionCard title="Site charges" description="Tick applicable charges and enter amounts">
        <div className="space-y-4">
          <label className="flex min-h-[44px] items-center gap-3 text-sm font-medium text-slate-800">
            <input type="checkbox" className={checkboxClass} {...register("parking_required")} />
            Parking
          </label>
          {parkingRequired && (
            <EworksLabel>
              Parking amount (£)
              <EworksInput type="number" min={0} step={0.01} {...register("parking_amount", { valueAsNumber: true })} />
              <EworksFieldError message={errors.parking_amount?.message} />
            </EworksLabel>
          )}
          <label className="flex min-h-[44px] items-center gap-3 text-sm font-medium text-slate-800">
            <input type="checkbox" className={checkboxClass} {...register("congestion_required")} />
            Congestion charge
          </label>
          {congestionRequired && (
            <EworksLabel>
              Congestion amount (£)
              <EworksInput
                type="number"
                min={0}
                step={0.01}
                {...register("congestion_amount", { valueAsNumber: true })}
              />
              <EworksFieldError message={errors.congestion_amount?.message} />
            </EworksLabel>
          )}
          <label className="flex min-h-[44px] items-center gap-3 text-sm font-medium text-slate-800">
            <input type="checkbox" className={checkboxClass} {...register("ulez_required")} />
            ULEZ
          </label>
          {ulezRequired && (
            <EworksLabel>
              ULEZ amount (£)
              <EworksInput type="number" min={0} step={0.01} {...register("ulez_amount", { valueAsNumber: true })} />
              <EworksFieldError message={errors.ulez_amount?.message} />
            </EworksLabel>
          )}
          <label className="flex min-h-[44px] items-center gap-3 text-sm font-medium text-slate-800">
            <input type="checkbox" className={checkboxClass} {...register("waste_required")} />
            Waste disposal
          </label>
          {wasteRequired && (
            <EworksLabel>
              Waste amount (£)
              <EworksInput type="number" min={0} step={0.01} {...register("waste_amount", { valueAsNumber: true })} />
              <EworksFieldError message={errors.waste_amount?.message} />
            </EworksLabel>
          )}
        </div>
      </SectionCard>

      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <PrimaryButton type="submit" disabled={isSaving} data-testid="engineer-submit-site-visit">
          {isSaving ? "Saving…" : "Submit to estimator"}
        </PrimaryButton>
        {saveMessage ? (
          <p className="text-sm font-medium text-emerald-700" data-testid="engineer-save-success">
            {saveMessage}
          </p>
        ) : null}
        <EworksFieldError message={saveError ?? undefined} />
      </div>
    </form>
  );
}
