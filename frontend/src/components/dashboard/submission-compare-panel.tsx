"use client";

import { useState } from "react";
import { Download } from "lucide-react";

import { StatusBadge } from "@/components/ui";
import type {
  DashboardQuoteGroupAssignmentSubmissionRow,
  DashboardQuoteGroupComparisonChargeLine,
  DashboardQuoteGroupComparisonWorkBreakdown,
  DashboardSelectedEstimateDecision,
  SelectedEstimatePdfView,
} from "@/lib/dashboard";
import { downloadSelectedEstimatePdf } from "@/lib/dashboard-auth";
import { formatSubmittedAt, money } from "@/components/dashboard/quote-groups-table";

const MAX_COMPARE = 3;

function formatRole(value: string | null | undefined): string {
  if (!value) return "—";
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function parseAmount(value: number | string | null | undefined): number | null {
  if (value == null || value === "") return null;
  const amount = Number(value);
  return Number.isNaN(amount) ? null : amount;
}

function lowestPriceSessionIds(rows: DashboardQuoteGroupAssignmentSubmissionRow[]): Set<string> {
  const amounts = rows
    .map((row) => ({
      sessionId: row.linked_session_id,
      amount: parseAmount(row.final_total),
    }))
    .filter((item): item is { sessionId: string; amount: number } => item.sessionId != null && item.amount != null);

  if (amounts.length === 0) return new Set();
  const minAmount = Math.min(...amounts.map((item) => item.amount));
  return new Set(amounts.filter((item) => item.amount === minAmount).map((item) => item.sessionId));
}

function compareGridClass(count: number): string {
  if (count === 1) return "grid-cols-1";
  if (count === 2) return "grid-cols-1 md:grid-cols-2";
  return "grid-cols-1 md:grid-cols-2 xl:grid-cols-3";
}

function formatVatLabel(vatRate: number | string | null | undefined): string {
  const rate = parseAmount(vatRate);
  if (rate == null) return "VAT";
  const formatted = Number.isInteger(rate) ? String(rate) : rate.toFixed(2).replace(/\.?0+$/, "");
  return `VAT ${formatted}%`;
}

function workProductTitle(work: DashboardQuoteGroupComparisonWorkBreakdown, index: number): string {
  const product = (work.product_name || work.product_code || "").trim();
  if (product) return product;
  const scope = (work.scope_preview || "").trim();
  if (scope) return scope.split("\n")[0];
  return `Work ${index + 1}`;
}

function nonZeroCharges(charges: DashboardQuoteGroupComparisonChargeLine[]): DashboardQuoteGroupComparisonChargeLine[] {
  return charges.filter((charge) => {
    const amount = parseAmount(charge.amount);
    return amount != null && amount !== 0;
  });
}

function isRowEstimateSelected(
  row: DashboardQuoteGroupAssignmentSubmissionRow,
  selectedEstimateDecision?: DashboardSelectedEstimateDecision | null,
): boolean {
  if (row.is_selected_estimate || row.is_job_assigned) return true;
  if (!row.linked_session_id || !selectedEstimateDecision?.selected_session_id) return false;
  return selectedEstimateDecision.selected_session_id === row.linked_session_id;
}

function isEstimateSelectedElsewhere(
  row: DashboardQuoteGroupAssignmentSubmissionRow,
  selectedEstimateDecision?: DashboardSelectedEstimateDecision | null,
): boolean {
  if (!selectedEstimateDecision?.selected_session_id || !row.linked_session_id) return false;
  return selectedEstimateDecision.selected_session_id !== row.linked_session_id;
}

const PDF_DOWNLOAD_SECONDARY: {
  view: SelectedEstimatePdfView;
  label: string;
  title?: string;
}[] = [
  { view: "internal", label: "Internal PDF" },
  { view: "full-estimate", label: "Full Estimate", title: "Download full estimate PDF" },
  { view: "all-trades", label: "All Trades", title: "Download all trades combined PDF" },
];

function BreakdownRow({
  label,
  amount,
  indent = false,
  testId,
}: {
  label: string;
  amount: number | string | null | undefined;
  indent?: boolean;
  testId?: string;
}) {
  return (
    <div className={`flex justify-between gap-4 ${indent ? "pl-4" : ""}`} data-testid={testId}>
      <dt className="text-slate-500">{label}</dt>
      <dd className="tabular-nums text-slate-900">{money(amount)}</dd>
    </div>
  );
}

export function SubmissionComparePanel({
  rows,
  onSelectEstimate,
  selectingSessionId,
  selectedEstimateDecision,
  quoteRef,
  allowReselect = false,
}: {
  rows: DashboardQuoteGroupAssignmentSubmissionRow[];
  onSelectEstimate: (row: DashboardQuoteGroupAssignmentSubmissionRow) => Promise<void>;
  selectingSessionId?: string | null;
  selectedEstimateDecision?: DashboardQuoteJobAssignmentDecision | null;
  quoteRef?: string | null;
  allowReselect?: boolean;
}) {
  const [downloadingKey, setDownloadingKey] = useState<string | null>(null);
  const [pdfError, setPdfError] = useState<string | null>(null);

  if (rows.length === 0) return null;

  const cheapestIds = lowestPriceSessionIds(rows);

  const handleDownloadPdf = async (sessionId: string, view: SelectedEstimatePdfView) => {
    const resolvedView = view === "full-estimate" ? "combined" : view;
    const downloadKey = `${sessionId}-${resolvedView}`;
    setDownloadingKey(downloadKey);
    setPdfError(null);
    try {
      await downloadSelectedEstimatePdf(sessionId, view, quoteRef ?? undefined);
    } catch (err) {
      setPdfError(err instanceof Error ? err.message : "PDF download failed");
    } finally {
      setDownloadingKey(null);
    }
  };

  return (
    <div className="space-y-4" data-testid="submission-compare-panel">
      <h3 className="text-base font-semibold text-slate-900">Compare selected submissions</h3>
      <div className={`grid gap-4 ${compareGridClass(rows.length)}`}>
        {rows.map((row) => {
          const sessionId = row.linked_session_id ?? "unknown";
          const summary = row.comparison_summary;
          const isCheapest = row.linked_session_id != null && cheapestIds.has(row.linked_session_id);
          const isSelected = isRowEstimateSelected(row, selectedEstimateDecision);
          const selectedElsewhere = isEstimateSelectedElsewhere(row, selectedEstimateDecision);
          const showSelectButton =
            (row.can_select_estimate ?? row.can_assign_job) &&
            row.linked_session_id != null &&
            !isSelected &&
            (allowReselect || !selectedElsewhere);
          const roleLabel = row.submitted_by_role
            ? formatRole(row.submitted_by_role)
            : formatRole(row.assignment_type);
          const finalTotal = summary?.final_total ?? row.final_total;
          const charges = summary?.additional_charges ?? [];
          const visibleCharges = nonZeroCharges(charges);
          const allChargesZero = charges.length > 0 && visibleCharges.length === 0;

          return (
            <div
              key={sessionId}
              className={
                isSelected
                  ? "flex h-full flex-col rounded-xl border-2 border-emerald-400 bg-emerald-50/40 p-4 shadow-sm"
                  : "flex h-full flex-col rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
              }
              data-testid={`compare-card-${sessionId}`}
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="font-semibold text-slate-900">{row.assignee_name}</p>
                  <p className="text-sm text-slate-600">{roleLabel}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {isCheapest ? (
                    <StatusBadge tone="success" data-testid={`compare-lowest-${sessionId}`}>
                      Lowest price
                    </StatusBadge>
                  ) : null}
                  {row.is_latest ? (
                    <StatusBadge tone="neutral" data-testid={`compare-latest-${sessionId}`}>
                      Latest
                    </StatusBadge>
                  ) : null}
                  {isSelected ? (
                    <StatusBadge tone="success" data-testid={`compare-assigned-${sessionId}`}>
                      Selected Estimate
                    </StatusBadge>
                  ) : null}
                </div>
              </div>

              <p className="mt-3 text-sm text-slate-500">
                Submitted at{" "}
                <span className="text-slate-900">{row.submitted_at ? formatSubmittedAt(row.submitted_at) : "—"}</span>
              </p>

              {summary ? (
                <>
                  {summary.works && summary.works.length > 0 ? (
                    <div className="mt-4 border-t border-slate-200 pt-4" data-testid={`compare-works-${sessionId}`}>
                      <p className="text-sm font-medium text-slate-900">Work breakdown</p>
                      <dl className="mt-2 space-y-3 text-sm">
                        {summary.works.map((work, index) => {
                          const scopePreview = (work.scope_preview || "").trim();
                          const productCode = (work.product_code || "").trim();
                          const showCode = productCode && productCode !== (work.product_name || "").trim();

                          return (
                            <div key={`${sessionId}-work-${index}`} data-testid={`compare-work-${sessionId}-${index}`}>
                              <p className="font-medium text-slate-900">{workProductTitle(work, index)}</p>
                              {showCode ? <p className="text-xs text-slate-500">{productCode}</p> : null}
                              {scopePreview ? (
                                <p className="mt-1 line-clamp-2 text-xs text-slate-500">{scopePreview}</p>
                              ) : null}
                              <div className="mt-1 space-y-1">
                                <BreakdownRow label="Labour" amount={work.labour_subtotal} indent />
                                <BreakdownRow label="Materials" amount={work.materials_subtotal} indent />
                                <BreakdownRow label="Work subtotal" amount={work.work_subtotal} />
                              </div>
                            </div>
                          );
                        })}
                      </dl>
                    </div>
                  ) : null}

                  {charges.length > 0 ? (
                    <div
                      className="mt-4 border-t border-slate-200 pt-4"
                      data-testid={`compare-charge-lines-${sessionId}`}
                    >
                      <dl className="space-y-1 text-sm">
                        {allChargesZero ? (
                          <BreakdownRow
                            label="Additional charges"
                            amount={summary.additional_charges_total ?? 0}
                            testId={`compare-additional-charges-summary-${sessionId}`}
                          />
                        ) : (
                          <>
                            {visibleCharges.map((charge) => (
                              <BreakdownRow
                                key={`${sessionId}-${charge.label}`}
                                label={charge.label}
                                amount={charge.amount}
                                testId={`compare-charge-${sessionId}-${charge.label.toLowerCase()}`}
                              />
                            ))}
                            <div className="border-t border-slate-200 pt-1">
                              <BreakdownRow
                                label="Total"
                                amount={summary.additional_charges_total}
                                testId={`compare-additional-charges-total-${sessionId}`}
                              />
                            </div>
                          </>
                        )}
                      </dl>
                    </div>
                  ) : null}

                  <div
                    className="mt-4 border-t border-slate-200 pt-4"
                    data-testid={`compare-calculation-${sessionId}`}
                  >
                    <p className="text-sm font-medium text-slate-900">Cost breakdown</p>
                    <dl className="mt-2 space-y-2 text-sm">
                      <BreakdownRow label="Works subtotal" amount={summary.works_subtotal} />
                      <BreakdownRow
                        label="Labour"
                        amount={summary.labour_subtotal}
                        indent
                        testId={`compare-labour-${sessionId}`}
                      />
                      <BreakdownRow
                        label="Materials"
                        amount={summary.materials_subtotal}
                        indent
                        testId={`compare-materials-${sessionId}`}
                      />
                      <BreakdownRow
                        label="Additional charges"
                        amount={summary.additional_charges_total}
                        testId={`compare-additional-charges-${sessionId}`}
                      />
                      <BreakdownRow
                        label={formatVatLabel(summary.vat_rate)}
                        amount={summary.vat_total}
                        testId={`compare-vat-${sessionId}`}
                      />
                    </dl>
                  </div>

                  <div
                    className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4"
                    data-testid={`compare-final-total-${sessionId}`}
                  >
                    <p className="text-sm text-slate-500">Final total</p>
                    <p className="text-2xl font-bold tabular-nums text-slate-900">{money(finalTotal)}</p>
                  </div>
                </>
              ) : (
                <div
                  className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4"
                  data-testid={`compare-final-total-${sessionId}`}
                >
                  <p className="text-sm text-slate-500">Final total</p>
                  <p className="text-2xl font-bold tabular-nums text-slate-900">{money(finalTotal)}</p>
                </div>
              )}

              {isSelected && row.linked_session_id ? (
                <div
                  className="mt-auto border-t border-slate-200 pt-4"
                  data-testid={`compare-download-pdfs-${sessionId}`}
                >
                  <h4 className="text-sm font-medium text-slate-900">Download PDFs</h4>
                  {(() => {
                    const clientDownloadKey = `${row.linked_session_id}-client`;
                    const isClientDownloading = downloadingKey === clientDownloadKey;
                    return (
                      <button
                        type="button"
                        className="mt-2 inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-blue-600 text-sm font-medium text-white transition hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-50"
                        disabled={isClientDownloading}
                        onClick={() => void handleDownloadPdf(row.linked_session_id!, "client")}
                        data-testid={`download-pdf-client-${sessionId}`}
                      >
                        <Download className="h-4 w-4 shrink-0" aria-hidden="true" />
                        {isClientDownloading ? "Generating…" : "Download Client PDF"}
                      </button>
                    );
                  })()}
                  <div className="mt-3 flex flex-wrap items-center justify-center gap-x-3 gap-y-2 text-sm">
                    {PDF_DOWNLOAD_SECONDARY.map(({ view, label, title }, index) => {
                      const resolvedView = view === "full-estimate" ? "combined" : view;
                      const downloadKey = `${row.linked_session_id}-${resolvedView}`;
                      const isDownloading = downloadingKey === downloadKey;
                      return (
                        <span key={resolvedView} className="inline-flex items-center gap-x-3">
                          {index > 0 ? (
                            <span className="text-slate-300" aria-hidden="true">
                              •
                            </span>
                          ) : null}
                          <button
                            type="button"
                            className="text-blue-600 transition hover:text-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-50"
                            title={title}
                            disabled={isDownloading}
                            onClick={() => void handleDownloadPdf(row.linked_session_id!, view)}
                            data-testid={`download-pdf-${resolvedView}-${sessionId}`}
                          >
                            {isDownloading ? "Generating…" : label}
                          </button>
                        </span>
                      );
                    })}
                  </div>
                  {pdfError ? <p className="mt-2 text-sm text-red-600">{pdfError}</p> : null}
                </div>
              ) : null}

              {showSelectButton ? (
                <button
                  type="button"
                  className="mt-auto w-full rounded-lg bg-blue-600 px-4 py-2 pt-4 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                  disabled={selectingSessionId === row.linked_session_id}
                  onClick={() => void onSelectEstimate(row)}
                  data-testid={`select-estimate-${row.linked_session_id}`}
                >
                  {selectingSessionId === row.linked_session_id ? "Selecting…" : "Select this estimate"}
                </button>
              ) : selectedElsewhere && selectedEstimateDecision && !allowReselect ? (
                <p
                  className="mt-auto pt-4 text-sm text-slate-500"
                  data-testid={`compare-selected-elsewhere-${sessionId}`}
                >
                  Selected estimate: {selectedEstimateDecision.assignee_name}
                </p>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export { MAX_COMPARE };
