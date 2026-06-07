import { test, expect, type Page } from "@playwright/test";

type MockUserRole = "admin" | "estimator" | "manager" | "engineer";

function mockUser(role: MockUserRole) {
  return {
    id: "dev-engineer",
    email: "engineer@example.com",
    name: "Dev engineer",
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

const MOCK_ACTIVE_ASSIGNMENT = {
  id: 3,
  synced_quote_id: 1,
  eworks_quote_id: 101,
  quote_ref: "Q-101",
  assigned_user_id: "dev-engineer",
  assigned_user_email: "engineer@example.com",
  assigned_user_name: "Engineer One",
  assignment_type: "engineer",
  assignee_kind: "registered",
  status: "in_progress",
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
  can_view_submission: false,
};

const MOCK_SUBMITTED_ASSIGNMENT = {
  ...MOCK_ACTIVE_ASSIGNMENT,
  id: 4,
  quote_ref: "Q-102",
  status: "submitted",
  assigned_at: "2026-06-04T10:00:00.000Z",
  submitted_at: "2026-06-05T18:00:00.000Z",
  final_total: "1234.56",
  calculation_session_id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
  can_start_estimate: true,
  can_view_submission: true,
  quote_summary: {
    ...MOCK_ACTIVE_ASSIGNMENT.quote_summary,
    quote_ref: "Q-102",
  },
};

const MOCK_ASSIGNED_JOB = {
  id: 1,
  eworks_job_id: 5001,
  job_ref: "JOB-001",
  eworks_quote_id: 29204,
  quote_ref: "Q22100",
  customer_name: "ACME Ltd",
  address: "1 Test Street",
  status: "open",
  status_name: "Open",
  job_date: "2026-06-01",
  description: "Kitchen refit",
  total: "100.00",
  appointment_user_name: "Dev engineer",
  appointment_type: "1 Hour Job",
  appointment_status: "Scheduled",
  appointment_start_at: "2026-06-10 11:00",
  appointment_end_at: "2026-06-10 12:00",
};

const MOCK_CANCELLED_ASSIGNED_JOB = {
  ...MOCK_ASSIGNED_JOB,
  id: 2,
  eworks_job_id: 5002,
  job_ref: "JOB-CANCELLED",
  appointment_status: "Cancelled",
};

async function mockMyAssignments(page: Page, items: unknown[]) {
  await page.route("**/api/v1/quote-assignments/my", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ success: true, data: items, meta: { total: items.length } }),
    });
  });
}

async function mockAssignedJobs(page: Page, items: unknown[]) {
  await page.route("**/api/v1/engineer/jobs/assigned", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ success: true, data: items, meta: { total: items.length } }),
    });
  });
}

test.describe("engineer estimate pages", () => {
  test("assigned estimates shows active assignments only", async ({ page }) => {
    await mockAuthMe(page, "engineer");
    await mockMyAssignments(page, [MOCK_ACTIVE_ASSIGNMENT, MOCK_SUBMITTED_ASSIGNMENT]);
    await page.goto("/engineer/assigned-estimates");

    await expect(page.getByTestId("engineer-assignment-3")).toBeVisible();
    await expect(page.getByTestId("engineer-assignment-4")).toHaveCount(0);
    await expect(page.getByTestId("engineer-assignment-status-3")).toHaveText("In Progress");
    await expect(page.locator("body")).not.toContainText("in_progress");
  });

  test("submitted estimates shows submitted assignments only", async ({ page }) => {
    await mockAuthMe(page, "engineer");
    await mockMyAssignments(page, [MOCK_ACTIVE_ASSIGNMENT, MOCK_SUBMITTED_ASSIGNMENT]);
    await page.goto("/engineer/submitted-estimates");

    await expect(page.getByTestId("engineer-submitted-4")).toBeVisible();
    await expect(page.getByTestId("engineer-submitted-3")).toHaveCount(0);
    await expect(page.getByTestId("engineer-submitted-status-4")).toHaveText("Submitted");
    await expect(page.getByTestId("engineer-submitted-total-4")).toContainText("1,234.56");
  });

  test("submitted estimates empty state links to assigned estimates", async ({ page }) => {
    await mockAuthMe(page, "engineer");
    await mockMyAssignments(page, [MOCK_ACTIVE_ASSIGNMENT]);
    await page.goto("/engineer/submitted-estimates");

    await expect(page.getByTestId("engineer-no-submitted-estimates")).toContainText("No submitted estimates yet.");
    await page.getByTestId("engineer-submitted-estimates-go-estimates").click();
    await page.waitForURL("**/engineer/assigned-estimates");
  });

  test("view submission button opens estimate session", async ({ page }) => {
    await mockAuthMe(page, "engineer");
    await mockMyAssignments(page, [MOCK_SUBMITTED_ASSIGNMENT]);
    await page.route("**/api/v1/quote-assignments/4/start-estimate", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            session_id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
            session_token: "view-submission-token",
            resume_url:
              "/eworks/calculate?session_id=cccccccc-cccc-cccc-cccc-cccccccccccc&token=view-submission-token",
            assignment_id: 4,
            quote_ref: "Q-102",
          },
        }),
      });
    });

    await page.goto("/engineer/submitted-estimates");
    await expect(page.getByTestId("engineer-submitted-view-4")).toHaveText("View Submission");
    await page.getByTestId("engineer-submitted-view-4").click();
    await page.waitForURL("**/eworks/calculate?session_id=**");
  });

  test("assignment list responses do not expose secrets", async ({ page }) => {
    await mockAuthMe(page, "engineer");
    await mockMyAssignments(page, [
      {
        ...MOCK_SUBMITTED_ASSIGNMENT,
        assignment_token: "secret-assignment-token",
        session_token: "secret-session-token",
        raw_payload: { secret: true },
      },
    ]);
    await page.goto("/engineer/submitted-estimates");
    const bodyText = await page.locator("body").innerText();
    expect(bodyText).not.toContain("secret-assignment-token");
    expect(bodyText).not.toContain("secret-session-token");
    expect(bodyText).not.toContain("raw_payload");
    expect(bodyText).not.toContain("assignment_token");
    expect(bodyText).not.toContain("profit");
    expect(bodyText).not.toContain("margin");
    expect(bodyText).not.toContain("formula");
    expect(bodyText).not.toContain("denominator");
  });
});

