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

const MOCK_QUOTES = {
  items: [
    {
      id: 1,
      eworks_quote_id: 101,
      quote_ref: "Q-101",
      customer_id: 5,
      customer_name: "ACME Ltd",
      status: "2",
      status_name: "Pending",
      quote_date: "2026-01-15",
      expiry_date: "2026-04-15",
      description: "Full rewire",
      customer_ref: null,
      po_ref: null,
      wo_ref: null,
      subtotal: 1200.0,
      vat: 240.0,
      total: 1440.0,
      tags: ["urgent", "electrical", "rewire"],
      synced_at: "2026-06-01T10:00:00Z",
      display_customer_name: "ACME Ltd",
      display_status: "Pending",
      display_tags: ["urgent", "electrical", "rewire"],
      display_total: 1440.0,
      display_quote_date: "2026-01-15",
    },
    {
      id: 3,
      eworks_quote_id: 303,
      quote_ref: "Q-303",
      customer_id: null,
      customer_name: "Fallback Customer",
      status: "1",
      status_name: "New Quote",
      quote_date: "2026-02-10",
      expiry_date: null,
      description: null,
      customer_ref: null,
      po_ref: null,
      wo_ref: null,
      subtotal: null,
      vat: null,
      total: 999.99,
      tags: ["alpha", "beta", "gamma"],
      synced_at: "2026-06-02T09:00:00Z",
      display_customer_name: "Fallback Customer",
      display_status: "New Quote",
      display_tags: ["alpha", "beta", "gamma"],
      display_total: 999.99,
      display_quote_date: "2026-02-10",
    },
  ],
  total: 2,
  limit: 50,
  offset: 0,
};

const MOCK_JOBS = {
  items: [
    {
      id: 2,
      eworks_job_id: 201,
      job_ref: "J-201",
      eworks_quote_id: 101,
      customer_id: 5,
      customer_name: "ACME Ltd",
      status: "1",
      status_name: "Open",
      job_date: "2026-02-01",
      description: "Install panel",
      address: null,
      subtotal: 900.0,
      vat: 180.0,
      total: 1080.0,
      synced_at: "2026-06-01T10:05:00Z",
    },
  ],
  total: 1,
  limit: 50,
  offset: 0,
};

const MOCK_QUOTE_SAFE_DETAIL = {
  identity: {
    id: 1,
    eworks_quote_id: 101,
    quote_ref: "Q-101",
    status: "2",
    status_name: "Pending",
    synced_at: "2026-06-01T10:00:00Z",
  },
  customer: {
    customer_id: 5,
    customer_name: "ACME Ltd",
    customer_contact_id: null,
    customer_contact_name: "Jane Smith",
    customer_site_id: null,
    site_name: "Main Office",
    site_address: "10 High Street, London",
    customer_ref: "CUST-1",
    po_ref: "PO-55",
    wo_ref: null,
  },
  quote_details: {
    quote_type_id: 1,
    quote_source_id: 2,
    project_id: null,
    quote_date: "2026-01-15",
    expiry_date: "2026-04-15",
    preferred_date: "2026-01-20",
    preferred_time: "09:00",
    description:
      '<span style="text-decoration: underline;"><strong>Access</strong></span>&nbsp;<br /><ol><li>Check fuse board</li><li>Replace panel</li></ol>',
    notes: "Internal note",
    customer_notes: "Call before visit",
    terms:
      '<span style="font-family: Arial; color: red;">Payment due in 30 days</span><script>window.__eworksXssTest=true</script>',
  },
  financials: {
    subtotal: 1200.0,
    vat: 240.0,
    total: 1440.0,
    discount_type: null,
    discount_value: null,
    currency: "GBP",
  },
  tags: ["urgent", "electrical"],
  items: [
    {
      name: "Panel install",
      description: "Main board replacement",
      quantity: "1",
      unit_price: "1200.00",
      total: "1200.00",
    },
  ],
  custom_fields: [
    { label: "Access Code", field_key: "access_code", value: "1234" },
  ],
  dates: {
    created_on: "2026-01-10",
    updated_on: "2026-01-12",
    converted_date: null,
    accepted_date: null,
  },
  linked_estimate: {
    has_estimate_session: true,
    session_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    status: "submitted",
    client_accepted_at: null,
  },
};

