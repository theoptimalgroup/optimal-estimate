import { test, expect, type Locator, type Page } from "@playwright/test";

type MockUserRole = "admin" | "manager" | "engineer";

function mockUser(role: MockUserRole) {
  return {
    id: `dev-${role}`,
    email: `${role}@example.com`,
    name: `Dev ${role.charAt(0).toUpperCase()}${role.slice(1)}`,
    role,
    is_active: true,
    auth_provider: "dev",
  };
}

async function mockAuthMe(page: Page, role: MockUserRole) {
  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ success: true, data: mockUser(role) }),
    });
  });
}

const EWORKS_SYNC_API = process.env.PLAYWRIGHT_API_URL ?? "http://127.0.0.1:8000";

const MOCK_RUN_ID = "aaaa-1111";

const MOCK_IDLE_STATUS = {
  quotes_count: 0,
  jobs_count: 0,
  customers_count: 0,
  last_quotes_sync: null,
  last_jobs_sync: null,
  last_customers_sync: null,
  eworks_api_enabled: true,
  active_sync: null,
  background_sync: {
    enabled: false,
    worker_enabled: false,
    scheduler_active: false,
    quotes_enabled: false,
    jobs_enabled: false,
    products_enabled: false,
    attachments_enabled: false,
    quotes_interval_minutes: 10,
    jobs_interval_minutes: 30,
    products_interval_minutes: 1440,
    lookback_days: 7,
    running_timeout_minutes: 30,
  },
  last_background_sync: null,
};

const MOCK_RUN_RUNNING = {
  id: MOCK_RUN_ID,
  sync_type: "all",
  status: "running",
  started_at: "2026-06-01T10:00:00Z",
  finished_at: null,
  fetched_count: 12,
  created_count: 0,
  updated_count: 4,
  failed_count: 0,
  error_message: null,
  metadata: { phase: "quotes" },
};

async function clearEworksSyncSessionStorage(page: Page) {
  await page.addInitScript(() => {
    sessionStorage.removeItem("eworks-active-sync-run");
  });
}

/** Proxy read-only eWorks sync GET calls via Node fetch (avoids browser CORS and route.fetch page-lifecycle errors). */
async function proxyEworksSyncReads(page: Page) {
  await page.route("**/api/v1/eworks-sync/**", async (route) => {
    if (route.request().method() !== "GET") {
      await route.fallback();
      return;
    }
    try {
      const request = route.request();
      const url = new URL(request.url());
      const backendUrl = `${EWORKS_SYNC_API}${url.pathname}${url.search}`;
      const response = await fetch(backendUrl, {
        method: "GET",
        headers: {
          Accept: request.headers().accept ?? "application/json",
          "Content-Type": "application/json",
        },
      });
      await route.fulfill({
        status: response.status,
        contentType: response.headers.get("content-type") ?? "application/json",
        body: await response.text(),
      });
    } catch {
      try {
        await route.abort();
      } catch {
        // Page may close while requests are still in flight.
      }
    }
  });
}

const MOCK_RUN_SUCCESS = {
  id: MOCK_RUN_ID,
  sync_type: "all",
  status: "success",
  started_at: "2026-06-01T10:00:00Z",
  finished_at: "2026-06-01T10:00:10Z",
  fetched_count: 59,
  created_count: 20,
  updated_count: 39,
  failed_count: 0,
  error_message: null,
  metadata: {
    phase: "completed",
    customers: { fetched: 12, created: 3, updated: 9, failed: 0 },
    quotes: { fetched: 42, created: 5, updated: 37, failed: 0 },
    jobs: { fetched: 17, created: 2, updated: 15, failed: 0 },
    errors: [],
  },
};

async function mockIdleEworksSyncStatus(page: Page) {
  await page.route("**/api/v1/eworks-sync/status**", async (route) => {
    if (route.request().method() !== "GET") {
      await route.fallback();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ success: true, data: MOCK_IDLE_STATUS }),
    });
  });
}

async function mockPersistentRunningSync(page: Page) {
  await mockIdleEworksSyncStatus(page);

  await page.route(`**/api/v1/eworks-sync/runs/${MOCK_RUN_ID}`, async (route) => {
    if (route.request().method() !== "GET") {
      await route.fallback();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ success: true, data: MOCK_RUN_RUNNING }),
    });
  });

  await page.route("**/api/v1/eworks-sync/all**", async (route) => {
    if (route.request().method() !== "POST") {
      await route.fallback();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: {
          run_id: MOCK_RUN_ID,
          sync_type: "all",
          status: "running",
          message: "Sync started in background",
        },
      }),
    });
  });
}