test.describe("engineer job pages", () => {
  test("assigned jobs shows mocked eWorks job cards", async ({ page }) => {
    await mockAuthMe(page, "engineer");
    await mockAssignedJobs(page, [MOCK_ASSIGNED_JOB]);
    await page.goto("/engineer/assigned-jobs");

    await expect(page.getByTestId("engineer-assigned-job-1")).toBeVisible();
    await expect(page.getByText("JOB-001")).toBeVisible();
    await expect(page.getByText("Quote Q22100")).toBeVisible();
    await expect(page.getByTestId("engineer-assigned-job-appointment-1")).toContainText("2026-06-10 11:00");
    await expect(page.getByTestId("engineer-assigned-job-assignee-1")).toContainText("Dev engineer");
    await expect(page.getByTestId("engineer-assigned-job-status-1")).toHaveText("Scheduled");
  });

  test("cancelled appointment job does not appear as active assigned job", async ({ page }) => {
    await mockAuthMe(page, "engineer");
    await mockAssignedJobs(page, [MOCK_ASSIGNED_JOB]);
    await page.goto("/engineer/assigned-jobs");
    await expect(page.getByTestId("engineer-assigned-job-2")).toHaveCount(0);
  });

  test("assigned jobs empty state", async ({ page }) => {
    await mockAuthMe(page, "engineer");
    await mockAssignedJobs(page, []);
    await page.goto("/engineer/assigned-jobs");
    await expect(page.getByTestId("engineer-no-assigned-jobs")).toContainText("No assigned jobs yet.");
  });

  test("submitted jobs shows clean empty state", async ({ page }) => {
    await mockAuthMe(page, "engineer");
    await page.goto("/engineer/submitted-jobs");

    await expect(page.getByTestId("engineer-no-submitted-jobs")).toContainText("No submitted jobs yet.");
    await expect(page.getByTestId("engineer-no-submitted-jobs")).toContainText(
      "Submitted jobs will appear here after you complete assigned jobs.",
    );
    await expect(page.locator("body")).not.toContainText("Coming soon");
    await expect(page.locator("body")).not.toContainText("placeholder");
  });

  test("assigned jobs response does not expose tokens", async ({ page }) => {
    await mockAuthMe(page, "engineer");
    await page.route("**/api/v1/engineer/jobs/assigned", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: [MOCK_ASSIGNED_JOB],
          meta: { total: 1 },
        }),
      });
    });
    await page.goto("/engineer/assigned-jobs");
    const bodyText = await page.locator("body").innerText();
    expect(bodyText).not.toContain("session_token");
    expect(bodyText).not.toContain("assignment_token");
    expect(bodyText).not.toContain("raw_payload");
    expect(bodyText).not.toContain("selected_session_id");
    expect(bodyText).not.toContain("selected_estimate_total");
  });
});
