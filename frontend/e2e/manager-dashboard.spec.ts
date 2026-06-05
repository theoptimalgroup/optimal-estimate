import { test, expect, type Page } from "@playwright/test";

type MockUserRole = "admin" | "manager" | "engineer" | "client";

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

const AWAITING_SUPPLIER_TAG = "Awaiting Supplier Info (Quotes)";
const READY_TO_SEND_TAG = "Quotes Ready to send (Quotes)";

const MOCK_DASHBOARD = {
  categories: {
    new_quotes: {
      count: 1,
      quotes: [
        {
          id: 1,
          eworks_quote_id: 101,
          quote_ref: "Q-NEW",
          customer_name: "New Customer",
          status: "1",
          status_name: "New",
          tags: [],
          quote_date: "2026-06-01",
          expiry_date: "2026-07-01",
          total: 500.0,
          synced_at: "2026-06-01T10:00:00Z",
        },
      ],
    },
    awaiting_supplier: {
      count: 1,
      quotes: [
        {
          id: 2,
          eworks_quote_id: 102,
          quote_ref: "Q-AWAIT",
          customer_name: "Awaiting Customer",
          status: "1",
          status_name: "New",
          tags: ["Awaiting Supplier Info (Quotes)", "URGENT"],
          quote_date: "2026-06-02",
          expiry_date: "2026-07-02",
          total: 750.0,
          synced_at: "2026-06-02T10:00:00Z",
        },
      ],
    },
    ready_to_send: {
      count: 1,
      quotes: [
        {
          id: 3,
          eworks_quote_id: 103,
          quote_ref: "Q-READY",
          customer_name: "Ready Customer",
          status: "1",
          status_name: "New",
          tags: [
            "Quote Ready to Send (Quotes)",
            "To Send With Invoice (QUOTES)",
            "URGENT",
          ],
          quote_date: "2026-06-03",
          expiry_date: "2026-07-03",
          total: 900.0,
          synced_at: "2026-06-03T10:00:00Z",
        },
      ],
    },
  },
  last_synced_at: "2026-06-03T10:00:00Z",
  totals: { all_open_quotes: 3 },
};

const MOCK_QUOTE_SAFE_DETAIL = {
  identity: {
    id: 1,
    eworks_quote_id: 101,
    quote_ref: "Q-NEW",
    status: "1",
    status_name: "New",
    synced_at: "2026-06-01T10:00:00Z",
  },
  customer: {
    customer_id: 5,
    customer_name: "New Customer",
    customer_contact_id: null,
    customer_contact_name: null,
    customer_site_id: null,
    site_name: null,
    site_address: null,
    customer_ref: null,
    po_ref: null,
    wo_ref: null,
  },
  quote_details: {
    quote_type_id: null,
    quote_source_id: null,
    project_id: null,
    quote_date: "2026-06-01",
    expiry_date: "2026-07-01",
    preferred_date: null,
    preferred_time: null,
    description: null,
    notes: null,
    customer_notes: null,
    terms: null,
  },
  financials: {
    subtotal: 500.0,
    vat: 100.0,
    total: 500.0,
    discount_type: null,
    discount_value: null,
    currency: "GBP",
  },
  tags: [],
  items: [],
  custom_fields: [],
  dates: {
    created_on: null,
    updated_on: null,
    converted_date: null,
    accepted_date: null,
  },
  linked_estimate: {
    has_estimate_session: false,
    session_id: null,
    status: null,
    client_accepted_at: null,
  },
};

async function mockDashboardApi(page: Page) {
  await page.route("**/api/v1/manager/dashboard**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ success: true, data: MOCK_DASHBOARD }),
    });
  });

  await page.route("**/api/v1/eworks-sync/quotes/1/safe", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ success: true, data: MOCK_QUOTE_SAFE_DETAIL }),
    });
  });

  await page.route("**/api/v1/eworks-sync/quotes/1/attachments", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ success: true, data: { items: [], total: 0 } }),
    });
  });
}

