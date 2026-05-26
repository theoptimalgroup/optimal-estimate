import { defineConfig } from "@playwright/test";

const e2ePort = process.env.PLAYWRIGHT_PORT ?? "3001";
const e2eBaseUrl = process.env.PLAYWRIGHT_BASE_URL ?? `http://127.0.0.1:${e2ePort}`;

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
        reuseExistingServer: !process.env.CI,
        env: {
          ...process.env,
          NEXT_PUBLIC_API_URL: process.env.PLAYWRIGHT_API_URL ?? "http://127.0.0.1:8000",
        },
      },
});
