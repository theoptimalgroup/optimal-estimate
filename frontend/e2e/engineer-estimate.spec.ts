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
    sharedStep2?: Record<string, unknown> | null;
    onPatch?: (body: Record<string, unknown>) => void;
    onSubmit?: (body: Record<string, unknown>) => void;
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
    const url = route.request().url();
    if (method === "POST" && url.endsWith("/submit")) {
      const submitBody = route.request().postDataJSON() as Record<string, unknown>;
      options.onSubmit?.(submitBody);
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ success: true, data: { submitted: true } }),
      });
      return;
    }
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
          shared_step2: options.sharedStep2 ?? null,
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

function workBlock(page: import("@playwright/test").Page, workIndex: number) {
  return page.getByTestId(`work-block-${workIndex}`);
}

async function expandWorkBlock(page: import("@playwright/test").Page, workIndex = 0) {
  const toggle = page.getByTestId(`work-block-toggle-${workIndex}`);
  if ((await toggle.getAttribute("aria-expanded")) !== "true") {
    await toggle.click();
  }
}

async function openProductCombobox(page: import("@playwright/test").Page, workIndex = 0) {
  await expandWorkBlock(page, workIndex);
  const block = workBlock(page, workIndex);
  const changeProduct = block.getByTestId(`change-product-${workIndex}`);
  if (await changeProduct.isVisible().catch(() => false)) {
    await changeProduct.click();
  }
  const combobox = block.getByTestId("product-combobox");
  await combobox.click();
  return combobox;
}

async function selectProduct(page: import("@playwright/test").Page, productLabel: string, workIndex = 0) {
  const combobox = await openProductCombobox(page, workIndex);
  await combobox.fill(productLabel.split(" · ")[0]);
  await workBlock(page, workIndex).getByTestId("product-option-existing").filter({ hasText: productLabel }).click();
}

async function startCustomScopeDraft(page: import("@playwright/test").Page, workIndex = 0) {
  await openProductCombobox(page, workIndex);
  await workBlock(page, workIndex).getByTestId("product-option-custom-scope").click();
  const dialog = page.getByTestId("work-mode-switch-dialog");
  if (await dialog.isVisible().catch(() => false)) {
    await page.getByTestId("work-mode-switch-dialog-confirm").click();
  }
  await expect(workBlock(page, workIndex).getByTestId(`custom-scope-draft-${workIndex}`)).toBeVisible();
}

test.describe("engineer estimate questionnaire — custom scope", () => {
  test("selecting existing product behaves as before", async ({ page }) => {
    const sessionId = "e2e-custom-product-select";
    const sessionToken = "e2e-custom-product-select-token";
    await mockProductsApi(page);
    await mockQuestionnaireSessionRoutes(page, sessionId, sessionToken);
    await openStep2(page, sessionId, sessionToken);

    await selectProduct(page, "Plant Room · PR-0011", 0);
    const block = workBlock(page, 0);
    await expect(block.getByTestId("tab-product")).toBeVisible();
    await expect(block.getByTestId("tab-scope")).toBeVisible();
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
    const block = workBlock(page, 0);
    await expect(block.getByTestId("custom-scope-title-input")).toBeVisible();
    await expect(block.getByTestId("custom-scope-description-input")).toBeVisible();
  });

  test("Continue to Scope is disabled until title entered", async ({ page }) => {
    const sessionId = "e2e-custom-continue-disabled";
    const sessionToken = "e2e-custom-continue-disabled-token";
    await mockProductsApi(page);
    await mockQuestionnaireSessionRoutes(page, sessionId, sessionToken);
    await openStep2(page, sessionId, sessionToken);

    await startCustomScopeDraft(page, 0);
    const block = workBlock(page, 0);
    const continueButton = block.getByTestId("custom-scope-continue-button");
    await expect(continueButton).toBeDisabled();
    await block.getByTestId("custom-scope-title-input").fill("Bespoke cladding repair");
    await expect(continueButton).toBeEnabled();
  });

  test("after title and continue, Scope tab opens", async ({ page }) => {
    const sessionId = "e2e-custom-continue-scope";
    const sessionToken = "e2e-custom-continue-scope-token";
    await mockProductsApi(page);
    await mockQuestionnaireSessionRoutes(page, sessionId, sessionToken);
    await openStep2(page, sessionId, sessionToken);

    await startCustomScopeDraft(page, 0);
    const block = workBlock(page, 0);
    await block.getByTestId("custom-scope-title-input").fill("Bespoke cladding repair");
    await block.getByTestId("custom-scope-description-input").fill("Repair damaged cladding on north elevation.");
    await block.getByTestId("custom-scope-continue-button").click();

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
    const block = workBlock(page, 0);
    await block.getByTestId("custom-scope-title-input").fill("One-off roof hatch");
    await block.getByTestId("custom-scope-continue-button").click();
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
    const block = workBlock(page, 0);
    await block.getByTestId("custom-scope-title-input").fill("Temporary scaffold access");
    await block.getByTestId("custom-scope-continue-button").click();
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
    const block = workBlock(page, 0);
    await block.getByTestId("custom-scope-title-input").fill("Should not persist");
    await block.getByTestId("custom-scope-cancel-button").click();

    await expect(block.getByTestId(`custom-scope-draft-0`)).toHaveCount(0);
    const combobox = block.getByTestId("product-combobox");
    await expect(combobox).toHaveValue("");
    await expect(block).toContainText("Select product");
  });

  test("existing work block values are not wiped when adding custom scope", async ({ page }) => {
    const sessionId = "e2e-custom-preserve-values";
    const sessionToken = "e2e-custom-preserve-values-token";
    await mockProductsApi(page);
    await mockQuestionnaireSessionRoutes(page, sessionId, sessionToken);
    await openStep2(page, sessionId, sessionToken);

    await expandWorkBlock(page, 0);
    const block = workBlock(page, 0);
    await page.getByTestId("work-tab-scope-0").click();
    await page.getByTestId("work-scope-0").fill("Existing scope text should remain.");
    await page.getByTestId("work-tab-product-0").click();

    await block.getByTestId("product-combobox").click();
    await block.getByTestId("product-option-custom-scope").click();
    await page.getByTestId("work-mode-switch-dialog-confirm").click();
    await expect(block.getByTestId("custom-scope-draft-0")).toBeVisible();

    await block.getByTestId("custom-scope-title-input").fill("Custom retained scope");
    await block.getByTestId("custom-scope-continue-button").click();

    await expect(page.getByTestId("work-scope-0")).toHaveValue("Existing scope text should remain.");
  });
});

