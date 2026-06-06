import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export function FilterBar({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col gap-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:flex-row sm:flex-wrap sm:items-end",
        className,
      )}
      data-testid="filter-bar"
    >
      {children}
    </div>
  );
}

export function FilterField({
  label,
  helper,
  error,
  children,
  className,
}: {
  label: string;
  helper?: string;
  error?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex min-w-[140px] flex-1 flex-col gap-1.5", className)}>
      <label className="text-sm font-medium text-slate-700">{label}</label>
      {children}
      {error ? (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      ) : helper ? (
        <p className="text-xs text-slate-500">{helper}</p>
      ) : null}
    </div>
  );
}

export const formInputClass =
  "h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 shadow-sm placeholder:text-slate-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400";

export const formTextareaClass =
  "min-h-[120px] w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 shadow-sm placeholder:text-slate-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 disabled:cursor-not-allowed disabled:bg-slate-50";

export const filterInputClass = formInputClass;
export const filterSelectClass = formInputClass;
