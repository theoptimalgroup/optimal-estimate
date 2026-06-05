"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X } from "lucide-react";
import { useState, type ReactNode } from "react";

import { AzureSignOutButton } from "@/components/auth/azure-sign-out-button";
import { DevAuthStatus } from "@/components/auth/dev-auth-status";
import { RoleBadge } from "@/components/ui/role-badge";
import { useCurrentUser } from "@/lib/auth/auth-context";
import { isAzureAuth } from "@/lib/auth/auth-config";
import { getNavigationForRole } from "@/lib/auth/navigation";
import { isNavItemActive } from "@/lib/auth/navigation-active";
import { getPageTitle, withNavIcons } from "@/lib/auth/navigation-icons";
import { cn } from "@/lib/utils";

type AppShellProps = {
  children: ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const { user, role } = useCurrentUser();
  const navItems = getNavigationForRole(role);
  const navWithIcons = withNavIcons(navItems);
  const showSidebar = navItems.length > 0;
  const azureMode = isAzureAuth();
  const pageTitle = getPageTitle(pathname, navItems);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-slate-50" data-testid="app-shell">
      {showSidebar ? (
        <>
          {mobileOpen ? (
            <button
              type="button"
              aria-label="Close navigation"
              className="fixed inset-0 z-40 bg-slate-900/30 lg:hidden"
              onClick={() => setMobileOpen(false)}
            />
          ) : null}

          <aside
            className={cn(
              "fixed inset-y-0 left-0 z-50 flex w-60 shrink-0 flex-col border-r border-slate-200 bg-white transition-transform lg:sticky lg:top-0 lg:z-auto lg:h-screen lg:translate-x-0",
              mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
            )}
          >
            <div className="flex items-center justify-between border-b border-slate-200 px-5 py-5">
              <div>
                <p className="text-sm font-semibold text-slate-900">Optimal Estimate</p>
                <p className="text-xs text-slate-500">Operations</p>
              </div>
              <button
                type="button"
                className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 lg:hidden"
                aria-label="Close sidebar"
                onClick={() => setMobileOpen(false)}
              >
                <X className="size-5" />
              </button>
            </div>

            <nav
              className="flex-1 space-y-1.5 overflow-y-auto px-3 py-4"
              aria-label="Main navigation"
              data-testid="app-shell-nav"
            >
              {navWithIcons.map((item) => {
                const active = isNavItemActive(pathname, item.href, navItems);
                const Icon = item.icon;
                return (
                  <Link
                    key={`${item.label}-${item.href}`}
                    href={item.href}
                    onClick={() => setMobileOpen(false)}
                    data-testid={`nav-item-${item.label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
                    className={cn(
                      "flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                      active
                        ? "border border-blue-200 bg-blue-50 text-blue-700"
                        : "border border-transparent text-slate-600 hover:bg-slate-50 hover:text-slate-900",
                    )}
                  >
                    <Icon className={cn("size-4 shrink-0", active ? "text-blue-600" : "text-slate-400")} />
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </aside>
        </>
      ) : null}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 border-b border-slate-200 bg-white">
          <div className="flex h-14 items-center justify-between gap-4 px-6">
            <div className="flex min-w-0 items-center gap-3">
              {showSidebar ? (
                <button
                  type="button"
                  className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 lg:hidden"
                  aria-label="Open navigation"
                  onClick={() => setMobileOpen(true)}
                >
                  <Menu className="size-5" />
                </button>
              ) : null}
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-slate-900">{pageTitle}</p>
                {user ? (
                  <p className="truncate text-xs text-slate-500">{user.email}</p>
                ) : (
                  <p className="text-xs text-slate-500">Signed out</p>
                )}
              </div>
            </div>

            <div className="flex shrink-0 items-center gap-3">
              {user ? (
                <div className="hidden items-center gap-2.5 sm:flex">
                  <span className="max-w-[140px] truncate text-sm text-slate-900">{user.name}</span>
                  <RoleBadge role={user.role} />
                </div>
              ) : null}
              {azureMode ? <AzureSignOutButton /> : null}
              <DevAuthStatus />
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-auto bg-slate-50">
          <div className="mx-auto w-full max-w-content space-y-6 px-6 py-6">{children}</div>
        </main>
      </div>
    </div>
  );
}
