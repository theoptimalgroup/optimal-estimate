"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { useCurrentUser } from "@/lib/auth/auth-context";
import { isAzureAuthRequested } from "@/lib/auth/auth-config";
import { isRegistrationError } from "@/lib/auth/dashboard-routes";
import type { UserRole } from "@/lib/auth/types";

type RequireRoleProps = {
  allowedRoles: UserRole[];
  children: ReactNode;
};

export function RequireRole({ allowedRoles, children }: RequireRoleProps) {
  const { isLoading, isAuthenticated, hasRole, error } = useCurrentUser();

  if (isLoading) {
    return (
      <div
        className="flex min-h-screen items-center justify-center bg-gray-50"
        data-testid="require-role-loading"
      >
        <p className="text-sm text-gray-600">Loading…</p>
      </div>
    );
  }

  if (error && isRegistrationError(error)) {
    return (
      <div
        className="flex min-h-screen items-center justify-center bg-gray-50 px-4"
        data-testid="require-role-registration-error"
      >
        <div className="max-w-md space-y-3 rounded-lg border border-red-200 bg-red-50 p-6 text-center">
          <p className="text-lg font-semibold text-red-900">Access denied</p>
          <p className="text-sm text-red-800">User not registered or inactive. Contact admin.</p>
          {isAzureAuthRequested() ? (
            <Link
              href="/login"
              className="inline-block text-sm font-medium text-red-900 underline underline-offset-2 hover:text-red-700"
            >
              Back to sign in
            </Link>
          ) : null}
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div
        className="flex min-h-screen items-center justify-center bg-gray-50 px-4"
        data-testid="require-role-unauthenticated"
      >
        <div className="max-w-md space-y-4 text-center">
          <p className="text-sm text-gray-700">Sign in to access this page.</p>
          {isAzureAuthRequested() ? (
            <Link
              href="/login"
              data-testid="require-role-sign-in"
              className="inline-flex items-center justify-center rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800"
            >
              Sign in with Microsoft
            </Link>
          ) : (
            <p className="text-xs text-gray-500">Enable dev auth on the backend or open /internal/auth-test.</p>
          )}
        </div>
      </div>
    );
  }

  if (!hasRole(...allowedRoles)) {
    return (
      <div
        className="flex min-h-screen items-center justify-center bg-gray-50"
        data-testid="require-role-forbidden"
      >
        <div className="text-center">
          <p className="text-3xl font-semibold text-gray-900">403</p>
          <p className="mt-2 text-sm text-gray-600">You do not have access to this page.</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
