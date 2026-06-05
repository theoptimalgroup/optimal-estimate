import { test, expect, type Page } from "@playwright/test";

const mockPublicQuote = {
  quote_ref: "Q-1001",
  client_name: "Atkinson McLeod",
  trade_name: "Painter",
  status: "submitted",
  scope_of_work: "Repaint hallway and landing",
  works: [
    {
      title: "Work 1",
      product_name: "Painting",
      scope: "Repaint hallway and landing",
      description: "Two coats emulsion",
      materials_summary: "Paint supplies",
      attachments: [],
    },
  ],
  summary: {
    work_charges: 800,
    materials: 200,
    additional_charges: 50,
    subtotal: 1050,
    vat: 210,
    total: 1260,
  },
  terms: "This quote is provided for review purposes.",
  created_at: "2026-06-01T10:00:00Z",
  submitted_at: "2026-06-01T12:00:00Z",
  acceptance: {
    accepted: false,
    accepted_at: null,
    name: null,
  },
};

const mockSettings = {
  app: {
    environment: "development",
    debug: true,
    version: "1.0.0",
    api_prefix: "/api/v1",
    formula_version: "1.0.0",
    template_version: "1.0.0",
  },
  auth: {
    dev_auth_enabled: true,
    dev_auth_email: "admin@optimal.example",
    dev_auth_auto_create_user: false,
    azure_enabled: false,
    auth_provider: "dev",
  },
  eworks: {
    base_url_configured: true,
    api_key_configured: true,
    license_key_configured: false,
    api_enabled: true,
  },
  dashboard: {
    password_configured: true,
    password_value: "***REDACTED***",
  },
  storage: {
    provider: "local",
    azure_blob_configured: false,
  },
  pdf: {
    enabled: true,
    engine: "weasyprint",
  },
  database: {
    configured: true,
    url: "***REDACTED***",
  },
  security: {
    cors_origins_count: 1,
    allowed_hosts_count: null,
  },
};

const mockStatus = {
  database_reachable: true,
  counts: {
    users: 5,
    clients: 12,
    trades: 8,
    products: 120,
    rate_rules: 24,
    submitted_sessions: 3,
    audit_logs: 42,
  },
  last_product_sync_at: "2026-06-01T10:00:00Z",
  latest_audit_log_at: "2026-06-04T09:00:00Z",
};

const mockDashboard = {
  kpis: {
    draft_count: 2,
    submitted_count: 4,
    reopened_count: 1,
    total_submitted_value: 5400,
    average_quote_value: 1350,
  },
  recent_quotes: [],
  needs_attention: [],
};

type MockUserRole = "admin" | "manager" | "estimator" | "engineer";

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

async function mockSettingsApi(page: Page) {
  await page.route("**/api/v1/settings/status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ success: true, data: mockStatus }),
    });
  });
  await page.route("**/api/v1/settings**", async (route) => {
    if (route.request().url().includes("/settings/status")) {
      await route.continue();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ success: true, data: mockSettings }),
    });
  });
}

async function mockManagerReviewApi(page: Page) {
  await page.route("**/api/v1/dashboard/quotes", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: {
          quotes: [],
        },
      }),
    });
  });
}

async function mockEstimatorDashboardApi(page: Page) {
  await page.route("**/api/v1/estimator/dashboard", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ success: true, data: mockDashboard }),
    });
  });
  await page.route("**/api/v1/estimator/quotes**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ success: true, data: [], meta: { total: 0, limit: 50, offset: 0 } }),
    });
  });
}

async function mockPublicQuoteApi(page: Page) {
  await page.route("**/api/v1/client-quotes/public/test-public-token", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, data: mockPublicQuote }),
      });
      return;
    }
    await route.continue();
  });
}

async function assertForbiddenStringsAbsent(page: Page) {
  await expect(page.getByText("internal notes")).toHaveCount(0);
  await expect(page.getByText("profit")).toHaveCount(0);
  await expect(page.getByText("margin")).toHaveCount(0);
  await expect(page.getByText("cost price")).toHaveCount(0);
  await expect(page.getByText("formula")).toHaveCount(0);
  await expect(page.getByText("denominator")).toHaveCount(0);
  await expect(page.getByText("session_token")).toHaveCount(0);
  await expect(page.getByText("api_key")).toHaveCount(0);
  await expect(page.getByText("dashboard_password")).toHaveCount(0);
}

test.describe("Phase 21 UI modernization smoke tests", () => {
  test("/login renders Microsoft button or dev auth", async ({ page }) => {
    await page.goto("/login");

    const azureButton = page.getByTestId("login-microsoft-button");
    const devPanel = page.getByRole("heading", { name: "Dev authentication" });

    if (await azureButton.isVisible().catch(() => false)) {
      await expect(azureButton).toBeVisible();
      await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
    } else {
      await expect(devPanel).toBeVisible();
    }
  });

  test("/admin/settings still loads with mocked auth", async ({ page }) => {
    await mockAuthMe(page, "admin");
    await mockSettingsApi(page);
    await page.goto("/admin/settings");
    await expect(page.getByTestId("admin-settings-page")).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId("settings-app-card")).toBeVisible({ timeout: 15000 });
  });

  test("/manager/review still loads with mocked auth", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockManagerReviewApi(page);
    await page.goto("/manager/review");
    await expect(page.getByTestId("app-shell")).toBeVisible({ timeout: 15000 });
    await expect(page.getByRole("heading", { name: "Approvals & Quotes" })).toBeVisible();
  });

  test("/estimator/dashboard still loads with mocked auth", async ({ page }) => {
    await mockAuthMe(page, "estimator");
    await mockEstimatorDashboardApi(page);
    await page.goto("/estimator/dashboard");
    await expect(page.getByTestId("estimator-dashboard-page")).toBeVisible({ timeout: 15000 });
  });

  test("/engineer/jobs still loads with mocked auth", async ({ page }) => {
    await mockAuthMe(page, "engineer");
    await page.goto("/engineer/jobs");
    await expect(page.getByTestId("app-shell")).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId("engineer-open-session-card")).toBeVisible();
    await expect(page.getByRole("heading", { name: "My Jobs" })).toBeVisible();
  });

  test("/client/quote mocked page hides forbidden strings", async ({ page }) => {
    await mockPublicQuoteApi(page);
    await page.goto("/client/quote/test-public-token");
    await expect(page.getByTestId("client-quote-page")).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId("client-quote-summary")).toBeVisible();
    await assertForbiddenStringsAbsent(page);
    await expect(page.locator('[data-testid="app-shell"]')).toHaveCount(0);
  });

  test("/eworks/calculate still loads without auth", async ({ page }) => {
    await page.route("**/api/v1/auth/me", async (route) => {
      await route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Not authenticated" }),
      });
    });
    await page.goto("/eworks/calculate");
    await expect(page.getByTestId("eworks-internal-nav-bar")).toHaveCount(0);
    await expect(page.getByTestId("app-shell")).toHaveCount(0);
    await expect(
      page
        .getByText(/OPTIMAL ESTIMATE|Estimate Calculator|Calculate|Invalid calculation link|Start local test session/i)
        .first(),
    ).toBeVisible({
      timeout: 15000,
    });
  });
});
