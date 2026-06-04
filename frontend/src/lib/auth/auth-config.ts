import { isAzureConfigured } from "@/lib/auth/msal-config";

export type AuthProviderName = "dev" | "azure";

/** Next.js only inlines NEXT_PUBLIC_* when accessed statically. */
const authProviderEnv = process.env.NEXT_PUBLIC_AUTH_PROVIDER;

export function getAuthProvider(): AuthProviderName {
  return authProviderEnv === "azure" ? "azure" : "dev";
}

export function isAzureAuth(): boolean {
  return getAuthProvider() === "azure" && isAzureConfigured();
}

export function isAzureAuthRequested(): boolean {
  return authProviderEnv === "azure";
}

export function isDevAuth(): boolean {
  return !isAzureAuthRequested();
}
