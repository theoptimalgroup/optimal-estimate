import { test, expect, type Page } from "@playwright/test";

type MockUserRole = "admin" | "estimator" | "manager" | "engineer";

const SESSION_ID = "22222222-2222-2222-2222-222222222222";
const SESSION_TOKEN = "engineer-mock-token";

function mockUser(role: MockUserRole) {
  return {
    id: `dev-${role}`,
    email: `${role}@example.com`,
    name: `Dev ${role}`,
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

const MOCK_ENGINEER_ASSIGNMENT = {
  id: 3,
  synced_quote_id: 1,
  eworks_quote_id: 101,
  quote_ref: "Q-101",
  assigned_user_id: "22222222-2222-2222-2222-222222222222",
  assigned_user_email: "engineer@example.com",
  assigned_user_name: "Engineer One",
  assignment_type: "engineer",
  assignee_kind: "registered",
  status: "in_progress",
  assignment_token: null,
  assignment_token_created_at: null,
  assignment_token_expires_at: null,
  assignment_token_revoked_at: null,
  assigned_by_user_id: "dev-manager",
  assigned_by_email: "manager@example.com",
  assigned_at: "2026-06-05T17:03:37.253Z",
  notes: "Please estimate",
  assignment_link: null,
  quote_summary: {
    synced_quote_id: 1,
    eworks_quote_id: 101,
    quote_ref: "Q-101",
    customer_name: "ACME Ltd",
    site_address: "10 High Street",
    quote_date: "2026-01-15",
    expiry_date: "2026-04-15",
    description: "Full rewire",
    tags: [],
  },
  has_calculation_session: true,
  calculation_session_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
  can_start_estimate: true,
};

async function mockEngineerAssignments(page: Page) {
  await page.route("**/api/v1/quote-assignments/my", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: [MOCK_ENGINEER_ASSIGNMENT],
        meta: { total: 1 },
      }),
    });
  });
}

const mockEngineerSession = {
  session_id: SESSION_ID,
  status: "in_progress",
  expires_at: "2026-12-31T00:00:00Z",
  job: {
    quote_number: "Q-SITE-1",
    job_number: "J-SITE-1",
    client_name: "Site Client Ltd",
    trade_name: "Electrical",
    property_address: "1 Test Street",
    engineer_name: "Alex",
    status: "in_progress",
  },
  site_visit: {
    scope: "Inspect panel",
    site_notes: "",
    findings: null,
    attachments: [],
    engineer_count: 1,
    labourer_count: 0,
    duration_type: "hourly",
    hours: 1.5,
    days: null,
    materials_required: "",
    unit_cost: 0,
    parking_required: false,
    parking_amount: null,
    congestion_required: false,
    congestion_amount: null,
    ulez_required: false,
    ulez_amount: null,
    waste_required: false,
    waste_amount: null,
  },
};

async function mockEngineerApis(page: Page) {
  await page.route(/\/api\/v1\/engineer\/sessions\/[0-9a-f-]+$/, async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, data: mockEngineerSession }),
      });
      return;
    }
    await route.continue();
  });

  await page.route(/\/api\/v1\/engineer\/sessions\/[0-9a-f-]+\/site-visit$/, async (route) => {
    if (route.request().method() !== "PUT") {
      await route.continue();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: { session_id: SESSION_ID, status: "in_progress", saved: true, message: "Site visit saved for estimator review." },
      }),
    });
  });
}

test.describe("engineer assignments page", () => {
  test("shows Assigned Estimates title and card", async ({ page }) => {
    await mockAuthMe(page, "engineer");
    await mockEngineerAssignments(page);
    await page.goto("/engineer/assigned-estimates");
    await expect(page.getByRole("heading", { name: "Assigned Estimates", level: 1 })).toBeVisible();
    await expect(page.getByText("Review assigned estimates and continue your work.")).toBeVisible();
    await expect(page.getByTestId("engineer-assigned-quotes")).toContainText("Assigned Estimates");
  });

  test("shows user-friendly status labels and formatted assigned date", async ({ page }) => {
    await mockAuthMe(page, "engineer");
    await mockEngineerAssignments(page);
    await page.goto("/engineer/assigned-estimates");
    await expect(page.getByTestId("engineer-assignment-status-3")).toHaveText("In Progress");
    await expect(page.locator("body")).not.toContainText("in_progress");
    await expect(page.getByTestId("engineer-assignment-date-3")).toContainText("Assigned 5 Jun 2026");
    await expect(page.getByTestId("engineer-assignment-date-3")).toContainText("17:03");
  });

  test("Continue Estimate button navigates to questionnaire", async ({ page }) => {
    await mockAuthMe(page, "engineer");
    await mockEngineerAssignments(page);
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
    await expect(page.getByTestId("engineer-assignment-action-3")).toHaveText("Continue Estimate");
    await page.getByTestId("engineer-assignment-action-3").click();
    await page.waitForURL("**/eworks/calculate?session_id=**");
    expect(page.url()).toContain("token=engineer-session-token");
  });

  test("manual session form is collapsed and token input hidden by default", async ({ page }) => {
    await mockAuthMe(page, "engineer");
    await mockEngineerAssignments(page);
    await page.goto("/engineer/assigned-estimates");
    await expect(page.getByTestId("engineer-advanced-session")).toBeVisible();
    await expect(page.getByText("Advanced: Open by session token")).toBeVisible();
    await expect(page.getByTestId("engineer-session-token-input")).not.toBeVisible();
    await expect(page.getByTestId("engineer-session-id-input")).not.toBeVisible();
  });

  test("legacy /engineer/jobs redirects to assigned estimates", async ({ page }) => {
    await mockAuthMe(page, "engineer");
    await mockEngineerAssignments(page);
    await page.goto("/engineer/jobs");
    await page.waitForURL("**/engineer/assigned-estimates");
    await expect(page.getByRole("heading", { name: "Assigned Estimates", level: 1 })).toBeVisible();
  });

  test("manager can access engineer assigned estimates", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockEngineerAssignments(page);
    await page.goto("/engineer/assigned-estimates");
    await expect(page.getByRole("heading", { name: "Assigned Estimates", level: 1 })).toBeVisible();
    await expect(page.getByTestId("require-role-forbidden")).toHaveCount(0);
  });
});

test.describe("engineer site visit UI", () => {
  test("engineer site visit page hides financial wording", async ({ page }) => {
    await mockAuthMe(page, "engineer");
    await mockEngineerApis(page);
    await page.goto(`/engineer/jobs/${SESSION_ID}?token=${SESSION_TOKEN}`);
    await expect(page.getByTestId("engineer-site-visit-form")).toBeVisible();
    const bodyText = await page.locator("body").innerText();
    const forbidden = ["Total", "VAT", "Profit", "Margin", "Rate Rule", "Internal Notes", "Subtotal"];
    for (const word of forbidden) {
      expect(bodyText).not.toContain(word);
    }
  });

  test("engineer can save site visit via mocked API", async ({ page }) => {
    await mockAuthMe(page, "engineer");
    await mockEngineerApis(page);
    await page.goto(`/engineer/jobs/${SESSION_ID}?token=${SESSION_TOKEN}`);
    await expect(page.getByTestId("engineer-site-visit-form")).toBeVisible();
    const saveResponse = page.waitForResponse(
      (resp) => resp.url().includes("/site-visit") && resp.request().method() === "PUT",
    );
    await page.getByTestId("engineer-submit-site-visit").click();
    const response = await saveResponse;
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body.data.message).toContain("Site visit saved");
    await expect(page.getByTestId("engineer-site-visit-form")).toBeVisible();
  });
});
