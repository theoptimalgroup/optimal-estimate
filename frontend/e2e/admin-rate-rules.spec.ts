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

const mockRateRules = [
  {
    id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    client_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    trade_id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
    client_name: "Acme Ltd",
    trade_name: "Electrical",
    version: "v1",
    formula_source: "simplified",
    is_active: true,
    hourly_rate: "75.00",
    half_day_rate: "280.00",
    day_rate: "520.00",
    minimum_hours: null,
    minimum_charge: null,
    material_markup_type: "percentage",
    material_markup_value: "20.00",
    vat_rate: "20.00",
    approval_threshold: null,
    minimum_margin_percentage: null,
    rounding_rule: null,
    active_from: "2024-01-01",
    active_to: null,
    created_at: "2024-01-01T00:00:00Z",
    client_fee_pct: "0.0000",
    hourly_overhead_pct: "0.3000",
    daily_overhead_pct: "0.2000",
    daily_overhead_long_job_pct: "0.1500",
    direct_hourly_cost: null,
    direct_daily_cost: null,
    labourer_hourly_cost: "18.75",
    labourer_daily_cost: "150.00",
    material_charge_denominator: "0.2000",
    parking_charge_denominator: "0.2000",
    congestion_charge_denominator: "0.2000",
    mround_increment: "5.00",
    oj_uplift_pct: "10.00",
    nhs_overhead_uplift_pct: "15.00",
    eaf_flat_fee: "1.00",
    internal_notes_template: "Standard notes",
    xlsx_client_name: null,
    xlsx_trade_name: null,
  },
];

async function mockRateRulesApi(page: Page) {
  await page.route("**/api/v1/rate-rules**", async (route) => {
    const url = new URL(route.request().url());
    if (route.request().method() !== "GET" || url.pathname.endsWith("/status")) {
      await route.continue();
      return;
    }
    if (url.pathname.includes("/rate-rules/")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            ...mockRateRules[0],
            usage: {
              quotes_using_version: 0,
              jobs_for_client: 0,
              lookup_priority: "exact_client_trade",
            },
          },
        }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: mockRateRules,
        meta: { limit: 50, offset: 0, total: 1 },
      }),
    });
  });
}

test.describe("admin rate rules page", () => {
  test("admin can open rate rules with mocked API", async ({ page }) => {
    await mockAuthMe(page, "admin");
    await mockRateRulesApi(page);
    await page.goto("/admin/rate-rules");

    await expect(page.getByTestId("admin-rate-rules-page")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Rate Rules" })).toBeVisible();
    await expect(page.getByTestId("rate-rules-table")).toBeVisible();
    await expect(page.getByRole("cell", { name: "Acme Ltd" })).toBeVisible();
    await expect(page.getByRole("cell", { name: "Electrical" })).toBeVisible();
  });

  test("manager gets 403 on admin rate rules", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await page.goto("/admin/rate-rules");

    await expect(page.getByTestId("require-role-forbidden")).toBeVisible();
    await expect(page.getByText("You do not have access to this page.")).toBeVisible();
  });

  test("engineer gets 403 on admin rate rules", async ({ page }) => {
    await mockAuthMe(page, "engineer");
    await page.goto("/admin/rate-rules");

    await expect(page.getByTestId("require-role-forbidden")).toBeVisible();
    await expect(page.getByText("You do not have access to this page.")).toBeVisible();
  });
});
