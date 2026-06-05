"use client";

import Link from "next/link";

import { AzureLoginPanel } from "@/components/auth/azure-login-panel";
import { useMsalInit } from "@/components/auth/msal-provider-wrapper";
import { isAzureAuth, isAzureAuthRequested, isDevAuth } from "@/lib/auth/auth-config";

function DevLoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-app-bg px-4">
      <div className="w-full max-w-md space-y-6 rounded-xl border border-app-border bg-app-card p-8 shadow-sm">
        <div className="space-y-2 text-center">
          <h1 className="text-page-title text-app-text">Dev authentication</h1>
          <p className="text-body text-app-muted">
            Microsoft sign-in is disabled. Enable <code className="rounded bg-slate-100 px-1">DEV_AUTH_ENABLED</code> on
            the backend and open a protected route directly.
          </p>
        </div>
        <div className="flex flex-col gap-2">
          <Link
            href="/internal/auth-test"
            className="inline-flex h-9 items-center justify-center rounded-md bg-app-primary px-4 text-sm font-medium text-white hover:bg-app-primary-hover"
          >
            Open auth test page
          </Link>
          <Link
            href="/eworks/calculate"
            className="inline-flex h-9 items-center justify-center rounded-md border border-app-border px-4 text-sm font-medium text-app-text hover:bg-slate-50"
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
