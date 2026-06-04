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
    unit_cost: null,
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
  await page.route(`**/api/v1/engineer/sessions/${SESSION_ID}`, async (route) => {
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

  await page.route(`**/api/v1/engineer/sessions/${SESSION_ID}/site-visit`, async (route) => {
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

test.describe("engineer site visit UI", () => {
  test("engineer jobs page has open session card", async ({ page }) => {
    await mockAuthMe(page, "engineer");
    await page.goto("/engineer/jobs");
    await expect(page.getByRole("heading", { name: "My Jobs" })).toBeVisible();
    await expect(page.getByTestId("engineer-open-session-card")).toBeVisible();
    await expect(page.getByTestId("engineer-session-id-input")).toBeVisible();
  });

  test("manager is blocked from engineer jobs", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await page.goto("/engineer/jobs");
    await expect(page.getByTestId("require-role-forbidden")).toBeVisible();
  });

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
    await page.getByTestId("engineer-submit-site-visit").click();
    await expect(page.getByTestId("engineer-save-success")).toContainText("Site visit saved");
  });
});