const MOCK_JOB_SAFE_DETAIL = {
  identity: {
    id: 2,
    eworks_job_id: 201,
    job_ref: "J-201",
    status: "1",
    status_name: "Open",
    synced_at: "2026-06-01T10:05:00Z",
  },
  customer: {
    customer_id: 5,
    customer_name: "ACME Ltd",
    customer_contact_id: null,
    customer_contact_name: null,
    customer_site_id: null,
    site_name: null,
    site_address: "10 High Street, London",
  },
  related_quote: {
    eworks_quote_id: 101,
    quote_ref: "Q-101",
  },
  job_details: {
    job_date: "2026-02-01",
    description: "Install panel",
    notes: "Rear gate access",
  },
  financials: {
    subtotal: 900.0,
    vat: 180.0,
    total: 1080.0,
    discount_type: null,
    discount_value: null,
    currency: "GBP",
  },
  tags: ["maintenance"],
  items: [],
  custom_fields: [],
  dates: {
    created_on: "2026-02-01",
    updated_on: null,
    completed_date: null,
  },
  linked_estimate: {
    has_estimate_session: false,
    session_id: null,
    status: null,
    client_accepted_at: null,
  },
};

async function mockSyncedDataApi(page: Page) {
  await page.route("**/api/v1/eworks-sync/quotes**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ success: true, data: MOCK_QUOTES }),
    });
  });

  await page.route("**/api/v1/eworks-sync/jobs**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ success: true, data: MOCK_JOBS }),
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
      body: JSON.stringify({
        success: true,
        data: {
          items: [
            {
              id: 10,
              filename: "scope.pdf",
              mime_type: "application/pdf",
              size_bytes: 2048,
              description: "Project scope",
              uploaded_by: "Alice",
              created_on: "2026-01-01",
              synced_at: "2026-06-01T10:00:00Z",
            },
          ],
          total: 1,
        },
      }),
    });
  });

  await page.route("**/api/v1/eworks-sync/jobs/2/safe", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ success: true, data: MOCK_JOB_SAFE_DETAIL }),
    });
  });

  await page.route("**/api/v1/eworks-sync/jobs/2/attachments", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: { items: [], total: 0 },
      }),
    });
  });
}

