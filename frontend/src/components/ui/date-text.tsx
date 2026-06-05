import { cn } from "@/lib/utils";

export function DateText({
  value,
  className,
  includeTime = false,
}: {
  value: string | Date | null | undefined;
  className?: string;
  includeTime?: boolean;
}) {
  if (!value) {
    return <span className={cn("text-slate-400", className)}>—</span>;
  }

  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) {
    return <span className={cn("text-slate-400", className)}>—</span>;
  }

  const formatted = includeTime
    ? date.toLocaleString("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : date.toLocaleDateString("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric",
      });

  return <time className={cn("text-slate-700", className)} dateTime={date.toISOString()}>{formatted}</time>;
}
