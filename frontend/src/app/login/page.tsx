"use client";

import Link from "next/link";

import { AzureLoginPanel } from "@/components/auth/azure-login-panel";
import { useMsalInit } from "@/components/auth/msal-provider-wrapper";
import { isAzureAuth, isAzureAuthRequested, isDevAuth } from "@/lib/auth/auth-config";

function DevLoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md space-y-6 rounded-xl border border-gray-200 bg-white p-8 shadow-sm">
        <div className="space-y-2 text-center">
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">Optimal Estimate</p>
          <h1 className="text-2xl font-bold text-gray-900">Dev authentication</h1>
          <p className="text-sm text-gray-600">
            Microsoft sign-in is disabled. Enable <code className="rounded bg-gray-100 px-1">DEV_AUTH_ENABLED</code> on
            the backend and open a protected route directly.
          </p>
        </div>
        <div className="flex flex-col gap-3">
          <Link
            href="/internal/auth-test"
            className="inline-flex items-center justify-center rounded-md bg-gray-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-gray-800"
          >
            Open auth test page
          </Link>
          <Link
            href="/eworks/calculate"
            className="inline-flex items-center justify-center rounded-md border border-gray-300 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Continue to calculator
          </Link>
        </div>
      </div>
    </main>
  );
}

export default function LoginPage() {
  const { ready } = useMsalInit();

  if (isDevAuth()) {
    return <DevLoginPage />;
  }

  if (isAzureAuthRequested() && !isAzureAuth()) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
        <div className="max-w-md rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-900">
          Azure env vars are missing. Check <code className="rounded bg-red-100 px-1">frontend/.env.local</code> and
          restart the dev server.
        </div>
      </main>
    );
  }

  if (isAzureAuth()) {
    if (!ready) {
      return (
        <main className="flex min-h-screen items-center justify-center bg-gray-50" data-testid="login-loading">
          <p className="text-sm text-gray-600">Loading authentication…</p>
        </main>
      );
    }
    return <AzureLoginPanel />;
  }

  return <DevLoginPage />;
}
