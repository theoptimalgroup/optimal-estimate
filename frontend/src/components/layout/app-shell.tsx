"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";

import { AzureSignOutButton } from "@/components/auth/azure-sign-out-button";
import { DevAuthStatus } from "@/components/auth/dev-auth-status";
import { CompanyLogo } from "@/components/ui/company-logo";
import { RoleBadge } from "@/components/ui/role-badge";
import { useCurrentUser } from "@/lib/auth/auth-context";
import { isAzureAuth } from "@/lib/auth/auth-config";
import { ENGINEER_NAV, getNavigationForRole } from "@/lib/auth/navigation";
import { isNavItemActive } from "@/lib/auth/navigation-active";
import { getPageTitle, withNavIcons, type NavItemWithIcon } from "@/lib/auth/navigation-icons";
import { cn } from "@/lib/utils";

type AppShellProps = {
  children: ReactNode;
};

function navItemTestId(label: string): string {
  return `nav-item-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
}

function SidebarNavLink({
  item,
  active,
  onNavigate,
}: {
  item: NavItemWithIcon;
  active: boolean;
  onNavigate: () => void;
}) {
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      onClick={onNavigate}
      data-testid={navItemTestId(item.label)}
      className={cn(
        "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
        active
          ? "border border-blue-200 bg-blue-50 text-blue-700"
          : "border border-transparent text-slate-600 hover:bg-slate-50 hover:text-slate-900",
      )}
    >
      <Icon
        className={cn(
          "size-[18px] shrink-0",
          active ? "text-blue-600" : "text-slate-400",
        )}
        aria-hidden
      />
      <span className="truncate">{item.label}</span>
    </Link>
  );
}

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const { user, role } = useCurrentUser();
  const navItems = getNavigationForRole(role);
  const navWithIcons = withNavIcons(navItems);
  const showSidebar = navItems.length > 0;
  const azureMode = isAzureAuth();
  const pageTitle = getPageTitle(pathname, navItems);
  const [mobileOpen, setMobileOpen] = useState(false);

  const engineerHrefSet = useMemo(() => new Set(ENGINEER_NAV.map((item) => item.href)), []);

  const { primaryNavItems, engineerNavItems } = useMemo(() => {
    if (role !== "manager") {
      return { primaryNavItems: navWithIcons, engineerNavItems: [] as NavItemWithIcon[] };
    }
    return {
      primaryNavItems: navWithIcons.filter((item) => !engineerHrefSet.has(item.href)),
      engineerNavItems: navWithIcons.filter((item) => engineerHrefSet.has(item.href)),
    };
  }, [engineerHrefSet, navWithIcons, role]);

  const closeMobileNav = () => setMobileOpen(false);

  const renderNavItem = (item: NavItemWithIcon) => (
    <SidebarNavLink
      key={`${item.label}-${item.href}`}
      item={item}
      active={isNavItemActive(pathname, item.href, navItems)}
      onNavigate={closeMobileNav}
    />
  );

  return (
    <div className="flex min-h-screen bg-slate-50" data-testid="app-shell">
      {showSidebar ? (
        <>
          {mobileOpen ? (
            <button
              type="button"
              aria-label="Close navigation"
              className="fixed inset-0 z-40 bg-slate-900/30 lg:hidden"
              onClick={closeMobileNav}
            />
          ) : null}

          <aside
            className={cn(
              "fixed inset-y-0 left-0 z-50 flex w-60 shrink-0 flex-col border-r border-slate-200 bg-white transition-transform lg:sticky lg:top-0 lg:z-auto lg:h-screen lg:translate-x-0",
              mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
            )}
          >
            <div className="relative border-b border-slate-200 px-5 py-6">
              <button
                type="button"
                className="absolute right-3 top-3 rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 lg:hidden"
                aria-label="Close sidebar"
                onClick={closeMobileNav}
              >
                <X className="size-5" />
              </button>
              <div className="flex flex-col items-center text-center" data-testid="sidebar-branding">
                <CompanyLogo className="mx-auto h-9 object-center sm:h-10" priority />
                <p className="mt-3 text-lg font-extrabold leading-tight tracking-tight text-slate-900">
                  Optimal Estimate
                </p>
              </div>
            </div>

            <nav
              className="flex-1 space-y-1 overflow-y-auto px-3 py-4"
              aria-label="Main navigation"
              data-testid="app-shell-nav"
            >
              {primaryNavItems.map(renderNavItem)}

              {engineerNavItems.length > 0 ? (
                <div className="pt-3">
                  <p
                    className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400"
                    data-testid="nav-section-engineer-work"
                  >
                    Engineer Work
                  </p>
                  <div className="space-y-1">{engineerNavItems.map(renderNavItem)}</div>
                </div>
              ) : null}
            </nav>
          </aside>
        </>
      ) : null}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 border-b border-slate-200 bg-white shadow-sm">
          <div className="flex min-h-16 items-center justify-between gap-4 px-6 py-3 lg:px-8">
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
              {showSidebar ? (
                <CompanyLogo className="h-7 shrink-0 lg:hidden" />
              ) : (
                <CompanyLogo className="h-8 shrink-0" />
              )}
              <div className="min-w-0">
                <p className="truncate text-base font-semibold text-slate-900">{pageTitle}</p>
                {user ? (
                  <p className="truncate text-xs text-slate-500">{user.email}</p>
                ) : (
                  <p className="text-xs text-slate-500">Signed out</p>
                )}
              </div>
            </div>

            <div className="flex shrink-0 items-center gap-2.5 sm:gap-3">
              {user ? (
                <>
                  <span className="hidden max-w-[140px] truncate text-sm text-slate-700 sm:inline">{user.name}</span>
                  <RoleBadge role={user.role} />
                </>
              ) : null}
              {azureMode ? <AzureSignOutButton /> : null}
              <DevAuthStatus />
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-auto bg-slate-50">
          <div className="mx-auto w-full max-w-content space-y-6 px-6 py-6 lg:px-8">{children}</div>
        </main>
      </div>
    </div>
  );
}
