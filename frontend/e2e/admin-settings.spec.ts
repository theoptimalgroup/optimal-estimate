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

async function mockSettingsApi(page: Page) {
  await page.route("**/api/v1/settings/status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ success: true, data: mockStatus }),
    });
  });

  await page.route("**/api/v1/settings", async (route) => {
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

test.describe("Admin settings page", () => {
  test("admin can open /admin/settings and see config cards", async ({ page }) => {
    await mockAuthMe(page, "admin");
    await mockSettingsApi(page);
    await page.goto("/admin/settings");
    await expect(page.getByTestId("admin-settings-page")).toBeVisible();
    await expect(page.getByTestId("settings-app-card")).toBeVisible();
    await expect(page.getByTestId("settings-auth-card")).toBeVisible();
    await expect(page.getByTestId("settings-eworks-card")).toBeVisible();
    await expect(page.getByTestId("settings-status-card")).toBeVisible();
    await expect(page.getByTestId("status-badge-eworks-api-key")).toContainText("Configured");
    await expect(page.getByTestId("status-badge-eworks-license-key")).toContainText("Not configured");
  });

  test("manager gets 403 on /admin/settings", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await page.goto("/admin/settings");
    await expect(page.getByText("You do not have access to this page.")).toBeVisible();
  });

  test("engineer gets 403 on /admin/settings", async ({ page }) => {
    await mockAuthMe(page, "engineer");
    await page.goto("/admin/settings");
    await expect(page.getByText("You do not have access to this page.")).toBeVisible();
  });

  test("no raw secret values appear in DOM", async ({ page }) => {
    await mockAuthMe(page, "admin");
    await mockSettingsApi(page);
    await page.goto("/admin/settings");
    await expect(page.getByText("super-secret-dashboard-pass")).toHaveCount(0);
    await expect(page.getByText("eworks-secret-key")).toHaveCount(0);
    await expect(page.getByText("postgresql://")).toHaveCount(0);
    await expect(page.getByText("session_token")).toHaveCount(0);
    await expect(page.getByText("api_key")).toHaveCount(0);
  });
});
