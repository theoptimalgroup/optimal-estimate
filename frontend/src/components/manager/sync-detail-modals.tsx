"use client";

import { useState } from "react";
import Link from "next/link";

import {
  DataTable,
  DataTableBody,
  DataTableCell,
  DataTableHead,
  DataTableRow,
  ErrorState,
  LoadingState,
  SectionCard,
  TagBadges,
} from "@/components/ui";
import { SafeRichText } from "@/components/ui/safe-rich-text";
import type { EworksAttachmentSafe, EworksJobSafeDetail, EworksQuoteSafeDetail } from "@/lib/eworks-sync";
import { backfillQuoteSalesAppointments, getSyncedAttachmentDownloadUrl } from "@/lib/eworks-sync";
import { QuoteAssignmentSection } from "@/components/manager/quote-assignment-section";

function fmtDate(val: string | null | undefined): string {
  if (!val) return "Not available";
  try {
    return new Date(val).toLocaleString();
  } catch {
    return val;
  }
}

function fmtMoney(val: number | null | undefined, currency?: string | null): string {
  if (val === null || val === undefined) return "Not available";
  const symbol = currency === "GBP" || !currency ? "£" : `${currency} `;
  return `${symbol}${val.toFixed(2)}`;
}

function displayValue(val: string | number | null | undefined): string {
  if (val === null || val === undefined || val === "") return "Not available";
  return String(val);
}

function displayCustomerName(val: string | null | undefined): string {
  if (val === null || val === undefined || val === "") return "Unknown Customer";
  return val;
}

function fmtFileSize(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined) return "Not available";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function AttachmentsSection({
  attachments,
  loading,
  parentLabel,
}: {
  attachments: EworksAttachmentSafe[];
  loading: boolean;
  parentLabel: "quote" | "job";
}) {
  return (
    <SectionCard title="Attachments" testId="attachments-section">
      {loading ? (
        <LoadingState message="Loading attachments…" />
      ) : attachments.length === 0 ? (
        <p className="text-sm text-slate-600" data-testid="attachments-empty">
          No attachments synced for this {parentLabel}.
        </p>
      ) : (
        <DataTable testId="attachments-table">
          <DataTableHead>
            <DataTableRow>
              <DataTableCell header>Filename</DataTableCell>
              <DataTableCell header>Type</DataTableCell>
              <DataTableCell header numeric>Size</DataTableCell>
              <DataTableCell header>Uploaded By</DataTableCell>
              <DataTableCell header>Created</DataTableCell>
              <DataTableCell header>Download</DataTableCell>
            </DataTableRow>
          </DataTableHead>
          <DataTableBody>
            {attachments.map((attachment) => (
              <DataTableRow key={attachment.id}>
                <DataTableCell>{displayValue(attachment.filename)}</DataTableCell>
                <DataTableCell>{displayValue(attachment.mime_type)}</DataTableCell>
                <DataTableCell numeric>{fmtFileSize(attachment.size_bytes)}</DataTableCell>
                <DataTableCell>{displayValue(attachment.uploaded_by)}</DataTableCell>
                <DataTableCell>{displayValue(attachment.created_on)}</DataTableCell>
                <DataTableCell>
                  <a
                    href={getSyncedAttachmentDownloadUrl(attachment.id)}
                    className="text-sm text-blue-700 hover:underline"
                    data-testid={`attachment-download-${attachment.id}`}
                  >
                    Download
                  </a>
                </DataTableCell>
              </DataTableRow>
            ))}
          </DataTableBody>
        </DataTable>
      )}
    </SectionCard>
  );
}

function TagBadgesSection({ tags }: { tags?: string[] }) {
  return <TagBadges tags={tags} emptyLabel="Not available" />;
}

function fmtSalesAppointment(value: boolean | null | undefined): string {
  if (value === true) return "Yes";
  if (value === false) return "No";
  return "Not available";
}

