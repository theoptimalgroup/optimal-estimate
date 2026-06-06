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
    await expect(page.getByTestId("filter-bar")).toBeVisible();
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
    await expect(cells.nth(8)).toContainText("View");
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

const MOCK_REVIEW_QUOTE = {
  session_id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
  session_token: "secret-session-token",
  quote_number: "Q22091",
  job_number: "29191",
  client_name: "Unknown Customer",
  trade_name: "Carpenter",
  submitted_at: "2026-06-05T17:46:00Z",
  final_total: 1.44,
  internal_notes: "secret internal note",
  breakdown: {
    works_subtotal: 1.2,
    additional_charges: 0,
    vat_total: 0.24,
    final_total: 1.44,
  },
  works: [
    {
      work_index: 0,
      scope: "- Drill and inject damp-proof course.",
      product_name: "Decoration - 2 Bedroom Flat",
      product_code: "D--0001",
      display_label: "Decoration - 2 Bedroom Flat · D--0001",
      labour_subtotal: 1.0,
      materials_subtotal: 0.2,
      internal_notes: null,
      attachments: [],
    },
  ],
  acceptance: {
    accepted: false,
    accepted_at: null,
    name: null,
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

test.describe("Manager quote review detail", () => {
  test("summary card uses neutral title and trade as secondary metadata", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockManagerReviewQuoteApi(page);
    await page.goto("/manager/review/cccccccc-cccc-cccc-cccc-cccccccccccc");

    const summaryCard = page.getByTestId("quote-summary-card");
    await expect(summaryCard).toBeVisible();
    await expect(summaryCard.getByRole("heading", { level: 2 })).toHaveText("Submission Summary");
    await expect(page.getByTestId("quote-summary-trade")).toHaveText("Trade: Carpenter");
    await expect(summaryCard.getByRole("heading", { level: 2 })).not.toHaveText("Carpenter");
    await expect(page.getByText("Decoration - 2 Bedroom Flat · D--0001")).toHaveCount(1);
    await expect(page.getByTestId("work-section-label-0")).toHaveText(
      "Decoration - 2 Bedroom Flat · D--0001",
    );
    await expect(page.getByText("secret-session-token")).toHaveCount(0);
    await expect(page.getByText("raw_payload")).toHaveCount(0);
  });

  test("work row supports checkbox selection without toggling collapse", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockManagerReviewQuoteApi(page);
    await page.goto("/manager/review/cccccccc-cccc-cccc-cccc-cccccccccccc");

    await expect(page.getByTestId("work-section-details-0")).toBeVisible();
    await page.getByTestId("work-section-checkbox-0").click();
    await expect(page.getByTestId("work-section-details-0")).toBeVisible();
    await expect(page.getByText("1 work selected")).toBeVisible();
  });

  test("chevron toggles work details while checkbox stays independent", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockManagerReviewQuoteApi(page);
    await page.goto("/manager/review/cccccccc-cccc-cccc-cccc-cccccccccccc");

    await expect(page.getByTestId("work-section-details-0")).toBeVisible();
    await page.getByTestId("work-section-toggle-0").click();
    await expect(page.getByTestId("work-section-details-0")).toHaveCount(0);
    await expect(page.getByTestId("work-section-scope-preview-0")).toBeVisible();
    await page.getByTestId("work-section-toggle-0").click();
    await expect(page.getByTestId("work-section-details-0")).toBeVisible();
  });

  test("hides client quote link and client acceptance sections", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockManagerReviewQuoteApi(page);
    await page.goto("/manager/review/cccccccc-cccc-cccc-cccc-cccccccccccc");

    await expect(page.getByTestId("client-link-panel")).toHaveCount(0);
    await expect(page.getByTestId("quote-acceptance-panel")).toHaveCount(0);
    await expect(page.getByTestId("quote-accepted-badge")).toHaveCount(0);
  });

  test("shows quote summary breakdown with correct totals", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockManagerReviewQuoteApi(page);
    await page.goto("/manager/review/cccccccc-cccc-cccc-cccc-cccccccccccc");

    await expect(page.getByTestId("quote-summary-breakdown")).toBeVisible();
    await expect(page.getByTestId("quote-summary-works-subtotal")).toHaveText("£1.20");
    await expect(page.getByTestId("quote-summary-additional-charges")).toHaveText("£0.00");
    await expect(page.getByTestId("quote-summary-vat")).toHaveText("£0.24");
    await expect(page.getByTestId("quote-summary-final-total")).toHaveText("£1.44");
    await expect(page.getByText("Work subtotal")).toBeVisible();
    await expect(page.getByText("£1.20").first()).toBeVisible();
  });

  test("VAT explains difference between work subtotal and final total", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await page.route("**/api/v1/dashboard/quotes", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            quotes: [
              {
                ...MOCK_REVIEW_QUOTE,
                final_total: 43.2,
                breakdown: {
                  works_subtotal: 36,
                  additional_charges: 0,
                  vat_total: 7.2,
                  final_total: 43.2,
                },
                works: [
                  {
                    ...MOCK_REVIEW_QUOTE.works[0],
                    labour_subtotal: 30,
                    materials_subtotal: 6,
                  },
                ],
              },
            ],
          },
        }),
      });
    });

    await page.goto("/manager/review/cccccccc-cccc-cccc-cccc-cccccccccccc");
    await expect(page.getByTestId("quote-summary-works-subtotal")).toHaveText("£36.00");
    await expect(page.getByTestId("quote-summary-vat")).toHaveText("£7.20");
    await expect(page.getByTestId("quote-summary-final-total")).toHaveText("£43.20");
  });

  test("does not expose internal pricing fields", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockManagerReviewQuoteApi(page);
    await page.goto("/manager/review/cccccccc-cccc-cccc-cccc-cccccccccccc");

    for (const label of [
      "profit",
      "margin",
      "rate rule",
      "denominator",
      "commission",
      "raw_payload",
      "session_token",
      "formula_source",
    ]) {
      await expect(page.getByText(label, { exact: false })).toHaveCount(0);
    }
  });

  test("multiple works keep neutral summary title and show each work once", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await page.route("**/api/v1/dashboard/quotes", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            quotes: [
              {
                ...MOCK_REVIEW_QUOTE,
                works: [
                  MOCK_REVIEW_QUOTE.works[0],
                  {
                    work_index: 1,
                    product_name: "Kitchen Refit",
                    product_code: "K-001",
                    display_label: "Kitchen Refit · K-001",
                    labour_subtotal: 2.0,
                    materials_subtotal: 0.5,
                    attachments: [],
                  },
                ],
              },
            ],
          },
        }),
      });
    });

    await page.goto("/manager/review/cccccccc-cccc-cccc-cccc-cccccccccccc");
    await expect(page.getByTestId("quote-summary-card").getByRole("heading", { level: 2 })).toHaveText(
      "Submission Summary",
    );
    await expect(page.getByTestId("quote-summary-trade")).toHaveText("Trade: Carpenter");
    await expect(page.getByTestId("work-section-label-0")).toHaveText(
      "Decoration - 2 Bedroom Flat · D--0001",
    );
    await expect(page.getByTestId("work-section-label-1")).toHaveText("Kitchen Refit · K-001");
    await expect(page.getByTestId("work-section-details-0")).toHaveCount(0);
    await expect(page.getByTestId("work-section-details-1")).toHaveCount(0);
  });
});

