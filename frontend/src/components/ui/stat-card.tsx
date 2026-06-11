import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

type StatCardProps = {
  label: string;
  value: ReactNode;
  hint?: string;
  icon?: ReactNode;
  iconClassName?: string;
  className?: string;
  "data-testid"?: string;
};

export function StatCard({
  label,
  value,
  hint,
  icon,
  iconClassName,
  className,
  "data-testid": testId,
}: StatCardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border border-slate-200 bg-white p-6 shadow-sm",
        className,
      )}
      data-testid={testId}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <p className="text-sm font-medium text-slate-600">{label}</p>
          <p className="text-2xl font-semibold tracking-tight text-slate-900">{value}</p>
          {hint ? <p className="text-xs text-slate-500">{hint}</p> : null}
        </div>
        {icon ? (
          <div
            className={cn(
              "flex size-9 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-slate-50 text-slate-500",
              iconClassName,
            )}
          >
            {icon}
          </div>
        ) : null}
      </div>
    </div>
  );
}
