import { test, expect, type Page } from "@playwright/test";

type MockUserRole = "admin" | "manager" | "estimator";

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
  assignments: [
    {
      id: 1,
      assignment_type: "estimator",
      assignee_kind: "registered",
      assigned_user_id: "11111111-1111-1111-1111-111111111111",
      assigned_user_name: "Estimator User",
      assigned_user_email: "estimator@example.com",
      status: "assigned",
      assigned_at: "2026-06-05T10:00:00Z",
      started_at: null,
      submitted_at: null,
      calculation_session_id: null,
      has_submission: false,
    },
    {
      id: 2,
      assignment_type: "engineer",
      assignee_kind: "registered",
      assigned_user_id: "22222222-2222-2222-2222-222222222222",
      assigned_user_name: "Engineer User",
      assigned_user_email: "engineer@example.com",
      status: "submitted",
      assigned_at: "2026-06-05T11:00:00Z",
      started_at: "2026-06-05T12:00:00Z",
      submitted_at: "2026-06-05T15:48:00Z",
      calculation_session_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
      has_submission: true,
    },
  ],
  sessions: [
    {
      session_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
      submitted_at: "2026-06-05T16:04:00Z",
      final_total: "174.24",
      works_count: 1,
      status: "submitted",
      accepted: false,
      client_accepted_at: null,
      submitted_by_user_id: null,
      submitted_by_name: "Unknown submitter",
      submitted_by_email: null,
      submitted_by_role: null,
      is_latest: true,
    },
    {
      session_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
      submitted_at: "2026-06-05T15:48:00Z",
      final_total: "0",
      works_count: 1,
      status: "submitted",
      accepted: false,
      client_accepted_at: null,
      submitted_by_user_id: "22222222-2222-2222-2222-222222222222",
      submitted_by_name: "Engineer User",
      submitted_by_email: "engineer@example.com",
      submitted_by_role: "engineer",
      is_latest: false,
    },
  ],
  assignment_submissions: [
    {
      assignment_id: null,
      assignment_type: "unknown",
      assignee_kind: "unknown",
      assignee_name: "Unknown",
      assignee_email: null,
      assignment_status: "submitted",
      assigned_at: null,
      started_at: null,
      submitted_at: "2026-06-05T16:04:00Z",
      linked_session_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
      submitted_by_name: "Unknown submitter",
      submitted_by_email: null,
      submitted_by_role: null,
      final_total: "174.24",
      works_count: 1,
      is_latest: true,
      can_view_details: true,
      can_reopen: true,
    },
    {
      assignment_id: 2,
      assignment_type: "engineer",
      assignee_kind: "registered",
      assignee_name: "Engineer User",
      assignee_email: "engineer@example.com",
      assignment_status: "submitted",
      assigned_at: "2026-06-05T11:00:00Z",
      started_at: "2026-06-05T12:00:00Z",
      submitted_at: "2026-06-05T15:48:00Z",
      linked_session_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
      submitted_by_name: "Engineer User",
      submitted_by_email: "engineer@example.com",
      submitted_by_role: "engineer",
      final_total: "0",
      works_count: 1,
      is_latest: false,
      can_view_details: true,
      can_reopen: true,
    },
    {
      assignment_id: 1,
      assignment_type: "estimator",
      assignee_kind: "registered",
      assignee_name: "Estimator User",
      assignee_email: "estimator@example.com",
      assignment_status: "assigned",
      assigned_at: "2026-06-05T10:00:00Z",
      started_at: null,
      submitted_at: null,
      linked_session_id: null,
      submitted_by_name: null,
      submitted_by_email: null,
      submitted_by_role: null,
      final_total: null,
      works_count: null,
      is_latest: false,
      can_view_details: false,
      can_reopen: false,
    },
  ],
};

const MOCK_QUOTE_GROUPS = {
  success: true,
  data: {
    groups: [
      {
        ...MOCK_GROUP_DETAIL,
        sessions: MOCK_GROUP_DETAIL.sessions.map(({ submitted_by_name, submitted_by_role, is_latest, ...session }) => session),
      },
    ],
  },
  meta: { total: 1 },
};

const MOCK_QUOTE_GROUP_DETAIL = {
  success: true,
  data: {
    group: MOCK_GROUP_DETAIL,
  },
};

async function mockQuoteGroupsApi(page: Page) {
  await page.route("**/api/v1/dashboard/quote-groups**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/quote-groups/detail")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_QUOTE_GROUP_DETAIL),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_QUOTE_GROUPS),
    });
  });
}

