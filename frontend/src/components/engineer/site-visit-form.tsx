"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Image from "next/image";
import { useCallback, useMemo, useState } from "react";
import { useForm } from "react-hook-form";

import {
  EworksButton,
  EworksFieldError,
  EworksInput,
  EworksLabel,
  EworksSectionTitle,
  EworksTextarea,
  eworksInputClass,
} from "@/components/eworks-ui";
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
    <form onSubmit={onSubmit} className="space-y-8" data-testid="engineer-site-visit-form">
      <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <EworksSectionTitle title="Job summary" subtitle="Read-only details from eWorks" />
        <dl className="mt-4 grid gap-3 sm:grid-cols-2">
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-gray-500">Quote ref</dt>
            <dd className="text-sm text-gray-900">{session.job.quote_number}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-gray-500">Job number</dt>
            <dd className="text-sm text-gray-900">{session.job.job_number}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-gray-500">Client</dt>
            <dd className="text-sm text-gray-900">{session.job.client_name}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-gray-500">Trade</dt>
            <dd className="text-sm text-gray-900">{session.job.trade_name}</dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-xs font-semibold uppercase tracking-wide text-gray-500">Property</dt>
            <dd className="text-sm text-gray-900">{session.job.property_address}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-gray-500">Status</dt>
            <dd className="text-sm capitalize text-gray-900">{session.status.replace(/_/g, " ")}</dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-gray-500">Session ID</dt>
            <dd className="break-all font-mono text-xs text-gray-700">{session.session_id}</dd>
          </div>
        </dl>
      </section>

      <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <EworksSectionTitle title="Work" subtitle="Scope and on-site notes for the estimator" />
        <div className="mt-4 space-y-4">
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
      </section>

      <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <EworksSectionTitle title="Photos" subtitle="Upload site photos for the estimator" />
        <div className="mt-4 space-y-4">
          <input
            type="file"
            accept="image/*"
            capture="environment"
            onChange={handlePhotoUpload}
            className="block w-full text-sm text-gray-700"
            data-testid="engineer-photo-upload"
          />
          <EworksFieldError message={uploadError ?? undefined} />
          {attachments.length > 0 ? (
            <ul className="grid gap-3 sm:grid-cols-2">
              {attachments.map((attachment) => (
                <li key={attachment.id} className="rounded-md border border-gray-200 p-2">
                  <div className="relative aspect-video overflow-hidden rounded bg-gray-100">
                    <Image
                      src={getAttachmentUrl(session.session_id, sessionToken, attachment.id)}
                      alt={attachment.file_name}
                      fill
                      className="object-cover"
                      unoptimized
                    />
                  </div>
                  <div className="mt-2 flex items-center justify-between gap-2">
                    <span className="truncate text-xs text-gray-600">{attachment.file_name}</span>
                    <EworksButton
                      type="button"
                      variant="ghost"
                      onClick={() => void handleDeleteAttachment(attachment.id)}
                    >
                      Remove
                    </EworksButton>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-500">No photos uploaded yet.</p>
          )}
        </div>
      </section>

      <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <EworksSectionTitle title="Labour" subtitle="Engineers and labourers on site" />
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
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
      </section>

      <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <EworksSectionTitle title="Materials" subtitle="Materials required on site (no markup shown)" />
        <div className="mt-4 space-y-4">
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
      </section>

      <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <EworksSectionTitle title="Site charges" subtitle="Tick applicable charges and enter amounts" />
        <div className="mt-4 space-y-4">
          <label className="flex items-center gap-2 text-sm font-medium text-gray-800">
            <input type="checkbox" {...register("parking_required")} />
            Parking
          </label>
          {parkingRequired && (
            <EworksLabel>
              Parking amount (£)
              <EworksInput type="number" min={0} step={0.01} {...register("parking_amount", { valueAsNumber: true })} />
              <EworksFieldError message={errors.parking_amount?.message} />
            </EworksLabel>
          )}
          <label className="flex items-center gap-2 text-sm font-medium text-gray-800">
            <input type="checkbox" {...register("congestion_required")} />
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
          <label className="flex items-center gap-2 text-sm font-medium text-gray-800">
            <input type="checkbox" {...register("ulez_required")} />
            ULEZ
          </label>
          {ulezRequired && (
            <EworksLabel>
              ULEZ amount (£)
              <EworksInput type="number" min={0} step={0.01} {...register("ulez_amount", { valueAsNumber: true })} />
              <EworksFieldError message={errors.ulez_amount?.message} />
            </EworksLabel>
          )}
          <label className="flex items-center gap-2 text-sm font-medium text-gray-800">
            <input type="checkbox" {...register("waste_required")} />
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
      </section>

      <div className="flex flex-wrap items-center gap-3">
        <EworksButton type="submit" disabled={isSaving} data-testid="engineer-submit-site-visit">
          {isSaving ? "Saving…" : "Submit to estimator"}
        </EworksButton>
        {saveMessage && (
          <p className="text-sm font-medium text-green-700" data-testid="engineer-save-success">
            {saveMessage}
          </p>
        )}
        <EworksFieldError message={saveError ?? undefined} />
      </div>
    </form>
  );
}
