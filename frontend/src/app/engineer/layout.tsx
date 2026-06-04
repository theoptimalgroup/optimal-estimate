"use client";

import { RequireRole } from "@/components/auth/require-role";
import { AppShell } from "@/components/layout/app-shell";

export default function EngineerLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireRole allowedRoles={["admin", "engineer"]}>
      <AppShell>{children}</AppShell>
    </RequireRole>
  );
}
