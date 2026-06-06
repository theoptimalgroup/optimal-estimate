import { test, expect, type Page } from "@playwright/test";

const mockPublicQuote = {
  quote_ref: "Q-1001",
  client_name: "Atkinson McLeod",
  trade_name: "Painter",
  status: "submitted",
  scope_of_work: "Repaint hallway and landing",
  works: [
    {
      title: "Painting",
      product_name: "Painting",
      scope: "Repaint hallway and landing",
      description: "Two coats emulsion",
      materials_summary: "Paint supplies",
      attachments: [],
    },
  ],
  summary: {
    work_charges: 800,
    materials: 200,
    additional_charges: 50,
    subtotal: 1050,
    vat: 210,
    total: 1260,
  },
  terms: "This quote is provided for review purposes.",
  created_at: "2026-06-01T10:00:00Z",
  submitted_at: "2026-06-01T12:00:00Z",
  acceptance: {
    accepted: false,
    accepted_at: null,
    name: null,
  },
};

const mockAcceptedQuote = {
  ...mockPublicQuote,
  acceptance: {
    accepted: true,
    accepted_at: "2026-06-02T14:30:00Z",
    name: "Jane Client",
  },
};

async function mockPublicQuoteApi(page: Page, quote = mockPublicQuote) {
  await page.route("**/api/v1/client-quotes/public/test-public-token", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, data: quote }),
      });
      return;
    }
    await route.continue();
  });
}

function mockUser(role: "manager" | "admin" | "estimator") {
  return {
    id: `dev-${role}`,
    email: `${role}@example.com`,
    name: `Dev ${role}`,
    role,
    is_active: true,
    auth_provider: "dev",
  };
}

async function mockAuthMe(page: Page, role: "manager" | "admin" | "estimator") {
  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ success: true, data: mockUser(role) }),
    });
  });
}

async function assertForbiddenStringsAbsent(page: Page) {
  await expect(page.getByText("internal notes")).toHaveCount(0);
  await expect(page.getByText("profit")).toHaveCount(0);
  await expect(page.getByText("margin")).toHaveCount(0);
  await expect(page.getByText("cost price")).toHaveCount(0);
  await expect(page.getByText("formula")).toHaveCount(0);
  await expect(page.getByText("denominator")).toHaveCount(0);
  await expect(page.getByText("session_token")).toHaveCount(0);
  await expect(page.getByText("api_key")).toHaveCount(0);
  await expect(page.getByText("dashboard_password")).toHaveCount(0);
}

test.describe("Client public quote page", () => {
  test("public quote page loads mocked sanitized quote without AppShell", async ({ page }) => {
    await mockPublicQuoteApi(page);
    await page.goto("/client/quote/test-public-token");
    await expect(page.getByTestId("client-quote-page")).toBeVisible();
    await expect(page.getByTestId("client-quote-summary")).toBeVisible();
    await expect(page.getByText("Q-1001")).toBeVisible();
    await expect(page.getByTestId("client-quote-accept-form")).toBeVisible();
    await assertForbiddenStringsAbsent(page);
    await expect(page.locator('[data-testid="app-shell"]')).toHaveCount(0);
  });

  test("public quote page shows accept form and user can accept quote", async ({ page }) => {
    let currentQuote = { ...mockPublicQuote };

    await page.route("**/api/v1/client-quotes/public/test-public-token", async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ success: true, data: currentQuote }),
        });
        return;
      }
      if (route.request().method() === "POST" && route.request().url().endsWith("/accept")) {
        currentQuote = {
          ...mockPublicQuote,
          acceptance: {
            accepted: true,
            accepted_at: "2026-06-02T14:30:00Z",
            name: "Jane Client",
          },
        };
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            success: true,
            data: {
              accepted: true,
              already_accepted: false,
              accepted_at: "2026-06-02T14:30:00Z",
              quote_ref: "Q-1001",
            },
          }),
        });
        return;
      }
      await route.continue();
    });

    await page.goto("/client/quote/test-public-token");
    await expect(page.getByTestId("client-quote-accept-form")).toBeVisible();
    await page.getByTestId("accept-name-input").fill("Jane Client");
    await page.getByTestId("accept-email-input").fill("client@example.com");
    await page.getByTestId("accept-confirm-checkbox").check();
    await page.getByTestId("accept-quote-button").click();
    await expect(page.getByTestId("client-quote-accepted")).toBeVisible();
    await expect(page.getByText("Quote accepted. Thank you.")).toBeVisible();
    await assertForbiddenStringsAbsent(page);
  });

  test("already accepted quote shows accepted state", async ({ page }) => {
    await mockPublicQuoteApi(page, mockAcceptedQuote);
    await page.goto("/client/quote/test-public-token");
    await expect(page.getByTestId("client-quote-accepted")).toBeVisible();
    await expect(page.getByText(/This quote was accepted on/i)).toBeVisible();
    await expect(page.getByTestId("client-quote-accept-form")).toHaveCount(0);
    await assertForbiddenStringsAbsent(page);
  });

  test("public quote page does not show eWorks sync status", async ({ page }) => {
    await mockPublicQuoteApi(page, mockAcceptedQuote);
    await page.goto("/client/quote/test-public-token");
    await expect(page.getByTestId("eworks-sync-panel")).toHaveCount(0);
    await expect(page.getByTestId("eworks-sync-badge")).toHaveCount(0);
    await assertForbiddenStringsAbsent(page);
  });
});

