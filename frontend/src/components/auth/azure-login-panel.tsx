"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useMsal } from "@azure/msal-react";

import { PrimaryButton } from "@/components/ui/buttons";
import { LoadingState } from "@/components/ui/states";
import { useCurrentUser } from "@/lib/auth/auth-context";
import { getDashboardForRole, isRegistrationError } from "@/lib/auth/dashboard-routes";
import { getLoginRequest } from "@/lib/auth/msal-config";

function MicrosoftIcon() {
  return (
    <svg aria-hidden className="size-4" viewBox="0 0 21 21" fill="none">
      <rect x="1" y="1" width="9" height="9" fill="#f25022" />
      <rect x="11" y="1" width="9" height="9" fill="#7fba00" />
      <rect x="1" y="11" width="9" height="9" fill="#00a4ef" />
      <rect x="11" y="11" width="9" height="9" fill="#ffb900" />
    </svg>
  );
}

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
      <main className="flex min-h-screen items-center justify-center bg-slate-50" data-testid="login-loading">
        <LoadingState message="Signing in…" />
      </main>
    );
  }

  if (isAuthenticated && user?.role === "client") {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
        <div
          className="w-full max-w-md space-y-4 rounded-2xl border border-amber-200 bg-amber-50 p-8 text-center shadow-sm"
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
    <main className="flex min-h-screen items-center justify-center bg-app-bg px-4">
      <div className="w-full max-w-md space-y-6 rounded-xl border border-app-border bg-app-card p-8 shadow-sm">
        <div className="space-y-4 text-center">
          <Image
            src="/optimal-group-logo-light.png"
            alt="Optimal Group"
            width={200}
            height={58}
            className="mx-auto h-9 w-auto object-contain"
            priority
          />
          <div className="space-y-1">
            <h1 className="text-page-title text-app-text">Sign in</h1>
            <p className="text-body text-app-muted">Sign in with your company Microsoft account</p>
          </div>
        </div>

        {displayError ? (
          <div
            className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
            data-testid="login-error"
            role="alert"
          >
            {displayError}
          </div>
        ) : null}

        <PrimaryButton
          onClick={() => void handleSignIn()}
          disabled={signingIn || msalBusy}
          data-testid="login-microsoft-button"
          className="w-full bg-[#2f2f2f] hover:bg-black"
        >
          <MicrosoftIcon />
          Sign in with Microsoft
        </PrimaryButton>

        <p className="text-center text-helper text-app-muted">
          After sign-in, your app role comes from the users table — not from Microsoft groups.
        </p>

        <div className="text-center">
          <button
            type="button"
            onClick={() => void refetchUser()}
            className="text-xs text-slate-500 underline underline-offset-2 hover:text-slate-800"
          >
            Already signed in? Refresh session
          </button>
        </div>
      </div>
    </main>
  );
}
