"use client";

import { forwardRef } from "react";
import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, TextareaHTMLAttributes } from "react";

import { CompanyLogo } from "@/components/ui/company-logo";

export function cn(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

/** @deprecated Use CompanyLogo from @/components/ui */
export function OptimalGroupLogo({ className }: { className?: string }) {
  return <CompanyLogo className={className} priority />;
}

export function EworksFormHeader({
  title = "Estimating Questionnaire",
  subtitle,
}: {
  title?: string;
  subtitle?: string;
}) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-slate-200 pb-5">
      <div className="min-w-0 space-y-1">
        <h2 className="text-xl font-bold uppercase tracking-wide text-slate-900 sm:text-2xl">{title}</h2>
        {subtitle && <p className="text-sm text-slate-600">{subtitle}</p>}
      </div>
      <OptimalGroupLogo className="shrink-0" />
    </div>
  );
}

export function EworksFieldError({ message }: { message?: string }) {
  const formatted =
    message === "Invalid input" || message?.startsWith("Invalid input:")
      ? "This field has an invalid value"
      : message;
  if (!formatted) return null;
  return (
    <p className="mt-1.5 flex items-start gap-1.5 text-xs font-medium text-red-600 animate-fade-in" role="alert">
      <span aria-hidden className="mt-0.5 shrink-0">
        •
      </span>
      {formatted}
    </p>
  );
}

export function EworksSectionTitle({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="space-y-0.5">
      <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
      {subtitle && <p className="text-xs text-slate-600">{subtitle}</p>}
    </div>
  );
}

export function EworksLabel({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <label className={cn("block space-y-2 text-sm font-medium text-slate-700", className)}>{children}</label>
  );
}

export function eworksInputClass(hasError?: boolean) {
  return cn(
    "w-full min-h-[44px] rounded-lg border border-slate-300 bg-white px-3.5 py-2.5 text-base text-slate-900 shadow-sm",
    "placeholder:text-slate-400 transition-all duration-200 ease-out",
    "focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20",
    hasError && "border-red-400 ring-2 ring-red-400/30",
  );
}

export const EworksInput = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement> & { hasError?: boolean }>(
  function EworksInput({ className, hasError, onFocus, ...props }, ref) {
    return (
      <input
        ref={ref}
        className={cn(eworksInputClass(hasError), className)}
        onFocus={(e) => {
          e.target.select();
          onFocus?.(e);
        }}
        {...props}
      />
    );
  },
);

export const EworksTextarea = forwardRef<
  HTMLTextAreaElement,
  TextareaHTMLAttributes<HTMLTextAreaElement> & { hasError?: boolean }
>(function EworksTextarea({ className, hasError, ...props }, ref) {
  return (
    <textarea
      ref={ref}
      className={cn(eworksInputClass(hasError), "min-h-[120px] resize-y py-3", className)}
      {...props}
    />
  );
});

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

const buttonVariants: Record<ButtonVariant, string> = {
  primary:
    "border border-transparent bg-blue-600 text-white shadow-sm hover:bg-blue-700 active:bg-blue-800 disabled:bg-slate-200 disabled:text-slate-400 disabled:shadow-none",
  secondary:
    "border border-slate-300 bg-white text-slate-700 hover:border-slate-400 hover:bg-slate-50 active:bg-slate-100 disabled:text-slate-400",
  ghost: "text-blue-600 hover:bg-slate-100 active:bg-slate-200 disabled:text-slate-400",
  danger:
    "border border-red-200 bg-red-50 text-red-700 hover:border-red-300 hover:bg-red-100 active:bg-red-100 disabled:opacity-50",
};