test.describe("Manager eWorks acceptance sync", () => {
  test("accepted quote shows eWorks sync status on manager review", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await page.route("**/api/v1/dashboard/quotes", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            quotes: [
              {
                session_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                session_token: "secret-session-token",
                quote_number: "Q-1001",
                job_number: "JOB-1",
                client_name: "Atkinson McLeod",
                trade_name: "Painter",
                submitted_at: "2026-06-01T12:00:00Z",
                final_total: 1260,
                internal_notes: "secret internal note",
                works: [],
                acceptance: {
                  accepted: true,
                  accepted_at: "2026-06-02T14:30:00Z",
                  name: "Jane Client",
                  email: "client@example.com",
                  notes: "Ready to proceed",
                  eworks_sync: {
                    status: "failed",
                    synced_at: null,
                    error: "eWorks unavailable",
                    attempts: 1,
                  },
                },
              },
            ],
          },
        }),
      });
    });

    await page.goto("/manager/review/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa");
    await expect(page.getByTestId("eworks-sync-panel")).toBeVisible();
    await expect(page.getByTestId("eworks-sync-badge")).toContainText("Sync failed");
    await expect(page.getByTestId("eworks-sync-error")).toContainText("eWorks unavailable");
    await expect(page.getByTestId("eworks-sync-retry-button")).toBeVisible();
    await expect(page.getByText("secret-session-token")).toHaveCount(0);
    await expect(page.getByText("api_key")).toHaveCount(0);
  });

  test("retry button calls mocked API and updates status", async ({ page }) => {
    await mockAuthMe(page, "manager");
    let syncStatus = "failed";

    await page.route("**/api/v1/dashboard/quotes", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            quotes: [
              {
                session_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                session_token: "secret-session-token",
                quote_number: "Q-1001",
                job_number: "JOB-1",
                client_name: "Atkinson McLeod",
                trade_name: "Painter",
                submitted_at: "2026-06-01T12:00:00Z",
                final_total: 1260,
                works: [],
                acceptance: {
                  accepted: true,
                  accepted_at: "2026-06-02T14:30:00Z",
                  name: "Jane Client",
                  email: "client@example.com",
                  eworks_sync: {
                    status: syncStatus,
                    synced_at: syncStatus === "success" ? "2026-06-02T15:00:00Z" : null,
                    error: syncStatus === "failed" ? "eWorks unavailable" : null,
                    attempts: 1,
                  },
                },
              },
            ],
          },
        }),
      });
    });

    await page.route("**/api/v1/client-quotes/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/sync-acceptance-eworks", async (route) => {
      syncStatus = "success";
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            status: "success",
            synced_at: "2026-06-02T15:00:00Z",
            error: null,
            attempts: 2,
          },
        }),
      });
    });

    await page.goto("/manager/review/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa");
    await page.getByTestId("eworks-sync-retry-button").click();
    await expect(page.getByTestId("eworks-sync-badge")).toContainText("Synced to eWorks");
  });
});

test.describe("Manager client link", () => {
  test("manager review page shows client link panel and acceptance badge", async ({ page }) => {
    await mockAuthMe(page, "manager");
    await page.route("**/api/v1/dashboard/quotes", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            quotes: [
              {
                session_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                session_token: "secret-session-token",
                quote_number: "Q-1001",
                job_number: "JOB-1",
                client_name: "Atkinson McLeod",
                trade_name: "Painter",
                submitted_at: "2026-06-01T12:00:00Z",
                final_total: 1260,
                internal_notes: "secret internal note",
                works: [],
                acceptance: {
                  accepted: true,
                  accepted_at: "2026-06-02T14:30:00Z",
                  name: "Jane Client",
                  email: "client@example.com",
                  notes: "Ready to proceed",
                },
              },
            ],
          },
        }),
      });
    });
    await page.route("**/api/v1/client-quotes/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/public-link", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            public_url: "/client/quote/test-public-token",
            public_token: "test-public-token",
            expires_at: null,
          },
        }),
      });
    });

    await page.goto("/manager/review/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa");
    await expect(page.getByTestId("client-link-panel")).toBeVisible();
    await expect(page.getByTestId("quote-acceptance-panel")).toBeVisible();
    await expect(page.getByTestId("quote-accepted-badge")).toBeVisible();
    await page.getByRole("button", { name: "Create client link" }).click();
    await expect(page.getByTestId("client-link-url")).toContainText("/client/quote/test-public-token");
    await expect(page.getByText("secret-session-token")).toHaveCount(0);
  });
});

test.describe("Estimator quote acceptance", () => {
  test("estimator quote detail shows accepted badge when mocked data includes acceptance", async ({ page }) => {
    await mockAuthMe(page, "estimator");
    await page.route("**/api/v1/estimator/quotes/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          data: {
            session_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            quote_ref: "Q-1001",
            job_number: "JOB-1",
            client_name: "Atkinson McLeod",
            trade_name: "Painter",
            status: "submitted",
            total: 1260,
            work_count: 1,
            property_address: "1 Test Street",
            created_at: "2026-06-01T10:00:00Z",
            updated_at: "2026-06-01T12:00:00Z",
            submitted_at: "2026-06-01T12:00:00Z",
            is_reopened: false,
            can_resume: false,
            acceptance: {
              accepted: true,
              accepted_at: "2026-06-02T14:30:00Z",
              name: "Jane Client",
              email: "client@example.com",
              notes: null,
            },
          },
        }),
      });
    });

    await page.goto("/estimator/quotes/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa");
    await expect(page.getByTestId("estimator-quote-detail-page")).toBeVisible();
    await expect(page.getByTestId("quote-acceptance-panel")).toBeVisible();
    await expect(page.getByTestId("quote-accepted-badge")).toBeVisible();
  });
});
