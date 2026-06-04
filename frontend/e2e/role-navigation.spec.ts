import { test, expect, type Page } from "@playwright/test";

type MockUserRole = "admin" | "estimator" | "manager" | "engineer";

const MOCK_DASHBOARD_PASSWORD = "optimal-dev";

function mockUser(role: MockUserRole | null) {
  if (!role) {
    return null;
  }
  return {
    id: `dev-${role}`,
    email: `${role}@example.com`,
    name: `Dev ${role.charAt(0).toUpperCase()}${role.slice(1)}`,
    role,
    is_active: true,
    auth_provider: "dev",
  };
}

async function mockAuthMe(page: Page, role: MockUserRole | null) {
  await page.route("**/api/v1/auth/me", async (route) => {
    if (!role) {
      await route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Not authenticated" }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ success: true, data: mockUser(role) }),
    });
  });
}

async function mockDashboardQuotes(page: Page, options?: { requirePassword?: boolean }) {
  const requirePassword = options?.requirePassword ?? false;
  await page.route("**/api/v1/dashboard/quotes", async (route) => {
    const password = route.request().headers()["x-dashboard-password"];
    if (requirePassword && password !== MOCK_DASHBOARD_PASSWORD) {
      await route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Invalid dashboard password" }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: {
          quotes: [
            {
              session_id: "11111111-1111-1111-1111-111111111111",
              session_token: "mock-session-token",
              quote_number: "Q-1001",
              job_number: "J-2001",
              client_name: "Acme Ltd",
              trade_name: "Electrical",
              submitted_at: "2026-06-01T10:00:00Z",
              final_total: "1234.56",
              internal_notes: null,
              works: [
                {
                  work_index: 0,
                  scope: "Replace panel",
                  labour_subtotal: "500",
                  materials_subtotal: "734.56",
                  internal_notes: "Note A",
                  attachments: [],
                  details: null,
                },
              ],
            },
          ],
        },
      }),
    });
  });
}

test.describe("role-based navigation and access", () => {
  test("admin sees admin nav and can access admin dashboard", async ({ page }) => {
    await mockAuthMe(page, "admin");
    await page.goto("/admin/dashboard");
    await expect(page.getByTestId("app-shell")).toBeVisible();
    await expect(page.getByTestId("app-shell-nav")).toBeVisible();
    await expect(page.getByTestId("nav-item-dashboard")).toBeVisible();
    await expect(page.getByTestId("nav-item-users-roles")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Admin Dashboard" })).toBeVisible();
  });

  test("estimator is blocked from admin pages", async ({ page }) => {
    await mockAuthMe(page, "estimator");
    await page.goto("/admin/dashboard");
    await expect(page.getByTestId("require-role-forbidden")).toBeVisible();
    await expect(page.getByText("You do not have access to this page.")).toBeVisible();
  });

  test("estimator sees estimator nav on estimator dashboard", async ({ page }) => {
    await mockAuthMe(page, "estimator");
    await page.goto("/estimator/dashboard");
    await expect(page.getByTestId("app-shell-nav")).toBeVisible();
    await expect(page.getByTestId("nav-item-quotes")).toBeVisible();
    await expect(page.getByTestId("nav-item-new-estimate")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Estimator Dashboard" })).toBeVisible();
  });

  test("manager can open manager review and load submitted quotes", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockDashboardQuotes(page);
    await page.goto("/manager/review");
    await expect(page.getByTestId("app-shell")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Approvals & Quotes" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Q-1001" })).toBeVisible();
    await expect(page.getByRole("cell", { name: "Acme Ltd" })).toBeVisible();
  });

  test("engineer gets 403 on manager review", async ({ page }) => {
    await mockAuthMe(page, "engineer");
    await page.goto("/manager/review");
    await expect(page.getByTestId("require-role-forbidden")).toBeVisible();
    await expect(page.getByText("You do not have access to this page.")).toBeVisible();
  });

  test("engineer can access engineer jobs", async ({ page }) => {
    await mockAuthMe(page, "engineer");
    await page.goto("/engineer/jobs");
    await expect(page.getByTestId("nav-item-my-jobs")).toBeVisible();
    await expect(page.getByRole("heading", { name: "My Jobs" })).toBeVisible();
    await expect(page.getByTestId("engineer-open-session-card")).toBeVisible();
  });

  test("unauthenticated user sees not authenticated on protected page", async ({ page }) => {
    await mockAuthMe(page, null);
    await page.goto("/manager/dashboard");
    await expect(page.getByTestId("require-role-unauthenticated")).toBeVisible();
    await expect(page.getByText("Not authenticated")).toBeVisible();
  });

  test("eworks calculate is not wrapped with RequireRole", async ({ page }) => {
    await mockAuthMe(page, null);
    await page.goto("/eworks/calculate");
    await expect(page.getByTestId("require-role-unauthenticated")).toHaveCount(0);
    await expect(page.getByTestId("require-role-forbidden")).toHaveCount(0);
    await expect(page.getByTestId("app-shell")).toHaveCount(0);
  });

  test("legacy eworks dashboard password unlock still works", async ({ page }) => {
    await mockAuthMe(page, null);
    await mockDashboardQuotes(page, { requirePassword: true });
    await page.goto("/eworks/dashboard");
    await expect(page.getByRole("heading", { name: "Submitted Quotes" })).toBeVisible();
    await page.getByLabel("Dashboard password").fill(MOCK_DASHBOARD_PASSWORD);
    await page.getByRole("button", { name: "Unlock dashboard" }).click();
    await expect(page.getByRole("heading", { name: "Submitted Quotes", exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "Q-1001" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Lock dashboard" })).toBeVisible();
  });
});