function AppointmentsTable({
  appointments,
  testId,
}: {
  appointments: EworksJobSafeDetail["appointments"];
  testId: string;
}) {
  if (!appointments?.length) return null;
  return (
    <SectionCard title="Appointments" testId={testId}>
      <DataTable testId={`${testId}-table`}>
        <DataTableHead>
          <DataTableRow>
            <DataTableCell header>User</DataTableCell>
            <DataTableCell header>Email</DataTableCell>
            <DataTableCell header>Appointment Time</DataTableCell>
            <DataTableCell header>Type</DataTableCell>
            <DataTableCell header>Status</DataTableCell>
            <DataTableCell header>Sales</DataTableCell>
          </DataTableRow>
        </DataTableHead>
        <DataTableBody>
          {appointments.map((appointment, index) => (
            <DataTableRow key={`${appointment.appointment_id ?? appointment.user_name ?? "appointment"}-${index}`}>
              <DataTableCell>{displayValue(appointment.user_name)}</DataTableCell>
              <DataTableCell>{displayValue(appointment.user_email)}</DataTableCell>
              <DataTableCell>
                {displayValue(
                  appointment.start_at && appointment.end_at
                    ? `${appointment.start_at} to ${appointment.end_at}`
                    : appointment.start_at ?? appointment.end_at,
                )}
              </DataTableCell>
              <DataTableCell>{displayValue(appointment.appointment_type)}</DataTableCell>
              <DataTableCell>{displayValue(appointment.status)}</DataTableCell>
              <DataTableCell>{fmtSalesAppointment(appointment.is_sales_appointment)}</DataTableCell>
            </DataTableRow>
          ))}
        </DataTableBody>
      </DataTable>
    </SectionCard>
  );
}

function SalesAppointmentsTable({
  appointments,
}: {
  appointments: EworksQuoteSafeDetail["sales_appointments"];
}) {
  if (!appointments?.length) return null;
  return (
    <SectionCard title="Sales Appointments" testId="quote-sales-appointments-section">
      <DataTable testId="quote-sales-appointments-table">
        <DataTableHead>
          <DataTableRow>
            <DataTableCell header>User</DataTableCell>
            <DataTableCell header>Email</DataTableCell>
            <DataTableCell header>Appointment Time</DataTableCell>
            <DataTableCell header>Status</DataTableCell>
            <DataTableCell header>Sales</DataTableCell>
          </DataTableRow>
        </DataTableHead>
        <DataTableBody>
          {appointments.map((appointment, index) => (
            <DataTableRow key={`${appointment.appointment_id ?? appointment.user_name ?? "appointment"}-${index}`}>
              <DataTableCell>{displayValue(appointment.user_name)}</DataTableCell>
              <DataTableCell>{displayValue(appointment.user_email)}</DataTableCell>
              <DataTableCell>
                {displayValue(
                  appointment.start_at && appointment.end_at
                    ? `${appointment.start_at} to ${appointment.end_at}`
                    : appointment.start_at ?? appointment.end_at,
                )}
              </DataTableCell>
              <DataTableCell>{displayValue(appointment.status)}</DataTableCell>
              <DataTableCell>{fmtSalesAppointment(appointment.is_sales_appointment)}</DataTableCell>
            </DataTableRow>
          ))}
        </DataTableBody>
      </DataTable>
    </SectionCard>
  );
}

function DetailField({
  label,
  value,
  align = "left",
}: {
  label: string;
  value: string;
  align?: "left" | "right";
}) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className={`mt-1 text-sm text-slate-900 ${align === "right" ? "text-right font-mono" : ""}`}>{value}</dd>
    </div>
  );
}

function RichTextBlock({
  label,
  value,
  testId,
}: {
  label: string;
  value?: string | null;
  testId?: string;
}) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <SafeRichText value={value} testId={testId} />
    </div>
  );
}

function LinkedEstimateSection({
  linked,
}: {
  linked: EworksQuoteSafeDetail["linked_estimate"] | EworksJobSafeDetail["linked_estimate"];
}) {
  if (linked.has_estimate_session && linked.session_id) {
    return (
      <SectionCard title="Linked Estimate Session" testId="linked-estimate-section">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-slate-900">Estimate Session: Available</p>
            <p className="mt-1 text-sm text-slate-600">
              Status: {displayValue(linked.status)}
              {linked.client_accepted_at ? ` · Accepted ${fmtDate(linked.client_accepted_at)}` : ""}
            </p>
          </div>
          <Link
            href={`/manager/review/${linked.session_id}`}
            className="inline-flex rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
            data-testid="view-estimate-link"
          >
            View Estimate
          </Link>
        </div>
      </SectionCard>
    );
  }

  return (
    <SectionCard title="Linked Estimate Session" testId="linked-estimate-section">
      <p className="text-sm text-slate-600">Estimate Session: Not created yet</p>
    </SectionCard>
  );
}

