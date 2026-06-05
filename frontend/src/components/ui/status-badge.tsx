import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export type StatusTone = "neutral" | "success" | "warning" | "error" | "info";

const toneStyles: Record<StatusTone, string> = {
  neutral: "bg-slate-100 text-slate-700",
  success: "bg-emerald-100 text-emerald-700",
  warning: "bg-amber-100 text-amber-800",
  error: "bg-red-100 text-red-700",
  info: "bg-blue-100 text-blue-700",
};

export function StatusBadge({
  children,
  tone = "neutral",
  className,
  "data-testid": testId,
}: {
  children: ReactNode;
  tone?: StatusTone;
  className?: string;
  "data-testid"?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md px-2.5 py-0.5 text-xs font-medium",
        toneStyles[tone],
        className,
      )}
      data-testid={testId}
    >
      {children}
    </span>
  );
}

export function quoteStatusTone(status: string): StatusTone {
  switch (status.toLowerCase().replace(/\s+/g, "_")) {
    case "accepted":
      return "success";
    case "submitted":
      return "info";
    case "reopened":
    case "needs_changes":
    case "needs_review":
      return "warning";
    case "rejected":
    case "failed":
      return "error";
    case "draft":
    case "in_progress":
      return "neutral";
    default:
      return "neutral";
  }
}

export function syncStatusTone(status: string): StatusTone {
  switch (status.toLowerCase()) {
    case "success":
    case "synced":
      return "success";
    case "failed":
    case "error":
      return "error";
    case "skipped":
    case "pending":
    default:
      return "neutral";
  }
}

export function activeStatusTone(active: boolean): StatusTone {
  return active ? "success" : "neutral";
}