async function mockFilteredQuotesApi(page: Page) {
  await page.route("**/api/v1/eworks-sync/quotes**", async (route) => {
    const url = new URL(route.request().url());
    const status = url.searchParams.get("status");
    const tag = url.searchParams.get("tag");

    let items = [...MOCK_DASHBOARD.categories.new_quotes.quotes];
    if (tag === AWAITING_SUPPLIER_TAG) {
      items = [...MOCK_DASHBOARD.categories.awaiting_supplier.quotes];
    } else if (tag === READY_TO_SEND_TAG) {
      items = [...MOCK_DASHBOARD.categories.ready_to_send.quotes];
    } else if (status === "1") {
      items = [...MOCK_DASHBOARD.categories.new_quotes.quotes];
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: { items, total: items.length, limit: 50, offset: 0 },
      }),
    });
  });
}

test.describe("Manager dashboard", () => {
  test("shows three quote categories with KPI cards", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockDashboardApi(page);
    await page.goto("/manager/dashboard");

    await expect(page.getByTestId("manager-dashboard-page")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Manager Dashboard" })).toBeVisible();
    await expect(
      page.getByText("Track synced eWorks quotes by operational status.")
    ).toBeVisible();

    await expect(page.getByTestId("kpi-new-quotes")).toBeVisible();
    await expect(page.getByTestId("kpi-awaiting-supplier")).toBeVisible();
    await expect(page.getByTestId("kpi-ready-to-send")).toBeVisible();
    await expect(page.getByTestId("kpi-last-sync")).toBeVisible();

    await expect(page.getByTestId("quote-bucket-board")).toBeVisible();
    await expect(page.getByTestId("category-new-quotes")).toBeVisible();
    await expect(page.getByTestId("category-awaiting-supplier")).toBeVisible();
    await expect(page.getByTestId("category-ready-to-send")).toBeVisible();
  });

  test("each bucket renders clickable quote cards", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockDashboardApi(page);
    await page.goto("/manager/dashboard");

    await expect(page.getByTestId("dashboard-quote-card-1")).toBeVisible();
    await expect(page.getByTestId("dashboard-quote-card-2")).toBeVisible();
    await expect(page.getByTestId("dashboard-quote-card-3")).toBeVisible();

    await expect(page.getByTestId("category-new-quotes-cards")).toContainText("Q-NEW");
    await expect(page.getByTestId("category-awaiting-supplier-cards")).toContainText("Q-AWAIT");
    await expect(page.getByTestId("category-ready-to-send-cards")).toContainText("Q-READY");
  });

  test("quote card click opens safe detail modal", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockDashboardApi(page);
    await page.goto("/manager/dashboard");

    await page.getByTestId("dashboard-quote-card-1").click();
    await expect(page.getByTestId("quote-detail-modal")).toBeVisible();
    await expect(page.getByTestId("quote-summary-section")).toBeVisible();
  });

  test("quote card keyboard activation opens safe detail modal", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockDashboardApi(page);
    await page.goto("/manager/dashboard");

    await page.getByTestId("dashboard-quote-card-1").focus();
    await page.keyboard.press("Enter");
    await expect(page.getByTestId("quote-detail-modal")).toBeVisible();
  });

  test("status 1 quote with no bucket tags appears only in New Quotes", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockDashboardApi(page);
    await page.goto("/manager/dashboard");

    await expect(page.getByTestId("category-new-quotes-cards")).toContainText("Q-NEW");
    await expect(page.getByTestId("category-new-quotes-cards")).not.toContainText("Q-AWAIT");
    await expect(page.getByTestId("category-new-quotes-cards")).not.toContainText("Q-READY");
    await expect(page.getByTestId("category-new-quotes-cards")).not.toContainText(
      AWAITING_SUPPLIER_TAG
    );
    await expect(page.getByTestId("category-new-quotes-cards")).not.toContainText("Ready to Send");
  });

  test("status 1 quote with awaiting supplier tag appears in Awaiting Supplier column", async ({
    page,
  }) => {
    await mockAuthMe(page, "manager");
    await mockDashboardApi(page);
    await page.goto("/manager/dashboard");

    await expect(page.getByTestId("category-awaiting-supplier-cards")).toContainText("Q-AWAIT");
    await expect(page.getByTestId("category-awaiting-supplier-cards")).toContainText(
      AWAITING_SUPPLIER_TAG
    );
    await expect(page.getByTestId("category-new-quotes-cards")).not.toContainText("Q-AWAIT");
  });

  test("status 1 quote with ready-to-send tag appears in Ready to Send column", async ({
    page,
  }) => {
    await mockAuthMe(page, "manager");
    await mockDashboardApi(page);
    await page.goto("/manager/dashboard");

    await expect(page.getByTestId("category-ready-to-send-cards")).toContainText("Q-READY");
    await expect(page.getByTestId("category-ready-to-send-cards")).toContainText("Ready to Send");
    await expect(page.getByTestId("category-new-quotes-cards")).not.toContainText("Q-READY");
  });

  test("status 1 quote appears in New Quotes section", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockDashboardApi(page);
    await page.goto("/manager/dashboard");
    await expect(page.getByTestId("category-new-quotes")).toContainText("Q-NEW");
    await expect(page.getByTestId("category-new-quotes")).toContainText("New Customer");
  });

  test("awaiting supplier tag appears in Awaiting Supplier section", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockDashboardApi(page);
    await page.goto("/manager/dashboard");
    await expect(page.getByTestId("category-awaiting-supplier")).toContainText("Q-AWAIT");
    await expect(page.getByTestId("category-awaiting-supplier")).toContainText(
      AWAITING_SUPPLIER_TAG
    );
  });

  test("ready-to-send tag appears in Ready to Send section", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockDashboardApi(page);
    await page.goto("/manager/dashboard");
    await expect(page.getByTestId("category-ready-to-send")).toContainText("Q-READY");
    await expect(page.getByTestId("category-ready-to-send-cards")).toContainText(
      "Quote Ready to Send (Quotes)"
    );
  });

  test("View all links navigate to filtered quotes page", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockDashboardApi(page);
    await mockFilteredQuotesApi(page);
    await page.goto("/manager/dashboard");

    await page.getByTestId("view-all-new_quotes").click();
    await expect(page).toHaveURL(/\/manager\/quotes\?type=quotes&status=1/);
    await expect(page.getByTestId("quotes-table")).toBeVisible();
    await expect(page.getByRole("cell", { name: "Q-NEW" })).toBeVisible();

    await page.goto("/manager/dashboard");
    await page.getByTestId("view-all-awaiting_supplier").click();
    await page.waitForURL(/\/manager\/quotes/);
    {
      const url = new URL(page.url());
      expect(url.searchParams.get("type")).toBe("quotes");
      expect(url.searchParams.get("tag")).toBe(AWAITING_SUPPLIER_TAG);
    }
    await expect(page.getByRole("cell", { name: "Q-AWAIT" })).toBeVisible();

    await page.goto("/manager/dashboard");
    await page.getByTestId("view-all-ready_to_send").click();
    await page.waitForURL(/\/manager\/quotes/);
    {
      const url = new URL(page.url());
      expect(url.searchParams.get("type")).toBe("quotes");
      expect(url.searchParams.get("tag")).toBe(READY_TO_SEND_TAG);
    }
    await expect(page.getByRole("cell", { name: "Q-READY" })).toBeVisible();
  });

  test("no raw_payload or secrets visible on dashboard", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockDashboardApi(page);
    await page.goto("/manager/dashboard");
    await expect(page.getByText("raw_payload")).toHaveCount(0);
    await expect(page.getByText("api_key")).toHaveCount(0);
    await expect(page.getByText("session_token")).toHaveCount(0);
  });

  test("engineer blocked from manager dashboard", async ({ page }) => {
    await mockAuthMe(page, "engineer");
    await page.goto("/manager/dashboard");
    await expect(page.getByTestId("require-role-forbidden")).toBeVisible();
  });

  test("client blocked from manager dashboard", async ({ page }) => {
    await mockAuthMe(page, "client");
    await page.goto("/manager/dashboard");
    await expect(page.getByTestId("require-role-forbidden")).toBeVisible();
  });

  test("admin can access manager dashboard", async ({ page }) => {
    await mockAuthMe(page, "admin");
    await mockDashboardApi(page);
    await page.goto("/manager/dashboard");
    await expect(page.getByTestId("manager-dashboard-page")).toBeVisible();
  });
});
