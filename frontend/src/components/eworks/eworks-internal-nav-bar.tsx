"use client";

import Link from "next/link";

import { RoleBadge } from "@/components/ui/role-badge";
import { useCurrentUser } from "@/lib/auth/auth-context";
import { getDashboardForRole } from "@/lib/auth/dashboard-routes";

export function EworksInternalNavBar() {
  const { user, isAuthenticated, isLoading } = useCurrentUser();

  if (isLoading || !isAuthenticated || !user) {
    return null;
  }

  const dashboardHref = getDashboardForRole(user.role);
  if (!dashboardHref) {
    return null;
  }

  return (
    <div
      className="border-b border-slate-200 bg-white"
      data-testid="eworks-internal-nav-bar"
    >
      <div className="mx-auto flex max-w-3xl items-center justify-between gap-3 px-4 py-2.5 sm:px-6">
        <Link
          href={dashboardHref}
          className="text-sm font-medium text-blue-600 hover:text-blue-700"
          data-testid="eworks-back-to-dashboard"
        >
          ← Back to Dashboard
        </Link>
        <RoleBadge role={user.role} />
      </div>
    </div>
  );
}