const MOCK_GROUP_DETAIL = {
  group_key: "quote_ref:Q22100",
  quote_ref: "Q22100",
  eworks_quote_id: 29204,
  client_name: "ACME Ltd",
  trade_name: "Carpenter",
  submission_count: 2,
  latest_submitted_at: "2026-06-05T16:04:00Z",
  latest_total: "174.24",
  highest_total: "174.24",
  lowest_total: "0",
  accepted: false,
  client_accepted_at: null,
  reopened_count: 0,
  latest_session_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
  review_status: "ready_for_review",
  assignment_summary: {
    total_assignments: 2,
    estimator_assignments: 1,
    engineer_assignments: 1,
    pending_assignments: 1,
    in_progress_assignments: 0,
    submitted_assignments: 1,
    cancelled_assignments: 0,
  },
  assignments: [],
  sessions: [],
  assignment_submissions: [
    {
      assignment_id: null,
      assignment_type: "unknown",
      assignee_kind: "unknown",
      assignee_name: "Unknown",
      assignment_status: "submitted",
      submitted_at: "2026-06-05T16:04:00Z",
      linked_session_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
      submitted_by_name: "Unknown submitter",
      final_total: "174.24",
      is_latest: true,
      can_view_details: true,
      can_reopen: true,
    },
    {
      assignment_id: 2,
      assignment_type: "engineer",
      assignee_kind: "registered",
      assignee_name: "Engineer User",
      assignment_status: "submitted",
      submitted_at: "2026-06-05T15:48:00Z",
      linked_session_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
      submitted_by_name: "Engineer User",
      final_total: "0",
      is_latest: false,
      can_view_details: true,
      can_reopen: true,
    },
    {
      assignment_id: 1,
      assignment_type: "estimator",
      assignee_kind: "registered",
      assignee_name: "Estimator User",
      assignment_status: "assigned",
      assigned_at: "2026-06-05T10:00:00Z",
      final_total: null,
      can_view_details: false,
      can_reopen: false,
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

test.describe("Manager quote group review", () => {
  test("assignment submissions section visible without separate cards", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockQuoteGroupDetailApi(page);
    await page.goto("/manager/review/group?quote_ref=Q22100");
    await expect(page.getByTestId("quote-group-assignment-submissions")).toBeVisible();
    await expect(page.getByTestId("quote-group-assignment-submissions-table")).toBeVisible();
    await expect(page.getByTestId("quote-group-assignments")).toHaveCount(0);
    await expect(page.getByTestId("quote-group-submissions")).toHaveCount(0);
  });

  test("submitted row shows assignee submitted at and final total", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockQuoteGroupDetailApi(page);
    await page.goto("/manager/review/group?quote_ref=Q22100");
    const engineerRow = page.getByTestId("assignment-submission-row-2");
    await expect(engineerRow).toContainText("Engineer User");
    await expect(engineerRow).toContainText("2026");
    await expect(engineerRow).toContainText("£0.00");
  });

  test("latest badge on latest submission and pending row has no final total", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockQuoteGroupDetailApi(page);
    await page.goto("/manager/review/group?quote_ref=Q22100");
    await expect(page.getByTestId("submission-latest-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")).toBeVisible();
    await expect(page.getByTestId("assignment-submission-row-1")).toContainText("—");
  });

  test("view details and reopen actions available without tokens", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockQuoteGroupDetailApi(page);
    await page.route("**/api/v1/dashboard/quotes/*/reopen", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            session_id: "dddddddd-dddd-dddd-dddd-dddddddddddd",
            session_token: "secret-reopen-token",
          },
        }),
      });
    });
    await page.goto("/manager/review/group?quote_ref=Q22100");
    await expect(page.getByTestId("view-session-detail-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")).toHaveAttribute(
      "href",
      "/manager/review/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    );
    await page.getByTestId("reopen-session-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb").click();
    await expect(page).toHaveURL(/\/eworks\/calculate\?session_id=dddddddd-dddd-dddd-dddd-dddddddddddd/);
    await expect(page.getByText("secret-reopen-token")).toHaveCount(0);
    await expect(page.getByText("session_token")).toHaveCount(0);
  });
});

