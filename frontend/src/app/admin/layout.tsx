"use client";

import { RequireRole } from "@/components/auth/require-role";
import { AppShell } from "@/components/layout/app-shell";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireRole allowedRoles={["admin"]}>
      <AppShell>{children}</AppShell>
    </RequireRole>
  );
}
