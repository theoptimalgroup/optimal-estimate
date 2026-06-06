import type { ReactNode } from "react";

/** Public assignment links — no AppShell, RequireRole, or MSAL sign-in. */
export default function AssignmentLayout({ children }: { children: ReactNode }) {
  return children;
}
