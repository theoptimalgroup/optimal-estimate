"use client";

import { formatSubmittedAt, money } from "@/components/dashboard/quote-groups-table";
import { StatusBadge } from "@/components/ui";
import type { DashboardQuoteGroupVersionItem } from "@/lib/dashboard";

type VersionHistoryTableProps = {
  sessionId: string;
  versions: DashboardQuoteGroupVersionItem[];
  onView?: (versionNumber: number) => void;
  onDownload?: (versionNumber: number) => void;
};

function revisionReasonLabel(reason: string | null | undefined): string {
  const text = (reason ?? "").trim();
  return text || "Initial submission";
}

export function VersionHistoryTable({ sessionId, versions, onView, onDownload }: VersionHistoryTableProps) {
  return (
    <div className="overflow-x-auto" data-testid={`version-history-table-${sessionId}`}>
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-600">
          <tr>
            <th className="px-3 py-2">Version</th>
            <th className="px-3 py-2">Submitted At</th>
            <th className="px-3 py-2">Submitted By</th>
            <th className="px-3 py-2">Revision Reason</th>
            <th className="px-3 py-2 text-right">Final Total</th>
            <th className="px-3 py-2">Current</th>
            <th className="px-3 py-2">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200">
          {versions.map((version) => (
            <tr key={version.version_number} data-testid={`version-row-${sessionId}-${version.version_number}`}>
              <td className="px-3 py-2 font-medium text-slate-900">v{version.version_number}</td>
              <td className="px-3 py-2 text-slate-600">
                {version.submitted_at ? formatSubmittedAt(version.submitted_at) : "—"}
              </td>
              <td className="px-3 py-2 text-slate-900">{version.submitted_by_name ?? "—"}</td>
              <td className="px-3 py-2 text-slate-600" data-testid={`version-reason-${sessionId}-${version.version_number}`}>
                {revisionReasonLabel(version.revision_reason)}
              </td>
              <td className="px-3 py-2 text-right font-semibold tabular-nums text-slate-900">{money(version.final_total)}</td>
              <td className="px-3 py-2">
                {version.is_current ? (
                  <StatusBadge tone="success" data-testid={`version-current-${sessionId}-${version.version_number}`}>
                    Current
                  </StatusBadge>
                ) : (
                  <span className="text-slate-400">—</span>
                )}
              </td>
              <td className="px-3 py-2">
                <div className="flex flex-wrap gap-2">
                  {onView ? (
                    <button
                      type="button"
                      className="text-sm font-medium text-blue-600 hover:text-blue-700"
                      onClick={() => onView(version.version_number)}
                      data-testid={`version-view-${sessionId}-${version.version_number}`}
                    >
                      View
                    </button>
                  ) : null}
                  {onDownload ? (
                    <button
                      type="button"
                      className="text-sm font-medium text-blue-600 hover:text-blue-700"
                      onClick={() => onDownload(version.version_number)}
                      data-testid={`version-download-${sessionId}-${version.version_number}`}
                    >
                      PDF
                    </button>
                  ) : null}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
