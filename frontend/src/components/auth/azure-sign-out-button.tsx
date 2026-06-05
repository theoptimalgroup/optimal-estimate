"use client";

import { useMsal } from "@azure/msal-react";

export function AzureSignOutButton() {
  const { instance } = useMsal();

  const handleSignOut = async () => {
    await instance.logoutRedirect({ postLogoutRedirectUri: `${window.location.origin}/login` });
  };

  return (
    <button
      type="button"
      onClick={() => void handleSignOut()}
      data-testid="azure-sign-out"
      className="h-9 rounded-lg border border-slate-300 bg-white px-3 text-xs font-medium text-slate-700 shadow-sm hover:bg-slate-50"
    >
      Sign out
    </button>
  );
}
