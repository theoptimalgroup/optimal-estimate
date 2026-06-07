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
      synced_at: "2026-06-01T10:00:00Z",
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
    site_address: "10 High Street",
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
    description: "Full rewire",
    notes: "Internal note",
    customer_notes: "Call before visit",
    terms: "30 day terms",
  },
  financials: {
    subtotal: 1200.0,
    vat: 240.0,
    total: 1440.0,
    discount_type: null,
    discount_value: null,
    currency: "GBP",
  },
  tags: ["urgent"],
  items: [],
  custom_fields: [],
  dates: {
    created_on: "2026-01-10",
    updated_on: "2026-01-12",
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

const MOCK_ASSIGNEES = [
  {
    id: "11111111-1111-1111-1111-111111111111",
    name: "Estimator One",
    email: "estimator@example.com",
    role: "estimator",
    is_active: true,
  },
  {
    id: "22222222-2222-2222-2222-222222222222",
    name: "Engineer One",
    email: "engineer@example.com",
    role: "engineer",
    is_active: true,
  },
];

const MOCK_REGISTERED_ASSIGNMENT = {
  id: 1,
  synced_quote_id: 1,
  eworks_quote_id: 101,
  quote_ref: "Q-101",
  assigned_user_id: "11111111-1111-1111-1111-111111111111",
  assigned_user_email: "estimator@example.com",
  assigned_user_name: "Estimator One",
  assignment_type: "estimator",
  assignee_kind: "registered",
  status: "assigned",
  assignment_token: null,
  assignment_token_created_at: null,
  assignment_token_expires_at: null,
  assignment_token_revoked_at: null,
  assigned_by_user_id: "dev-manager",
  assigned_by_email: "manager@example.com",
  assigned_at: "2026-06-05T10:00:00Z",
  notes: "Please estimate",
  assignment_link: null,
  has_calculation_session: false,
  calculation_session_id: null,
  can_start_estimate: true,
};

const MOCK_EXTERNAL_ASSIGNMENT = {
  ...MOCK_REGISTERED_ASSIGNMENT,
  id: 2,
  assignee_kind: "external",
  assigned_user_id: null,
  assigned_user_email: "external@example.com",
  assigned_user_name: "External Estimator",
  assignment_token: "public-assignment-token-abc",
  assignment_link: "/assignment/public-assignment-token-abc",
};

const MOCK_MY_ESTIMATOR_ASSIGNMENTS = {
  success: true,
  data: [MOCK_REGISTERED_ASSIGNMENT],
  meta: { total: 1 },
};

const MOCK_MY_ENGINEER_ASSIGNMENTS = {
  success: true,
  data: [
    {
      ...MOCK_REGISTERED_ASSIGNMENT,
      id: 3,
      assignment_type: "engineer",
      assigned_user_id: "22222222-2222-2222-2222-222222222222",
      assigned_user_email: "engineer@example.com",
      assigned_user_name: "Engineer One",
      has_calculation_session: false,
      calculation_session_id: null,
      can_start_estimate: true,
    },
  ],
  meta: { total: 1 },
};

const MOCK_PUBLIC_ASSIGNMENT = {
  success: true,
  data: {
    assignment_id: 2,
    assignment_type: "estimator",
    assignee_kind: "external",
    status: "assigned",
    assigned_user_name: "External Estimator",
    assigned_user_email: "external@example.com",
    assigned_by_name: "Manager",
    assigned_at: "2026-06-05T10:00:00Z",
    notes: "Please review",
    quote_ref: "Q-101",
    customer_name: "ACME Ltd",
    site_address: "10 High Street",
    quote_date: "2026-01-15",
    expiry_date: "2026-04-15",
    description: "Full rewire",
    tags: ["urgent"],
  },
};

async function mockManagerQuotesWithAssignments(page: Page, assignmentsState: { items: unknown[] }) {
  await page.route("**/api/v1/eworks-sync/quotes**", async (route) => {
    const url = route.request().url();
    if (url.includes("/assignments")) {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: { items: assignmentsState.items, total: assignmentsState.items.length },
          }),
        });
        return;
      }
      const body = route.request().postDataJSON();
      const created = body?.assignee_kind === "external" ? MOCK_EXTERNAL_ASSIGNMENT : MOCK_REGISTERED_ASSIGNMENT;
      assignmentsState.items = [created];
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, data: created }),
      });
      return;
    }
    if (url.includes("/safe")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, data: MOCK_QUOTE_SAFE_DETAIL }),
      });
      return;
    }
    if (url.includes("/attachments")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, data: { items: [], total: 0 } }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ success: true, data: MOCK_QUOTES }),
    });
  });

  await page.route("**/api/v1/quote-assignments/assignees", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ success: true, data: MOCK_ASSIGNEES }),
    });
  });
}

