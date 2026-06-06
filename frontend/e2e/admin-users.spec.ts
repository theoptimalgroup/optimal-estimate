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
  const users = [...mockUsers];

  await page.route("**/api/v1/users**", async (route) => {
    const url = new URL(route.request().url());
    const method = route.request().method();

    if (method === "GET" && url.pathname.endsWith("/users")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: users,
          meta: { total: users.length, limit: 25, offset: 0 },
        }),
      });
      return;
    }

    if (method === "POST" && url.pathname.endsWith("/users")) {
      const body = route.request().postDataJSON() as {
        email?: string;
        name?: string;
        role?: string;
        is_active?: boolean;
      };
      const email = String(body.email ?? "").toLowerCase();
      if (users.some((item) => item.email.toLowerCase() === email)) {
        await route.fulfill({
          status: 400,
          contentType: "application/json",
          body: JSON.stringify({ detail: "A user with this email already exists" }),
        });
        return;
      }
      const created = {
        id: "33333333-3333-3333-3333-333333333333",
        email,
        name: String(body.name ?? ""),
        role: body.role ?? "estimator",
        is_active: body.is_active ?? true,
        auth_provider: "azure",
        created_at: "2024-06-03T00:00:00Z",
        updated_at: "2024-06-03T00:00:00Z",
      };
      users.push(created);
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, data: created }),
      });
      return;
    }

    if (method === "GET" && url.pathname.includes("/users/")) {
      const userId = url.pathname.split("/").pop();
      const user = users.find((item) => item.id === userId) ?? users[0];
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
      const user = users.find((item) => item.id === userId) ?? users[0];
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

  test("admin sees Add User button", async ({ page }) => {
    await mockAuthMe(page, "admin");
    await mockUsersApi(page);
    await page.goto("/admin/users");
    await expect(page.getByTestId("btn-add-user")).toBeVisible();
  });

  test("admin can create user with mocked API", async ({ page }) => {
    await mockAuthMe(page, "admin");
    await mockUsersApi(page);
    await page.goto("/admin/users");
    await page.getByTestId("btn-add-user").click();
    await expect(page.getByTestId("user-create-modal")).toBeVisible();
    await page.getByTestId("user-create-name-input").fill("Estimator User");
    await page.getByTestId("user-create-email-input").fill("estimator@optimal.example");
    await page.getByTestId("user-create-role-select").selectOption("estimator");
    await page.getByTestId("user-create-save").click();
    await expect(page.getByTestId("user-create-modal")).not.toBeVisible();
    await expect(page.getByTestId("user-create-success")).toContainText("estimator@optimal.example");
    await expect(page.getByText("Estimator User")).toBeVisible();
    await expect(page.getByText("password_hash")).toHaveCount(0);
  });

  test("admin sees duplicate email error when creating user", async ({ page }) => {
    await mockAuthMe(page, "admin");
    await mockUsersApi(page);
    await page.goto("/admin/users");
    await page.getByTestId("btn-add-user").click();
    await page.getByTestId("user-create-name-input").fill("Duplicate Admin");
    await page.getByTestId("user-create-email-input").fill("admin@optimal.example");
    await page.getByTestId("user-create-save").click();
    await expect(page.getByTestId("user-create-error")).toContainText("already exists");
  });
});
