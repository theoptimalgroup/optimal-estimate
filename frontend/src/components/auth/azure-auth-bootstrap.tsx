"use client";

import { InteractionRequiredAuthError } from "@azure/msal-browser";
import { useMsal } from "@azure/msal-react";
import { useEffect, type ReactNode } from "react";

import { getLoginRequest } from "@/lib/auth/msal-config";
import { notifyMsalReady, setAccessTokenGetter } from "@/lib/auth/token-provider";

type AzureAuthBootstrapProps = {
  children: ReactNode;
};

async function resolveAccessToken(
  instance: ReturnType<typeof useMsal>["instance"],
  accounts: ReturnType<typeof useMsal>["accounts"],
): Promise<{ hasAccount: boolean; hasAccessToken: boolean }> {
  const account = instance.getActiveAccount() ?? accounts[0] ?? null;
  if (!account) {
    return { hasAccount: false, hasAccessToken: false };
  }

  try {
    const result = await instance.acquireTokenSilent({
      ...getLoginRequest(),
      account,
    });
    return { hasAccount: true, hasAccessToken: Boolean(result.accessToken) };
  } catch (error) {
    if (error instanceof InteractionRequiredAuthError) {
      return { hasAccount: true, hasAccessToken: false };
    }
    throw error;
  }
}

export function AzureAuthBootstrap({ children }: AzureAuthBootstrapProps) {
  const { instance, accounts } = useMsal();

  useEffect(() => {
    let cancelled = false;

    setAccessTokenGetter(async () => {
      const state = await resolveAccessToken(instance, accounts);
      if (!state.hasAccessToken) {
        return null;
      }
      const account = instance.getActiveAccount() ?? accounts[0] ?? null;
      if (!account) {
        return null;
      }
      const result = await instance.acquireTokenSilent({
        ...getLoginRequest(),
        account,
      });
      return result.accessToken;
    });

    void resolveAccessToken(instance, accounts).then((state) => {
      if (!cancelled) {
        notifyMsalReady(state);
      }
    });

    return () => {
      cancelled = true;
      setAccessTokenGetter(null);
    };
  }, [instance, accounts]);

  return <>{children}</>;
}