async function mockSyncTriggerApis(page: Page) {
  let pollCount = 0;

  await page.route(`**/api/v1/eworks-sync/runs/${MOCK_RUN_ID}`, async (route) => {
    pollCount += 1;
    const isRunning = pollCount < 3;
    const run = isRunning
      ? {
          ...MOCK_RUN_SUCCESS,
          status: "running",
          finished_at: null,
          fetched_count: 0,
          metadata: { phase: pollCount === 1 ? "customers" : pollCount === 2 ? "quotes" : "jobs" },
        }
      : MOCK_RUN_SUCCESS;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ success: true, data: run }),
    });
  });

  await page.route("**/api/v1/eworks-sync/all**", async (route) => {
    if (route.request().method() !== "POST") {
      await route.fallback();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: {
          run_id: MOCK_RUN_ID,
          sync_type: "all",
          status: "running",
          message: "Sync started in background",
        },
      }),
    });
  });
}

async function gotoEworksSyncPage(page: Page) {
  await page.goto("/admin/eworks-sync");
  await expect(page.getByTestId("eworks-sync-page")).toBeVisible({ timeout: 15000 });
}

async function waitForSyncOverview(page: Page) {
  await expect(page.getByTestId("eworks-sync-status-cards")).toBeVisible({ timeout: 30000 });
}

async function expectNumericCountCard(card: Locator) {
  await expect(card).toBeVisible();
  const text = (await card.innerText()).replace(/,/g, "");
  expect(text).toMatch(/\d+/);
}

async function expectCustomersTabContent(page: Page) {
  const panel = page.getByTestId("eworks-sync-tab-customers-panel");
  await expect(panel).toBeVisible({ timeout: 15000 });
  const table = panel.getByTestId("eworks-sync-customers-table");
  const empty = panel.getByTestId("eworks-sync-empty-customers");
  await expect(table.or(empty)).toBeVisible({ timeout: 30000 });
}

async function expectQuotesTabContent(page: Page) {
  const panel = page.getByTestId("eworks-sync-tab-quotes-panel");
  await expect(panel).toBeVisible({ timeout: 15000 });
  const table = panel.getByTestId("eworks-sync-quotes-table");
  const empty = panel.getByTestId("eworks-sync-empty-quotes");
  await expect(table.or(empty)).toBeVisible({ timeout: 30000 });
}

async function expectJobsTabContent(page: Page) {
  const panel = page.getByTestId("eworks-sync-tab-jobs-panel");
  await expect(panel).toBeVisible({ timeout: 15000 });
  const table = panel.getByTestId("eworks-sync-jobs-table");
  const empty = panel.getByTestId("eworks-sync-empty-jobs");
  await expect(table.or(empty)).toBeVisible({ timeout: 30000 });
}

async function expectRecentSyncRunsContent(page: Page) {
  const table = page.getByTestId("eworks-sync-runs-table");
  const empty = page.getByTestId("eworks-sync-empty-runs");
  await expect(table.or(empty)).toBeVisible({ timeout: 15000 });
}

async function assertNoSecretsVisible(page: Page) {
  await expect(page.getByText("EWORKS_API_KEY")).toHaveCount(0);
  await expect(page.getByText("api_key")).toHaveCount(0);
  await expect(page.getByText("session_token")).toHaveCount(0);
  await expect(page.getByText("dashboard_password")).toHaveCount(0);
  await expect(page.getByText("super-secret")).toHaveCount(0);
}

// ---------------------------------------------------------------------------
// Admin access tests
// ---------------------------------------------------------------------------

