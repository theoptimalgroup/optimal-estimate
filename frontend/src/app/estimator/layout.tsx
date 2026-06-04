"use client";

import { RequireRole } from "@/components/auth/require-role";
import { AppShell } from "@/components/layout/app-shell";

export default function EstimatorLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireRole allowedRoles={["admin", "estimator"]}>
      <AppShell>{children}</AppShell>
    </RequireRole>
  );
}
