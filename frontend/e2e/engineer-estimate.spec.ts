import { test, expect } from "@playwright/test";

const API = process.env.PLAYWRIGHT_API_URL ?? "http://127.0.0.1:8000";
const FRONTEND = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3001";

const MOCK_PRODUCTS = [
  {
    id: 1,
    eworks_item_id: 1403,
    product_name: "Plant Room",
    product_code: "PR-0011",
    scope_of_work: "Inspect plant room equipment and report findings.",
    cost_price: "0",
    selling_price: "100",
    margin: "0",
    tax_rate_id: "3",
    track_stock_level: false,
    current_stock_level: "0",
    category: "General",
    category_id: 1,
    type: "Products",
    type_id: 1,
    eworks_created_on: null,
    eworks_last_updated_on: null,
  },
];

function futureExpiryIso(days = 30) {
  const date = new Date();
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().replace(/\.\d{3}Z$/, "Z");
}

async function mockProductsApi(page: import("@playwright/test").Page) {
  let productPostCount = 0;
  await page.route("**/api/v1/products**", async (route) => {
    if (route.request().method() === "POST") {
      productPostCount += 1;
    }
    const url = new URL(route.request().url());
    const idMatch = url.pathname.match(/\/products\/(\d+)$/);
    if (idMatch) {
      const product = MOCK_PRODUCTS.find((p) => p.id === Number(idMatch[1]));
      await route.fulfill({
        status: product ? 200 : 404,
        contentType: "application/json",
        body: JSON.stringify(
          product ? { success: true, data: product } : { success: false, detail: "Not found" },
        ),
      });
      return;
    }
    if (route.request().method() === "POST") {
      await route.fulfill({
        status: 405,
        contentType: "application/json",
        body: JSON.stringify({ success: false, detail: "Method not allowed" }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: MOCK_PRODUCTS,
        meta: { total: MOCK_PRODUCTS.length, page: 1, per_page: 100, last_page: 1 },
      }),
    });
  });
  return {
    getProductPostCount: () => productPostCount,
  };
}

async function mockQuestionnaireSessionRoutes(
  page: import("@playwright/test").Page,
  sessionId: string,
  sessionToken: string,
  options: {
    uiStep?: number;
    step2?: Record<string, unknown> | null;
    onPatch?: (body: Record<string, unknown>) => void;
  } = {},
) {
  let savedStep2: Record<string, unknown> | null = options.step2 ?? null;
  const uiStep = options.uiStep ?? 1;

  await page.route("**/api/v1/trades**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: { items: [{ id: "trade-1", name: "Carpenter", is_active: true }] },
      }),
    });
  });

  await page.route(`**/api/v1/calculation-session/${sessionId}**`, async (route) => {
    const method = route.request().method();
    if (method === "PATCH") {
      const patchBody = route.request().postDataJSON() as Record<string, unknown>;
      if (patchBody.step2) {
        savedStep2 = patchBody.step2 as Record<string, unknown>;
      }
      options.onPatch?.(patchBody);
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, data: { saved: true } }),
      });
      return;
    }
    if (method !== "GET") {
      await route.fallback();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data: {
          session_id: sessionId,
          session_token: sessionToken,
          step1: {
            quote_number: "Q-E2E-CUSTOM",
            job_number: "JOB-E2E-CUSTOM",
            client_name: "Test Client",
            trade_name: "Carpenter",
            property_address: "1 Test Street",
            quote_description: "",
            findings_report: "",
            congestion_required: false,
            congestion_amount: 0,
            travel: 0,
          },
          step2: savedStep2,
          resolved: {
            client_id: "client-1",
            trade_id: "trade-1",
            rule_version: "1",
            formula_source: "none",
            client_fee_pct: 0,
          },
          expires_at: futureExpiryIso(),
          ui_state: { current_step: uiStep, max_reachable_step: uiStep },
          resumed: true,
        },
      }),
    });
  });

  return {
    getSavedStep2: () => savedStep2,
  };
}

async function openStep2(page: import("@playwright/test").Page, sessionId: string, sessionToken: string) {
  await page.goto(`${FRONTEND}/eworks/calculate?session_id=${sessionId}&token=${sessionToken}`, {
    waitUntil: "networkidle",
    timeout: 60000,
  });
  await expect(page.getByText("Step 2 of 3: Estimating Questionnaire")).toBeVisible({ timeout: 15000 });
}

async function expandWorkBlock(page: import("@playwright/test").Page, workIndex = 0) {
  const toggle = page.getByTestId(`work-block-toggle-${workIndex}`);
  if ((await toggle.getAttribute("aria-expanded")) !== "true") {
    await toggle.click();
  }
}

