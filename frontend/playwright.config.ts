import { defineConfig } from "@playwright/test";

const useAzureAuthBuild = process.env.PLAYWRIGHT_AZURE_AUTH === "1";
const e2ePort = useAzureAuthBuild
  ? (process.env.PLAYWRIGHT_AZURE_PORT ?? "3002")
  : (process.env.PLAYWRIGHT_PORT ?? "3001");
const e2eBaseUrl = process.env.PLAYWRIGHT_BASE_URL ?? `http://127.0.0.1:${e2ePort}`;

const webServerEnv = useAzureAuthBuild
  ? {
      ...process.env,
      NEXT_PUBLIC_AUTH_PROVIDER: "azure",
      NEXT_PUBLIC_API_URL: process.env.PLAYWRIGHT_API_URL ?? "http://127.0.0.1:8000",
      NEXT_PUBLIC_AZURE_TENANT_ID: process.env.NEXT_PUBLIC_AZURE_TENANT_ID ?? "test-tenant-id",
      NEXT_PUBLIC_AZURE_CLIENT_ID: process.env.NEXT_PUBLIC_AZURE_CLIENT_ID ?? "test-spa-client-id",
      NEXT_PUBLIC_AZURE_API_SCOPE:
        process.env.NEXT_PUBLIC_AZURE_API_SCOPE ?? "api://test-api-client-id/access_as_user",
    }
  : {
      ...process.env,
      NEXT_PUBLIC_AUTH_PROVIDER: "dev",
      NEXT_PUBLIC_API_URL: process.env.PLAYWRIGHT_API_URL ?? "http://127.0.0.1:8000",
    };

export default defineConfig({
  testDir: "./e2e",
  globalSetup: "./e2e/global-setup.ts",
  retries: 2,
  timeout: 120000,
  use: {
    baseURL: e2eBaseUrl,
    headless: true,
  },
  webServer: process.env.PLAYWRIGHT_SKIP_WEBSERVER
    ? undefined
    : {
        command: `npm run dev -- -p ${e2ePort}`,
        url: e2eBaseUrl,
        reuseExistingServer: !process.env.CI && !useAzureAuthBuild,
        env: webServerEnv,
      },
});
