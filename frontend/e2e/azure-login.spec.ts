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
    if (status === 403) {
      await route.fulfill({
        status: 403,
        contentType: "application/json",
        body: JSON.stringify({ detail: "User not registered" }),
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

test.describe("Azure login and public routes", () => {
  test("/login renders Microsoft sign-in when Azure provider is enabled", async ({ page }) => {
    await page.goto("/login");

    const azureButton = page.getByTestId("login-microsoft-button");
    const devPanel = page.getByRole("heading", { name: "Dev authentication" });

    if (await azureButton.isVisible().catch(() => false)) {
      await expect(azureButton).toBeVisible();
      await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
    } else {
      await expect(devPanel).toBeVisible();
    }
  });

  test("/eworks/calculate remains public without auth", async ({ page }) => {
    await mockAuthMe(page, 401);
    await page.goto("/eworks/calculate");
    await expect(page.getByText(/OPTIMAL ESTIMATE|Estimate Calculator|Calculate/i).first()).toBeVisible({
      timeout: 15000,
    });
  });

  test("protected route prompts sign-in when unauthenticated", async ({ page }) => {
    await mockAuthMe(page, 401);
    await page.goto("/admin/dashboard");

    await expect(page.getByTestId("require-role-unauthenticated")).toBeVisible();
    const signIn = page.getByTestId("require-role-sign-in");
    if (await signIn.isVisible().catch(() => false)) {
      await expect(signIn).toHaveAttribute("href", "/login");
    }
  });

  test("protected route loads after mocked admin auth/me", async ({ page }) => {
    await mockAuthMe(page, 200, adminUser);
    await page.route("**/api/v1/**", async (route) => {
      const url = route.request().url();
      if (url.includes("/api/v1/auth/me")) {
        await route.continue();
        return;
      }
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true, data: [], meta: { total: 0, limit: 25, offset: 0 } }),
        });
        return;
      }
      await route.continue();
    });

    await page.goto("/admin/dashboard");
    await expect(page.getByTestId("app-shell")).toBeVisible({ timeout: 15000 });
    await expect(page.getByText("Admin User")).toBeVisible();
  });

  test("unregistered Azure user sees registration error", async ({ page }) => {
    await mockAuthMe(page, 403);
    await page.goto("/admin/dashboard");
    await expect(page.getByTestId("require-role-registration-error")).toBeVisible();
    await expect(page.getByText("User not registered or inactive. Contact admin.")).toBeVisible();
  });
});
