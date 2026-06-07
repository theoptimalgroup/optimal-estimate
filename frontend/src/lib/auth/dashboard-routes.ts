import type { UserRole } from "@/lib/auth/types";

export function getDashboardForRole(role: UserRole): string | null {
  switch (role) {
    case "admin":
      return "/admin/dashboard";
    case "manager":
      return "/manager/dashboard";
    case "estimator":
      return "/estimator/dashboard";
    case "engineer":
      return "/engineer/assigned-estimates";
    case "client":
      return null;
    default:
      return null;
  }
}

export function isRegistrationError(message: string | null): boolean {
  if (!message) return false;
  const normalized = message.toLowerCase();
  return normalized.includes("not registered") || normalized.includes("inactive");
}
