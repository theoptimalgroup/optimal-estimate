"use client";

import { useState } from "react";

import { VersionHistoryTable } from "@/components/dashboard/version-history-table";
import type { DashboardQuoteGroupVersionItem } from "@/lib/dashboard";

type SessionVersionHistoryPanelProps = {
  sessionId: string;
  versions: DashboardQuoteGroupVersionItem[];
  onViewSession?: (sessionId: string, versionNumber?: number) => void;
  onDownloadPdf?: (sessionId: string, versionNumber: number) => void | Promise<void>;
};

export function SessionVersionHistoryPanel({
  sessionId,
  versions,
  onViewSession,
  onDownloadPdf,
}: SessionVersionHistoryPanelProps) {
  const [expanded, setExpanded] = useState(false);

  if (versions.length <= 1) {
    return null;
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white" data-testid={`session-version-history-${sessionId}`}>
      <button
        type="button"
        className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-medium text-slate-900"
        onClick={() => setExpanded((value) => !value)}
        data-testid={`session-version-history-toggle-${sessionId}`}
      >
        <span>Version history ({versions.length})</span>
        <span className="text-slate-500">{expanded ? "Hide" : "Show"}</span>
      </button>
      {expanded ? (
        <div className="border-t border-slate-200 px-2 pb-3">
          <VersionHistoryTable
            sessionId={sessionId}
            versions={versions}
            onView={(versionNumber) => onViewSession?.(sessionId, versionNumber)}
            onDownload={(versionNumber) => void onDownloadPdf?.(sessionId, versionNumber)}
          />
        </div>
      ) : null}
    </div>
  );
}
