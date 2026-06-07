import type { ReactNode } from "react";

import { BackLink } from "@/components/ui/back-link";
import { cn } from "@/lib/utils";

type PageHeaderProps = {
  title: string;
  subtitle?: string;
  /** @deprecated Use subtitle instead */
  description?: string;
  backHref?: string;
  backLabel?: string;
  actions?: ReactNode;
  className?: string;
};

export function PageHeader({
  title,
  subtitle,
  description,
  backHref,
  backLabel,
  actions,
  className,
}: PageHeaderProps) {
  const resolvedSubtitle = subtitle ?? description;

  return (
    <div className={cn("space-y-4", className)}>
      {backHref && backLabel ? <BackLink href={backHref} label={backLabel} className="mb-0" /> : null}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{title}</h1>
          {resolvedSubtitle ? <p className="text-sm text-slate-500">{resolvedSubtitle}</p> : null}
        </div>
        {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
      </div>
    </div>
  );
}
