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

const mockProducts = [
  {
    id: 1,
    eworks_item_id: 1403,
    product_name: "Plant Room",
    product_code: "PR-0011",
    scope_of_work: "Inspect plant room equipment",
    description: "Annual inspection",
    category: "Plumber",
    type: "Products",
    is_active: true,
    selling_price: "100.00",
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-06-01T00:00:00Z",
    eworks_created_on: null,
    eworks_last_updated_on: null,
  },
];

async function mockProductsApi(page: Page) {
  await page.route("**/api/v1/products**", async (route) => {
    const url = new URL(route.request().url());
    const method = route.request().method();

    if (method === "GET" && url.pathname.endsWith("/products")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: mockProducts,
          meta: { total: 1, page: 1, per_page: 25, last_page: 1 },
        }),
      });
      return;
    }

    if (method === "GET" && url.pathname.includes("/products/")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, data: mockProducts[0] }),
      });
      return;
    }

    if (method === "PATCH") {
      const body = route.request().postDataJSON() as { scope_of_work?: string };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: { ...mockProducts[0], scope_of_work: body.scope_of_work ?? mockProducts[0].scope_of_work },
        }),
      });
      return;
    }

    await route.continue();
  });
}

test.describe("Admin products page", () => {
  test("admin can open /admin/products and see mocked product table", async ({ page }) => {
    await mockAuthMe(page, "admin");
    await mockProductsApi(page);
    await page.goto("/admin/products");
    await expect(page.getByTestId("admin-products-page")).toBeVisible();
    await expect(page.getByTestId("products-table")).toBeVisible();
    await expect(page.getByText("Plant Room")).toBeVisible();
  });

  test("manager gets 403 on /admin/products", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await page.goto("/admin/products");
    await expect(page.getByText("You do not have access to this page.")).toBeVisible();
  });

  test("engineer gets 403 on /admin/products", async ({ page }) => {
    await mockAuthMe(page, "engineer");
    await page.goto("/admin/products");
    await expect(page.getByText("You do not have access to this page.")).toBeVisible();
  });

  test("admin can open edit panel and update scope with mocked API", async ({ page }) => {
    await mockAuthMe(page, "admin");
    await mockProductsApi(page);
    await page.goto("/admin/products");
    await page.getByTestId("product-edit-1").click();
    await expect(page.getByTestId("product-edit-modal")).toBeVisible();
    await page.getByTestId("product-scope-input").fill("Updated scope from admin");
    await page.getByTestId("product-save").click();
    await expect(page.getByTestId("product-edit-modal")).not.toBeVisible();
  });
});
