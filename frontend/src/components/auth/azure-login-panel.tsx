"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useMsal } from "@azure/msal-react";

import { useCurrentUser } from "@/lib/auth/auth-context";
import { getDashboardForRole, isRegistrationError } from "@/lib/auth/dashboard-routes";
import { getLoginRequest } from "@/lib/auth/msal-config";

export function AzureLoginPanel() {
  const router = useRouter();
  const { instance, inProgress } = useMsal();
  const { user, isLoading, isAuthenticated, error, refetchUser } = useCurrentUser();
  const [actionError, setActionError] = useState<string | null>(null);
  const [signingIn, setSigningIn] = useState(false);

  const displayError = actionError ?? (isRegistrationError(error) ? error : null);
  const msalBusy = inProgress !== "none";

  useEffect(() => {
    if (isLoading || !isAuthenticated || !user) {
      return;
    }

    const dashboard = getDashboardForRole(user.role);
    if (dashboard) {
      router.replace(dashboard);
    }
  }, [isLoading, isAuthenticated, user, router]);

  const handleSignIn = async () => {
    setActionError(null);
    setSigningIn(true);
    try {
      await instance.loginRedirect(getLoginRequest());
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Sign-in failed");
      setSigningIn(false);
    }
  };

  if (isLoading || msalBusy || signingIn) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gray-50" data-testid="login-loading">
        <p className="text-sm text-gray-600">Signing in…</p>
      </main>
    );
  }

  if (isAuthenticated && user?.role === "client") {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
        <div
          className="w-full max-w-md space-y-4 rounded-xl border border-amber-200 bg-amber-50 p-8 text-center"
          data-testid="login-client-unsupported"
        >
          <h1 className="text-xl font-semibold text-amber-900">Internal access not available</h1>
          <p className="text-sm text-amber-800">
            Your account is registered as a client. Internal staff dashboards are not available for this role.
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md space-y-6 rounded-xl border border-gray-200 bg-white p-8 shadow-sm">
        <div className="space-y-2 text-center">
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">Optimal Estimate</p>
          <h1 className="text-2xl font-bold text-gray-900">Sign in</h1>
          <p className="text-sm text-gray-600">Use your Microsoft work account to access the estimate workspace.</p>
        </div>

        {displayError ? (
          <div
            className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
            data-testid="login-error"
          >
            {displayError}
          </div>
        ) : null}

        <button
          type="button"
          onClick={() => void handleSignIn()}
          disabled={signingIn || msalBusy}
          data-testid="login-microsoft-button"
          className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-[#2f2f2f] px-4 py-2.5 text-sm font-medium text-white hover:bg-black disabled:cursor-not-allowed disabled:opacity-60"
        >
          <span aria-hidden="true">⬡</span>
          Sign in with Microsoft
        </button>

        <p className="text-center text-xs text-gray-500">
          After sign-in, your app role comes from the users table — not from Microsoft groups.
        </p>

        <div className="text-center">
          <button
            type="button"
            onClick={() => void refetchUser()}
            className="text-xs text-gray-500 underline underline-offset-2 hover:text-gray-800"
          >
            Already signed in? Refresh session
          </button>
        </div>
      </div>
    </main>
  );
}
