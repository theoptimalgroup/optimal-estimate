import { test, expect, type Page } from "@playwright/test";

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

const MOCK_STATUS = {
  quotes_count: 42,
  jobs_count: 17,
  last_quotes_sync: "2026-06-01T10:00:00Z",
  last_jobs_sync: "2026-06-01T10:05:00Z",
  eworks_api_enabled: true,
};

const MOCK_RUNS = {
  items: [
    {
      id: "aaaa-1111",
      sync_type: "all",
      status: "success",
      started_at: "2026-06-01T10:00:00Z",
      finished_at: "2026-06-01T10:00:10Z",
      fetched_count: 59,
      created_count: 20,
      updated_count: 39,
      failed_count: 0,
      error_message: null,
    },
  ],
  total: 1,
  limit: 10,
  offset: 0,
};

const MOCK_QUOTES = {
  items: [
    {
      id: 1,
      eworks_quote_id: 101,
      quote_ref: "Q-101",
      customer_id: 5,
      customer_name: "ACME Ltd",
      status: "2",
      status_name: "Pending",
      quote_date: "2026-01-15",
      expiry_date: "2026-04-15",
      description: "Full rewire",
      customer_ref: null,
      po_ref: null,
      wo_ref: null,
      subtotal: 1200.0,
      vat: 240.0,
      total: 1440.0,
      synced_at: "2026-06-01T10:00:00Z",
    },
  ],
  total: 1,
  limit: 50,
  offset: 0,
};

const MOCK_JOBS = {
  items: [
    {
      id: 1,
      eworks_job_id: 201,
      job_ref: "J-201",
      eworks_quote_id: 101,
      customer_id: 5,
      customer_name: "ACME Ltd",
      status: "open",
      status_name: "Open",
      job_date: "2026-02-01",
      description: "Site inspection",
      address: "10 Main St, London",
      subtotal: 400.0,
      vat: 80.0,
      total: 480.0,
      synced_at: "2026-06-01T10:05:00Z",
    },
  ],
  total: 1,
  limit: 50,
  offset: 0,
};

async function mockEworksSyncApis(page: Page) {
  await page.route("**/api/v1/eworks-sync/status**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ success: true, data: MOCK_STATUS }),
    });
  });

  await page.route("**/api/v1/eworks-sync/runs**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ success: true, data: MOCK_RUNS }),
    });
  });

  await page.route("**/api/v1/eworks-sync/quotes**", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, data: MOCK_QUOTES }),
      });
    } else {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: { summary: { fetched: 42, created: 5, updated: 37, failed: 0 }, run_id: "aaaa" },
        }),
      });
    }
  });

  await page.route("**/api/v1/eworks-sync/jobs**", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, data: MOCK_JOBS }),
      });
    } else {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: { summary: { fetched: 17, created: 2, updated: 15, failed: 0 }, run_id: "bbbb" },
        }),
      });
    }
  });

  await page.route("**/api/v1/eworks-sync/all**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: {
          quotes: { fetched: 42, created: 5, updated: 37, failed: 0 },
          jobs: { fetched: 17, created: 2, updated: 15, failed: 0 },
          errors: [],
        },
      }),
    });
  });
}

// ---------------------------------------------------------------------------
// Admin access tests
// ---------------------------------------------------------------------------

