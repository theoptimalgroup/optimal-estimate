import { test, expect, type Page } from "@playwright/test";

const adminUser = {
  id: "11111111-1111-1111-1111-111111111111",
  email: "admin@optimal.example",
  name: "Admin User",
  role: "admin",
  is_active: true,
  auth_provider: "azure",
};

async function mockAuthMe(page: Page, status: number, body?: unknown) {
  await page.route("**/api/v1/auth/me", async (route) => {
    if (status === 401) {
      await route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Not authenticated" }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ success: true, data: body ?? adminUser }),
    });
  });
}

test.describe("Azure production auth UX", () => {
  test.skip(process.env.PLAYWRIGHT_AZURE_AUTH !== "1", "Set PLAYWRIGHT_AZURE_AUTH=1 to run azure-build e2e");

  test("admin dashboard redirects to /login when unauthenticated", async ({ page }) => {
    await mockAuthMe(page, 401);
    await page.goto("/admin/dashboard");
    await page.waitForURL("**/login", { timeout: 15000 });
    await expect(page.getByTestId("login-microsoft-button")).toBeVisible();
  });

  test("/login shows Microsoft sign-in with azure provider build", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByTestId("login-microsoft-button")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  });

  test("/internal/auth-test shows azure provider before login", async ({ page }) => {
    await mockAuthMe(page, 401);
    await page.goto("/internal/auth-test");
    await expect(page.getByTestId("auth-test-frontend-provider")).toHaveText("azure");
    await expect(page.getByTestId("auth-test-azure-configured")).toHaveText("true");
    await expect(page.getByTestId("auth-test-is-authenticated")).toHaveText("false");
  });
});
