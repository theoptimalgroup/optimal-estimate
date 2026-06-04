"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { AzureSignOutButton } from "@/components/auth/azure-sign-out-button";
import { DevAuthStatus } from "@/components/auth/dev-auth-status";
import { useCurrentUser } from "@/lib/auth/auth-context";
import { isAzureAuth } from "@/lib/auth/auth-config";
import { getNavigationForRole } from "@/lib/auth/navigation";
import { cn } from "@/lib/utils";

type AppShellProps = {
  children: ReactNode;
};

function isNavItemActive(pathname: string, href: string): boolean {
  if (href === "/eworks/calculate") {
    return pathname === href || pathname.startsWith("/eworks/calculate/");
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const { user, role } = useCurrentUser();
  const navItems = getNavigationForRole(role);
  const showSidebar = navItems.length > 0;
  const azureMode = isAzureAuth();

  return (
    <div className="flex min-h-screen bg-gray-100" data-testid="app-shell">
      {showSidebar ? (
        <aside className="flex w-60 shrink-0 flex-col border-r border-gray-200 bg-white">
          <div className="border-b border-gray-200 px-5 py-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">Optimal Estimate</p>
            <p className="mt-1 text-sm font-semibold text-gray-900">Workspace</p>
          </div>
          <nav className="flex-1 space-y-1 px-3 py-4" aria-label="Main navigation" data-testid="app-shell-nav">
            {navItems.map((item) => {
              const active = isNavItemActive(pathname, item.href);
              return (
                <Link
                  key={`${item.label}-${item.href}`}
                  href={item.href}
                  data-testid={`nav-item-${item.label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
                  className={cn(
                    "block rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    active
                      ? "bg-gray-900 text-white"
                      : "text-gray-700 hover:bg-gray-100 hover:text-gray-900",
                  )}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </aside>
      ) : null}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="border-b border-gray-200 bg-white px-6 py-3">
          <div className="flex items-center justify-between gap-4">
            <div className="min-w-0">
              {user ? (
                <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-sm">
                  <span className="font-semibold text-gray-900">{user.name}</span>
                  <span className="text-gray-500">{user.email}</span>
                  <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium uppercase tracking-wide text-gray-700">
                    {user.role}
                  </span>
                </div>
              ) : (
                <p className="text-sm text-gray-500">Signed out</p>
              )}
            </div>
            <div className="flex items-center gap-3">
              {azureMode ? <AzureSignOutButton /> : null}
              <DevAuthStatus />
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  );
}
