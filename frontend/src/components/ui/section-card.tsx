import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

type SectionCardProps = {
  title?: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
  padding?: "none" | "sm" | "md";
  testId?: string;
};

export function SectionCard({
  title,
  description,
  actions,
  children,
  className,
  bodyClassName,
  padding = "md",
  testId,
}: SectionCardProps) {
  const paddingClass = padding === "none" ? "p-0" : padding === "sm" ? "p-5" : "p-6";

  return (
    <section
      className={cn(
        "overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm",
        className,
      )}
      data-testid={testId}
    >
      {title || actions ? (
        <div className="flex flex-col gap-2 border-b border-slate-200 px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            {title ? <h2 className="text-base font-semibold text-slate-900">{title}</h2> : null}
            {description ? <p className="mt-0.5 text-sm text-slate-600">{description}</p> : null}
          </div>
          {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
        </div>
      ) : null}
      <div className={cn(paddingClass, bodyClassName)}>{children}</div>
    </section>
  );
}