function ItemsTable({ items }: { items: EworksQuoteSafeDetail["items"] }) {
  if (!items.length) return null;
  return (
    <SectionCard title="Quote Items / Lines" testId="quote-items-section">
      <DataTable testId="quote-items-table">
        <DataTableHead>
          <DataTableRow>
            <DataTableCell header>Item</DataTableCell>
            <DataTableCell header>Description</DataTableCell>
            <DataTableCell header>Quantity</DataTableCell>
            <DataTableCell header numeric>Unit Price</DataTableCell>
            <DataTableCell header numeric>Total</DataTableCell>
          </DataTableRow>
        </DataTableHead>
        <DataTableBody>
          {items.map((item, index) => (
            <DataTableRow key={`${item.name ?? "item"}-${index}`}>
              <DataTableCell>{displayValue(item.name)}</DataTableCell>
              <DataTableCell>{displayValue(item.description)}</DataTableCell>
              <DataTableCell>{displayValue(item.quantity)}</DataTableCell>
              <DataTableCell numeric>{displayValue(item.unit_price)}</DataTableCell>
              <DataTableCell numeric>{displayValue(item.total)}</DataTableCell>
            </DataTableRow>
          ))}
        </DataTableBody>
      </DataTable>
    </SectionCard>
  );
}

function CustomFieldsTable({
  fields,
}: {
  fields: EworksQuoteSafeDetail["custom_fields"] | EworksJobSafeDetail["custom_fields"];
}) {
  if (!fields.length) return null;
  return (
    <SectionCard title="Custom Fields" testId="custom-fields-section">
      <DataTable testId="custom-fields-table">
        <DataTableHead>
          <DataTableRow>
            <DataTableCell header>Label</DataTableCell>
            <DataTableCell header>Field Key</DataTableCell>
            <DataTableCell header>Value</DataTableCell>
          </DataTableRow>
        </DataTableHead>
        <DataTableBody>
          {fields.map((field) => (
            <DataTableRow key={`${field.field_key}-${field.label}`}>
              <DataTableCell>{field.label}</DataTableCell>
              <DataTableCell>{field.field_key}</DataTableCell>
              <DataTableCell>{field.value}</DataTableCell>
            </DataTableRow>
          ))}
        </DataTableBody>
      </DataTable>
    </SectionCard>
  );
}

