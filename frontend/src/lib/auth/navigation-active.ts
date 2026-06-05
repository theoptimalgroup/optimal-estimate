import type { NavItem } from "@/lib/auth/navigation";

/** Longest-prefix match so detail routes highlight the correct parent nav item only. */
export function getActiveNavHref(pathname: string, navItems: NavItem[]): string | null {
  let best: NavItem | null = null;

  for (const item of navItems) {
    const matches =
      pathname === item.href ||
      (item.href !== "/eworks/calculate" && pathname.startsWith(`${item.href}/`));

    if (matches && (!best || item.href.length > best.href.length)) {
      best = item;
    }
  }

  return best?.href ?? null;
}

export function isNavItemActive(pathname: string, href: string, navItems: NavItem[]): boolean {
  return getActiveNavHref(pathname, navItems) === href;
}

export function getPageTitleFromNav(pathname: string, navItems: NavItem[]): string {
  const activeHref = getActiveNavHref(pathname, navItems);
  if (activeHref) {
    const match = navItems.find((item) => item.href === activeHref);
    if (match) return match.label;
  }
  return "Optimal Estimate";
}

/** Returns true if any two nav items share the same href (duplicate destinations). */
export function hasDuplicateNavHrefs(navItems: NavItem[]): boolean {
  const hrefs = navItems.map((item) => item.href);
  return new Set(hrefs).size !== hrefs.length;
}
