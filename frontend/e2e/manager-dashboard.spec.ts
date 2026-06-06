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
      "Awaiting Supplier",
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
    await expect(page.getByTestId("category-ready-to-send-cards")).toContainText(
      "Quote Ready to Sen",
    );
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
    await expect(page.getByTestId("category-awaiting-supplier")).toContainText("Awaiting Supplier");
  });

  test("ready-to-send tag appears in Ready to Send section", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockDashboardApi(page);
    await page.goto("/manager/dashboard");
    await expect(page.getByTestId("category-ready-to-send")).toContainText("Q-READY");
    await expect(page.getByTestId("category-ready-to-send-cards")).toContainText(
      "Quote Ready to Sen",
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

const MOCK_REVIEW_QUOTE = {
  session_id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
  session_token: "secret-session-token",
  quote_number: "Q22091",
  job_number: "29191",
  client_name: "Unknown Customer",
  trade_name: "Carpenter",
  submitted_at: "2026-06-05T17:46:00Z",
  final_total: 43.2,
  breakdown: {
    works_subtotal: 36,
    additional_charges: 0,
    vat_total: 7.2,
    final_total: 43.2,
  },
  works: [
    {
      work_index: 0,
      scope: "- Drill and inject damp-proof course.",
      product_name: "Decoration - 2 Bedroom Flat",
      product_code: "D--0001",
      display_label: "Decoration - 2 Bedroom Flat · D--0001",
      labour_subtotal: 30,
      materials_subtotal: 6,
      internal_notes: null,
      attachments: [],
    },
  ],
  acceptance: {
    accepted: true,
    accepted_at: "2026-06-02T14:30:00Z",
    name: "Jane Client",
  },
};

async function mockManagerReviewQuoteApi(page: Page) {
  await page.route("**/api/v1/dashboard/quotes", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: { quotes: [MOCK_REVIEW_QUOTE] },
      }),
    });
  });
}

test.describe("Manager quote review detail from dashboard context", () => {
  test("hides client link and acceptance on review detail", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockManagerReviewQuoteApi(page);
    await page.goto("/manager/review/cccccccc-cccc-cccc-cccc-cccccccccccc");

    await expect(page.getByTestId("client-link-panel")).toHaveCount(0);
    await expect(page.getByTestId("quote-acceptance-panel")).toHaveCount(0);
  });

  test("shows quote summary breakdown on review detail", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockManagerReviewQuoteApi(page);
    await page.goto("/manager/review/cccccccc-cccc-cccc-cccc-cccccccccccc");

    await expect(page.getByTestId("quote-summary-card").getByRole("heading", { level: 2 })).toHaveText(
      "Submission Summary",
    );
    await expect(page.getByTestId("quote-summary-breakdown")).toBeVisible();
    await expect(page.getByTestId("quote-summary-works-subtotal")).toHaveText("£36.00");
    await expect(page.getByTestId("quote-summary-vat")).toHaveText("£7.20");
    await expect(page.getByTestId("quote-summary-final-total")).toHaveText("£43.20");
    await expect(page.getByTestId("work-section-label-0")).toHaveText(
      "Decoration - 2 Bedroom Flat · D--0001",
    );
    await expect(page.getByTestId("work-section-subtotal-0")).toContainText("£36.00");
    await expect(page.getByTestId("work-section-checkbox-0")).toBeVisible();
    await expect(page.getByTestId("work-section-toggle-0")).toBeVisible();
    await expect(page.getByText("secret-session-token")).toHaveCount(0);
    await expect(page.getByText("profit")).toHaveCount(0);
  });
});

const MOCK_GROUP_DETAIL = {
  group_key: "quote_ref:Q22100",
  quote_ref: "Q22100",
  eworks_quote_id: 29204,
  client_name: "ACME Ltd",
  trade_name: "Carpenter",
  submission_count: 1,
  latest_submitted_at: "2026-06-05T16:04:00Z",
  latest_total: "174.24",
  highest_total: "174.24",
  lowest_total: "174.24",
  accepted: false,
  client_accepted_at: null,
  reopened_count: 0,
  latest_session_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
  review_status: "ready_for_review",
  assignment_summary: {
    total_assignments: 1,
    estimator_assignments: 0,
    engineer_assignments: 1,
    pending_assignments: 0,
    in_progress_assignments: 0,
    submitted_assignments: 1,
    cancelled_assignments: 0,
  },
  assignments: [],
  sessions: [],
  assignment_submissions: [
    {
      assignment_id: 2,
      assignment_type: "engineer",
      assignee_kind: "registered",
      assignee_name: "Engineer User",
      assignment_status: "submitted",
      submitted_at: "2026-06-05T16:04:00Z",
      linked_session_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
      submitted_by_name: "Engineer User",
      final_total: "174.24",
      is_latest: true,
      can_view_details: true,
      can_reopen: true,
    },
  ],
};

async function mockQuoteGroupDetailApi(page: Page) {
  await page.route("**/api/v1/dashboard/quote-groups/detail**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ success: true, data: { group: MOCK_GROUP_DETAIL } }),
    });
  });
}

test.describe("Manager dashboard quote group review", () => {
  test("assignment submissions table visible on group review page", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockQuoteGroupDetailApi(page);
    await page.goto("/manager/review/group?quote_ref=Q22100");
    await expect(page.getByTestId("quote-group-assignment-submissions")).toBeVisible();
    await expect(page.getByTestId("quote-group-assignment-submissions-table")).toBeVisible();
    await expect(page.getByTestId("quote-group-assignments")).toHaveCount(0);
    await expect(page.getByTestId("quote-group-submissions")).toHaveCount(0);
    await expect(page.getByTestId("assignment-submission-row-2")).toContainText("Engineer User");
    await expect(page.getByTestId("submission-latest-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")).toBeVisible();
    await expect(page.getByText("session_token")).toHaveCount(0);
  });
});
