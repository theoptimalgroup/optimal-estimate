"use client";

import Link from "next/link";
import { useState } from "react";
import { EworksButton, EworksSectionTitle, cn } from "@/components/eworks-ui";
import type { DashboardQuoteItem, DashboardWorkItem } from "@/lib/dashboard";
import type { AttachmentMeta } from "@/lib/eworks-calculate-schema";
import type { MaterialOrderRow, WorkBlockSnapshot } from "@/lib/eworks-session";
import { getAttachmentUrl } from "@/lib/eworks-session";

export function money(value?: number | string | null) {
  if (value === undefined || value === null || value === "") return "—";
  return `£${Number(value).toFixed(2)}`;
}

export function formatSubmittedAt(value: string) {
  try {
    return new Intl.DateTimeFormat("en-GB", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function workAttachments(work: DashboardWorkItem): AttachmentMeta[] {
  if (work.attachments.length > 0) return work.attachments;
  return work.details?.attachments ?? [];
}

function attachmentSummary(attachments: AttachmentMeta[]) {
  const photos = attachments.filter((item) => item.media_type === "photo").length;
  const videos = attachments.filter((item) => item.media_type === "video").length;
  const files = attachments.length - photos - videos;
  const parts: string[] = [];
  if (photos > 0) parts.push(`${photos} photo${photos === 1 ? "" : "s"}`);
  if (videos > 0) parts.push(`${videos} video${videos === 1 ? "" : "s"}`);
  if (files > 0) parts.push(`${files} file${files === 1 ? "" : "s"}`);
  return parts.join(" · ");
}

function WorkAttachmentsGallery({
  quote,
  attachments,
}: {
  quote: DashboardQuoteItem;
  attachments: AttachmentMeta[];
}) {
  return (
    <div className="space-y-3">
      <EworksSectionTitle title="Photos / Videos" subtitle="Click to open full size" />
      {attachments.length === 0 ? (
        <p className="text-sm text-optimal-muted">No photos or videos uploaded for this work.</p>
      ) : (
        <div className="grid gap-3 grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
          {attachments.map((attachment) => {
            const viewUrl = getAttachmentUrl(quote.session_id, quote.session_token, attachment.id);
            const isPhoto = attachment.media_type === "photo";
            const isVideo = attachment.media_type === "video";
            return (
              <a
                key={attachment.id}
                href={viewUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="overflow-hidden rounded-lg border border-gray-200 bg-optimal-field transition-colors hover:border-gray-300"
              >
                {isPhoto ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={viewUrl}
                    alt={attachment.file_name}
                    className="aspect-video w-full bg-white object-cover"
                  />
                ) : (
                  <div className="flex aspect-video w-full items-center justify-center bg-white text-3xl text-optimal-field-text">
                    {isVideo ? "▶" : "📄"}
                  </div>
                )}
                <div className="border-t border-black/10 px-3 py-2">
                  <p className="truncate text-sm font-medium text-optimal-field-text">
                    {isPhoto ? "Photo" : isVideo ? "Video" : "File"}
                  </p>
                  <p className="truncate text-xs text-optimal-muted">{attachment.file_name}</p>
                </div>
              </a>
            );
          })}
        </div>
      )}
    </div>
  );
}

function hasText(value?: string | null) {
  return Boolean(value?.trim());
}

function hasNumber(value?: number | string | null) {
  return value !== undefined && value !== null && value !== "" && Number(value) !== 0;
}

function DetailRow({ label, value }: { label: string; value?: string | null }) {
  if (!hasText(value)) return null;
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-optimal-muted">{label}</p>
      <p className="whitespace-pre-wrap text-sm text-gray-900">{value}</p>
    </div>
  );
}

function ReadOnlyMaterialTable({
  title,
  linkLabel,
  rows,
}: {
  title: string;
  linkLabel: string;
  rows?: MaterialOrderRow[];
}) {
  const visibleRows = (rows ?? []).filter(
    (row) => hasText(row.link) || hasNumber(row.quantity) || hasNumber(row.cost),
  );
  if (visibleRows.length === 0) return null;

  return (
    <div className="space-y-2">
      <EworksSectionTitle title={title} />
      <div className="overflow-x-auto rounded-lg border border-gray-200">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-gray-50 text-xs uppercase tracking-wide text-optimal-muted">
            <tr>
              <th className="px-3 py-2 font-medium">{linkLabel}</th>
              <th className="px-3 py-2 font-medium">Quantity</th>
              <th className="px-3 py-2 font-medium">Cost</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {visibleRows.map((row, index) => (
              <tr key={index}>
                <td className="px-3 py-2 text-gray-900">{row.link || "—"}</td>
                <td className="px-3 py-2 text-gray-900">{row.quantity ?? "—"}</td>
                <td className="px-3 py-2 text-gray-900">{money(row.cost)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function WorkDetailsReadonly({ details }: { details: WorkBlockSnapshot }) {
  const engineerUnit = details.engineer_time_unit === "days" ? "days" : "hours";
  const engineerDuration =
    details.engineers_required !== false
      ? `${details.engineers_needed ?? details.engineers ?? 1} engineer(s) · ${details.engineer_time_value ?? details.hours ?? details.days ?? "—"} ${engineerUnit}`
      : null;
  const labourDuration =
    details.labour_required && Number(details.labour_needed) > 0
      ? `${details.labour_needed} labour · ${details.labour_time_value ?? details.labourer_days ?? "—"} days`
      : null;

  const chargeLines: string[] = [];
  if (details.parking_required) {
    if (details.parking_type === "hourly") {
      chargeLines.push(
        `Parking: ${money(details.parking_rate_per_hour)}/hr × ${details.parking_hours ?? 0} hrs`,
      );
    } else {
      chargeLines.push(`Parking: ${money(details.parking_fixed_amount)}`);
    }
  }
  if (details.congestion_required && hasNumber(details.congestion_amount)) {
    chargeLines.push(`Congestion: ${money(details.congestion_amount)}`);
  }
  if (hasNumber(details.travel_charge)) {
    chargeLines.push(`Travel: ${money(details.travel_charge)}`);
  }
  if (hasNumber(details.other_charge)) {
    const reason = details.other_charge_reason?.trim();
    chargeLines.push(`Other: ${money(details.other_charge)}${reason ? ` (${reason})` : ""}`);
  }

  return (
    <div className="space-y-4">
      {hasText(details.scope) && (
        <div className="space-y-2">
          <EworksSectionTitle title="Scope of Works" />
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-gray-800">{details.scope}</p>
        </div>
      )}

      <ReadOnlyMaterialTable title="Materials to Order and Cost" linkLabel="Link" rows={details.materials_to_order} />
      <ReadOnlyMaterialTable title="Materials bought off the Shelf and Cost" linkLabel="Item" rows={details.shelf_materials_rows} />

      <div className="grid gap-3 grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
        <DetailRow label="Skill required" value={details.skill_required} />
        <DetailRow label="Best engineer" value={details.best_engineer} />
        <DetailRow label="Subcontractors" value={details.subcontractors} />
      </div>

      {engineerDuration && (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
          <p className="text-xs uppercase tracking-wide text-optimal-muted">Engineer</p>
          <p className="mt-1 text-sm text-gray-900">{engineerDuration}</p>
        </div>
      )}

      {labourDuration && (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
          <p className="text-xs uppercase tracking-wide text-optimal-muted">Labour</p>
          <p className="mt-1 text-sm text-gray-900">{labourDuration}</p>
        </div>
      )}

      <div className="grid gap-3 grid-cols-2 md:grid-cols-4">
        <DetailRow label="Time frame" value={details.time_frame} />
        <DetailRow label="Markup" value={details.markup_value != null ? `${details.markup_value}%` : null} />
      </div>

      {chargeLines.length > 0 && (
        <div className="space-y-2 rounded-lg border border-gray-200 bg-gray-50 p-3">
          <EworksSectionTitle title="Charges" />
          <ul className="space-y-1 text-sm text-gray-900">
            {chargeLines.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </div>
      )}

      <DetailRow label="Any other notes" value={details.other_notes} />
      <DetailRow label="Findings" value={details.findings} />
    </div>
  );
}

export function WorkSection({
  work,
  quote,
  open,
  onToggle,
  selected,
  onSelect,
  selectable = false,
}: {
  work: DashboardWorkItem;
  quote: DashboardQuoteItem;
  open: boolean;
  onToggle: () => void;
  selected?: boolean;
  onSelect?: (checked: boolean) => void;
  selectable?: boolean;
}) {
  const attachments = workAttachments(work);
  const attachmentLabel = attachmentSummary(attachments);
  const workTotal =
    work.labour_subtotal != null || work.materials_subtotal != null
      ? Number(work.labour_subtotal ?? 0) + Number(work.materials_subtotal ?? 0)
      : null;

  return (
    <section
      className={cn(
        "overflow-hidden rounded-lg border bg-gray-50 transition-colors",
        selected ? "border-optimal-orange/60 ring-1 ring-optimal-orange/30" : "border-gray-200",
      )}
    >
      <div className="flex items-stretch">
        {selectable && onSelect && (
          <label className="flex shrink-0 cursor-pointer items-center px-4">
            <input
              type="checkbox"
              checked={selected ?? false}
              onChange={(event) => onSelect(event.target.checked)}
              className="size-5 rounded border-gray-300 bg-optimal-field text-optimal-orange focus:ring-optimal-orange/40"
              aria-label={`Select work ${work.work_index + 1}`}
            />
          </label>
        )}
        <button
          type="button"
          onClick={onToggle}
          className="flex min-w-0 flex-1 items-center gap-3 p-4 text-left transition-colors hover:bg-gray-50"
          aria-expanded={open}
        >
          <span
            className={cn(
              "shrink-0 text-optimal-muted transition-transform duration-200",
              open && "rotate-90",
            )}
            aria-hidden
          >
            ▶
          </span>
          <div className="min-w-0 flex-1">
            <p className="font-semibold text-gray-900">Work {work.work_index + 1}</p>
            {!open && work.scope && (
              <p className="mt-1 truncate text-sm text-optimal-muted">{work.scope}</p>
            )}
            {attachmentLabel && (
              <p className="mt-1 text-xs text-optimal-orange">{attachmentLabel}</p>
            )}
          </div>
          <div className="shrink-0 text-right text-sm">
            <p className="text-xs uppercase tracking-wide text-optimal-muted">Subtotal</p>
            <p className="font-semibold text-gray-900">{money(workTotal)}</p>
          </div>
        </button>
      </div>

      {open && (
        <div className="space-y-4 border-t border-gray-200 px-4 pb-4 pt-3">
          {work.details ? (
            <WorkDetailsReadonly details={work.details} />
          ) : (
            work.scope && <p className="text-sm leading-relaxed text-gray-800">{work.scope}</p>
          )}

          <WorkAttachmentsGallery quote={quote} attachments={attachments} />

          <div className="grid gap-2 text-sm md:grid-cols-2 lg:grid-cols-4">
            <p className="text-optimal-muted">
              Labour subtotal: <span className="font-semibold text-gray-900">{money(work.labour_subtotal)}</span>
            </p>
            <p className="text-optimal-muted">
              Materials subtotal: <span className="font-semibold text-gray-900">{money(work.materials_subtotal)}</span>
            </p>
          </div>

          <div className="space-y-2">
            <EworksSectionTitle title="Internal notes" />
            {work.internal_notes ? (
              <pre className="whitespace-pre-wrap rounded-lg bg-optimal-field p-3 text-xs leading-relaxed text-optimal-field-text">
                {work.internal_notes}
              </pre>
            ) : (
              <p className="text-sm text-optimal-muted">No internal notes for this work.</p>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

export function CombinedNotesModal({
  notesText,
  onClose,
  title = "Combined internal notes",
  onDownloadClient,
  onDownloadOptimal,
  downloadingClient = false,
  downloadingOptimal = false,
  pdfError = null,
}: {
  notesText: string;
  onClose: () => void;
  title?: string;
  onDownloadClient?: () => void | Promise<void>;
  onDownloadOptimal?: () => void | Promise<void>;
  downloadingClient?: boolean;
  downloadingOptimal?: boolean;
  pdfError?: string | null;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(notesText);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-6">
      <div className="absolute inset-0" role="presentation" onClick={onClose} />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="combined-notes-title"
        className="relative z-10 flex max-h-[90vh] w-full max-w-6xl flex-col rounded-lg border border-gray-200 bg-optimal-elevated shadow-xl"
      >
        <div className="flex items-center justify-between gap-3 border-b border-gray-200 px-5 py-4">
          <h2 id="combined-notes-title" className="text-lg font-semibold text-gray-900">
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-sm text-optimal-muted transition-colors hover:bg-gray-50 hover:text-gray-900"
            aria-label="Close"
          >
            ✕
          </button>
        </div>
        <pre className="mx-5 flex-1 overflow-y-auto whitespace-pre-wrap rounded-lg bg-optimal-field p-4 text-xs leading-relaxed text-optimal-field-text">
          {notesText}
        </pre>
        {pdfError && <p className="px-5 text-sm text-red-600">{pdfError}</p>}
        <div className="flex flex-wrap items-center gap-3 border-t border-gray-200 px-5 py-4">
          <EworksButton variant="secondary" onClick={() => void handleCopy()}>
            {copied ? "Copied!" : "Copy to clipboard"}
          </EworksButton>
          {onDownloadClient && (
            <EworksButton
              variant="secondary"
              disabled={downloadingClient}
              onClick={() => void onDownloadClient()}
            >
              {downloadingClient ? "Generating…" : "Download Client View PDF"}
            </EworksButton>
          )}
          {onDownloadOptimal && (
            <EworksButton
              variant="secondary"
              disabled={downloadingOptimal}
              onClick={() => void onDownloadOptimal()}
            >
              {downloadingOptimal ? "Generating…" : "Download Optimal View PDF"}
            </EworksButton>
          )}
          <EworksButton onClick={onClose}>Close</EworksButton>
        </div>
      </div>
    </div>
  );
}

export function WorkSelectionBar({
  selectedCount,
  onCalculate,
  onClear,
  calculating = false,
}: {
  selectedCount: number;
  onCalculate: () => void;
  onClear: () => void;
  calculating?: boolean;
}) {
  return (
    <div className="fixed inset-x-0 bottom-0 z-40 border-t border-gray-200 bg-white/95 px-6 py-4 backdrop-blur lg:px-8">
      <div className="flex w-full items-center gap-4">
        <p className="text-sm font-medium text-gray-900">
          {selectedCount} work{selectedCount === 1 ? "" : "s"} selected
        </p>
        <div className="ml-auto flex items-center gap-3">
          <EworksButton disabled={calculating} onClick={onCalculate}>
            {calculating ? "Calculating…" : "Calculate combined Internal Notes"}
          </EworksButton>
          <button
            type="button"
            onClick={onClear}
            className="px-3 py-2 text-sm text-optimal-muted underline-offset-2 hover:text-gray-900 hover:underline"
          >
            Clear selection
          </button>
        </div>
      </div>
    </div>
  );
}

export function QuoteSummaryCard({ quote }: { quote: DashboardQuoteItem }) {
  return (
    <article className="rounded-lg border border-gray-200 bg-optimal-elevated p-5 transition-colors hover:border-gray-300 hover:bg-gray-50 lg:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <h2 className="text-lg font-semibold text-gray-900">
            Quote {quote.quote_number} · Job {quote.job_number}
          </h2>
          <p className="text-sm text-optimal-muted">
            {quote.client_name} · {quote.trade_name}
          </p>
          <p className="text-xs text-optimal-muted">Submitted {formatSubmittedAt(quote.submitted_at)}</p>
          <span className="mt-2 inline-block rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-optimal-muted">
            {quote.works.length} work{quote.works.length === 1 ? "" : "s"}
          </span>
        </div>
        <div className="text-right">
          <p className="text-xs uppercase tracking-wide text-optimal-muted">Final total</p>
          <p className="text-2xl font-bold text-optimal-orange">{money(quote.final_total)}</p>
        </div>
      </div>
    </article>
  );
}

export function QuotesTable({ quotes }: { quotes: DashboardQuoteItem[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase tracking-wide text-optimal-muted">
          <tr>
            <th className="px-4 py-3 font-medium lg:px-5">Quote</th>
            <th className="px-4 py-3 font-medium lg:px-5">Job</th>
            <th className="px-4 py-3 font-medium lg:px-5">Client</th>
            <th className="px-4 py-3 font-medium lg:px-5">Trade</th>
            <th className="px-4 py-3 font-medium lg:px-5">Submitted</th>
            <th className="px-4 py-3 font-medium lg:px-5">Works</th>
            <th className="px-4 py-3 text-right font-medium lg:px-5">Final total</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {quotes.map((quote) => (
            <tr
              key={quote.session_id}
              className="transition-colors hover:bg-gray-50"
            >
              <td className="px-4 py-3 lg:px-5">
                <Link
                  href={`/eworks/dashboard/${quote.session_id}`}
                  className="font-semibold text-optimal-orange hover:underline"
                >
                  {quote.quote_number}
                </Link>
              </td>
              <td className="px-4 py-3 text-gray-900 lg:px-5">{quote.job_number}</td>
              <td className="px-4 py-3 text-gray-900 lg:px-5">{quote.client_name}</td>
              <td className="px-4 py-3 text-optimal-muted lg:px-5">{quote.trade_name}</td>
              <td className="px-4 py-3 text-optimal-muted lg:px-5">{formatSubmittedAt(quote.submitted_at)}</td>
              <td className="px-4 py-3 text-optimal-muted lg:px-5">{quote.works.length}</td>
              <td className="px-4 py-3 text-right font-semibold text-gray-900 lg:px-5">{money(quote.final_total)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
