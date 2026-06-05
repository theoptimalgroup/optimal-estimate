import type { UserRole } from "@/lib/auth/types";
import { cn } from "@/lib/utils";

const roleLabels: Record<UserRole, string> = {
  admin: "Admin",
  manager: "Manager",
  estimator: "Estimator",
  engineer: "Engineer",
  client: "Client",
};

export function RoleBadge({ role, className }: { role: UserRole; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md bg-slate-100 px-2.5 py-0.5 text-xs font-medium uppercase tracking-wide text-slate-700",
        className,
      )}
    >
      {roleLabels[role]}
    </span>
  );
}
