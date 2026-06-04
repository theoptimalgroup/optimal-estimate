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
      className="rounded-md border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
    >
      Sign out
    </button>
  );
}
