import type { LucideIcon } from "lucide-react";
import {
  BarChart3,
  Briefcase,
  Building2,
  Calculator,
  CalendarRange,
  CheckSquare,
  ClipboardCheck,
  FileCheck,
  FileText,
  LayoutDashboard,
  Package,
  Percent,
  PhoneCall,
  RefreshCw,
  Settings,
  Shield,
  TrendingUp,
  Upload,
  Users,
  Wrench,
} from "lucide-react";

import type { NavItem } from "@/lib/auth/navigation";
import { getPageTitleFromNav } from "@/lib/auth/navigation-active";

export type NavItemWithIcon = NavItem & {
  icon: LucideIcon;
};

const ICON_BY_HREF: Record<string, LucideIcon> = {
  // Dashboards
  "/admin/dashboard": LayoutDashboard,
  "/manager/dashboard": LayoutDashboard,
  "/estimator/dashboard": LayoutDashboard,

  // Sales & follow-up
  "/admin/processed-dashboard": TrendingUp,
  "/manager/processed-dashboard": TrendingUp,
  "/admin/call-back-dashboard": PhoneCall,
  "/manager/call-back-dashboard": PhoneCall,

  // Quotes & review
  "/manager/quotes": FileText,
  "/estimator/quotes": FileText,
  "/manager/review": ClipboardCheck,
  "/estimator/approvals": CheckSquare,

  // Estimates
  "/new-estimate": Calculator,
  "/eworks/calculate": Calculator,

  // Reporting & clients
  "/manager/reports": BarChart3,
  "/admin/clients": Building2,
  "/manager/clients": Building2,
  "/estimator/clients": Building2,

  // Admin configuration
  "/admin/trades": Wrench,
  "/admin/products": Package,
  "/estimator/products": Package,
  "/admin/rate-rules": Percent,
  "/admin/users": Users,
  "/admin/eworks-sync": RefreshCw,
  "/admin/audit-logs": Shield,
  "/admin/settings": Settings,

  // Engineer field work
  "/engineer/assigned-estimates": Briefcase,
  "/engineer/assigned-jobs": CalendarRange,
  "/engineer/submitted-estimates": FileCheck,
  "/engineer/submitted-jobs": CheckSquare,

  // Legacy engineer routes (hidden from nav but mapped if referenced)
  "/engineer/site-notes": ClipboardCheck,
  "/engineer/uploads": Upload,
};

export function withNavIcons(items: NavItem[]): NavItemWithIcon[] {
  return items.map((item) => ({
    ...item,
    icon: ICON_BY_HREF[item.href] ?? LayoutDashboard,
  }));
}

export function getPageTitle(pathname: string, navItems: NavItem[]): string {
  return getPageTitleFromNav(pathname, navItems);
}
