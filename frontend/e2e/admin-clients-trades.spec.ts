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

const mockClients = [
  {
    id: "11111111-1111-1111-1111-111111111111",
    name: "Atkinson McLeod",
    billing_email: "billing@example.com",
    default_vat_rate: "20.00",
    is_active: true,
    aliases: ["Atkinson"],
    rate_rules_count: 2,
    calculation_sessions_count: 5,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-06-01T00:00:00Z",
  },
];

const mockTrades = [
  {
    id: "22222222-2222-2222-2222-222222222222",
    name: "Plumber",
    description: "Plumbing works",
    is_active: true,
    rate_rules_count: 3,
    products_count: 12,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-06-01T00:00:00Z",
  },
];

async function mockClientsApi(page: Page) {
  await page.route("**/api/v1/clients**", async (route) => {
    const url = new URL(route.request().url());
    const method = route.request().method();

    if (method === "GET" && url.pathname.endsWith("/clients")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: mockClients,
          meta: { total: 1, limit: 25, offset: 0 },
        }),
      });
      return;
    }

    if (method === "GET" && url.pathname.includes("/clients/")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, data: mockClients[0] }),
      });
      return;
    }

    if (method === "PATCH") {
      const body = route.request().postDataJSON() as { name?: string };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: { ...mockClients[0], name: body.name ?? mockClients[0].name },
        }),
      });
      return;
    }

    await route.continue();
  });
}

async function mockTradesApi(page: Page) {
  await page.route("**/api/v1/trades**", async (route) => {
    const url = new URL(route.request().url());
    const method = route.request().method();
    const hasLimit = url.searchParams.has("limit");

    if (method === "GET" && url.pathname.endsWith("/trades") && hasLimit) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: mockTrades,
          meta: { total: 1, limit: 25, offset: 0 },
        }),
      });
      return;
    }

    if (method === "GET" && url.pathname.endsWith("/trades")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: [{ id: mockTrades[0].id, name: mockTrades[0].name, description: mockTrades[0].description, is_active: true }],
          meta: { page: 1, page_size: 100, total: 1, total_pages: 1 },
        }),
      });
      return;
    }

    if (method === "GET" && url.pathname.includes("/trades/")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, data: mockTrades[0] }),
      });
      return;
    }

    if (method === "PATCH") {
      const body = route.request().postDataJSON() as { description?: string };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: { ...mockTrades[0], description: body.description ?? mockTrades[0].description },
        }),
      });
      return;
    }

    await route.continue();
  });
}

test.describe("Admin clients and trades pages", () => {
  test("admin can open /admin/clients and see mocked client table", async ({ page }) => {
    await mockAuthMe(page, "admin");
    await mockClientsApi(page);
    await page.goto("/admin/clients");
    await expect(page.getByTestId("admin-clients-page")).toBeVisible();
    await expect(page.getByTestId("clients-table")).toBeVisible();
    await expect(page.getByText("Atkinson McLeod")).toBeVisible();
  });

  test("admin can open /admin/trades and see mocked trade table", async ({ page }) => {
    await mockAuthMe(page, "admin");
    await mockTradesApi(page);
    await page.goto("/admin/trades");
    await expect(page.getByTestId("admin-trades-page")).toBeVisible();
    await expect(page.getByTestId("trades-table")).toBeVisible();
    await expect(page.getByText("Plumber")).toBeVisible();
  });

  test("manager gets 403 on /admin/clients and /admin/trades", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await page.goto("/admin/clients");
    await expect(page.getByText("You do not have access to this page.")).toBeVisible();
    await page.goto("/admin/trades");
    await expect(page.getByText("You do not have access to this page.")).toBeVisible();
  });

  test("engineer gets 403 on /admin/clients and /admin/trades", async ({ page }) => {
    await mockAuthMe(page, "engineer");
    await page.goto("/admin/clients");
    await expect(page.getByText("You do not have access to this page.")).toBeVisible();
    await page.goto("/admin/trades");
    await expect(page.getByText("You do not have access to this page.")).toBeVisible();
  });

  test("admin can edit client and trade with mocked API", async ({ page }) => {
    await mockAuthMe(page, "admin");
    await mockClientsApi(page);
    await mockTradesApi(page);

    await page.goto("/admin/clients");
    await page.getByTestId("client-edit-11111111-1111-1111-1111-111111111111").click();
    await expect(page.getByTestId("client-edit-modal")).toBeVisible();
    await page.getByTestId("client-name-input").fill("Atkinson Updated");
    await page.getByTestId("client-save").click();
    await expect(page.getByTestId("client-edit-modal")).not.toBeVisible();

    await page.goto("/admin/trades");
    await page.getByTestId("trade-edit-22222222-2222-2222-2222-222222222222").click();
    await expect(page.getByTestId("trade-edit-modal")).toBeVisible();
    await page.getByTestId("trade-description-input").fill("Updated plumbing scope");
    await page.getByTestId("trade-save").click();
    await expect(page.getByTestId("trade-edit-modal")).not.toBeVisible();
  });
});