export function QuoteDetailModal({
  detail,
  quoteId,
  attachments,
  attachmentsLoading,
  loading,
  error,
  onClose,
  allowSalesAppointmentBackfill = false,
}: {
  detail: EworksQuoteSafeDetail | null;
  quoteId: number | null;
  attachments: EworksAttachmentSafe[];
  attachmentsLoading: boolean;
  loading: boolean;
  error: string | null;
  onClose: () => void;
  allowSalesAppointmentBackfill?: boolean;
}) {
  const [salesBackfillLoading, setSalesBackfillLoading] = useState(false);
  const [salesBackfillMessage, setSalesBackfillMessage] = useState<string | null>(null);
  const [salesBackfillError, setSalesBackfillError] = useState<string | null>(null);

  const handleBackfillSalesAppointments = async () => {
    if (!detail) return;
    setSalesBackfillLoading(true);
    setSalesBackfillMessage(null);
    setSalesBackfillError(null);
    try {
      const summary = await backfillQuoteSalesAppointments({
        quoteRef: detail.identity.quote_ref ?? undefined,
        eworksQuoteId: detail.identity.eworks_quote_id,
        limit: 1,
      });
      setSalesBackfillMessage(
        `Sales appointments ${summary.sales_appointments_found} · +${summary.appointments_created} / ~${summary.appointments_updated} updated`,
      );
    } catch (e: unknown) {
      setSalesBackfillError(e instanceof Error ? e.message : "Failed to backfill sales appointments");
    } finally {
      setSalesBackfillLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-4 sm:p-8"
      role="dialog"
      aria-modal="true"
      aria-labelledby="quote-detail-title"
      data-testid="quote-detail-modal"
    >
      <div className="flex max-h-[92vh] w-full max-w-6xl flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-lg">
        <div className="sticky top-0 z-10 flex shrink-0 items-start justify-between gap-4 border-b border-slate-200 bg-white px-6 py-5">
          <div className="min-w-0">
            <h2 id="quote-detail-title" className="text-lg font-semibold text-slate-900">
              Quote Details
            </h2>
            <p className="mt-1 truncate text-sm text-slate-600">
              {detail?.identity.quote_ref ?? detail?.identity.eworks_quote_id ?? "Synced eWorks quote"}
            </p>
            {allowSalesAppointmentBackfill && detail ? (
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => void handleBackfillSalesAppointments()}
                  disabled={salesBackfillLoading}
                  className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                  data-testid="btn-backfill-quote-sales-appointments-single"
                >
                  {salesBackfillLoading ? "Backfilling…" : "Backfill Sales Appointments"}
                </button>
                {salesBackfillMessage ? (
                  <span className="text-xs text-slate-600" data-testid="quote-sales-backfill-message">
                    {salesBackfillMessage}
                  </span>
                ) : null}
                {salesBackfillError ? (
                  <span className="text-xs text-red-600" data-testid="quote-sales-backfill-error">
                    {salesBackfillError}
                  </span>
                ) : null}
              </div>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close quote details"
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/30"
          >
            Close
          </button>
        </div>

        <div className="space-y-5 overflow-y-auto px-6 py-6">
          {loading ? (
            <LoadingState message="Loading quote details…" />
          ) : error ? (
            <ErrorState message={error} />
          ) : detail ? (
            <>
              <SectionCard title="Quote Summary" testId="quote-summary-section">
                <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  <DetailField label="Quote Ref" value={displayValue(detail.identity.quote_ref)} />
                  <DetailField label="eWorks Quote ID" value={String(detail.identity.eworks_quote_id)} />
                  <DetailField
                    label="Status"
                    value={displayValue(detail.identity.status_name ?? detail.identity.status)}
                  />
                  <DetailField label="Synced At" value={fmtDate(detail.identity.synced_at)} />
                </dl>
              </SectionCard>

              <SectionCard title="Customer / Site" testId="customer-site-section">
                <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  <DetailField label="Customer" value={displayCustomerName(detail.customer.customer_name)} />
                  <DetailField label="Contact" value={displayValue(detail.customer.customer_contact_name)} />
                  <DetailField label="Site" value={displayValue(detail.customer.site_name)} />
                  <DetailField label="Address" value={displayValue(detail.customer.site_address)} />
                  <DetailField label="Customer Ref" value={displayValue(detail.customer.customer_ref)} />
                  <DetailField label="PO Ref" value={displayValue(detail.customer.po_ref)} />
                  <DetailField label="WO Ref" value={displayValue(detail.customer.wo_ref)} />
                </dl>
              </SectionCard>

              <SectionCard title="Quote Dates" testId="quote-dates-section">
                <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  <DetailField label="Quote Date" value={displayValue(detail.quote_details.quote_date)} />
                  <DetailField label="Expiry Date" value={displayValue(detail.quote_details.expiry_date)} />
                  {!detail.sales_appointments?.length ? (
                    <>
                      <DetailField label="Preferred Date" value={displayValue(detail.quote_details.preferred_date)} />
                      <DetailField label="Preferred Time" value={displayValue(detail.quote_details.preferred_time)} />
                    </>
                  ) : null}
                  <DetailField label="Converted Date" value={displayValue(detail.dates.converted_date)} />
                  <DetailField label="Accepted Date" value={displayValue(detail.dates.accepted_date)} />
                  <DetailField label="Created On" value={displayValue(detail.dates.created_on)} />
                  <DetailField label="Updated On" value={displayValue(detail.dates.updated_on)} />
                </dl>
              </SectionCard>

              <SalesAppointmentsTable appointments={detail.sales_appointments} />

              <SectionCard title="Description & Notes" testId="description-notes-section">
                <div className="space-y-4">
                  <RichTextBlock
                    label="Description"
                    value={detail.quote_details.description}
                    testId="quote-description-rich-text"
                  />
                  <RichTextBlock
                    label="Customer Notes"
                    value={detail.quote_details.customer_notes}
                    testId="quote-customer-notes-rich-text"
                  />
                  <RichTextBlock
                    label="Terms"
                    value={detail.quote_details.terms}
                    testId="quote-terms-rich-text"
                  />
                  <RichTextBlock
                    label="Notes"
                    value={detail.quote_details.notes}
                    testId="quote-notes-rich-text"
                  />
                </div>
              </SectionCard>

              <SectionCard title="Financial Summary" testId="financial-summary-section">
                <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  <DetailField
                    label="Subtotal"
                    value={fmtMoney(detail.financials.subtotal, detail.financials.currency)}
                    align="right"
                  />
                  <DetailField
                    label="VAT"
                    value={fmtMoney(detail.financials.vat, detail.financials.currency)}
                    align="right"
                  />
                  <DetailField
                    label="Total"
                    value={fmtMoney(detail.financials.total, detail.financials.currency)}
                    align="right"
                  />
                  <DetailField label="Currency" value={displayValue(detail.financials.currency)} />
                  <DetailField label="Discount Type" value={displayValue(detail.financials.discount_type)} />
                  <DetailField label="Discount Value" value={displayValue(detail.financials.discount_value)} />
                </dl>
              </SectionCard>

              <ItemsTable items={detail.items} />

              <SectionCard title="Tags" testId="tags-section">
                <TagBadgesSection tags={detail.tags} />
              </SectionCard>

              <CustomFieldsTable fields={detail.custom_fields} />

              <AttachmentsSection
                attachments={attachments}
                loading={attachmentsLoading}
                parentLabel="quote"
              />

              <LinkedEstimateSection linked={detail.linked_estimate} />
            </>
          ) : null}

          {quoteId ?? detail?.identity.id ? (
            <QuoteAssignmentSection
              quoteId={quoteId ?? detail?.identity.id ?? null}
              appointmentAssignee={detail?.appointment_assignee}
            />
          ) : null}
        </div>
      </div>
    </div>
  );
}

export function JobDetailModal({
  detail,
  attachments,
  attachmentsLoading,
  loading,
  error,
  onClose,
}: {
  detail: EworksJobSafeDetail | null;
  attachments: EworksAttachmentSafe[];
  attachmentsLoading: boolean;
  loading: boolean;
  error: string | null;
  onClose: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-4 sm:p-8"
      role="dialog"
      aria-modal="true"
      aria-labelledby="job-detail-title"
      data-testid="job-detail-modal"
    >
      <div className="flex max-h-[92vh] w-full max-w-6xl flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-lg">
        <div className="sticky top-0 z-10 flex shrink-0 items-start justify-between gap-4 border-b border-slate-200 bg-white px-6 py-5">
          <div className="min-w-0">
            <h2 id="job-detail-title" className="text-lg font-semibold text-slate-900">
              Job Details
            </h2>
            <p className="mt-1 truncate text-sm text-slate-600">
              {detail?.identity.job_ref ?? detail?.identity.eworks_job_id ?? "Synced eWorks job"}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close job details"
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/30"
          >
            Close
          </button>
        </div>

        <div className="space-y-5 overflow-y-auto px-6 py-6">
          {loading ? (
            <LoadingState message="Loading job details…" />
          ) : error ? (
            <ErrorState message={error} />
          ) : detail ? (
            <>
              <SectionCard title="Job Summary" testId="job-summary-section">
                <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  <DetailField label="Job Ref" value={displayValue(detail.identity.job_ref)} />
                  <DetailField label="eWorks Job ID" value={String(detail.identity.eworks_job_id)} />
                  <DetailField
                    label="Status"
                    value={displayValue(detail.identity.status_name ?? detail.identity.status)}
                  />
                  <DetailField label="Synced At" value={fmtDate(detail.identity.synced_at)} />
                </dl>
              </SectionCard>

              <SectionCard title="Customer / Site" testId="job-customer-site-section">
                <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  <DetailField label="Customer" value={displayCustomerName(detail.customer.customer_name)} />
                  <DetailField label="Contact" value={displayValue(detail.customer.customer_contact_name)} />
                  <DetailField label="Site" value={displayValue(detail.customer.site_name)} />
                  <DetailField label="Address" value={displayValue(detail.customer.site_address)} />
                </dl>
              </SectionCard>

              <SectionCard title="Related Quote" testId="related-quote-section">
                <dl className="grid gap-4 sm:grid-cols-2">
                  <DetailField
                    label="eWorks Quote ID"
                    value={displayValue(detail.related_quote.eworks_quote_id)}
                  />
                  <DetailField label="Quote Ref" value={displayValue(detail.related_quote.quote_ref)} />
                </dl>
              </SectionCard>

              <SectionCard title="Job Dates" testId="job-dates-section">
                <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  <DetailField label="Job Date" value={displayValue(detail.job_details.job_date)} />
                  <DetailField label="Completed Date" value={displayValue(detail.dates.completed_date)} />
                  <DetailField label="Created On" value={displayValue(detail.dates.created_on)} />
                  <DetailField label="Updated On" value={displayValue(detail.dates.updated_on)} />
                </dl>
              </SectionCard>

              {detail.appointments?.length ? (
                <AppointmentsTable appointments={detail.appointments} testId="job-appointments-section" />
              ) : null}

              <SectionCard title="Description & Notes" testId="job-description-notes-section">
                <div className="space-y-4">
                  <RichTextBlock
                    label="Description"
                    value={detail.job_details.description}
                    testId="job-description-rich-text"
                  />
                  <RichTextBlock
                    label="Notes"
                    value={detail.job_details.notes}
                    testId="job-notes-rich-text"
                  />
                </div>
              </SectionCard>

              <SectionCard title="Financial Summary" testId="job-financial-summary-section">
                <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  <DetailField
                    label="Subtotal"
                    value={fmtMoney(detail.financials.subtotal, detail.financials.currency)}
                    align="right"
                  />
                  <DetailField
                    label="VAT"
                    value={fmtMoney(detail.financials.vat, detail.financials.currency)}
                    align="right"
                  />
                  <DetailField
                    label="Total"
                    value={fmtMoney(detail.financials.total, detail.financials.currency)}
                    align="right"
                  />
                  <DetailField label="Currency" value={displayValue(detail.financials.currency)} />
                </dl>
              </SectionCard>

              {detail.items.length ? (
                <SectionCard title="Job Items / Lines" testId="job-items-section">
                  <DataTable testId="job-items-table">
                    <DataTableHead>
                      <DataTableRow>
                        <DataTableCell header>Item</DataTableCell>
                        <DataTableCell header>Description</DataTableCell>
                        <DataTableCell header>Quantity</DataTableCell>
                        <DataTableCell header numeric>Unit Price</DataTableCell>
                        <DataTableCell header numeric>Total</DataTableCell>
                      </DataTableRow>
                    </DataTableHead>
                    <DataTableBody>
                      {detail.items.map((item, index) => (
                        <DataTableRow key={`${item.name ?? "item"}-${index}`}>
                          <DataTableCell>{displayValue(item.name)}</DataTableCell>
                          <DataTableCell>{displayValue(item.description)}</DataTableCell>
                          <DataTableCell>{displayValue(item.quantity)}</DataTableCell>
                          <DataTableCell numeric>{displayValue(item.unit_price)}</DataTableCell>
                          <DataTableCell numeric>{displayValue(item.total)}</DataTableCell>
                        </DataTableRow>
                      ))}
                    </DataTableBody>
                  </DataTable>
                </SectionCard>
              ) : null}

              <SectionCard title="Tags" testId="job-tags-section">
                <TagBadgesSection tags={detail.tags} />
              </SectionCard>

              <CustomFieldsTable fields={detail.custom_fields} />

              <AttachmentsSection
                attachments={attachments}
                loading={attachmentsLoading}
                parentLabel="job"
              />

              <LinkedEstimateSection linked={detail.linked_estimate} />
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}
