import type { UserRole } from "@/lib/auth/types";

export type NavItem = {
  label: string;
  href: string;
};

const ADMIN_NAV: NavItem[] = [
  { label: "Dashboard", href: "/admin/dashboard" },
  { label: "New Estimate", href: "/eworks/calculate" },
  { label: "Quote Review", href: "/manager/review" },
  { label: "Reports", href: "/manager/reports" },
  { label: "Users & Roles", href: "/admin/users" },
  { label: "Clients", href: "/admin/clients" },
  { label: "Trades", href: "/admin/trades" },
  { label: "Products/Scope", href: "/admin/products" },
  { label: "Rate Rules", href: "/admin/rate-rules" },
  { label: "eWorks Sync", href: "/admin/eworks-sync" },
  { label: "Audit Logs", href: "/admin/audit-logs" },
  { label: "Settings", href: "/admin/settings" },
];

const ESTIMATOR_NAV: NavItem[] = [
  { label: "Dashboard", href: "/estimator/dashboard" },
  { label: "Quotes", href: "/estimator/quotes" },
  { label: "New Estimate", href: "/eworks/calculate" },
  { label: "Clients", href: "/estimator/clients" },
  { label: "Products/Scope", href: "/estimator/products" },
  { label: "Approvals", href: "/estimator/approvals" },
];

const MANAGER_NAV: NavItem[] = [
  { label: "Dashboard", href: "/manager/dashboard" },
  { label: "Quote Review", href: "/manager/review" },
  { label: "Reports", href: "/manager/reports" },
  { label: "Clients", href: "/manager/clients" },
];

const ENGINEER_NAV: NavItem[] = [
  { label: "My Jobs", href: "/engineer/jobs" },
  { label: "Site Visit Notes", href: "/engineer/site-notes" },
  { label: "Upload Photos", href: "/engineer/uploads" },
  { label: "Submitted Jobs", href: "/engineer/submitted" },
];

export function getNavigationForRole(role: UserRole | null): NavItem[] {
  switch (role) {
    case "admin":
      return ADMIN_NAV;
    case "estimator":
      return ESTIMATOR_NAV;
    case "manager":
      return MANAGER_NAV;
    case "engineer":
      return ENGINEER_NAV;
    case "client":
    default:
      return [];
  }
}
