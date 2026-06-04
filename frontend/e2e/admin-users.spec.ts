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

const mockUsers = [
  {
    id: "11111111-1111-1111-1111-111111111111",
    email: "admin@optimal.example",
    name: "Admin User",
    role: "admin",
    is_active: true,
    auth_provider: "local",
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-06-01T00:00:00Z",
  },
  {
    id: "22222222-2222-2222-2222-222222222222",
    email: "manager@optimal.example",
    name: "Manager User",
    role: "manager",
    is_active: true,
    auth_provider: "local",
    created_at: "2024-01-02T00:00:00Z",
    updated_at: "2024-06-02T00:00:00Z",
  },
];

async function mockUsersApi(page: Page) {
  await page.route("**/api/v1/users**", async (route) => {
    const url = new URL(route.request().url());
    const method = route.request().method();

    if (method === "GET" && url.pathname.endsWith("/users")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: mockUsers,
          meta: { total: 2, limit: 25, offset: 0 },
        }),
      });
      return;
    }

    if (method === "GET" && url.pathname.includes("/users/")) {
      const userId = url.pathname.split("/").pop();
      const user = mockUsers.find((item) => item.id === userId) ?? mockUsers[0];
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, data: user }),
      });
      return;
    }

    if (method === "PATCH") {
      const userId = url.pathname.split("/").pop();
      const body = route.request().postDataJSON() as { role?: string; name?: string; is_active?: boolean };
      const user = mockUsers.find((item) => item.id === userId) ?? mockUsers[0];
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            ...user,
            role: body.role ?? user.role,
            name: body.name ?? user.name,
            is_active: body.is_active ?? user.is_active,
          },
        }),
      });
      return;
    }

    await route.continue();
  });
}

test.describe("Admin users page", () => {
  test("admin can open /admin/users and see mocked users", async ({ page }) => {
    await mockAuthMe(page, "admin");
    await mockUsersApi(page);
    await page.goto("/admin/users");
    await expect(page.getByTestId("admin-users-page")).toBeVisible();
    await expect(page.getByTestId("users-table")).toBeVisible();
    await expect(page.getByText("Admin User")).toBeVisible();
    await expect(page.getByText("Manager User")).toBeVisible();
    await expect(page.getByText("password_hash")).toHaveCount(0);
  });

  test("manager gets 403 on /admin/users", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await page.goto("/admin/users");
    await expect(page.getByText("You do not have access to this page.")).toBeVisible();
  });

  test("engineer gets 403 on /admin/users", async ({ page }) => {
    await mockAuthMe(page, "engineer");
    await page.goto("/admin/users");
    await expect(page.getByText("You do not have access to this page.")).toBeVisible();
  });

  test("admin can open edit modal and change role with mocked API", async ({ page }) => {
    await mockAuthMe(page, "admin");
    await mockUsersApi(page);
    await page.goto("/admin/users");
    await page.getByTestId("user-edit-22222222-2222-2222-2222-222222222222").click();
    await expect(page.getByTestId("user-edit-modal")).toBeVisible();
    await page.getByTestId("user-role-select").selectOption("estimator");
    await page.getByTestId("user-save").click();
    await expect(page.getByTestId("user-edit-modal")).not.toBeVisible();
    await expect(page.getByText("password_hash")).toHaveCount(0);
  });
});
