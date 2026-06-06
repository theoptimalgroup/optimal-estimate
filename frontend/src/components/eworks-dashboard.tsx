"use client";

import Link from "next/link";
import { useState } from "react";
import { EworksButton, EworksSectionTitle, cn } from "@/components/eworks-ui";
import type { DashboardQuoteItem, DashboardWorkItem } from "@/lib/dashboard";
import type { AttachmentMeta } from "@/lib/eworks-calculate-schema";
import type { MaterialOrderRow, MaterialSupplier, WorkBlockSnapshot } from "@/lib/eworks-session";
import { formatSupplierDisplayName, migrateLegacyMaterialRows } from "@/lib/eworks-calculate-schema";
import { cleanRichTextForTextarea } from "@/lib/html-text";
import { getAttachmentUrl } from "@/lib/eworks-session";
import { formatProductLabel, formatWorkLabel, scopePreview } from "@/lib/work-label";

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
      <EworksSectionTitle title="Photos / Videos" />
      {attachments.length === 0 ? (
        <p className="text-sm text-slate-600">No photos or videos uploaded for this work.</p>
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
                className="overflow-hidden rounded-lg border border-slate-200 bg-white transition-colors hover:border-slate-300"
              >
                {isPhoto ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={viewUrl}
                    alt={attachment.file_name}
                    className="aspect-video w-full bg-white object-cover"
                  />
                ) : (
                  <div className="flex aspect-video w-full items-center justify-center bg-white text-3xl text-slate-900">
                    {isVideo ? "▶" : "📄"}
                  </div>
                )}
                <div className="border-t border-black/10 px-3 py-2">
                  <p className="truncate text-sm font-medium text-slate-900">
                    {isPhoto ? "Photo" : isVideo ? "Video" : "File"}
                  </p>
                  <p className="truncate text-xs text-slate-600">{attachment.file_name}</p>
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
      <p className="text-xs uppercase tracking-wide text-slate-600">{label}</p>
      <p className="whitespace-pre-wrap text-sm text-slate-900">{value}</p>
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
      <div className="overflow-x-auto rounded-lg border border-slate-200">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-600">
            <tr>
              <th className="px-3 py-2 font-medium">{linkLabel}</th>
              <th className="px-3 py-2 font-medium">Quantity</th>
              <th className="px-3 py-2 font-medium">Cost</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {visibleRows.map((row, index) => (
              <tr key={index}>
                <td className="px-3 py-2 text-slate-900">{row.link || "—"}</td>
                <td className="px-3 py-2 text-slate-900">{row.quantity ?? "—"}</td>
                <td className="px-3 py-2 text-slate-900">{money(row.cost)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function supplierTotal(supplier: MaterialSupplier): number {
  const linksTotal = (supplier.links ?? []).reduce((sum, row) => {
    const qty = Number(row.quantity) || 0;
    const cost = Number(row.cost) || 0;
    return sum + qty * cost;
  }, 0);
  return linksTotal + (Number(supplier.delivery_charge) || 0);
}

function ReadOnlySupplierMaterials({ suppliers }: { suppliers?: MaterialSupplier[] }) {
  const normalized = migrateLegacyMaterialRows(suppliers ?? []);
  const visible = normalized.filter(
    (supplier) =>
      supplier.links.some((row) => hasText(row.link) || hasNumber(row.quantity) || hasNumber(row.cost)) ||
      hasNumber(supplier.delivery_charge),
  );
  if (visible.length === 0) return null;

  return (
    <div className="space-y-3">
      <EworksSectionTitle title="Materials to Order and Cost" />
      {visible.map((supplier, supplierIndex) => {
        const linkRows = supplier.links.filter(
          (row) => hasText(row.link) || hasNumber(row.quantity) || hasNumber(row.cost),
        );
        return (
          <div key={supplierIndex} className="space-y-2 rounded-lg border border-slate-200 p-3">
            <p className="text-sm font-semibold text-slate-900">
              {formatSupplierDisplayName(supplier, supplierIndex)}
            </p>
            {linkRows.length > 0 && (
              <div className="overflow-x-auto rounded-lg border border-slate-200">
                <table className="min-w-full text-left text-sm">
                  <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-600">
                    <tr>
                      <th className="px-3 py-2 font-medium">Link</th>
                      <th className="px-3 py-2 font-medium">Quantity</th>
                      <th className="px-3 py-2 font-medium">Cost per item</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {linkRows.map((row, index) => (
                      <tr key={index}>
                        <td className="px-3 py-2 text-slate-900">{row.link || "—"}</td>
                        <td className="px-3 py-2 text-slate-900">{row.quantity ?? "—"}</td>
                        <td className="px-3 py-2 text-slate-900">{money(row.cost)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <div className="grid gap-2 text-sm sm:grid-cols-2">
              <p className="text-slate-700">Delivery: {money(supplier.delivery_charge)}</p>
              <p className="font-semibold text-slate-900">Total: {money(supplierTotal(supplier))}</p>
            </div>
          </div>
        );
      })}
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


  return (
    <div className="space-y-4">
      {hasText(details.scope) && (
        <div className="space-y-2">
          <EworksSectionTitle title="Scope of Works" />
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-800">
            {cleanRichTextForTextarea(details.scope)}
          </p>
        </div>
      )}

      <ReadOnlySupplierMaterials suppliers={details.materials_to_order} />
      <ReadOnlyMaterialTable title="Materials bought off the Shelf and Cost" linkLabel="Item" rows={details.shelf_materials_rows} />

      <div className="grid gap-3 grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
        <DetailRow label="Skill required" value={details.skill_required} />
        <DetailRow label="Best engineer" value={details.best_engineer} />
        <DetailRow label="Subcontractors" value={details.subcontractors} />
      </div>

      {engineerDuration && (
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <p className="text-xs uppercase tracking-wide text-slate-600">Engineer</p>
          <p className="mt-1 text-sm text-slate-900">{engineerDuration}</p>
        </div>
      )}

      {labourDuration && (
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <p className="text-xs uppercase tracking-wide text-slate-600">Labour</p>
          <p className="mt-1 text-sm text-slate-900">{labourDuration}</p>
        </div>
      )}

      <div className="grid gap-3 grid-cols-2 md:grid-cols-4">
        <DetailRow label="Time frame" value={details.time_frame} />
        <DetailRow label="Markup" value={details.markup_value != null ? `${details.markup_value}%` : null} />
      </div>

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
  const resolvedProductName = work.product_name ?? work.details?.product_name ?? null;
  const resolvedProductCode = work.product_code ?? work.details?.product_code ?? null;
  const resolvedScope = work.scope ?? work.details?.scope ?? null;
  const workLabel =
    work.display_label ??
    formatWorkLabel({
      product_name: resolvedProductName,
      product_code: resolvedProductCode,
      scope: resolvedScope,
    });
  const hasProductLabel = Boolean(formatProductLabel(resolvedProductName, resolvedProductCode));
  const collapsedScopePreview = scopePreview(resolvedScope);
  const workTotal =
    work.labour_subtotal != null || work.materials_subtotal != null
      ? Number(work.labour_subtotal ?? 0) + Number(work.materials_subtotal ?? 0)
      : null;

  return (
    <section
      data-testid={`work-section-${work.work_index}`}
      className={cn(
        "overflow-hidden rounded-lg border bg-slate-50 transition-colors",
        selected ? "border-blue-200 ring-1 ring-blue-200" : "border-slate-200",
      )}
    >
      <div className="flex items-stretch">
        {selectable && onSelect && (
          <label
            className="flex shrink-0 cursor-pointer items-center px-4"
            onClick={(event) => event.stopPropagation()}
          >
            <input
              type="checkbox"
              data-testid={`work-section-checkbox-${work.work_index}`}
              checked={selected ?? false}
              onChange={(event) => {
                event.stopPropagation();
                onSelect(event.target.checked);
              }}
              onClick={(event) => event.stopPropagation()}
              className="size-5 rounded border-slate-300 bg-white text-blue-600 focus:ring-blue-500/30"
              aria-label={`Select ${workLabel}`}
            />
          </label>
        )}
        <button
          type="button"
          data-testid={`work-section-toggle-${work.work_index}`}
          onClick={onToggle}
          className="flex min-w-0 flex-1 items-center gap-3 p-4 text-left transition-colors hover:bg-slate-50"
          aria-expanded={open}
        >
          <span
            className={cn(
              "shrink-0 text-slate-600 transition-transform duration-200",
              open && "rotate-90",
            )}
            aria-hidden
          >
            ▶
          </span>
          <div className="min-w-0 flex-1">
            <p className="font-semibold text-slate-900" data-testid={`work-section-label-${work.work_index}`}>
              {workLabel}
            </p>
            {!open && collapsedScopePreview && hasProductLabel && (
              <p
                className="mt-1 truncate text-sm text-slate-600"
                data-testid={`work-section-scope-preview-${work.work_index}`}
              >
                {collapsedScopePreview}
              </p>
            )}
            {attachmentLabel && (
              <p className="mt-1 text-xs text-slate-600">{attachmentLabel}</p>
            )}
          </div>
          <div className="shrink-0 text-right text-sm" data-testid={`work-section-subtotal-${work.work_index}`}>
            <p className="text-xs uppercase tracking-wide text-slate-600">Work subtotal</p>
            <p className="font-semibold text-slate-900">{money(workTotal)}</p>
          </div>
        </button>
      </div>

      {open && (
        <div
          className="space-y-4 border-t border-slate-200 px-4 pb-4 pt-3"
          data-testid={`work-section-details-${work.work_index}`}
        >
          {work.details ? (
            <WorkDetailsReadonly details={work.details} />
          ) : (
            work.scope && (
              <p className="text-sm leading-relaxed text-slate-800">{cleanRichTextForTextarea(work.scope)}</p>
            )
          )}

          <WorkAttachmentsGallery quote={quote} attachments={attachments} />

          <div className="grid gap-2 text-sm md:grid-cols-2 lg:grid-cols-4">
            <p className="text-slate-600">
              Labour subtotal: <span className="font-semibold text-slate-900">{money(work.labour_subtotal)}</span>
            </p>
            <p className="text-slate-600">
              Materials subtotal: <span className="font-semibold text-slate-900">{money(work.materials_subtotal)}</span>
            </p>
          </div>

          <div className="space-y-2">
            <EworksSectionTitle title="Internal notes" />
            {work.internal_notes ? (
              <pre className="whitespace-pre-wrap rounded-lg bg-white p-3 text-xs leading-relaxed text-slate-900">
                {work.internal_notes}
              </pre>
            ) : (
              <p className="text-sm text-slate-600">No internal notes for this work.</p>
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
        className="relative z-10 flex max-h-[90vh] w-full max-w-6xl flex-col rounded-lg border border-slate-200 bg-white shadow-xl"
      >
        <div className="flex items-center justify-between gap-3 border-b border-slate-200 px-5 py-4">
          <h2 id="combined-notes-title" className="text-lg font-semibold text-slate-900">
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-sm text-slate-600 transition-colors hover:bg-slate-50 hover:text-slate-900"
            aria-label="Close"
          >
            ✕
          </button>
        </div>
        <pre className="mx-5 flex-1 overflow-y-auto whitespace-pre-wrap rounded-lg bg-white p-4 text-xs leading-relaxed text-slate-900">
          {notesText}
        </pre>
        {pdfError && <p className="px-5 text-sm text-red-600">{pdfError}</p>}
        <div className="flex flex-wrap items-center gap-3 border-t border-slate-200 px-5 py-4">
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
    <div className="fixed inset-x-0 bottom-0 z-40 border-t border-slate-200 bg-white/95 px-6 py-4 backdrop-blur lg:px-8">
      <div className="flex w-full items-center gap-4">
        <p className="text-sm font-medium text-slate-900">
          {selectedCount} work{selectedCount === 1 ? "" : "s"} selected
        </p>
        <div className="ml-auto flex items-center gap-3">
          <EworksButton disabled={calculating} onClick={onCalculate}>
            {calculating ? "Calculating…" : "Calculate combined Internal Notes"}
          </EworksButton>
          <button
            type="button"
            onClick={onClear}
            className="px-3 py-2 text-sm text-slate-600 underline-offset-2 hover:text-slate-900 hover:underline"
          >
            Clear selection
          </button>
        </div>
      </div>
    </div>
  );
}

export function QuoteAdditionalChargesSection({ lines }: { lines: string[] }) {
  if (lines.length === 0) return null;
  return (
    <div className="space-y-2 rounded-lg border border-slate-200 bg-slate-50 p-4" data-testid="quote-additional-charges">
      <EworksSectionTitle title="Additional Charges" />
      <ul className="space-y-1 text-sm text-slate-900">
        {lines.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
    </div>
  );
}

function workSubtotalFromQuote(quote: DashboardQuoteItem): number | null {
  let total = 0;
  let hasValue = false;
  for (const work of quote.works) {
    if (work.labour_subtotal != null || work.materials_subtotal != null) {
      total += Number(work.labour_subtotal ?? 0) + Number(work.materials_subtotal ?? 0);
      hasValue = true;
    }
  }
  return hasValue ? total : null;
}

export function QuoteSummaryBreakdown({ quote }: { quote: DashboardQuoteItem }) {
  const breakdown = quote.breakdown;
  const worksSubtotal = breakdown?.works_subtotal ?? workSubtotalFromQuote(quote);
  const additionalCharges = breakdown?.additional_charges ?? null;
  const vatTotal = breakdown?.vat_total ?? null;
  const finalTotal = breakdown?.final_total ?? quote.final_total ?? null;

  if (worksSubtotal == null && finalTotal == null) {
    return null;
  }

  return (
    <div
      className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4"
      data-testid="quote-summary-breakdown"
    >
      <p className="text-sm font-semibold text-slate-900">Quote Summary</p>
      <dl className="mt-3 space-y-2 text-sm">
        {worksSubtotal != null ? (
          <div className="flex items-center justify-between gap-4">
            <dt className="text-slate-600">Works subtotal</dt>
            <dd className="font-medium text-slate-900" data-testid="quote-summary-works-subtotal">
              {money(worksSubtotal)}
            </dd>
          </div>
        ) : null}
        {additionalCharges != null ? (
          <div className="flex items-center justify-between gap-4">
            <dt className="text-slate-600">Additional charges</dt>
            <dd className="font-medium text-slate-900" data-testid="quote-summary-additional-charges">
              {money(additionalCharges)}
            </dd>
          </div>
        ) : null}
        {vatTotal != null ? (
          <div className="flex items-center justify-between gap-4">
            <dt className="text-slate-600">VAT</dt>
            <dd className="font-medium text-slate-900" data-testid="quote-summary-vat">
              {money(vatTotal)}
            </dd>
          </div>
        ) : null}
        {finalTotal != null ? (
          <div className="flex items-center justify-between gap-4 border-t border-slate-200 pt-2">
            <dt className="font-semibold text-slate-900">Final total</dt>
            <dd className="text-base font-bold text-blue-700" data-testid="quote-summary-final-total">
              {money(finalTotal)}
            </dd>
          </div>
        ) : null}
      </dl>
    </div>
  );
}

export function QuoteSummaryCard({ quote }: { quote: DashboardQuoteItem }) {
  return (
    <article className="rounded-lg border border-slate-200 bg-white p-5 transition-colors hover:border-slate-300 hover:bg-slate-50 lg:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <h2 className="text-lg font-semibold text-slate-900">
            Quote {quote.quote_number} · Job {quote.job_number}
          </h2>
          <p className="text-sm text-slate-600">
            {quote.client_name} · {quote.trade_name}
          </p>
          <p className="text-xs text-slate-600">Submitted {formatSubmittedAt(quote.submitted_at)}</p>
          <span className="mt-2 inline-block rounded-full border border-slate-200 bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600">
            {quote.works.length} work{quote.works.length === 1 ? "" : "s"}
          </span>
        </div>
        <div className="text-right">
          <p className="text-xs uppercase tracking-wide text-slate-600">Final total</p>
          <p className="text-2xl font-bold text-slate-900">{money(quote.final_total)}</p>
        </div>
      </div>
    </article>
  );
}

export function QuotesTable({
  quotes,
  detailHref = (sessionId) => `/eworks/dashboard/${sessionId}`,
}: {
  quotes: DashboardQuoteItem[];
  detailHref?: (sessionId: string) => string;
}) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-600">
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
        <tbody className="divide-y divide-slate-200">
          {quotes.map((quote) => (
            <tr
              key={quote.session_id}
              className="transition-colors hover:bg-slate-50"
            >
              <td className="px-4 py-3 lg:px-5">
                <Link
                  href={detailHref(quote.session_id)}
                  className="font-semibold text-blue-600 hover:text-blue-700 hover:underline"
                >
                  {quote.quote_number}
                </Link>
              </td>
              <td className="px-4 py-3 text-slate-900 lg:px-5">{quote.job_number}</td>
              <td className="px-4 py-3 text-slate-900 lg:px-5">{quote.client_name}</td>
              <td className="px-4 py-3 text-slate-600 lg:px-5">{quote.trade_name}</td>
              <td className="px-4 py-3 text-slate-600 lg:px-5">{formatSubmittedAt(quote.submitted_at)}</td>
              <td className="px-4 py-3 text-slate-600 lg:px-5">{quote.works.length}</td>
              <td className="px-4 py-3 text-right font-semibold text-slate-900 lg:px-5">{money(quote.final_total)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
