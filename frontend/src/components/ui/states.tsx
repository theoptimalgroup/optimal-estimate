import type { ReactNode } from "react";

import { SecondaryButton } from "@/components/ui/buttons";
import { cn } from "@/lib/utils";

export function LoadingState({
  message = "Loading…",
  className,
}: {
  message?: string;
  className?: string;
}) {
  return (
    <div
      className={cn("flex flex-col items-center justify-center gap-3 py-16", className)}
      data-testid="loading-state"
    >
      <div className="relative size-8">
        <div className="absolute inset-0 animate-spin rounded-full border-2 border-slate-200 border-t-blue-600" />
      </div>
      <p className="text-sm text-slate-600">{message}</p>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
  icon,
  className,
  "data-testid": testId,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  icon?: ReactNode;
  className?: string;
  "data-testid"?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-200 bg-white px-6 py-12 text-center shadow-sm",
        className,
      )}
      data-testid={testId ?? "empty-state"}
    >
      {icon ? (
        <div className="mb-3 flex size-10 items-center justify-center rounded-lg bg-slate-50 text-slate-400">
          {icon}
        </div>
      ) : null}
      <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
      {description ? <p className="mt-1.5 max-w-md text-sm text-slate-600">{description}</p> : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}

export function ErrorState({
  title = "Something went wrong",
  message,
  onRetry,
  className,
}: {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700",
        className,
      )}
      data-testid="error-state"
      role="alert"
    >
      <p className="font-medium text-red-800">{title}</p>
      {message ? <p className="mt-1">{message}</p> : null}
      {onRetry ? (
        <div className="mt-3">
          <SecondaryButton variant="danger" onClick={onRetry}>
            Try again
          </SecondaryButton>
        </div>
      ) : null}
    </div>
  );
}
