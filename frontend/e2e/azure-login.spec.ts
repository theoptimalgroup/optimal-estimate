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
    await expect(page.getByText(/Invalid calculation link|Start local test session/i).first()).toBeVisible({
      timeout: 15000,
    });
  });

  test("/eworks/calculate with session params does not prompt sign-in", async ({ page }) => {
    await mockAuthMe(page, 401);
    await page.route("**/api/v1/calculation-session/cccccccc-cccc-cccc-cccc-cccccccccccc", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            session_id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
            session_token: "public-session-token",
            resumed: false,
            step1: {
              quote_number: "Q-101",
              job_number: "J-101",
              client_name: "ACME Ltd",
              trade_name: "Electrical",
              property_address: "10 High Street",
              congestion_required: false,
              congestion_amount: 0,
              travel: 0,
            },
            step2: { works: [] },
            resolved: {},
            ui_state: { current_step: 0, max_reachable_step: 0 },
          },
        }),
      });
    });

    await page.goto(
      "/eworks/calculate?session_id=cccccccc-cccc-cccc-cccc-cccccccccccc&token=public-session-token",
    );
    await expect(page.getByTestId("require-role-unauthenticated")).toHaveCount(0);
    await expect(page.getByTestId("login-microsoft-button")).toHaveCount(0);
    await expect(page.getByText(/OPTIMAL ESTIMATE/i).first()).toBeVisible({ timeout: 15000 });
  });

  test("/assignment does not prompt Microsoft sign-in", async ({ page }) => {
    await mockAuthMe(page, 401);
    await page.route("**/api/v1/quote-assignments/public/test-token/start-estimate", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            session_id: "dddddddd-dddd-dddd-dddd-dddddddddddd",
            session_token: "assignment-session-token",
            resume_url:
              "/eworks/calculate?session_id=dddddddd-dddd-dddd-dddd-dddddddddddd&token=assignment-session-token",
            assignment_id: 2,
            quote_ref: "Q-101",
          },
        }),
      });
    });

    await page.goto("/assignment/test-token");
    await expect(page.getByTestId("login-microsoft-button")).toHaveCount(0);
    await expect(page.getByTestId("require-role-unauthenticated")).toHaveCount(0);
    await page.waitForURL("**/eworks/calculate?session_id=**");
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

  test("manager dashboard still requires auth when unauthenticated", async ({ page }) => {
    await mockAuthMe(page, 401);
    await page.goto("/manager/dashboard");
    await expect(page.getByTestId("require-role-unauthenticated")).toBeVisible();
  });

  test("protected route loads after mocked admin auth/me", async ({ page }) => {
    await mockAuthMe(page, 200, adminUser);
    await page.route("**/api/v1/**", async (route) => {
      const url = route.request().url();
      if (url.includes("/api/v1/auth/me")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true, data: adminUser }),
        });
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