test.describe("Quote assignments", () => {
  test("manager quote detail shows Assign Estimator / Engineer section", async ({ page }) => {
    await mockAuthMe(page, "manager");
    const assignmentsState = { items: [] as unknown[] };
    await mockManagerQuotesWithAssignments(page, assignmentsState);

    await page.goto("/manager/quotes");
    await page.getByTestId("quote-view-1").click();
    await expect(page.getByTestId("quote-detail-modal")).toBeVisible();
    await expect(page.getByTestId("quote-assignment-section")).toBeVisible();
    await expect(page.getByText("Assign Estimator / Engineer")).toBeVisible();
  });

  test("manager can open assign form and assign registered user", async ({ page }) => {
    await mockAuthMe(page, "manager");
    const assignmentsState = { items: [] as unknown[] };
    await mockManagerQuotesWithAssignments(page, assignmentsState);

    await page.goto("/manager/quotes");
    await page.getByTestId("quote-view-1").click();
    await page.getByTestId("open-assignment-form").click();
    await expect(page.getByTestId("assignment-form")).toBeVisible();
    await page.getByTestId("assignee-user-select").selectOption("11111111-1111-1111-1111-111111111111");
    await page.getByTestId("submit-assignment-button").click();
    await expect(page.getByTestId("assignment-row-1")).toBeVisible();
    await expect(page.getByText("Estimator One")).toBeVisible();
  });

  test("external assignment shows copy link", async ({ page }) => {
    await mockAuthMe(page, "manager");
    const assignmentsState = { items: [] as unknown[] };
    await mockManagerQuotesWithAssignments(page, assignmentsState);

    await page.goto("/manager/quotes");
    await page.getByTestId("quote-view-1").click();
    await page.getByTestId("open-assignment-form").click();
    await page.getByTestId("assignee-kind-select").selectOption("external");
    await page.getByTestId("external-assignee-name").fill("External Estimator");
    await page.getByTestId("external-assignee-email").fill("external@example.com");
    await page.getByTestId("submit-assignment-button").click();
    await expect(page.getByTestId("copy-assignment-link-2")).toBeVisible();
  });

  test("estimator dashboard shows assigned quote", async ({ page }) => {
    await mockAuthMe(page, "estimator");
    await page.route("**/api/v1/estimator/dashboard", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            kpis: {
              draft_count: 0,
              submitted_count: 0,
              reopened_count: 0,
              total_submitted_value: 0,
              average_quote_value: 0,
            },
            recent_quotes: [],
            needs_attention: [],
          },
        }),
      });
    });
    await page.route("**/api/v1/quote-assignments/my", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_MY_ESTIMATOR_ASSIGNMENTS),
      });
    });

    await page.goto("/estimator/dashboard");
    await expect(page.getByTestId("estimator-assigned-quotes")).toBeVisible();
    await expect(page.getByTestId("assigned-quote-1")).toBeVisible();
    await expect(page.getByTestId("start-assignment-1")).toHaveText("Start Estimate");
    await expect(page.getByText("raw_payload")).toHaveCount(0);
  });

  test("estimator Start Estimate calls API and navigates to questionnaire", async ({ page }) => {
    await mockAuthMe(page, "estimator");
    await page.route("**/api/v1/estimator/dashboard", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            kpis: {
              draft_count: 0,
              submitted_count: 0,
              reopened_count: 0,
              total_submitted_value: 0,
              average_quote_value: 0,
            },
            recent_quotes: [],
            needs_attention: [],
          },
        }),
      });
    });
    await page.route("**/api/v1/quote-assignments/my", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_MY_ESTIMATOR_ASSIGNMENTS),
      });
    });
    await page.route("**/api/v1/quote-assignments/1/start-estimate", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            session_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            session_token: "mock-session-token",
            resume_url:
              "/eworks/calculate?session_id=aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa&token=mock-session-token",
            assignment_id: 1,
            quote_ref: "Q-101",
          },
        }),
      });
    });

    await page.goto("/estimator/dashboard");
    await page.getByTestId("start-assignment-1").click();
    await page.waitForURL("**/eworks/calculate?session_id=**");
    expect(page.url()).toContain("/eworks/calculate");
    expect(page.url()).toContain("session_id=aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa");
    expect(page.url()).toContain("token=mock-session-token");
  });

  test("estimator Continue Estimate label when session exists", async ({ page }) => {
    await mockAuthMe(page, "estimator");
    await page.route("**/api/v1/quote-assignments/my", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: [
            {
              ...MOCK_REGISTERED_ASSIGNMENT,
              has_calculation_session: true,
              calculation_session_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            },
          ],
          meta: { total: 1 },
        }),
      });
    });
    await page.route("**/api/v1/estimator/dashboard", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            kpis: {
              draft_count: 0,
              submitted_count: 0,
              reopened_count: 0,
              total_submitted_value: 0,
              average_quote_value: 0,
            },
            recent_quotes: [],
            needs_attention: [],
          },
        }),
      });
    });

    await page.goto("/estimator/dashboard");
    await expect(page.getByTestId("start-assignment-1")).toHaveText("Continue Estimate");
  });

  test("engineer assigned estimates shows assigned quote", async ({ page }) => {
    await mockAuthMe(page, "engineer");
    await page.route("**/api/v1/quote-assignments/my", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_MY_ENGINEER_ASSIGNMENTS),
      });
    });

    await page.goto("/engineer/assigned-estimates");
    await expect(page.getByTestId("engineer-assigned-quotes")).toBeVisible();
    await expect(page.getByTestId("engineer-assignment-3")).toBeVisible();
    await expect(page.getByTestId("engineer-assignment-action-3")).toHaveText("Start Estimate");
    await expect(page.getByText("secret_token")).toHaveCount(0);
  });

  test("engineer Continue Estimate navigates to questionnaire", async ({ page }) => {
    await mockAuthMe(page, "engineer");
    await page.route("**/api/v1/quote-assignments/my", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_MY_ENGINEER_ASSIGNMENTS),
      });
    });
    await page.route("**/api/v1/quote-assignments/3/start-estimate", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            session_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            session_token: "engineer-session-token",
            resume_url:
              "/eworks/calculate?session_id=bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb&token=engineer-session-token",
            assignment_id: 3,
            quote_ref: "Q-101",
          },
        }),
      });
    });

    await page.goto("/engineer/assigned-estimates");
    await page.getByTestId("engineer-assignment-action-3").click();
    await page.waitForURL("**/eworks/calculate?session_id=**");
    expect(page.url()).toContain("token=engineer-session-token");
  });

  test("public assignment start-estimate sends no Authorization header", async ({ page }) => {
    let requestHeaders: Record<string, string> = {};
    await page.route("**/api/v1/quote-assignments/public/public-assignment-token-abc/start-estimate", async (route) => {
      requestHeaders = route.request().headers();
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            session_id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
            session_token: "public-session-token",
            resume_url:
              "/eworks/calculate?session_id=cccccccc-cccc-cccc-cccc-cccccccccccc&token=public-session-token",
            assignment_id: 2,
            quote_ref: "Q-101",
          },
        }),
      });
    });

    await page.goto("/assignment/public-assignment-token-abc");
    await page.waitForURL("**/eworks/calculate?session_id=**");
    expect(requestHeaders.authorization).toBeUndefined();
  });

  test("public assignment link auto-redirects to estimate questionnaire", async ({ page }) => {
    let startEstimateCalled = false;
    await page.route("**/api/v1/quote-assignments/public/public-assignment-token-abc/start-estimate", async (route) => {
      startEstimateCalled = true;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            session_id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
            session_token: "public-session-token",
            resume_url:
              "/eworks/calculate?session_id=cccccccc-cccc-cccc-cccc-cccccccccccc&token=public-session-token",
            assignment_id: 2,
            quote_ref: "Q-101",
          },
        }),
      });
    });

    await page.goto("/assignment/public-assignment-token-abc");
    await expect(page.getByText("Preparing estimate questionnaire…")).toBeVisible();
    await page.waitForURL("**/eworks/calculate?session_id=**");
    expect(startEstimateCalled).toBe(true);
    expect(page.url()).toContain("token=public-session-token");
    await expect(page.getByTestId("assignment-summary-section")).toHaveCount(0);
    await expect(page.locator('[data-testid="app-shell"]')).toHaveCount(0);
    await expect(page.getByTestId("eworks-internal-nav-bar")).toHaveCount(0);
    await expect(page.getByTestId("back-link")).toHaveCount(0);
    await expect(page.getByText("raw_payload")).toHaveCount(0);
  });

  test("expired public assignment shows error state", async ({ page }) => {
    await page.route("**/api/v1/quote-assignments/public/expired-token/start-estimate", async (route) => {
      await route.fulfill({
        status: 410,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Assignment link has expired" }),
      });
    });

    await page.goto("/assignment/expired-token");
    await expect(page.getByText("This assignment link is invalid or has expired.")).toBeVisible();
    await expect(page.getByTestId("assignment-summary-section")).toHaveCount(0);
    await expect(page.url()).not.toContain("/eworks/calculate");
  });
});
