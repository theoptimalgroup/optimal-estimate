"use client";

import Image from "next/image";
import { forwardRef } from "react";
import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, TextareaHTMLAttributes } from "react";

export function cn(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

export function OptimalGroupLogo({ className }: { className?: string }) {
  return (
    <Image
      src="/optimal-group-logo.png"
      alt="Optimal Group"
      width={320}
      height={92}
      priority
      className={cn("h-9 w-auto object-contain sm:h-11", className)}
    />
  );
}

export function EworksFormHeader({
  title = "Estimating Questionnaire",
  subtitle,
}: {
  title?: string;
  subtitle?: string;
}) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-white/10 pb-5">
      <div className="min-w-0 space-y-1">
        <h2 className="text-xl font-bold uppercase tracking-wide text-optimal-orange sm:text-2xl">{title}</h2>
        {subtitle && <p className="text-sm text-optimal-muted">{subtitle}</p>}
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
    <p className="mt-1.5 flex items-start gap-1.5 text-xs font-medium text-red-400 animate-fade-in" role="alert">
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
      <h3 className="text-sm font-semibold text-optimal-orange">{title}</h3>
      {subtitle && <p className="text-xs text-optimal-muted">{subtitle}</p>}
    </div>
  );
}

export function EworksLabel({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <label className={cn("block space-y-2 text-sm font-semibold text-optimal-orange", className)}>{children}</label>
  );
}

export function eworksInputClass(hasError?: boolean) {
  return cn(
    "w-full min-h-[44px] rounded-lg border-0 bg-optimal-field px-3.5 py-2.5 text-base text-optimal-field-text shadow-none",
    "placeholder:text-gray-500 transition-all duration-200 ease-out",
    "focus:bg-white focus:outline-none focus:ring-2 focus:ring-optimal-orange/60",
    hasError && "ring-2 ring-red-400/70",
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
    "bg-optimal-orange text-optimal-bg shadow-md shadow-black/20 hover:bg-optimal-orange-dark active:brightness-95 disabled:bg-optimal-panel disabled:text-optimal-muted disabled:shadow-none",
  secondary:
    "border border-white/15 bg-optimal-elevated text-white hover:border-white/25 hover:bg-optimal-panel active:bg-optimal-bg disabled:text-optimal-muted",
  ghost: "text-optimal-orange hover:bg-white/5 active:bg-white/10 disabled:text-optimal-muted",
  danger:
    "border border-red-400/30 bg-red-500/10 text-red-300 hover:border-red-400/50 hover:bg-red-500/20 active:bg-red-500/30 disabled:opacity-50",
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
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-optimal-orange/50 focus-visible:ring-offset-2 focus-visible:ring-offset-optimal-bg",
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
        "transition-colors duration-200 hover:bg-white/5",
        className,
      )}
    >
      <input
        ref={ref}
        type="checkbox"
        className="size-5 shrink-0 rounded border-white/20 bg-optimal-field text-optimal-orange transition-transform duration-150 focus:ring-optimal-orange/40 active:scale-95"
        {...props}
      />
      <span className="text-sm font-medium text-white">{label}</span>
    </label>
  );
});

export function EworksCard({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("space-y-5", className)}>{children}</div>;
}

export function EworksTableShell({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn("overflow-x-auto rounded-lg bg-optimal-field/95 shadow-inner", className)}>
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
    <div className="space-y-3">
      <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
        <div
          className="h-full rounded-full bg-optimal-orange transition-all duration-500 ease-out"
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
                "shrink-0 rounded-full px-3.5 py-2 text-xs font-semibold transition-all duration-200 ease-out",
                "min-h-[36px] active:scale-[0.97] disabled:cursor-not-allowed disabled:active:scale-100",
                active && "bg-optimal-orange text-optimal-bg shadow-md shadow-black/20",
                !active && reachable && "border border-white/15 bg-optimal-elevated text-white hover:border-white/25",
                !reachable && "border border-white/5 bg-optimal-bg text-optimal-muted",
              )}
            >
              <span className="flex items-center gap-1.5">
                <span
                  className={cn(
                    "flex size-5 items-center justify-center rounded-full text-[10px] font-bold",
                    active && "bg-optimal-bg/20 text-optimal-bg",
                    !active && complete && "bg-emerald-500/20 text-emerald-300",
                    !active && !complete && reachable && "bg-white/10 text-white",
                    !reachable && "bg-white/5 text-optimal-muted",
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
      ? { text: "Saving…", className: "text-optimal-muted animate-pulse-soft" }
      : status === "saved"
        ? { text: "All changes saved", className: "text-emerald-400" }
        : { text: "Save failed", className: "text-red-400" };

  return (
    <span className={cn("inline-flex items-center gap-1.5 text-xs font-medium transition-opacity duration-300", copy.className)}>
      {status === "saved" && (
        <span className="flex size-4 items-center justify-center rounded-full bg-emerald-500/20 text-[10px] text-emerald-300">✓</span>
      )}
      {copy.text}
    </span>
  );
}

export function EworksLoadingScreen({ message = "Opening calculation link…" }: { message?: string }) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-6">
      <div className="relative size-12">
        <div className="absolute inset-0 animate-spin rounded-full border-2 border-white/10 border-t-optimal-orange" />
      </div>
      <p className="text-sm font-medium text-optimal-muted animate-pulse-soft">{message}</p>
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
    <div className="min-h-screen bg-optimal-bg pb-28 md:pb-8">
      <header className="border-b border-white/10 bg-optimal-bg">
        <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1 space-y-1">
              <h1 className="truncate text-xl font-bold uppercase tracking-wide text-white sm:text-2xl">{title}</h1>
              {subtitle && <p className="text-sm text-optimal-muted">{subtitle}</p>}
              {meta && <div className="pt-0.5 text-xs text-optimal-muted">{meta}</div>}
              {badge}
            </div>
            <div className="flex shrink-0 flex-col items-end gap-2">
              <OptimalGroupLogo />
              {saveStatus}
            </div>
          </div>
          {stepIndicator && <div className="mt-4">{stepIndicator}</div>}
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-5 sm:px-6 sm:py-6">
        <div className="animate-fade-in">{children}</div>
      </main>

      {footer && (
        <footer className="fixed inset-x-0 bottom-0 z-30 border-t border-white/10 bg-optimal-bg/95 p-4 backdrop-blur-xl md:static md:mx-auto md:max-w-3xl md:border-0 md:bg-transparent md:p-0 md:px-6 md:pb-8 md:backdrop-blur-none">
          <div className="mx-auto max-w-3xl">{footer}</div>
        </footer>
      )}
    </div>
  );
}
