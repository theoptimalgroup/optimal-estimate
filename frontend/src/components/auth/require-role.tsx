"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { LoadingState } from "@/components/ui/states";
import { PrimaryButton, SecondaryButton } from "@/components/ui/buttons";

import { useCurrentUser } from "@/lib/auth/auth-context";
import { isAzureAuthRequested } from "@/lib/auth/auth-config";
import { isRegistrationError } from "@/lib/auth/dashboard-routes";
import type { UserRole } from "@/lib/auth/types";

type RequireRoleProps = {
  allowedRoles: UserRole[];
  children: ReactNode;
};

function AccessCard({ children, testId }: { children: ReactNode; testId: string }) {
  return (
    <div
      className="flex min-h-screen items-center justify-center bg-app-bg px-4"
      data-testid={testId}
    >
      <div className="w-full max-w-md rounded-xl border border-app-border bg-app-card p-8 text-center shadow-sm">
        {children}
      </div>
    </div>
  );
}

export function RequireRole({ allowedRoles, children }: RequireRoleProps) {
  const router = useRouter();
  const { isLoading, isAuthenticated, hasRole, error } = useCurrentUser();

  useEffect(() => {
    if (isLoading || isAuthenticated || error) {
      return;
    }
    if (isAzureAuthRequested()) {
      router.replace("/login");
    }
  }, [isLoading, isAuthenticated, error, router]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50" data-testid="require-role-loading">
        <LoadingState message="Loading…" />
      </div>
    );
  }

  if (error && isRegistrationError(error)) {
    return (
      <AccessCard testId="require-role-registration-error">
        <p className="text-lg font-semibold text-rose-900">Access denied</p>
        <p className="mt-2 text-sm text-slate-600">User not registered or inactive. Contact admin.</p>
        {isAzureAuthRequested() ? (
          <div className="mt-5">
            <Link href="/login">
              <SecondaryButton>Back to sign in</SecondaryButton>
            </Link>
          </div>
        ) : null}
      </AccessCard>
    );
  }

  if (!isAuthenticated) {
    return (
      <AccessCard testId="require-role-unauthenticated">
        <p className="text-sm text-slate-700">Sign in to access this page.</p>
        {isAzureAuthRequested() ? (
          <div className="mt-5">
            <Link href="/login" data-testid="require-role-sign-in">
              <PrimaryButton>Sign in with Microsoft</PrimaryButton>
            </Link>
          </div>
        ) : (
          <p className="mt-3 text-xs text-slate-500">Enable dev auth on the backend or open /internal/auth-test.</p>
        )}
      </AccessCard>
    );
  }

  if (!hasRole(...allowedRoles)) {
    return (
      <AccessCard testId="require-role-forbidden">
        <p className="text-3xl font-semibold text-slate-900">403</p>
        <p className="mt-2 text-sm text-slate-600">You do not have access to this page.</p>
      </AccessCard>
    );
  }

  return <>{children}</>;
}
