import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/utils";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

const variants: Record<ButtonVariant, string> = {
  primary:
    "border border-transparent bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800 disabled:bg-slate-200 disabled:text-slate-400",
  secondary:
    "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 active:bg-slate-100 disabled:text-slate-400 disabled:bg-slate-50",
  ghost: "border border-transparent text-slate-600 hover:bg-slate-100 hover:text-slate-900 disabled:text-slate-400",
  danger:
    "border border-red-200 bg-white text-red-600 hover:border-red-300 hover:bg-red-50 active:bg-red-100 disabled:opacity-50",
};

const baseClass =
  "inline-flex items-center justify-center gap-2 rounded-lg px-4 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/30 focus-visible:ring-offset-2 disabled:cursor-not-allowed";

const sizeClass = {
  default: "h-10",
  sm: "h-9 px-3 text-xs",
} as const;

type AppButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: keyof typeof sizeClass;
  children: ReactNode;
};

export function PrimaryButton({ className, children, size = "default", ...props }: AppButtonProps) {
  return (
    <button type="button" className={cn(baseClass, sizeClass[size], variants.primary, className)} {...props}>
      {children}
    </button>
  );
}

export function SecondaryButton({
  className,
  children,
  variant = "secondary",
  size = "default",
  ...props
}: AppButtonProps) {
  return (
    <button
      type="button"
      className={cn(baseClass, sizeClass[size], variants[variant], className)}
      {...props}
    >
      {children}
    </button>
  );
}