function defaultMaterialsBlock() {
  return [
    {
      supplier_name: "Supplier 1",
      links: [{ link: "", quantity: 0, cost: 0 }],
    },
  ];
}

function workBlockWithAttachment(
  work: Record<string, unknown>,
  attachment: Record<string, unknown>,
) {
  return {
    works: [
      {
        scope: "",
        selected_product_id: null,
        is_custom_scope: false,
        custom_title: "",
        eworks_item_id: null,
        product_name: "",
        product_code: "",
        product_quantity: 1,
        product_unit_price: 0,
        product_total_price: 0,
        scope_from_product: false,
        materials_to_order: defaultMaterialsBlock(),
        skill_required: "Carpenter",
        engineers_required: false,
        engineers_needed: 0,
        engineer_time_unit: "hours",
        engineer_time_value: 1.5,
        labour_required: false,
        labour_needed: 0,
        labour_time_value: 1,
        attachments: [attachment],
        markup_value: 20,
        ...work,
      },
    ],
  };
}

test.describe("engineer estimate questionnaire — attachment context", () => {
  test("Photos & Videos shows product name and truncated scope labels", async ({ page }) => {
    const sessionId = "e2e-attachment-context-product";
    const sessionToken = "e2e-attachment-context-product-token";
    const longScope = `Repair ${"damaged cladding ".repeat(30)}`.trim();
    await mockProductsApi(page);
    await mockQuestionnaireSessionRoutes(page, sessionId, sessionToken, {
      uiStep: 1,
      step2: workBlockWithAttachment(
        {
          scope: longScope,
          selected_product_id: 1,
          eworks_item_id: 1403,
          product_name: "74 MOANOR ROAD",
          product_code: "PR-0011",
          product_quantity: 1,
          product_unit_price: 100,
          product_total_price: 100,
        },
        {
          id: "att-e2e-product-scope",
          file_name: "site-photo.jpg",
          size: 2048,
          media_type: "photo",
          stored_name: "stored.jpg",
          product_name: "74 MOANOR ROAD",
          is_custom_scope: false,
          scope_snapshot: longScope,
          work_block_label: "74 MOANOR ROAD · PR-0011",
        },
      ),
    });
    await openStep2(page, sessionId, sessionToken);
    await expandWorkBlock(page, 0);
    await page.getByTestId("work-tab-scope-0").click();

    const productContext = page.getByTestId("attachment-product-context-0");
    const scopeContext = page.getByTestId("attachment-scope-context-0");
    await expect(productContext).toHaveText("Product: 74 MOANOR ROAD");
    await expect(scopeContext).not.toContainText(longScope);
    expect((await scopeContext.textContent())?.length ?? 0).toBeLessThan(120);
    await expect(page.getByTestId("work-scope-0")).toHaveValue(longScope);
    await expect(page.getByText("site-photo.jpg")).toBeVisible();
  });

  test("Photos & Videos shows custom scope title without full scope snapshot", async ({ page }) => {
    const sessionId = "e2e-attachment-context-custom";
    const sessionToken = "e2e-attachment-context-custom-token";
    const longScope = "Investigate leak and repair membrane. ".repeat(12).trim();
    await mockProductsApi(page);
    await mockQuestionnaireSessionRoutes(page, sessionId, sessionToken, {
      uiStep: 1,
      step2: workBlockWithAttachment(
        {
          scope: longScope,
          selected_product_id: null,
          is_custom_scope: true,
          custom_title: "Roof hatch",
          product_name: "Roof hatch",
        },
        {
          id: "att-e2e-custom-scope",
          file_name: "hatch-photo.jpg",
          size: 2048,
          media_type: "photo",
          stored_name: "stored.jpg",
          is_custom_scope: true,
          custom_scope_title: "Roof hatch",
          product_name: "Roof hatch",
          scope_snapshot: longScope,
          work_block_label: "Roof hatch",
        },
      ),
    });
    await openStep2(page, sessionId, sessionToken);
    await expandWorkBlock(page, 0);
    await page.getByTestId("work-tab-scope-0").click();

    const productContext = page.getByTestId("attachment-product-context-0");
    const scopeContext = page.getByTestId("attachment-scope-context-0");
    await expect(productContext).toHaveText("Custom: Roof hatch");
    await expect(scopeContext).toHaveText("Scope: Roof hatch");
    await expect(scopeContext).not.toContainText("Investigate leak");
    await expect(page.getByTestId("work-scope-0")).toHaveValue(longScope);
  });

  test("engineer B submits with shared product without reselecting product", async ({ page }) => {
    const sessionId = "e2e-shared-product-submit";
    const sessionToken = "e2e-shared-product-submit-token";
    const sharedWorkBlock = {
      scope: "Shared dishwasher scope from engineer A",
      selected_product_id: 1,
      product_name: "Plant Room",
      product_code: "PR-0011",
      product_quantity: 1,
      product_unit_price: 100,
      product_total_price: 100,
      time_frame: "1.5 hours",
      engineers_required: true,
      engineers_needed: 1,
      materials_to_order: defaultMaterialsBlock(),
      markup_value: 20,
      attachments: [],
    };
    let submitBody: Record<string, unknown> | null = null;

    await mockProductsApi(page);
    await mockQuestionnaireSessionRoutes(page, sessionId, sessionToken, {
      step2: { works: [sharedWorkBlock] },
      sharedStep2: {
        updated_by_name: "Engineer A",
        updated_at: "2026-06-10T10:00:00Z",
      },
      onSubmit: (body) => {
        submitBody = body;
      },
    });

    await openStep2(page, sessionId, sessionToken);
    await expandWorkBlock(page, 0);

    await expect(page.getByText("Plant Room")).toBeVisible();
    await expect(page.getByTestId("product-combobox")).toHaveCount(0);

    await page.getByRole("button", { name: "Submit", exact: true }).click();

    await expect(page.getByText("Step 3 of 3: Submitted")).toBeVisible({ timeout: 15000 });
    await expect(page.getByText("Select a product or add custom scope")).toHaveCount(0);
    expect(submitBody).not.toBeNull();
    const submittedWorks = ((submitBody as { step2?: { works?: Array<Record<string, unknown>> } }).step2?.works ??
      []) as Array<Record<string, unknown>>;
    expect(submittedWorks[0]?.selected_product_id).toBe(1);
    expect(submittedWorks[0]?.product_name).toBe("Plant Room");
    expect(submittedWorks[0]?.scope).toBe("Shared dishwasher scope from engineer A");
  });

  test("engineer B submits with shared scope-only work without selecting product", async ({ page }) => {
    const sessionId = "e2e-shared-scope-only-submit";
    const sessionToken = "e2e-shared-scope-only-submit-token";
    const sharedScope = "Replace damaged kitchen tap and check pipework";
    const sharedWorkBlock = {
      scope: sharedScope,
      selected_product_id: null,
      is_custom_scope: false,
      custom_title: "",
      product_name: "",
      time_frame: "1.5 hours",
      engineers_required: true,
      engineers_needed: 1,
      materials_to_order: defaultMaterialsBlock(),
      markup_value: 20,
      attachments: [],
    };
    let submitBody: Record<string, unknown> | null = null;

    await mockProductsApi(page);
    await mockQuestionnaireSessionRoutes(page, sessionId, sessionToken, {
      step2: { works: [sharedWorkBlock] },
      sharedStep2: {
        updated_by_name: "Engineer A",
        updated_at: "2026-06-10T10:00:00Z",
      },
      onSubmit: (body) => {
        submitBody = body;
      },
    });

    await openStep2(page, sessionId, sessionToken);
    await expandWorkBlock(page, 0);

    await expect(page.getByTestId("work-block-0")).toContainText(sharedScope);
    await page.getByTestId("work-tab-product-0").click();
    await expect(page.getByTestId("custom-scope-summary-0")).toContainText(`Custom: ${sharedScope}`);
    await expect(page.getByTestId("product-combobox")).toHaveCount(0);

    await page.getByRole("button", { name: "Submit", exact: true }).click();

    await expect(page.getByText("Step 3 of 3: Submitted")).toBeVisible({ timeout: 15000 });
    await expect(page.getByText("Select a product or add custom scope")).toHaveCount(0);
    expect(submitBody).not.toBeNull();
    const submittedWorks = ((submitBody as { step2?: { works?: Array<Record<string, unknown>> } }).step2?.works ??
      []) as Array<Record<string, unknown>>;
    expect(submittedWorks[0]?.is_custom_scope).toBe(true);
    expect(submittedWorks[0]?.custom_title).toBe(sharedScope);
    expect(submittedWorks[0]?.scope).toBe(sharedScope);
  });
});
