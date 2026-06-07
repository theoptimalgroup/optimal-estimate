"use client";

import Link from "next/link";

import { VersionHistoryTable } from "@/components/dashboard/version-history-table";
import { SecondaryButton } from "@/components/ui";
import type { DashboardQuoteGroupVersionItem } from "@/lib/dashboard";

type VersionHistoryModalProps = {
  open: boolean;
  assigneeName: string;
  sessionId: string;
  quoteRef?: string | null;
  versions: DashboardQuoteGroupVersionItem[];
  sessionDetailHref?: (sessionId: string) => string;
  onClose: () => void;
  onDownloadPdf?: (sessionId: string, versionNumber: number) => void | Promise<void>;
};

export function VersionHistoryModal({
  open,
  assigneeName,
  sessionId,
  quoteRef,
  versions,
  sessionDetailHref = (id) => `/manager/review/${id}`,
  onClose,
  onDownloadPdf,
}: VersionHistoryModalProps) {
  if (!open) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4"
      role="presentation"
      onClick={onClose}
      data-testid={`version-history-modal-backdrop-${sessionId}`}
    >
      <div
        className="max-h-[85vh] w-full max-w-4xl overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby={`version-history-title-${sessionId}`}
        onClick={(event) => event.stopPropagation()}
        data-testid={`version-history-modal-${sessionId}`}
      >
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-5 py-4">
          <div>
            <h2 id={`version-history-title-${sessionId}`} className="text-lg font-semibold text-slate-900">
              Version History — {assigneeName}
            </h2>
            {quoteRef ? <p className="mt-1 text-sm text-slate-600">{quoteRef}</p> : null}
          </div>
          <SecondaryButton type="button" onClick={onClose} data-testid={`version-history-close-${sessionId}`}>
            Close
          </SecondaryButton>
        </div>
        <div className="max-h-[calc(85vh-5rem)] overflow-y-auto px-2 py-3">
          <VersionHistoryTable
            sessionId={sessionId}
            versions={versions}
            onView={(versionNumber) => {
              window.location.href = `${sessionDetailHref(sessionId)}?version=${versionNumber}`;
            }}
            onDownload={onDownloadPdf ? (versionNumber) => void onDownloadPdf(sessionId, versionNumber) : undefined}
          />
        </div>
        <div className="border-t border-slate-200 px-5 py-3 text-sm text-slate-500">
          <Link href={sessionDetailHref(sessionId)} className="font-medium text-blue-600 hover:text-blue-700">
            View latest submission details
          </Link>
        </div>
      </div>
    </div>
  );
}
