import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export type StatusTone = "neutral" | "success" | "warning" | "error" | "info";

export const badgeToneClasses: Record<StatusTone, string> = {
  neutral: "border border-slate-200 bg-slate-100 text-slate-700",
  success: "border border-emerald-200 bg-emerald-50 text-emerald-700",
  warning: "border border-amber-200 bg-amber-50 text-amber-800",
  error: "border border-red-200 bg-red-50 text-red-700",
  info: "border border-blue-200 bg-blue-50 text-blue-700",
};

const toneStyles = badgeToneClasses;

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
    case "partial":
      return "warning";
    case "running":
    case "in_progress":
      return "info";
    case "failed":
    case "error":
      return "error";
    case "skipped":
    case "pending":
    default:
      return "neutral";
  }
}

export function roleTone(role: string): StatusTone {
  switch (role.toLowerCase()) {
    case "admin":
      return "error";
    case "manager":
      return "info";
    case "estimator":
      return "success";
    case "engineer":
      return "warning";
    default:
      return "neutral";
  }
}

export function activeStatusTone(active: boolean): StatusTone {
  return active ? "success" : "neutral";
}
