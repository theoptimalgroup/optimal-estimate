import { cn } from "@/lib/utils";

export function MoneyText({
  value,
  className,
}: {
  value: string | number;
  className?: string;
}) {
  return (
    <span className={cn("font-medium tabular-nums text-app-text", className)}>
      {typeof value === "number" ? `£${value.toLocaleString("en-GB")}` : value}
    </span>
  );
}