test.describe("Manager quote group comparison and job assignment", () => {
  const COMPARISON_SUMMARY_HIGH = {
    final_total: "174.24",
    works_subtotal: "145.20",
    labour_subtotal: "120",
    materials_subtotal: "25.20",
    additional_charges_total: "0",
    vat_total: "29.04",
    vat_rate: "20",
    scope_preview: "Full rewire",
    product_preview: "Panel install",
    works: [
      {
        product_name: "Panel install",
        product_code: "P-001",
        scope_preview: "Full rewire",
        labour_subtotal: "120",
        materials_subtotal: "25.20",
        work_subtotal: "145.20",
      },
    ],
    additional_charges: [
      { label: "Parking", amount: "0" },
      { label: "Congestion", amount: "0" },
      { label: "Travel", amount: "0" },
      { label: "Other", amount: "0" },
    ],
  };

  const COMPARISON_SUMMARY_LOW = {
    final_total: "0",
    works_subtotal: "0",
    labour_subtotal: "0",
    materials_subtotal: "0",
    additional_charges_total: "0",
    vat_total: "0",
    vat_rate: "20",
    works: [
      {
        product_name: null,
        product_code: null,
        scope_preview: "Basic repair",
        labour_subtotal: "0",
        materials_subtotal: "0",
        work_subtotal: "0",
      },
    ],
    additional_charges: [
      { label: "Parking", amount: "0" },
      { label: "Congestion", amount: "0" },
      { label: "Travel", amount: "0" },
      { label: "Other", amount: "0" },
    ],
  };

  const COMPARABLE_GROUP_DETAIL = {
    ...MOCK_GROUP_DETAIL,
    job_assignment_decision: null,
    assignment_submissions: [
      {
        ...MOCK_GROUP_DETAIL.assignment_submissions[0],
        can_assign_job: true,
        is_job_assigned: false,
        works_count: 1,
        comparison_summary: COMPARISON_SUMMARY_HIGH,
      },
      {
        ...MOCK_GROUP_DETAIL.assignment_submissions[1],
        can_assign_job: true,
        is_job_assigned: false,
        works_count: 1,
        comparison_summary: COMPARISON_SUMMARY_LOW,
      },
      MOCK_GROUP_DETAIL.assignment_submissions[2],
    ],
  };

  async function mockComparableGroupDetailApi(page: Page, group = COMPARABLE_GROUP_DETAIL) {
    await page.route("**/api/v1/dashboard/quote-groups/detail**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, data: { group } }),
      });
    });
  }

  test("compare panel hidden until selection and appears below assignment table", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockComparableGroupDetailApi(page);
    await page.goto("/manager/review/group?quote_ref=Q22100");

    await expect(page.getByTestId("quote-group-summary")).toBeVisible();
    await expect(page.getByTestId("quote-group-assignment-submissions")).toBeVisible();
    await expect(page.getByTestId("quote-group-compare-submissions")).toHaveCount(0);
    await expect(page.getByTestId("submission-compare-panel")).toHaveCount(0);

    const isDomAfter = (earlierId: string, laterId: string) =>
      page.evaluate(
        ([earlier, later]) => {
          const a = document.querySelector(`[data-testid="${earlier}"]`);
          const b = document.querySelector(`[data-testid="${later}"]`);
          return Boolean(a && b && a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
        },
        [earlierId, laterId],
      );

    expect(await isDomAfter("quote-group-summary", "quote-group-assignment-submissions")).toBe(true);

    await page.getByTestId("compare-select-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb").check();

    await expect(page.getByTestId("quote-group-compare-submissions")).toBeVisible();
    await expect(page.getByTestId("submission-compare-panel")).toBeVisible();
    expect(await isDomAfter("quote-group-assignment-submissions", "quote-group-compare-submissions")).toBe(true);
    expect(await isDomAfter("quote-group-summary", "quote-group-compare-submissions")).toBe(true);
  });

  test("selection limit shows message on fourth pick", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockComparableGroupDetailApi(page, {
      ...COMPARABLE_GROUP_DETAIL,
      assignment_submissions: [
        ...COMPARABLE_GROUP_DETAIL.assignment_submissions,
        {
          assignment_id: 3,
          assignment_type: "engineer",
          assignee_kind: "registered",
          assignee_name: "Third Engineer",
          assignment_status: "submitted",
          submitted_at: "2026-06-05T14:00:00Z",
          linked_session_id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
          submitted_by_name: "Third Engineer",
          final_total: "50",
          can_view_details: true,
          can_reopen: true,
          can_assign_job: true,
          is_job_assigned: false,
          works_count: 1,
        },
        {
          assignment_id: 4,
          assignment_type: "engineer",
          assignee_kind: "registered",
          assignee_name: "Fourth Engineer",
          assignment_status: "submitted",
          submitted_at: "2026-06-05T13:00:00Z",
          linked_session_id: "dddddddd-dddd-dddd-dddd-dddddddddddd",
          submitted_by_name: "Fourth Engineer",
          final_total: "60",
          can_view_details: true,
          can_reopen: true,
          can_assign_job: true,
          is_job_assigned: false,
          works_count: 1,
        },
      ],
    });
    await page.goto("/manager/review/group?quote_ref=Q22100");

    await page.getByTestId("compare-select-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb").check();
    await page.getByTestId("compare-select-aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa").check();
    await page.getByTestId("compare-select-cccccccc-cccc-cccc-cccc-cccccccccccc").check();
    await page.getByTestId("compare-select-dddddddd-dddd-dddd-dddd-dddddddddddd").click();

    await expect(page.getByTestId("submission-selection-limit-message")).toContainText(
      "You can compare up to 3 submissions.",
    );
    await expect(page.getByTestId("compare-card-dddddddd-dddd-dddd-dddd-dddddddddddd")).toHaveCount(0);
  });

  test("compare panel shows calculation breakdown work lines and VAT", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockComparableGroupDetailApi(page);
    await page.goto("/manager/review/group?quote_ref=Q22100");

    await page.getByTestId("compare-select-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb").check();

    const card = page.getByTestId("compare-card-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb");
    await expect(card.getByTestId("compare-works-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")).toContainText("Work breakdown");
    await expect(card.getByTestId("compare-works-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")).toContainText("Panel install");
    await expect(card.getByTestId("compare-works-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")).toContainText("P-001");
    await expect(card.getByTestId("compare-works-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")).toContainText("Full rewire");
    await expect(card.getByTestId("compare-charge-lines-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")).toContainText(
      "Additional charges",
    );
    await expect(card.getByTestId("compare-charge-lines-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")).toContainText("£0.00");
    await expect(card.getByTestId("compare-charge-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb-parking")).toHaveCount(0);
    await expect(card.getByTestId("compare-calculation-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")).toContainText(
      "Cost breakdown",
    );
    await expect(card.getByTestId("compare-labour-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")).toContainText("£120.00");
    await expect(card.getByTestId("compare-materials-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")).toContainText("£25.20");
    await expect(card.getByTestId("compare-vat-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")).toContainText("VAT 20%");
    await expect(card.getByTestId("compare-vat-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")).toContainText("£29.04");
    await expect(card.getByTestId("compare-final-total-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")).toContainText("£174.24");
  });

  test("compare card sections appear in required DOM order", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockComparableGroupDetailApi(page);
    await page.goto("/manager/review/group?quote_ref=Q22100");
    await page.getByTestId("compare-select-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb").check();

    const sessionId = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb";
    const isDomAfter = (earlierId: string, laterId: string) =>
      page.evaluate(
        ([earlier, later]) => {
          const a = document.querySelector(`[data-testid="${earlier}"]`);
          const b = document.querySelector(`[data-testid="${later}"]`);
          return Boolean(a && b && a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
        },
        [earlierId, laterId],
      );

    expect(await isDomAfter(`compare-works-${sessionId}`, `compare-charge-lines-${sessionId}`)).toBe(true);
    expect(await isDomAfter(`compare-charge-lines-${sessionId}`, `compare-calculation-${sessionId}`)).toBe(true);
    expect(await isDomAfter(`compare-calculation-${sessionId}`, `compare-final-total-${sessionId}`)).toBe(true);
    expect(await isDomAfter(`compare-final-total-${sessionId}`, `assign-job-${sessionId}`)).toBe(true);
  });

  test("compare panel shows only non-zero additional charge rows", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockComparableGroupDetailApi(page, {
      ...COMPARABLE_GROUP_DETAIL,
      assignment_submissions: [
        {
          ...COMPARABLE_GROUP_DETAIL.assignment_submissions[0],
          comparison_summary: {
            ...COMPARISON_SUMMARY_HIGH,
            additional_charges_total: "15",
            additional_charges: [
              { label: "Parking", amount: "10" },
              { label: "Congestion", amount: "0" },
              { label: "Travel", amount: "5" },
              { label: "Other", amount: "0" },
            ],
          },
        },
      ],
    });
    await page.goto("/manager/review/group?quote_ref=Q22100");
    await page.getByTestId("compare-select-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb").check();

    const card = page.getByTestId("compare-card-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb");
    await expect(card.getByTestId("compare-charge-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb-parking")).toContainText(
      "£10.00",
    );
    await expect(card.getByTestId("compare-charge-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb-travel")).toContainText(
      "£5.00",
    );
    await expect(card.getByTestId("compare-charge-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb-congestion")).toHaveCount(0);
    await expect(card.getByTestId("compare-charge-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb-other")).toHaveCount(0);
    await expect(card.getByTestId("compare-additional-charges-total-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")).toContainText(
      "£15.00",
    );
  });

  test("compare panel shows badges and assign buttons without secrets", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockComparableGroupDetailApi(page);
    await page.goto("/manager/review/group?quote_ref=Q22100");

    await page.getByTestId("compare-select-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb").check();
    await page.getByTestId("compare-select-aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa").check();

    await expect(page.getByTestId("submission-compare-panel")).toBeVisible();
    await expect(page.getByTestId("compare-latest-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")).toBeVisible();
    await expect(page.getByTestId("compare-lowest-aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")).toBeVisible();
    await expect(page.getByTestId("assign-job-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")).toContainText(
      "Assign Job to Unknown",
    );

    for (const label of ["session_token", "assignment_token", "raw_payload", "profit", "margin", "denominator"]) {
      await expect(page.getByText(label, { exact: false })).toHaveCount(0);
    }
  });

  test("assign job success updates banner summary and row badge", async ({ page }) => {
    await mockAuthMe(page, "manager");
    let currentGroup = COMPARABLE_GROUP_DETAIL;

    await page.route("**/api/v1/dashboard/quote-groups/detail**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, data: { group: currentGroup } }),
      });
    });

    await page.route("**/api/v1/manager/quotes/Q22100/assign-job", async (route) => {
      currentGroup = {
        ...COMPARABLE_GROUP_DETAIL,
        job_assignment_decision: {
          id: 1,
          selected_session_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
          assignee_name: "Rohit",
          assignee_email: "rohit@example.com",
          assignment_id: null,
          assigned_at: "2026-06-06T10:00:00Z",
        },
        assignment_submissions: COMPARABLE_GROUP_DETAIL.assignment_submissions.map((row) =>
          row.linked_session_id === "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
            ? { ...row, is_job_assigned: true }
            : row,
        ),
      };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            decision: currentGroup.job_assignment_decision,
          },
        }),
      });
    });

    await page.goto("/manager/review/group?quote_ref=Q22100");
    await page.getByTestId("compare-select-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb").check();
    await page.getByTestId("assign-job-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb").click();

    await expect(page.getByTestId("job-assignment-success-banner")).toContainText("Job assigned to Rohit.");
    await expect(page.getByTestId("quote-group-job-assignment")).toContainText("Assigned to Rohit");
    await expect(page.getByTestId("submission-assigned-job-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")).toBeVisible();
    await expect(page.getByTestId("change-job-assignment")).toBeVisible();
  });
});