export function EworksButton({
  variant = "primary",
  className,
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }) {
  return (
    <button
      type="button"
      className={cn(
        "inline-flex min-h-[44px] min-w-[44px] items-center justify-center gap-2 rounded-lg px-5 py-2.5 text-sm font-semibold",
        "transition-all duration-200 ease-out active:scale-[0.98] disabled:cursor-not-allowed disabled:active:scale-100",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/30 focus-visible:ring-offset-2 focus-visible:ring-offset-white",
        buttonVariants[variant],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}

export const EworksCheckbox = forwardRef<
  HTMLInputElement,
  InputHTMLAttributes<HTMLInputElement> & { label: ReactNode }
>(function EworksCheckbox({ label, className, ...props }, ref) {
  return (
    <label
      className={cn(
        "flex min-h-[44px] cursor-pointer items-center gap-3 rounded-lg px-1 py-2",
        "transition-colors duration-200 hover:bg-slate-50",
        className,
      )}
    >
      <input
        ref={ref}
        type="checkbox"
        className="size-5 shrink-0 rounded border-slate-300 bg-white text-blue-600 transition-transform duration-150 focus:ring-blue-500/30 active:scale-95"
        {...props}
      />
      <span className="text-sm font-medium text-slate-900">{label}</span>
    </label>
  );
});

export function EworksCard({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn("space-y-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm", className)}>
      {children}
    </div>
  );
}

export function EworksTableShell({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn("overflow-x-auto rounded-xl border border-slate-200 bg-slate-50/80 shadow-sm", className)}>
      {children}
    </div>
  );
}

export function EworksStepIndicator({
  steps,
  currentStep,
  maxReachableStep,
  onStepClick,
}: {
  steps: readonly string[];
  currentStep: number;
  maxReachableStep: number;
  onStepClick: (index: number) => void;
}) {
  const progress = ((currentStep + 1) / steps.length) * 100;

  return (
    <div className="space-y-4">
      <div className="h-1.5 overflow-hidden rounded-full bg-slate-200">
        <div
          className="h-full rounded-full bg-blue-600 transition-all duration-500 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>
      <div className="flex gap-2 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {steps.map((label, index) => {
          const reachable = index <= maxReachableStep;
          const active = index === currentStep;
          const complete = index < currentStep;

          return (
            <button
              key={label}
              type="button"
              disabled={!reachable}
              onClick={() => onStepClick(index)}
              className={cn(
                "shrink-0 rounded-lg px-3.5 py-2 text-xs font-semibold transition-all duration-200 ease-out",
                "min-h-[36px] active:scale-[0.97] disabled:cursor-not-allowed disabled:active:scale-100",
                active && "border border-blue-200 bg-blue-50 text-blue-700 shadow-sm",
                !active && reachable && "border border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50",
                !reachable && "border border-slate-200 bg-slate-50 text-slate-400",
              )}
            >
              <span className="flex items-center gap-1.5">
                <span
                  className={cn(
                    "flex size-5 items-center justify-center rounded-full text-[10px] font-bold",
                    active && "bg-blue-600 text-white",
                    !active && complete && "bg-emerald-100 text-emerald-700",
                    !active && !complete && reachable && "bg-slate-200 text-slate-700",
                    !reachable && "bg-slate-100 text-slate-400",
                  )}
                >
                  {complete ? "✓" : index + 1}
                </span>
                <span className="whitespace-nowrap">{label}</span>
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function EworksSaveStatus({ status }: { status: "idle" | "saving" | "saved" | "error" }) {
  if (status === "idle") return null;

  const copy =
    status === "saving"
      ? { text: "Saving…", className: "text-slate-500" }
      : status === "saved"
        ? { text: "Saved", className: "text-slate-500" }
        : { text: "Save failed", className: "text-red-600" };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 text-xs text-slate-500 transition-opacity duration-300",
        copy.className,
        status === "saving" && "animate-pulse",
      )}
      aria-live="polite"
    >
      {copy.text}
    </span>
  );
}

export function EworksLoadingScreen({ message = "Opening calculation link…" }: { message?: string }) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-6">
      <div className="relative size-12">
        <div className="absolute inset-0 animate-spin rounded-full border-2 border-slate-200 border-t-blue-600" />
      </div>
      <p className="text-sm font-medium text-slate-600 animate-pulse-soft">{message}</p>
    </div>
  );
}

/** Full-width desktop layout for the internal submitted-quotes dashboard (not the field wizard). */
export function DashboardPageShell({
  title,
  subtitle,
  meta,
  children,
  footer,
  backLink,
}: {
  title: string;
  subtitle?: string;
  meta?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  backLink?: ReactNode;
}) {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white shadow-sm">
        <div className="mx-auto w-full px-6 py-6 lg:px-8 lg:py-7">
          <div className="flex items-start justify-between gap-6">
            <div className="min-w-0 flex-1 space-y-1.5">
              {backLink}
              <h1 className="text-2xl font-bold uppercase tracking-wide text-slate-900 lg:text-3xl">{title}</h1>
              {subtitle && <p className="text-sm text-slate-600 lg:text-base">{subtitle}</p>}
              {meta && <div className="pt-0.5 text-xs text-slate-500">{meta}</div>}
            </div>
            <div className="shrink-0">
              <OptimalGroupLogo className="h-11 lg:h-12" />
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full px-6 py-7 lg:px-8 lg:py-9">
        <div className="animate-fade-in">{children}</div>
      </main>

      {footer && (
        <footer className="border-t border-slate-200 bg-white px-6 py-6 shadow-[0_-1px_3px_rgba(15,23,42,0.04)] lg:px-8 lg:py-7">
          {footer}
        </footer>
      )}
    </div>
  );
}

export function EworksPageShell({
  title,
  subtitle,
  meta,
  badge,
  saveStatus,
  stepIndicator,
  children,
  footer,
}: {
  title: string;
  subtitle?: string;
  meta?: ReactNode;
  badge?: ReactNode;
  saveStatus?: ReactNode;
  stepIndicator?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div className="min-h-screen bg-slate-50 pb-28 md:pb-8">
      <header className="border-b border-slate-200 bg-white shadow-sm">
        <div className="mx-auto max-w-3xl px-4 py-5 sm:px-6">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1 space-y-1.5">
              <h1 className="truncate text-xl font-bold uppercase tracking-wide text-slate-900 sm:text-2xl">{title}</h1>
              {subtitle && <p className="text-sm text-slate-600">{subtitle}</p>}
              {meta && <div className="pt-0.5 text-xs text-slate-500">{meta}</div>}
              {badge}
            </div>
            <div className="flex shrink-0 flex-col items-end gap-2">
              <OptimalGroupLogo />
              {saveStatus}
            </div>
          </div>
          {stepIndicator && <div className="mt-6">{stepIndicator}</div>}
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
        <div className="animate-fade-in space-y-8">{children}</div>
      </main>

      {footer && (
        <footer className="fixed inset-x-0 bottom-0 z-30 border-t border-slate-200 bg-white/95 p-4 shadow-[0_-4px_12px_rgba(15,23,42,0.06)] backdrop-blur-xl md:static md:mx-auto md:max-w-3xl md:border-0 md:bg-transparent md:p-0 md:px-6 md:pb-8 md:shadow-none md:backdrop-blur-none">
          <div className="mx-auto max-w-3xl">{footer}</div>
        </footer>
      )}
    </div>
  );
}
