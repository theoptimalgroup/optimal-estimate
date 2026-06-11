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

const MOCK_PROCESSED_DASHBOARD = {
  totals: {
    processed_quotes: 1,
    pipeline_value: 1200,
    strong_value: 0,
    dormant_quotes: 0,
    overdue_followups: 0,
    due_today_followups: 0,
    no_followup_set: 1,
    average_age_days: 5,
    conversion_rate: 50,
    accepted_count: 1,
    rejected_count: 1,
    accepted_value: 800,
    rejected_value: 200,
  },
  categories: {
    pending: {
      count: 1,
      value: 1200,
      average_age_days: 5,
      overdue_followups: 0,
      quotes: [
        {
          id: 10,
          quote_ref: "Q-PROC",
          eworks_quote_id: 501,
          customer_name: "Pipeline Customer",
          site_address: "10 Market St",
          quote_value: 1200,
          processed_at: "2026-06-06T09:00:00Z",
          days_since_processed: 5,
          days_in_current_bucket: 5,
          last_follow_up_at: null,
          next_follow_up_at: null,
          follow_up_status: "no_followup",
          sales_bucket: "pending",
          sales_note: null,
          assigned_sales_name: null,
          assigned_sales_email: null,
          assigned_sales_user_id: null,
          eworks_status: "2",
          eworks_status_name: "Processed",
          tags: [],
          quote_detail_link: "/manager/quotes?quote_id=10",
        },
      ],
    },
    possible: { count: 0, value: 0, average_age_days: 0, overdue_followups: 0, quotes: [] },
    strong: { count: 0, value: 0, average_age_days: 0, overdue_followups: 0, quotes: [] },
    dormant: { count: 0, value: 0, average_age_days: 0, overdue_followups: 0, quotes: [] },
  },
  aging: {
    "0_7_days": { count: 1, value: 1200 },
    "8_14_days": { count: 0, value: 0 },
    "15_30_days": { count: 0, value: 0 },
    "31_60_days": { count: 0, value: 0 },
    "60_plus_days": { count: 0, value: 0 },
  },
  follow_up_reminders: {
    overdue: [],
    due_today: [],
    due_this_week: [],
    no_followup_set: [
      {
        id: 10,
        quote_ref: "Q-PROC",
        eworks_quote_id: 501,
        customer_name: "Pipeline Customer",
        site_address: "10 Market St",
        quote_value: 1200,
        processed_at: "2026-06-06T09:00:00Z",
        days_since_processed: 5,
        days_in_current_bucket: 5,
        last_follow_up_at: null,
        next_follow_up_at: null,
        follow_up_status: "no_followup",
        sales_bucket: "pending",
        sales_note: null,
        assigned_sales_name: null,
        assigned_sales_email: null,
        assigned_sales_user_id: null,
        eworks_status: "2",
        eworks_status_name: "Processed",
        tags: [],
        quote_detail_link: "/manager/quotes?quote_id=10",
      },
    ],
  },
  salesperson_performance: [],
  accepted_rejected_trend: [{ month: "2026-06", accepted_count: 1, rejected_count: 1, accepted_value: 800, rejected_value: 200 }],
  monthly_pipeline_value: [
    {
      month: "2026-06",
      new_processed_value: 1200,
      active_pipeline_value: 1200,
      strong_pipeline_value: 0,
      accepted_value: 800,
      rejected_value: 200,
    },
  ],
};

async function mockProcessedDashboard(page: Page, apiBase: "admin" | "manager") {
  await page.route(`**/api/v1/${apiBase}/processed-dashboard**`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ success: true, data: MOCK_PROCESSED_DASHBOARD }),
    });
  });
}

test.describe("Sales Pipeline processed dashboard", () => {
  test("manager can open /manager/processed-dashboard", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockProcessedDashboard(page, "manager");
    await page.goto("/manager/processed-dashboard");
    await expect(page.getByTestId("processed-dashboard-page")).toBeVisible();
    await expect(page.getByTestId("kpi-processed-quotes")).toBeVisible();
    await expect(page.getByTestId("pipeline-bucket-pending")).toBeVisible();
    await expect(page.getByText("Q-PROC")).toBeVisible();
  });

  test("admin can open /admin/processed-dashboard", async ({ page }) => {
    await mockAuthMe(page, "admin");
    await mockProcessedDashboard(page, "admin");
    await page.goto("/admin/processed-dashboard");
    await expect(page.getByTestId("processed-dashboard-page")).toBeVisible();
    await expect(page.getByTestId("salesperson-performance-section")).toBeVisible();
  });

  test("engineer cannot access manager processed dashboard", async ({ page }) => {
    await mockAuthMe(page, "engineer");
    await page.goto("/manager/processed-dashboard");
    await expect(page.getByTestId("require-role-forbidden")).toBeVisible();
  });
});
