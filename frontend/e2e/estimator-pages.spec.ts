import { test, expect, type Page } from "@playwright/test";

type MockUserRole = "estimator" | "manager" | "engineer" | "admin";

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

const mockDashboard = {
  kpis: {
    draft_count: 2,
    submitted_count: 4,
    reopened_count: 1,
    total_submitted_value: 5400,
    average_quote_value: 1350,
  },
  recent_quotes: [
    {
      session_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
      quote_ref: "Q-1001",
      client_name: "Atkinson McLeod",
      trade_name: "Painter",
      status: "in_progress",
      total: 500,
      updated_at: "2026-06-04T10:00:00Z",
      submitted_at: null,
      has_notes: false,
      work_count: 1,
      can_resume: true,
      can_view_review: false,
      is_reopened: false,
    },
  ],
  needs_attention: [
    {
      session_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
      quote_ref: "Q-1002",
      reason: "Reopened by manager",
    },
  ],
};

const mockQuotes = {
  success: true,
  data: [
    {
      session_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
      quote_ref: "Q-1001",
      client_name: "Atkinson McLeod",
      trade_name: "Painter",
      status: "in_progress",
      total: 500,
      updated_at: "2026-06-04T10:00:00Z",
      submitted_at: null,
      has_notes: false,
      work_count: 1,
      can_resume: true,
      can_view_review: false,
      is_reopened: false,
    },
  ],
  meta: { total: 1, limit: 50, offset: 0 },
};

async function mockEstimatorApi(page: Page) {
  await page.route("**/api/v1/estimator/dashboard", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ success: true, data: mockDashboard }),
    });
  });

  await page.route("**/api/v1/estimator/quotes**", async (route) => {
    const url = route.request().url();
    if (url.includes("/resume")) {
      await route.continue();
      return;
    }
    if (url.match(/\/quotes\/[0-9a-f-]+$/)) {
      await route.continue();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockQuotes),
    });
  });

  await page.route("**/api/v1/estimator/approvals**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: [
          {
            ...mockQuotes.data[0],
            status: "submitted",
            submitted_at: "2026-06-01T12:00:00Z",
            can_resume: false,
            can_view_review: true,
          },
        ],
        meta: { total: 1, limit: 50, offset: 0 },
      }),
    });
  });
}

test.describe("Estimator pages", () => {
  test("estimator can open /estimator/dashboard", async ({ page }) => {
    await mockAuthMe(page, "estimator");
    await mockEstimatorApi(page);
    await page.goto("/estimator/dashboard");
    await expect(page.getByTestId("estimator-dashboard-page")).toBeVisible();
    await expect(page.getByTestId("estimator-kpi-cards")).toBeVisible();
    await expect(page.getByTestId("new-estimate-button")).toBeVisible();
    await expect(page.getByText("session_token")).toHaveCount(0);
    await expect(page.getByText("formula")).toHaveCount(0);
    await expect(page.getByText("denominator")).toHaveCount(0);
  });

  test("estimator can open /estimator/quotes", async ({ page }) => {
    await mockAuthMe(page, "estimator");
    await mockEstimatorApi(page);
    await page.goto("/estimator/quotes");
    await expect(page.getByTestId("estimator-quotes-page")).toBeVisible();
    await expect(page.getByTestId("estimator-quotes-table")).toBeVisible();
  });

  test("estimator can open /estimator/approvals", async ({ page }) => {
    await mockAuthMe(page, "estimator");
    await mockEstimatorApi(page);
    await page.goto("/estimator/approvals");
    await expect(page.getByTestId("estimator-approvals-page")).toBeVisible();
    await expect(page.getByTestId("estimator-approvals-table")).toBeVisible();
  });

  test("manager gets 403 on /estimator/dashboard", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await page.goto("/estimator/dashboard");
    await expect(page.getByText("You do not have access to this page.")).toBeVisible();
  });

  test("engineer gets 403 on /estimator/dashboard", async ({ page }) => {
    await mockAuthMe(page, "engineer");
    await page.goto("/estimator/dashboard");
    await expect(page.getByText("You do not have access to this page.")).toBeVisible();
  });

  test("New Estimate button points to /eworks/calculate", async ({ page }) => {
    await mockAuthMe(page, "estimator");
    await mockEstimatorApi(page);
    await page.goto("/estimator/dashboard");
    await expect(page.getByTestId("new-estimate-button").locator("xpath=ancestor::a")).toHaveAttribute(
      "href",
      "/eworks/calculate",
    );
  });
});
