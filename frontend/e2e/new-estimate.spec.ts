import { test, expect, type Page } from "@playwright/test";

const MOCK_SESSION = {
  session_id: "dddddddd-dddd-dddd-dddd-dddddddddddd",
  session_token: "mock-manual-session-token",
  resume_url:
    "/eworks/calculate?session_id=dddddddd-dddd-dddd-dddd-dddddddddddd&token=mock-manual-session-token",
};

function mockUser(role: "admin" | "manager" | "estimator" | "engineer") {
  return {
    id: `dev-${role}`,
    email: `${role}@example.com`,
    name: `Dev ${role.charAt(0).toUpperCase()}${role.slice(1)}`,
    role,
    is_active: true,
    auth_provider: "dev",
  };
}

async function mockAuthMe(page: Page, role: "admin" | "manager" | "estimator" | "engineer" | null) {
  await page.route("**/api/v1/auth/me", async (route) => {
    if (!role) {
      await route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ detail: "Not authenticated" }) });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ success: true, data: mockUser(role) }),
    });
  });
}

async function mockManualSessionApi(page: Page) {
  await page.route("**/api/v1/calculation-session/manual", async (route) => {
    if (route.request().method() !== "POST") {
      await route.fallback();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ success: true, data: MOCK_SESSION }),
    });
  });
}

test.describe("New Estimate flow", () => {
  test("sidebar New Estimate creates session and redirects to calculate", async ({ page }) => {
    await mockAuthMe(page, "admin");
    await mockManualSessionApi(page);
    await page.goto("/admin/dashboard");
    await page.getByTestId("nav-item-new-estimate").click();
    await page.waitForURL("**/eworks/calculate?session_id=**&token=**");
    expect(page.url()).toContain("session_id=dddddddd-dddd-dddd-dddd-dddddddddddd");
    expect(page.url()).toContain("token=mock-manual-session-token");
    await expect(page.getByText("session_token")).toHaveCount(0);
  });

  test("admin dashboard New Estimate link uses /new-estimate", async ({ page }) => {
    await mockAuthMe(page, "admin");
    await page.goto("/admin/dashboard");
    await expect(page.getByRole("link", { name: "New Estimate" })).toHaveAttribute("href", "/new-estimate");
  });

  test("bare /eworks/calculate still shows invalid link message", async ({ page }) => {
    await mockAuthMe(page, "admin");
    await page.goto("/eworks/calculate");
    await expect(page.getByRole("heading", { name: "Invalid calculation link" })).toBeVisible({
      timeout: 15000,
    });
  });

  test("engineer is blocked from /new-estimate", async ({ page }) => {
    await mockAuthMe(page, "engineer");
    await page.goto("/new-estimate");
    await expect(page.getByTestId("require-role-forbidden")).toBeVisible({ timeout: 15000 });
  });
});
