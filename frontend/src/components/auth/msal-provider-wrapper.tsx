"use client";

import { PublicClientApplication } from "@azure/msal-browser";
import { MsalProvider } from "@azure/msal-react";
import { usePathname } from "next/navigation";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { AzureAuthBootstrap } from "@/components/auth/azure-auth-bootstrap";
import { isAzureAuthRequested } from "@/lib/auth/auth-config";
import { getLoginRequest, getMissingAzureEnvVars, getMsalConfig, isAzureConfigured } from "@/lib/auth/msal-config";
import { shouldSkipMsalInit } from "@/lib/auth/public-routes";
import { notifyMsalReady } from "@/lib/auth/token-provider";

let msalInstance: PublicClientApplication | null = null;

function getOrCreateMsalInstance(): PublicClientApplication {
  if (!msalInstance) {
    msalInstance = new PublicClientApplication(getMsalConfig());
  }
  return msalInstance;
}

type MsalInitContextValue = {
  ready: boolean;
  instance: PublicClientApplication | null;
  configError: string | null;
};

const MsalInitContext = createContext<MsalInitContextValue>({
  ready: !isAzureAuthRequested(),
  instance: null,
  configError: null,
});

export function useMsalInit() {
  return useContext(MsalInitContext);
}

function AzureConfigError({ missing }: { missing: string[] }) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div
        className="max-w-lg space-y-3 rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-900"
        data-testid="azure-config-error"
      >
        <p className="font-semibold">Azure sign-in is not configured</p>
        <p>
          <code className="rounded bg-red-100 px-1">NEXT_PUBLIC_AUTH_PROVIDER=azure</code> is set but these
          frontend env vars are missing:
        </p>
        <ul className="list-disc pl-5">
          {missing.map((name) => (
            <li key={name}>
              <code className="rounded bg-red-100 px-1">{name}</code>
            </li>
          ))}
        </ul>
        <p className="text-red-800">
          Add them to <code className="rounded bg-red-100 px-1">frontend/.env.local</code> and restart{" "}
          <code className="rounded bg-red-100 px-1">npm run dev</code>.
        </p>
      </div>
    </main>
  );
}

type MsalProviderWrapperProps = {
  children: ReactNode;
};

export function MsalProviderWrapper({ children }: MsalProviderWrapperProps) {
  const pathname = usePathname();
  const [instance, setInstance] = useState<PublicClientApplication | null>(null);
  const [initError, setInitError] = useState<string | null>(null);

  const skipMsal = shouldSkipMsalInit(pathname);
  const missingVars = isAzureAuthRequested() && !isAzureConfigured() ? getMissingAzureEnvVars() : [];

  useEffect(() => {
    if (skipMsal || !isAzureAuthRequested() || !isAzureConfigured()) {
      if (skipMsal) {
        setInstance(null);
        setInitError(null);
        notifyMsalReady({ hasAccount: false, hasAccessToken: false });
      }
      return;
    }

    let cancelled = false;

    try {
      const pca = getOrCreateMsalInstance();
      void pca
        .initialize()
        .then(() => pca.handleRedirectPromise())
        .then(async (result) => {
          if (result?.account) {
            pca.setActiveAccount(result.account);
          } else {
            const existingAccount = pca.getAllAccounts()[0];
            if (existingAccount) {
              pca.setActiveAccount(existingAccount);
            }
          }

          const account = pca.getActiveAccount() ?? pca.getAllAccounts()[0] ?? null;
          if (!account) {
            if (!cancelled) {
              notifyMsalReady({ hasAccount: false, hasAccessToken: false });
            }
            return;
          }

          if (result?.accessToken) {
            if (!cancelled) {
              notifyMsalReady({ hasAccount: true, hasAccessToken: true });
            }
            return;
          }

          try {
            const tokenResult = await pca.acquireTokenSilent({
              ...getLoginRequest(),
              account,
            });
            if (!cancelled) {
              notifyMsalReady({
                hasAccount: true,
                hasAccessToken: Boolean(tokenResult.accessToken),
              });
            }
          } catch {
            if (!cancelled) {
              notifyMsalReady({ hasAccount: true, hasAccessToken: false });
            }
          }
        })
        .catch((error: unknown) => {
          if (!cancelled) {
            setInitError(error instanceof Error ? error.message : "Failed to initialize Microsoft sign-in");
          }
        })
        .finally(() => {
          if (!cancelled) {
            setInstance(pca);
          }
        });
    } catch (error: unknown) {
      setInitError(error instanceof Error ? error.message : "Failed to initialize Microsoft sign-in");
    }

    return () => {
      cancelled = true;
    };
  }, [skipMsal]);

  const initValue: MsalInitContextValue = {
    ready:
      skipMsal ||
      !isAzureAuthRequested() ||
      !isAzureConfigured() ||
      instance !== null ||
      Boolean(initError),
    instance,
    configError: initError,
  };

  if (missingVars.length > 0) {
    return <AzureConfigError missing={missingVars} />;
  }

  if (skipMsal || !isAzureAuthRequested() || !isAzureConfigured()) {
    return <MsalInitContext.Provider value={initValue}>{children}</MsalInitContext.Provider>;
  }

  if (initError) {
    return (
      <MsalInitContext.Provider value={initValue}>
        <main className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
          <div className="max-w-lg rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-900">
            <p className="font-semibold">Microsoft sign-in failed to start</p>
            <p className="mt-2">{initError}</p>
          </div>
        </main>
      </MsalInitContext.Provider>
    );
  }

  if (!instance) {
    return <MsalInitContext.Provider value={initValue}>{children}</MsalInitContext.Provider>;
  }

  return (
    <MsalInitContext.Provider value={initValue}>
      <MsalProvider instance={instance}>
        <AzureAuthBootstrap>{children}</AzureAuthBootstrap>
      </MsalProvider>
    </MsalInitContext.Provider>
  );
}