test.describe("Admin: /admin/eworks-sync", () => {
  test("admin can open eWorks Sync page", async ({ page }) => {
    await mockAuthMe(page, "admin");
    await mockEworksSyncApis(page);

    await page.goto("/admin/eworks-sync");
    await expect(page.getByTestId("eworks-sync-page")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("eWorks Sync")).toBeVisible();
  });

  test("admin sees status cards with counts", async ({ page }) => {
    await mockAuthMe(page, "admin");
    await mockEworksSyncApis(page);

    await page.goto("/admin/eworks-sync");
    await expect(page.getByTestId("stat-quotes-count")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("42")).toBeVisible();
    await expect(page.getByText("17")).toBeVisible();
  });

  test("admin sees read-only warning", async ({ page }) => {
    await mockAuthMe(page, "admin");
    await mockEworksSyncApis(page);

    await page.goto("/admin/eworks-sync");
    await expect(page.getByText("Read-only from eWorks")).toBeVisible({ timeout: 10000 });
  });

  test("admin sees sync buttons", async ({ page }) => {
    await mockAuthMe(page, "admin");
    await mockEworksSyncApis(page);

    await page.goto("/admin/eworks-sync");
    await expect(page.getByTestId("btn-sync-all")).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId("btn-sync-quotes")).toBeVisible();
    await expect(page.getByTestId("btn-sync-jobs")).toBeVisible();
  });

  test("admin can trigger Sync All and sees result summary", async ({ page }) => {
    await mockAuthMe(page, "admin");
    await mockEworksSyncApis(page);

    await page.goto("/admin/eworks-sync");
    await page.getByTestId("btn-sync-all").click();

    await expect(page.getByTestId("sync-result")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Sync completed")).toBeVisible();
  });

  test("admin sees recent sync runs table", async ({ page }) => {
    await mockAuthMe(page, "admin");
    await mockEworksSyncApis(page);

    await page.goto("/admin/eworks-sync");
    await expect(page.getByTestId("sync-runs-table")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("success")).toBeVisible();
  });

  test("admin can view Quotes tab", async ({ page }) => {
    await mockAuthMe(page, "admin");
    await mockEworksSyncApis(page);

    await page.goto("/admin/eworks-sync");
    await page.getByTestId("tab-quotes").click();
    await expect(page.getByTestId("quotes-table")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("ACME Ltd")).toBeVisible();
    await expect(page.getByText("Q-101")).toBeVisible();
  });

  test("admin can view Jobs tab", async ({ page }) => {
    await mockAuthMe(page, "admin");
    await mockEworksSyncApis(page);

    await page.goto("/admin/eworks-sync");
    await page.getByTestId("tab-jobs").click();
    await expect(page.getByTestId("jobs-table")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("J-201")).toBeVisible();
    await expect(page.getByText("10 Main St, London")).toBeVisible();
  });

  test("no API key or secret visible in DOM", async ({ page }) => {
    await mockAuthMe(page, "admin");
    await mockEworksSyncApis(page);

    await page.goto("/admin/eworks-sync");
    await expect(page.getByTestId("eworks-sync-page")).toBeVisible({ timeout: 10000 });

    const bodyText = await page.locator("body").innerText();
    expect(bodyText).not.toContain("api_key");
    expect(bodyText).not.toContain("EWORKS_API_KEY");
  });
});

// ---------------------------------------------------------------------------
// Non-admin access tests
// ---------------------------------------------------------------------------

test.describe("Non-admin: /admin/eworks-sync blocked", () => {
  test("manager gets redirected/blocked from /admin/eworks-sync", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await page.route("**/api/v1/eworks-sync/**", async (route) => {
      await route.fulfill({ status: 403, body: JSON.stringify({ detail: "Forbidden" }) });
    });

    await page.goto("/admin/eworks-sync");
    // The admin layout requires admin role — manager should be redirected to login or shown denied
    // The RequireRole component redirects to /login for non-admin
    await page.waitForTimeout(2000);
    const url = page.url();
    expect(url).not.toContain("/admin/eworks-sync");
  });
});

// ---------------------------------------------------------------------------
// Navigation item test
// ---------------------------------------------------------------------------

test("admin sidebar shows eWorks Sync navigation item", async ({ page }) => {
  await mockAuthMe(page, "admin");
  await mockEworksSyncApis(page);
  await page.route("**/api/v1/**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ success: true, data: {} }),
    });
  });

  await page.goto("/admin/dashboard");
  await page.waitForTimeout(1500);
  const navItem = page.getByRole("link", { name: /eWorks Sync/i });
  await expect(navItem).toBeVisible({ timeout: 10000 });
});