test.describe("Manager quotes page", () => {
  test("manager can open /manager/quotes with Quotes tab default", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockSyncedDataApi(page);
    await page.goto("/manager/quotes");
    await expect(page.getByTestId("manager-quotes-page")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Quotes", exact: true })).toBeVisible();
    await expect(page.getByText("Search quotes and jobs synced from eWorks.")).toBeVisible();
    await expect(page.getByTestId("tab-quotes")).toHaveClass(/border-blue-600/);
    await expect(page.getByTestId("quotes-table")).toBeVisible();
    await expect(page.getByRole("cell", { name: "Q-101" })).toBeVisible();
  });

  test("quotes search renders mocked quote records", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockSyncedDataApi(page);
    await page.goto("/manager/quotes");
    await expect(page.getByTestId("quotes-search")).toBeVisible();
    await expect(page.getByRole("cell", { name: "ACME Ltd" })).toBeVisible();
    await expect(page.getByRole("cell", { name: "Pending" })).toBeVisible();
    await expect(page.getByRole("cell", { name: "£1440.00" })).toBeVisible();
    await expect(page.getByTestId("quote-row-1").getByText("+1 more")).toBeVisible();
    await expect(page.getByText("raw_payload")).toHaveCount(0);
    await expect(page.getByText("session_token")).toHaveCount(0);
  });

  test("quotes table columns align with headers", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockSyncedDataApi(page);
    await page.goto("/manager/quotes");

    const row = page.getByTestId("quote-row-3");
    await expect(row).toBeVisible();

    const cells = row.locator("td");
    await expect(cells).toHaveCount(9);
    await expect(cells.nth(0)).toHaveText("Q-303");
    await expect(cells.nth(1)).toHaveText("303");
    await expect(cells.nth(2)).toHaveText("Fallback Customer");
    await expect(cells.nth(3)).toHaveText("New Quote");
    await expect(cells.nth(4)).toContainText("alpha");
    await expect(cells.nth(4)).toContainText("+1 more");
    await expect(cells.nth(5)).toHaveText("2026-02-10");
    await expect(cells.nth(6)).toHaveText("£999.99");
    await expect(cells.nth(7)).toContainText("2026");
    await expect(cells.nth(8)).toContainText("View Details");
  });

  test("switch to Jobs tab renders mocked job records", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockSyncedDataApi(page);
    await page.goto("/manager/quotes");
    await page.getByTestId("tab-jobs").click();
    await expect(page.getByTestId("jobs-table")).toBeVisible();
    await expect(page.getByRole("cell", { name: "J-201" })).toBeVisible();
    await expect(page.getByRole("cell", { name: "101", exact: true })).toBeVisible();
  });

  test("View Details opens grouped quote detail modal without secrets", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockSyncedDataApi(page);
    await page.goto("/manager/quotes");
    await page.getByTestId("quote-view-1").click();
    await expect(page.getByTestId("quote-detail-modal")).toBeVisible();
    await expect(page.getByTestId("quote-summary-section")).toBeVisible();
    await expect(page.getByTestId("customer-site-section")).toBeVisible();
    await expect(page.getByTestId("financial-summary-section")).toBeVisible();
    await expect(page.getByTestId("custom-fields-section")).toBeVisible();
    await expect(page.getByTestId("quote-items-table")).toBeVisible();
    await expect(page.getByTestId("attachments-section")).toBeVisible();
    await expect(page.getByTestId("attachments-table")).toBeVisible();
    await expect(page.getByRole("cell", { name: "scope.pdf" })).toBeVisible();
    await expect(page.getByRole("cell", { name: "Alice" })).toBeVisible();
    await expect(page.getByText("Call before visit")).toBeVisible();
    await expect(page.getByTestId("quote-description-rich-text")).toContainText("Access");
    await expect(page.getByTestId("quote-description-rich-text")).toContainText("Check fuse board");
    await expect(page.getByTestId("quote-description-rich-text")).toContainText("Replace panel");
    await expect(page.getByTestId("quote-terms-rich-text")).toContainText("Payment due in 30 days");
    await expect(page.getByTestId("description-notes-section")).not.toContainText("<span");
    await expect(page.getByTestId("description-notes-section")).not.toContainText("<ol>");
    await expect(page.getByTestId("description-notes-section")).not.toContainText("<strong>");
    await expect(
      page.evaluate(() => (window as Window & { __eworksXssTest?: boolean }).__eworksXssTest)
    ).resolves.toBeUndefined();
    await expect(page.getByTestId("tags-section").getByText("urgent")).toBeVisible();
    await expect(page.getByTestId("view-estimate-link")).toHaveAttribute(
      "href",
      "/manager/review/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    );
    await expect(page.getByText("raw_payload")).toHaveCount(0);
    await expect(page.getByText("session_token")).toHaveCount(0);
    await expect(page.getByText("api_key")).toHaveCount(0);
  });

  test("no Sync button visible on manager quotes page", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockSyncedDataApi(page);
    await page.goto("/manager/quotes");
    await expect(page.getByRole("button", { name: /Sync Quotes/i })).toHaveCount(0);
    await expect(page.getByRole("button", { name: /Sync Jobs/i })).toHaveCount(0);
    await expect(page.getByRole("button", { name: /Sync All/i })).toHaveCount(0);
  });

  test("engineer gets 403 on /manager/quotes", async ({ page }) => {
    await mockAuthMe(page, "engineer");
    await page.goto("/manager/quotes");
    await expect(page.getByTestId("require-role-forbidden")).toBeVisible();
    await expect(page.getByText("You do not have access to this page.")).toBeVisible();
  });

  test("admin can also access /manager/quotes", async ({ page }) => {
    await mockAuthMe(page, "admin");
    await mockSyncedDataApi(page);
    await page.goto("/manager/quotes");
    await expect(page.getByTestId("manager-quotes-page")).toBeVisible();
    await expect(page.getByTestId("quotes-table")).toBeVisible();
  });

  test("manager sidebar shows Quotes nav item", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockSyncedDataApi(page);
    await page.goto("/manager/quotes");
    await expect(page.getByTestId("nav-item-quotes")).toBeVisible();
  });

  test("job detail modal shows attachments empty state", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockSyncedDataApi(page);
    await page.goto("/manager/quotes");
    await page.getByTestId("tab-jobs").click();
    await page.getByTestId("job-view-2").click();
    await expect(page.getByTestId("job-detail-modal")).toBeVisible();
    await expect(page.getByTestId("attachments-section")).toBeVisible();
    await expect(page.getByTestId("attachments-empty")).toHaveText(
      "No attachments synced for this job."
    );
    await expect(page.getByText("raw_payload")).toHaveCount(0);
    await expect(page.getByText("api_key")).toHaveCount(0);
  });
});
