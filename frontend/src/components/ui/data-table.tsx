import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/utils";

type DataTableProps = {
  children: ReactNode;
  className?: string;
  testId?: string;
};

export function DataTable({ children, className, testId }: DataTableProps) {
  return (
    <div
      className={cn("overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm", className)}
      data-testid={testId}
    >
      <table className="min-w-full divide-y divide-slate-200 text-sm">{children}</table>
    </div>
  );
}

export function DataTableHead({ children, sticky }: { children: ReactNode; sticky?: boolean }) {
  return (
    <thead className={cn("bg-slate-50", sticky && "sticky top-0 z-10 shadow-[0_1px_0_0_rgb(226_232_240)]")}>
      <tr className="text-left text-xs font-medium uppercase tracking-wide text-slate-600">{children}</tr>
    </thead>
  );
}

export function DataTableBody({ children }: { children: ReactNode }) {
  return <tbody className="divide-y divide-slate-200 bg-white">{children}</tbody>;
}

export function DataTableRow({
  children,
  className,
  onClick,
  ...props
}: HTMLAttributes<HTMLTableRowElement> & {
  children: ReactNode;
}) {
  return (
    <tr
      className={cn("transition-colors hover:bg-slate-50", onClick && "cursor-pointer", className)}
      onClick={onClick}
      {...props}
    >
      {children}
    </tr>
  );
}

export function DataTableCell({
  children,
  className,
  header,
  align = "left",
  numeric,
}: {
  children: ReactNode;
  className?: string;
  header?: boolean;
  align?: "left" | "right" | "center";
  /** @deprecated Prefer align="right" */
  numeric?: boolean;
}) {
  const resolvedAlign = numeric ? "right" : align;
  const alignClass =
    resolvedAlign === "right" ? "text-right" : resolvedAlign === "center" ? "text-center" : "text-left";

  if (header) {
    return <th className={cn("px-4 py-3 font-medium", alignClass, className)}>{children}</th>;
  }
  return <td className={cn("px-4 py-3 text-slate-900", alignClass, className)}>{children}</td>;
}

export function PaginationBar({
  total,
  offset,
  limit,
  onPageChange,
  className,
}: {
  total: number;
  offset: number;
  limit: number;
  onPageChange: (nextOffset: number) => void;
  className?: string;
}) {
  const page = Math.floor(offset / limit) + 1;
  const totalPages = Math.max(1, Math.ceil(total / limit));
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + limit, total);

  return (
    <div
      className={cn(
        "flex flex-col gap-3 border-t border-slate-200 px-4 py-3 text-sm text-slate-600 sm:flex-row sm:items-center sm:justify-between",
        className,
      )}
      data-testid="pagination-bar"
    >
      <p>
        Showing {from}–{to} of {total}
      </p>
      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={offset <= 0}
          onClick={() => onPageChange(Math.max(0, offset - limit))}
          className="h-9 rounded-lg border border-slate-300 bg-white px-3 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Previous
        </button>
        <span className="px-2 tabular-nums text-slate-600">
          Page {page} of {totalPages}
        </span>
        <button
          type="button"
          disabled={offset + limit >= total}
          onClick={() => onPageChange(offset + limit)}
          className="h-9 rounded-lg border border-slate-300 bg-white px-3 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Next
        </button>
      </div>
    </div>
  );
}
