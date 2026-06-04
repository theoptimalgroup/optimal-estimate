"use client";

import { useCurrentUser } from "@/lib/auth/auth-context";

export function DevAuthStatus() {
  const { user, role, isLoading, error, refetchUser } = useCurrentUser();

  if (process.env.NODE_ENV !== "development") {
    return null;
  }

  if (isLoading) {
    return (
      <p className="text-xs text-gray-500" data-testid="dev-auth-status">
        Dev Auth: loading…
      </p>
    );
  }

  if (error) {
    return (
      <p className="text-xs text-red-600" data-testid="dev-auth-status">
        Dev Auth: error — {error}
      </p>
    );
  }

  if (!user) {
    return (
      <p className="text-xs text-gray-500" data-testid="dev-auth-status">
        Dev Auth: not authenticated (enable DEV_AUTH_ENABLED on backend)
      </p>
    );
  }

  return (
    <p className="text-xs text-gray-600" data-testid="dev-auth-status">
      Dev Auth: {role ?? user.role} ·{" "}
      <a href={`mailto:${user.email}`} className="underline underline-offset-2 hover:text-gray-900">
        {user.email}
      </a>
      {user.auth_provider ? ` · ${user.auth_provider}` : null}
      {" · "}
      <button
        type="button"
        onClick={() => void refetchUser()}
        className="underline underline-offset-2 hover:text-gray-900"
        data-testid="dev-auth-refetch"
      >
        Refetch
      </button>
    </p>
  );
}