test.describe("Manager grouped quote review", () => {
  test("review list shows one row per quote with submission count", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockQuoteGroupsApi(page);
    await page.goto("/manager/review");
    await expect(page.getByTestId("quote-groups-table")).toBeVisible();
    await expect(page.getByTestId("quote-group-row-quote_ref:Q22100")).toHaveCount(1);
    await expect(page.getByTestId("quote-group-row-quote_ref:Q22100")).toContainText("Q22100");
    await expect(page.getByTestId("quote-group-row-quote_ref:Q22100")).toContainText("2");
    await expect(page.getByText("session_token")).toHaveCount(0);
    await expect(page.getByText("raw_payload")).toHaveCount(0);
  });

  test("view submissions opens group detail with combined assignment submissions table", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockQuoteGroupsApi(page);
    await page.goto("/manager/review");
    await page.getByTestId("view-quote-group-quote_ref:Q22100").click();
    await expect(page.getByTestId("manager-review-group-page")).toBeVisible();
    await expect(page.getByTestId("quote-group-assignment-submissions")).toBeVisible();
    await expect(page.getByTestId("quote-group-assignment-submissions-table")).toBeVisible();
    await expect(page.getByTestId("quote-group-assignments")).toHaveCount(0);
    await expect(page.getByTestId("quote-group-submissions")).toHaveCount(0);
    await expect(page.getByTestId("assignment-submission-row-1")).toBeVisible();
    await expect(page.getByTestId("assignment-submission-status-1")).toContainText("Assigned");
    await expect(page.getByTestId("assignment-submission-row-2")).toBeVisible();
    await expect(
      page.getByTestId("assignment-submission-row-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
    ).toBeVisible();
    await expect(page.getByTestId("quote-group-submissions-notice")).toContainText("2 submissions received");
  });

  test("group detail shows latest badge without submitter line in card", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockQuoteGroupsApi(page);
    await page.goto("/manager/review/group?quote_ref=Q22100");
    await expect(page.getByTestId("submission-latest-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")).toBeVisible();
    await expect(page.getByTestId("assignment-submission-row-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")).not.toContainText(
      "Submitted by",
    );
    await expect(page.getByTestId("assignment-submission-row-2")).not.toContainText("engineer@example.com");
    await expect(page.getByTestId("quote-group-review-status")).toContainText("Ready for Review");
    await expect(page.getByText("assignment_token")).toHaveCount(0);
    await expect(page.getByTestId("assignment-submission-row-1")).toContainText("No submission yet");
  });

  test("assignment submissions section precedes compare section in DOM order", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await page.route("**/api/v1/dashboard/quote-groups/detail**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            group: {
              ...MOCK_GROUP_DETAIL,
              assignment_submissions: MOCK_GROUP_DETAIL.assignment_submissions.map((row) =>
                row.linked_session_id
                  ? { ...row, can_assign_job: true, is_job_assigned: false, works_count: 1 }
                  : row,
              ),
            },
          },
        }),
      });
    });
    await page.goto("/manager/review/group?quote_ref=Q22100");

    await expect(page.getByTestId("quote-group-summary")).toBeVisible();
    await expect(page.getByTestId("quote-group-assignment-submissions")).toBeVisible();
    await expect(page.getByTestId("quote-group-compare-submissions")).toHaveCount(0);

    await page.getByTestId("compare-select-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb").check();

    await expect(page.getByTestId("quote-group-compare-submissions")).toBeVisible();

    const isDomAfter = await page.evaluate(
      ([earlier, later]) => {
        const a = document.querySelector(`[data-testid="${earlier}"]`);
        const b = document.querySelector(`[data-testid="${later}"]`);
        return Boolean(a && b && a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
      },
      ["quote-group-assignment-submissions", "quote-group-compare-submissions"],
    );

    expect(isDomAfter).toBe(true);
  });

  test("group detail view details links to session detail page", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await mockQuoteGroupsApi(page);
    await page.goto("/manager/review/group?quote_ref=Q22100");
    await expect(page.getByTestId("view-session-detail-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")).toHaveAttribute(
      "href",
      "/manager/review/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    );
  });

  test("pending notice appears when assignments pending and no submissions", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await page.route("**/api/v1/dashboard/quote-groups/detail**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            group: {
              ...MOCK_GROUP_DETAIL,
              submission_count: 0,
              sessions: [],
              review_status: "pending",
              assignment_summary: {
                ...MOCK_GROUP_DETAIL.assignment_summary,
                pending_assignments: 1,
                submitted_assignments: 0,
              },
              assignment_submissions: MOCK_GROUP_DETAIL.assignment_submissions.filter(
                (row) => row.assignment_status !== "submitted" || row.assignment_id === 1,
              ).map((row) =>
                row.assignment_id === 1
                  ? row
                  : { ...row, submitted_at: null, final_total: null, is_latest: false, can_view_details: false, can_reopen: false },
              ),
            },
          },
        }),
      });
    });
    await page.goto("/manager/review/group?quote_ref=Q22100");
    await expect(page.getByTestId("quote-group-pending-notice")).toContainText("No estimate has been submitted yet");
    await expect(page.getByTestId("quote-group-review-status")).toContainText("Pending");
    await expect(page.getByTestId("quote-group-assignment-submissions-table")).toBeVisible();
  });
});
