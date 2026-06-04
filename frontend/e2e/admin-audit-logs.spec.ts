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

const mockAuditLogs = [
  {
    id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    actor_user_id: "11111111-1111-1111-1111-111111111111",
    actor_email: "admin@optimal.example",
    action: "user_updated",
    entity_type: "user",
    entity_id: "22222222-2222-2222-2222-222222222222",
    summary: "user_updated on user 22222222-2222-2222-2222-222222222222",
    ip_address: null,
    created_at: "2024-06-01T12:00:00Z",
  },
];

async function mockAuditLogsApi(page: Page) {
  await page.route("**/api/v1/audit-logs**", async (route) => {
    const url = new URL(route.request().url());
    const method = route.request().method();

    if (method === "GET" && url.pathname.endsWith("/audit-logs")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: mockAuditLogs,
          meta: { total: 1, limit: 25, offset: 0 },
        }),
      });
      return;
    }

    if (method === "GET" && url.pathname.includes("/audit-logs/")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            ...mockAuditLogs[0],
            metadata: { actor_email: "admin@optimal.example" },
            before_snapshot: { role: "manager", password_hash: "***REDACTED***" },
            after_snapshot: { role: "admin" },
          },
        }),
      });
      return;
    }

    await route.continue();
  });
}

test.describe("Admin audit logs page", () => {
  test("admin can open /admin/audit-logs and see mocked table", async ({ page }) => {
    await mockAuthMe(page, "admin");
    await mockAuditLogsApi(page);
    await page.goto("/admin/audit-logs");
    await expect(page.getByTestId("admin-audit-logs-page")).toBeVisible();
    await expect(page.getByTestId("audit-logs-table")).toBeVisible();
    await expect(page.getByText("user_updated")).toBeVisible();
    await expect(page.getByText("password_hash")).toHaveCount(0);
  });

  test("manager gets 403 on /admin/audit-logs", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await page.goto("/admin/audit-logs");
    await expect(page.getByText("You do not have access to this page.")).toBeVisible();
  });

  test("engineer gets 403 on /admin/audit-logs", async ({ page }) => {
    await mockAuthMe(page, "engineer");
    await page.goto("/admin/audit-logs");
    await expect(page.getByText("You do not have access to this page.")).toBeVisible();
  });

  test("admin can open audit detail modal", async ({ page }) => {
    await mockAuthMe(page, "admin");
    await mockAuditLogsApi(page);
    await page.goto("/admin/audit-logs");
    await page.getByTestId("audit-view-aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa").click();
    await expect(page.getByTestId("audit-detail-modal")).toBeVisible();
    await expect(page.getByTestId("audit-before")).toContainText("***REDACTED***");
    await expect(page.getByText("secret")).toHaveCount(0);
  });
});
