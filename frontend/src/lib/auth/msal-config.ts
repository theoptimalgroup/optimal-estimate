import type { Configuration } from "@azure/msal-browser";

/** Next.js only inlines NEXT_PUBLIC_* when accessed statically (not via process.env[name]). */
export const azureTenantId = process.env.NEXT_PUBLIC_AZURE_TENANT_ID ?? "";
export const azureClientId = process.env.NEXT_PUBLIC_AZURE_CLIENT_ID ?? "";
export const azureApiScope = process.env.NEXT_PUBLIC_AZURE_API_SCOPE ?? "";

export function isAzureConfigured(): boolean {
  return Boolean(azureTenantId && azureClientId && azureApiScope);
}

export function getMissingAzureEnvVars(): string[] {
  const missing: string[] = [];
  if (!azureTenantId) missing.push("NEXT_PUBLIC_AZURE_TENANT_ID");
  if (!azureClientId) missing.push("NEXT_PUBLIC_AZURE_CLIENT_ID");
  if (!azureApiScope) missing.push("NEXT_PUBLIC_AZURE_API_SCOPE");
  return missing;
}

export function getAzureRedirectUri(): string {
  // Must match a redirect URI registered on the SPA app in Azure Portal (typically the origin only).
  if (typeof window !== "undefined") {
    return window.location.origin;
  }
  return "http://localhost:3000";
}

export function getAzurePostLogoutRedirectUri(): string {
  if (typeof window !== "undefined") {
    return `${window.location.origin}/login`;
  }
  return "http://localhost:3000/login";
}

export function getMsalConfig(): Configuration {
  if (!isAzureConfigured()) {
    throw new Error(`Missing Azure env: ${getMissingAzureEnvVars().join(", ")}`);
  }

  return {
    auth: {
      clientId: azureClientId,
      authority: `https://login.microsoftonline.com/${azureTenantId}`,
      redirectUri: getAzureRedirectUri(),
      postLogoutRedirectUri: getAzurePostLogoutRedirectUri(),
    },
    cache: {
      cacheLocation: "sessionStorage",
      storeAuthStateInCookie: false,
    },
  };
}

export function getLoginRequest() {
  return {
    scopes: [azureApiScope],
  };
}
