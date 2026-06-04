import { test, expect, type Page } from "@playwright/test";

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

const mockReportSummary = {
  kpis: {
    submitted_quotes: 3,
    total_value: 4500,
    average_quote_value: 1500,
    approved_or_ready_count: 3,
    reopened_count: 1,
    with_internal_notes_count: 2,
  },
  by_status: [{ status: "submitted", count: 3, value: 4500 }],
  by_client: [{ client_id: "11111111-1111-1111-1111-111111111111", client_name: "Atkinson McLeod", count: 3, value: 4500 }],
  by_trade: [{ trade_id: "22222222-2222-2222-2222-222222222222", trade_name: "Painter", count: 3, value: 4500 }],
  trend: [{ period: "2026-06-01", count: 3, value: 4500 }],
  recent_quotes: [
    {
      session_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
      quote_ref: "Q-1001",
      client_name: "Atkinson McLeod",
      trade_name: "Painter",
      status: "submitted",
      total: 450,
      submitted_at: "2026-06-01T12:00:00Z",
    },
  ],
};

async function mockReportsApi(page: Page) {
  await page.route("**/api/v1/reports/summary**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ success: true, data: mockReportSummary }),
    });
  });
}

test.describe("Manager reports page", () => {
  test("manager can open /manager/reports and see mocked KPI cards", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockReportsApi(page);
    await page.goto("/manager/reports");
    await expect(page.getByTestId("manager-reports-page")).toBeVisible();
    await expect(page.getByTestId("reports-kpi-cards")).toBeVisible();
    await expect(page.getByTestId("kpi-submitted-quotes")).toContainText("3");
    await expect(page.getByText("session_token")).toHaveCount(0);
    await expect(page.getByText("dashboard_password")).toHaveCount(0);
    await expect(page.getByText("formula denominator")).toHaveCount(0);
  });

  test("admin can open /manager/reports", async ({ page }) => {
    await mockAuthMe(page, "admin");
    await mockReportsApi(page);
    await page.goto("/manager/reports");
    await expect(page.getByTestId("manager-reports-page")).toBeVisible();
    await expect(page.getByTestId("reports-kpi-cards")).toBeVisible();
  });

  test("engineer gets 403 on /manager/reports", async ({ page }) => {
    await mockAuthMe(page, "engineer");
    await page.goto("/manager/reports");
    await expect(page.getByText("You do not have access to this page.")).toBeVisible();
  });

  test("estimator gets 403 on /manager/reports", async ({ page }) => {
    await mockAuthMe(page, "estimator");
    await page.goto("/manager/reports");
    await expect(page.getByText("You do not have access to this page.")).toBeVisible();
  });

  test("recent quote View link points to /manager/review/[sessionId]", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockReportsApi(page);
    await page.goto("/manager/reports");
    const viewLink = page.getByTestId("report-view-aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa");
    await expect(viewLink).toHaveAttribute("href", "/manager/review/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa");
  });
});
