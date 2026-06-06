import type { LucideIcon } from "lucide-react";
import {
  BarChart3,
  Briefcase,
  Calculator,
  ClipboardCheck,
  ClipboardList,
  FileText,
  LayoutDashboard,
  Package,
  RefreshCw,
  Settings,
  Shield,
  Upload,
  Users,
  Wrench,
} from "lucide-react";

import type { NavItem } from "@/lib/auth/navigation";

export type NavItemWithIcon = NavItem & {
  icon: LucideIcon;
};

const ICON_BY_HREF: Record<string, LucideIcon> = {
  "/admin/dashboard": LayoutDashboard,
  "/manager/dashboard": LayoutDashboard,
  "/estimator/dashboard": LayoutDashboard,
  "/manager/review": ClipboardCheck,
  "/manager/quotes": FileText,
  "/estimator/quotes": FileText,
  "/estimator/approvals": ClipboardCheck,
  "/new-estimate": Calculator,
  "/eworks/calculate": Calculator,
  "/admin/clients": Briefcase,
  "/manager/clients": Briefcase,
  "/estimator/clients": Briefcase,
  "/admin/trades": Wrench,
  "/admin/products": Package,
  "/estimator/products": Package,
  "/admin/rate-rules": BarChart3,
  "/admin/users": Users,
  "/admin/eworks-sync": RefreshCw,
  "/admin/audit-logs": Shield,
  "/admin/settings": Settings,
  "/manager/reports": BarChart3,
  "/engineer/jobs": Briefcase,
  "/engineer/site-notes": ClipboardList,
  "/engineer/uploads": Upload,
  "/engineer/submitted": ClipboardCheck,
};

export function withNavIcons(items: NavItem[]): NavItemWithIcon[] {
  return items.map((item) => ({
    ...item,
    icon: ICON_BY_HREF[item.href] ?? LayoutDashboard,
  }));
}

import { getPageTitleFromNav } from "@/lib/auth/navigation-active";

export function getPageTitle(pathname: string, navItems: NavItem[]): string {
  return getPageTitleFromNav(pathname, navItems);
}
