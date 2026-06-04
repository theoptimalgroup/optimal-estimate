"use client";

import { RequireRole } from "@/components/auth/require-role";
import { AppShell } from "@/components/layout/app-shell";

export default function ManagerLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireRole allowedRoles={["admin", "manager"]}>
      <AppShell>{children}</AppShell>
    </RequireRole>
  );
}
