"use client";

import Link from "next/link";

import { DevAuthStatus } from "@/components/auth/dev-auth-status";
import { getAuthProvider, isAzureAuth, isAzureAuthRequested } from "@/lib/auth/auth-config";
import { useCurrentUser } from "@/lib/auth/auth-context";
import { isAzureConfigured } from "@/lib/auth/msal-config";
import { getMsalReadyState } from "@/lib/auth/token-provider";

function authGuidance(): string {
  const msal = getMsalReadyState();

  if (isAzureAuth()) {
    if (!msal?.hasAccount) {
      return "Frontend is in Azure mode with no Microsoft session. Sign in at /login first.";
    }
    if (!msal.hasAccessToken) {
      return "MSAL account found but no access token yet. Try /login or click Refetch user.";
    }
    return "Azure session active. If user is still null, check backend AUTH_PROVIDER=azure and that your email exists in the users table.";
  }

  if (isAzureAuthRequested() && !isAzureConfigured()) {
    return "NEXT_PUBLIC_AUTH_PROVIDER=azure but Azure env vars are missing. Add them to frontend/.env.local and restart the dev server (or rebuild the Docker frontend).";
  }

  return "Frontend is in dev mode (no Bearer token sent). Backend must use AUTH_PROVIDER=dev with DEV_AUTH_ENABLED=true, or rebuild the frontend with NEXT_PUBLIC_AUTH_PROVIDER=azure and sign in.";
}

export default function AuthTestPage() {
  const { user, role, isLoading, isAuthenticated, error, hasRole, refetchUser } = useCurrentUser();
  const msal = getMsalReadyState();

  return (
    <main className="mx-auto max-w-2xl space-y-6 px-6 py-10">
      <div className="space-y-2">
        <h1 className="text-2xl font-bold text-gray-900">Auth provider test</h1>
        <p className="text-sm text-gray-600">Internal page for verifying GET /api/v1/auth/me integration.</p>
        <DevAuthStatus />
      </div>

      <section className="space-y-3 rounded-lg border border-amber-200 bg-amber-50 p-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-amber-900">Configuration</h2>
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
          <dt className="text-amber-800">frontend provider</dt>
          <dd data-testid="auth-test-frontend-provider">{getAuthProvider()}</dd>
          <dt className="text-amber-800">azure configured</dt>
          <dd data-testid="auth-test-azure-configured">{String(isAzureConfigured())}</dd>
          <dt className="text-amber-800">msal hasAccount</dt>
          <dd>{msal ? String(msal.hasAccount) : "—"}</dd>
          <dt className="text-amber-800">msal hasAccessToken</dt>
          <dd>{msal ? String(msal.hasAccessToken) : "—"}</dd>
        </dl>
        <p className="text-sm text-amber-900">{authGuidance()}</p>
        {!isAuthenticated ? (
          <Link href="/login" className="inline-block text-sm font-medium text-blue-700 underline underline-offset-2">
            Go to /login
          </Link>
        ) : null}
      </section>

      <section className="space-y-3 rounded-lg border border-gray-200 bg-gray-50 p-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-700">State</h2>
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
          <dt className="text-gray-500">isLoading</dt>
          <dd>{String(isLoading)}</dd>
          <dt className="text-gray-500">isAuthenticated</dt>
          <dd data-testid="auth-test-is-authenticated">{String(isAuthenticated)}</dd>
          <dt className="text-gray-500">role</dt>
          <dd>{role ?? "—"}</dd>
          <dt className="text-gray-500">hasRole(&quot;admin&quot;)</dt>
          <dd>{String(hasRole("admin"))}</dd>
          <dt className="text-gray-500">error</dt>
          <dd className="text-red-600">{error ?? "—"}</dd>
        </dl>
        <button
          type="button"
          onClick={() => void refetchUser()}
          className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm hover:bg-gray-100"
        >
          Refetch user
        </button>
      </section>

      <section className="space-y-2 rounded-lg border border-gray-200 p-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-700">Current user</h2>
        <pre className="overflow-x-auto rounded-md bg-gray-900 p-4 text-xs text-gray-100">
          {JSON.stringify(user, null, 2)}
        </pre>
      </section>

      <section className="space-y-3 rounded-lg border border-gray-200 p-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-700">Role dashboards</h2>
        <ul className="flex flex-wrap gap-3 text-sm">
          <li>
            <Link href="/admin/dashboard" className="text-blue-600 underline underline-offset-2 hover:text-blue-800">
              Admin dashboard
            </Link>
          </li>
          <li>
            <Link href="/manager/dashboard" className="text-blue-600 underline underline-offset-2 hover:text-blue-800">
              Manager dashboard
            </Link>
          </li>
          <li>
            <Link
              href="/estimator/dashboard"
              className="text-blue-600 underline underline-offset-2 hover:text-blue-800"
            >
              Estimator dashboard
            </Link>
          </li>
          <li>
            <Link
              href="/engineer/assigned-estimates"
              className="text-blue-600 underline underline-offset-2 hover:text-blue-800"
            >
              Engineer assigned estimates
            </Link>
          </li>
        </ul>
      </section>
    </main>
  );
}