async function openProductCombobox(page: import("@playwright/test").Page, workIndex = 0) {
  await expandWorkBlock(page, workIndex);
  const block = page.getByTestId(`work-block-${workIndex}`);
  const changeProduct = block.getByTestId(`change-product-${workIndex}`);
  if (await changeProduct.isVisible().catch(() => false)) {
    await changeProduct.click();
  }
  const combobox = block.getByRole("combobox").first();
  await combobox.click();
  return combobox;
}

async function selectProduct(page: import("@playwright/test").Page, productLabel: string, workIndex = 0) {
  const combobox = await openProductCombobox(page, workIndex);
  await combobox.fill(productLabel.split(" · ")[0]);
  await page.getByRole("option", { name: productLabel }).click();
}

async function startCustomScopeDraft(page: import("@playwright/test").Page, workIndex = 0) {
  const combobox = await openProductCombobox(page, workIndex);
  await page.getByTestId("product-add-custom-scope").click();
  const dialog = page.getByTestId("work-mode-switch-dialog");
  if (await dialog.isVisible().catch(() => false)) {
    await page.getByTestId("work-mode-switch-dialog-confirm").click();
  }
  await expect(page.getByTestId(`custom-scope-draft-${workIndex}`)).toBeVisible();
}

test.describe("engineer estimate questionnaire — custom scope", () => {
  test("selecting existing product behaves as before", async ({ page }) => {
    const sessionId = "e2e-custom-product-select";
    const sessionToken = "e2e-custom-product-select-token";
    await mockProductsApi(page);
    await mockQuestionnaireSessionRoutes(page, sessionId, sessionToken);
    await openStep2(page, sessionId, sessionToken);

    await selectProduct(page, "Plant Room · PR-0011", 0);
    await expect(page.getByTestId("work-tab-product-0")).toHaveAttribute("aria-selected", "false");
    await expect(page.getByTestId("work-tab-scope-0")).toHaveAttribute("aria-selected", "true");
    await expect(page.getByTestId("work-scope-0")).toBeVisible();
    await expect(page.getByTestId("work-block-0")).toContainText("Plant Room");
  });

  test("selecting Product not listed does not immediately switch tabs", async ({ page }) => {
    const sessionId = "e2e-custom-no-tab-jump";
    const sessionToken = "e2e-custom-no-tab-jump-token";
    await mockProductsApi(page);
    await mockQuestionnaireSessionRoutes(page, sessionId, sessionToken);
    await openStep2(page, sessionId, sessionToken);

    await startCustomScopeDraft(page, 0);
    await expect(page.getByTestId("work-tab-product-0")).toHaveAttribute("aria-selected", "true");
    await expect(page.getByTestId("work-tab-scope-0")).toHaveAttribute("aria-selected", "false");
    await expect(page.getByTestId("work-panel-product-0")).toBeVisible();
    await expect(page.getByTestId("work-scope-0")).toHaveCount(0);
  });

  test("custom title input appears after choosing Product not listed", async ({ page }) => {
    const sessionId = "e2e-custom-input-visible";
    const sessionToken = "e2e-custom-input-visible-token";
    await mockProductsApi(page);
    await mockQuestionnaireSessionRoutes(page, sessionId, sessionToken);
    await openStep2(page, sessionId, sessionToken);

    await startCustomScopeDraft(page, 0);
    await expect(page.getByTestId("custom-scope-title-0")).toBeVisible();
    await expect(page.getByTestId("custom-scope-description-0")).toBeVisible();
  });

  test("Continue to Scope is disabled until title entered", async ({ page }) => {
    const sessionId = "e2e-custom-continue-disabled";
    const sessionToken = "e2e-custom-continue-disabled-token";
    await mockProductsApi(page);
    await mockQuestionnaireSessionRoutes(page, sessionId, sessionToken);
    await openStep2(page, sessionId, sessionToken);

    await startCustomScopeDraft(page, 0);
    const continueButton = page.getByTestId("custom-scope-continue-0");
    await expect(continueButton).toBeDisabled();
    await page.getByTestId("custom-scope-title-0").fill("Bespoke cladding repair");
    await expect(continueButton).toBeEnabled();
  });

  test("after title and continue, Scope tab opens", async ({ page }) => {
    const sessionId = "e2e-custom-continue-scope";
    const sessionToken = "e2e-custom-continue-scope-token";
    await mockProductsApi(page);
    await mockQuestionnaireSessionRoutes(page, sessionId, sessionToken);
    await openStep2(page, sessionId, sessionToken);

    await startCustomScopeDraft(page, 0);
    await page.getByTestId("custom-scope-title-0").fill("Bespoke cladding repair");
    await page.getByTestId("custom-scope-description-0").fill("Repair damaged cladding on north elevation.");
    await page.getByTestId("custom-scope-continue-0").click();

    await expect(page.getByTestId("work-tab-scope-0")).toHaveAttribute("aria-selected", "true");
    await expect(page.getByTestId("work-scope-0")).toBeVisible();
    await expect(page.getByTestId("work-scope-0")).toHaveValue("Repair damaged cladding on north elevation.");
    await expect(page.getByTestId("work-block-0")).toContainText("Bespoke cladding repair");
  });

  test("custom title persists after auto-save and reload", async ({ page }) => {
    const sessionId = "e2e-custom-autosave-reload";
    const sessionToken = "e2e-custom-autosave-reload-token";
    const patchBodies: Record<string, unknown>[] = [];
    await mockProductsApi(page);
    await mockQuestionnaireSessionRoutes(page, sessionId, sessionToken, {
      onPatch: (body) => patchBodies.push(body),
    });
    await openStep2(page, sessionId, sessionToken);

    await startCustomScopeDraft(page, 0);
    await page.getByTestId("custom-scope-title-0").fill("One-off roof hatch");
    await page.getByTestId("custom-scope-continue-0").click();
    await page.getByTestId("work-scope-0").fill("Supply and fit custom roof hatch.");

    await expect
      .poll(() => {
        const step2 = patchBodies.at(-1)?.step2 as
          | { works?: Array<{ is_custom_scope?: boolean; custom_title?: string }> }
          | undefined;
        return step2?.works?.[0]?.is_custom_scope === true && step2?.works?.[0]?.custom_title === "One-off roof hatch";
      })
      .toBeTruthy();

    await page.reload({ waitUntil: "networkidle" });
    await expandWorkBlock(page, 0);
    await expect(page.getByTestId("work-block-0")).toContainText("One-off roof hatch");
    await page.getByTestId("work-tab-product-0").click();
    await expect(page.getByTestId("custom-scope-summary-0")).toContainText("Custom: One-off roof hatch");
  });

  test("no global product is created when adding custom scope", async ({ page }) => {
    const sessionId = "e2e-custom-no-product-create";
    const sessionToken = "e2e-custom-no-product-create-token";
    const productsApi = await mockProductsApi(page);
    await mockQuestionnaireSessionRoutes(page, sessionId, sessionToken);
    await openStep2(page, sessionId, sessionToken);

    await startCustomScopeDraft(page, 0);
    await page.getByTestId("custom-scope-title-0").fill("Temporary scaffold access");
    await page.getByTestId("custom-scope-continue-0").click();
    await page.getByTestId("work-scope-0").fill("Provide temporary scaffold access.");

    expect(productsApi.getProductPostCount()).toBe(0);
  });

  test("cancel restores product dropdown to no selection state", async ({ page }) => {
    const sessionId = "e2e-custom-cancel";
    const sessionToken = "e2e-custom-cancel-token";
    await mockProductsApi(page);
    await mockQuestionnaireSessionRoutes(page, sessionId, sessionToken);
    await openStep2(page, sessionId, sessionToken);

    await startCustomScopeDraft(page, 0);
    await page.getByTestId("custom-scope-title-0").fill("Should not persist");
    await page.getByTestId("custom-scope-cancel-0").click();

    await expect(page.getByTestId("custom-scope-draft-0")).toHaveCount(0);
    const combobox = page.getByTestId("work-block-0").getByRole("combobox").first();
    await expect(combobox).toHaveValue("");
    await expect(page.getByTestId("work-block-0")).toContainText("Select product");
  });

  test("existing work block values are not wiped when adding custom scope", async ({ page }) => {
    const sessionId = "e2e-custom-preserve-values";
    const sessionToken = "e2e-custom-preserve-values-token";
    await mockProductsApi(page);
    await mockQuestionnaireSessionRoutes(page, sessionId, sessionToken);
    await openStep2(page, sessionId, sessionToken);

    await expandWorkBlock(page, 0);
    await page.getByTestId("work-tab-scope-0").click();
    await page.getByTestId("work-scope-0").fill("Existing scope text should remain.");
    await page.getByTestId("work-tab-product-0").click();

    const combobox = page.getByTestId("work-block-0").getByRole("combobox").first();
    await combobox.click();
    await page.getByTestId("product-add-custom-scope").click();
    await page.getByTestId("work-mode-switch-dialog-confirm").click();
    await expect(page.getByTestId("custom-scope-draft-0")).toBeVisible();

    await page.getByTestId("custom-scope-title-0").fill("Custom retained scope");
    await page.getByTestId("custom-scope-continue-0").click();

    await expect(page.getByTestId("work-scope-0")).toHaveValue("Existing scope text should remain.");
  });
});