test.describe("Admin: /admin/eworks-sync", () => {
  test.beforeEach(async ({ page }) => {
    await clearEworksSyncSessionStorage(page);
    await mockAuthMe(page, "admin");
    await proxyEworksSyncReads(page);
  });

  test.afterEach(async ({ page }) => {
    await page.unrouteAll({ behavior: "ignoreErrors" });
  });

  test("admin can open eWorks Sync page", async ({ page }) => {
    await gotoEworksSyncPage(page);
    await expect(page.getByTestId("eworks-sync-title")).toContainText("eWorks Sync");
  });

  test("admin sees status cards with counts", async ({ page }) => {
    await gotoEworksSyncPage(page);
    await waitForSyncOverview(page);
    await expectNumericCountCard(page.getByTestId("eworks-sync-card-customers-count"));
    await expectNumericCountCard(page.getByTestId("eworks-sync-card-quotes-count"));
    await expectNumericCountCard(page.getByTestId("eworks-sync-card-jobs-count"));
    await expect(page.getByTestId("eworks-sync-card-last-status")).toBeVisible();
  });

  test("admin sees background sync configuration", async ({ page }) => {
    await gotoEworksSyncPage(page);
    await waitForSyncOverview(page);
    await expect(page.getByTestId("eworks-sync-background-config")).toBeVisible();
    await expect(page.getByTestId("background-sync-status")).toBeVisible();
    await expect(page.getByTestId("background-sync-last-run")).toBeVisible();
  });

  test("admin sees read-only warning", async ({ page }) => {
    await gotoEworksSyncPage(page);
    await expect(page.getByTestId("eworks-sync-readonly-warning")).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId("eworks-sync-readonly-warning")).toContainText("Read-only from eWorks");
  });

  test("admin sees sync buttons", async ({ page }) => {
    await gotoEworksSyncPage(page);
    await expect(page.getByTestId("btn-sync-all")).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId("btn-sync-quotes")).toBeVisible();
    await expect(page.getByTestId("btn-sync-jobs")).toBeVisible();
    await expect(page.getByTestId("btn-sync-customers")).toBeVisible();
  });

  test("admin can trigger Sync All and sees result summary", async ({ page }) => {
    await mockSyncTriggerApis(page);
    await gotoEworksSyncPage(page);
    await page.getByTestId("btn-sync-all").click();

    await expect(page.getByTestId("sync-active-banner")).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId("sync-result")).toBeVisible({ timeout: 15000 });
    await expect(page.getByText("Sync completed")).toBeVisible();
  });

  test("sync banner stays visible when switching tabs", async ({ page }) => {
    await mockPersistentRunningSync(page);
    await gotoEworksSyncPage(page);
    await page.getByTestId("btn-sync-all").click();

    const banner = page.getByTestId("sync-active-banner");
    await expect(banner).toBeVisible({ timeout: 15000 });

    await page.getByTestId("eworks-sync-tab-quotes").click();
    await expect(banner).toBeVisible();

    await page.getByTestId("eworks-sync-tab-jobs").click();
    await expect(banner).toBeVisible();
  });

  test("admin sees recent sync runs table", async ({ page }) => {
    await gotoEworksSyncPage(page);
    await waitForSyncOverview(page);
    await expectRecentSyncRunsContent(page);
  });

  test("admin can view Customers tab", async ({ page }) => {
    await gotoEworksSyncPage(page);
    await page.getByTestId("eworks-sync-tab-customers").click();
    await expectCustomersTabContent(page);
  });

  test("admin can view Quotes tab", async ({ page }) => {
    await gotoEworksSyncPage(page);
    await page.getByTestId("eworks-sync-tab-quotes").click();
    await expectQuotesTabContent(page);
  });

  test("admin can view Jobs tab", async ({ page }) => {
    await gotoEworksSyncPage(page);
    await page.getByTestId("eworks-sync-tab-jobs").click();
    await expectJobsTabContent(page);
  });

  test("no API key or secret visible in DOM", async ({ page }) => {
    await gotoEworksSyncPage(page);
    await assertNoSecretsVisible(page);
  });
});

// ---------------------------------------------------------------------------
// Non-admin access tests
// ---------------------------------------------------------------------------

test.describe("Non-admin: /admin/eworks-sync blocked", () => {
  test("manager gets redirected/blocked from /admin/eworks-sync", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await page.goto("/admin/eworks-sync");
    await expect(page.getByTestId("require-role-forbidden")).toBeVisible({ timeout: 15000 });
    await expect(page.getByText("You do not have access to this page.")).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Navigation item test
// ---------------------------------------------------------------------------

test("admin sidebar shows eWorks Sync navigation item", async ({ page }) => {
  await mockAuthMe(page, "admin");
  await page.goto("/admin/dashboard");
  await expect(page.getByRole("link", { name: /eWorks Sync/i })).toBeVisible({ timeout: 15000 });
});
