import { badgeToneClasses, roleTone } from "@/components/ui/status-badge";
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
  const tone = roleTone(role);

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md px-2.5 py-0.5 text-xs font-medium uppercase tracking-wide",
        badgeToneClasses[tone],
        className,
      )}
    >
      {roleLabels[role]}
    </span>
  );
}
