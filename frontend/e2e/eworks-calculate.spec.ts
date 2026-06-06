import { test, expect } from "@playwright/test";
import crypto from "crypto";

const API = process.env.PLAYWRIGHT_API_URL ?? "http://127.0.0.1:8000";
const FRONTEND = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3001";

const HTML_SCOPE =
  "<strong>Inspect</strong> plant room<br />Check ventilation&nbsp;units<ol><li>Item one</li></ol>";

const MALFORMED_QUOTE_DESCRIPTION =
  '<span style="text-decoration: underline;"><strong>Access</strong></span>:&nbsp;<br /><br />' +
  '</span style="text-decoration: underline;"><strong>Quote</strong></span>: Please quote for Velux window replacement in the kitchen area.<br /><br />' +
  '</span style="text-decoration: underline;"><strong>Info</strong></span>: Booked by&nbsp;<br /><br /></span>' +
  '</span style="text-decoration: underline;"><strong>Contact</strong></span>: Miss Brenda - 07960696064';

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
  {
    id: 2,
    eworks_item_id: 1404,
    product_name: "Window Repair",
    product_code: "WR-001",
    scope_of_work: "",
    cost_price: "0",
    selling_price: "50",
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
  {
    id: 3,
    eworks_item_id: 1405,
    product_name: "<strong>HTML Product</strong>",
    product_code: "HTML-001",
    scope_of_work: HTML_SCOPE,
    cost_price: "0",
    selling_price: "75",
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

function makeSignedLink(payload: Record<string, unknown>, secret = "dev-secret-key-change-in-production") {
  const raw = Buffer.from(JSON.stringify(payload)).toString("base64url");
  const sig = crypto.createHmac("sha256", secret).update(raw).digest("hex");
  return { raw, sig };
}

async function mockProductsApi(page: import("@playwright/test").Page) {
  await page.route("**/api/v1/products**", async (route) => {
    const url = new URL(route.request().url());
    const idMatch = url.pathname.match(/\/products\/(\d+)$/);
    if (idMatch) {
      const product = MOCK_PRODUCTS.find((p) => p.id === Number(idMatch[1]));
      await route.fulfill({
        status: product ? 200 : 404,
        contentType: "application/json",
        body: JSON.stringify(
          product
            ? { success: true, data: product }
            : { success: false, detail: "Not found" },
        ),
      });
      return;
    }
    const search = (url.searchParams.get("search") ?? "").toLowerCase();
    const activeOnly = url.searchParams.get("active") === "true";
    let data = MOCK_PRODUCTS;
    if (activeOnly) {
      data = data.filter((p) => p.id !== 99);
    }
    if (search) {
      data = data.filter(
        (p) =>
          p.product_name.toLowerCase().includes(search) ||
          p.product_code.toLowerCase().includes(search) ||
          (p.scope_of_work ?? "").toLowerCase().includes(search),
      );
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        data,
        meta: { total: data.length, page: 1, per_page: 100, last_page: 1 },
      }),
    });
  });
}

async function mockSessionResume(page: import("@playwright/test").Page, quoteDescription: string) {
  const sessionId = "e2e-session-malformed-html";
  const sessionToken = "e2e-token-malformed-html";
  await mockQuestionnaireSessionRoutes(page, sessionId, sessionToken, quoteDescription);
}

async function mockQuestionnaireSessionRoutes(
  page: import("@playwright/test").Page,
  sessionId: string,
  sessionToken: string,
  quoteDescription = "",
  uiStep = 0,
) {
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
            quote_number: "Q-RESUME-HTML",
            job_number: "JOB-RESUME-HTML",
            client_name: "Test Client",
            trade_name: "Carpenter",
            property_address: "1 Test Street",
            quote_description: quoteDescription,
            findings_report: "",
            congestion_required: false,
            congestion_amount: 0,
            travel: 0,
          },
          step2: null,
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
}

async function expandWorkBlock(page: import("@playwright/test").Page, workIndex = 0) {
  const collapseLabel = `Collapse work ${workIndex + 1}`;
  const expandBtn = page.getByRole("button", { name: new RegExp(`^(Expand|Collapse) work ${workIndex + 1}$`) });
  const isExpanded = await page.getByRole("button", { name: collapseLabel }).isVisible().catch(() => false);
  if (!isExpanded) {
    await expandBtn.click();
  }
}

async function selectProduct(
  page: import("@playwright/test").Page,
  productLabel: string,
  workIndex = 0,
) {
  const comboboxes = page.getByRole("combobox", { name: "" });
  const combobox = comboboxes.nth(workIndex);
  await combobox.click();
  await combobox.fill(productLabel.split(" · ")[0]);
  await page.getByRole("option", { name: productLabel }).click();
}

async function fillWorkBlock(
  page: import("@playwright/test").Page,
  {
    scope,
    materialCost = "190",
    skill = "Carpenter",
    duration = "1.5",
    workIndex = 0,
    productLabel,
  }: {
    scope: string;
    materialCost?: string;
    skill?: string;
    duration?: string;
    workIndex?: number;
    productLabel?: string;
  },
) {
  await expandWorkBlock(page, workIndex);
  const block = page.locator("main");
  if (productLabel) {
    await selectProduct(page, productLabel, workIndex);
  }
  await block.locator("textarea").nth(workIndex).fill(scope);
  await block.getByLabel("Skill Required").nth(workIndex).selectOption(skill);
  await block.locator('input[type="number"]').nth(workIndex * 4 + 1).fill(materialCost);
  await block.getByRole("checkbox", { name: "Engineer needed" }).nth(workIndex).check();
  await block.getByLabel("Number of engineers").nth(workIndex).fill("1");
  await block.getByLabel("Hours or Days").nth(workIndex).selectOption("hours");
  await block.getByLabel("Duration").nth(workIndex).fill(duration);
}

test.describe.configure({ mode: "serial" });

test.describe("eWorks calculate link flow", () => {
  test("opens public wizard, completes questionnaire, and submits quote", async ({ page }) => {
    await mockProductsApi(page);
    const payload = {
      source: "eworks",
      quote_number: "Q-E2E-001",
      job_number: `JOB-E2E-${Date.now()}`,
      client: "Lambert Chartered Surveyors",
      trade: "Carpenter",
      property_address: "The Factory, 1 Nile Street",
      congestion_required: true,
      congestion_amount: 18,
      travel: 0,
      expires_at: futureExpiryIso(),
    };
    const { raw, sig } = makeSignedLink(payload);

    const url = `${FRONTEND}/eworks/calculate?payload=${encodeURIComponent(raw)}&sig=${encodeURIComponent(sig)}`;
    await page.goto(url, { waitUntil: "networkidle", timeout: 60000 });
    await expect(page.getByText("Step 1 of 3")).toBeVisible({ timeout: 20000 });
    await expect(page.getByText("Engineer Name")).toBeVisible();
    await expect(page.getByText("Description of what quoting for")).toBeVisible();
    await expect(page.getByText("Lamberts Chartered Surveyors")).toBeVisible();

    await page.getByRole("button", { name: "Continue" }).click();
    await expect(page.getByText("Step 2 of 3: Estimating Questionnaire")).toBeVisible();

    await fillWorkBlock(page, { scope: "Replace architrave and make good." });

    await page.getByRole("button", { name: "Submit" }).click();

    await expect(page.getByText("Step 3 of 3: Submitted")).toBeVisible({ timeout: 15000 });
    await expect(page.getByRole("heading", { name: "Quote submitted" })).toBeVisible();
    await expect(page.getByText("Estimate submitted.")).toBeVisible();
  });

  test("adds second work block and submits combined quote", async ({ page }) => {
    await mockProductsApi(page);
    const payload = {
      source: "eworks",
      quote_number: "Q-E2E-002",
      job_number: `JOB-E2E-MW-${Date.now()}`,
      client: "Lambert Chartered Surveyors",
      trade: "Carpenter",
      property_address: "The Factory, 1 Nile Street",
      congestion_required: true,
      congestion_amount: 18,
      travel: 0,
      expires_at: futureExpiryIso(),
    };
    const { raw, sig } = makeSignedLink(payload);

    const url = `${FRONTEND}/eworks/calculate?payload=${encodeURIComponent(raw)}&sig=${encodeURIComponent(sig)}`;
    await page.goto(url, { waitUntil: "networkidle", timeout: 60000 });
    await expect(page.getByText("Step 1 of 3")).toBeVisible({ timeout: 20000 });
    await page.getByRole("button", { name: "Continue" }).click();
    await expect(page.getByRole("combobox").first()).toBeVisible();

    await fillWorkBlock(page, { scope: "First work scope." });

    await page.getByRole("button", { name: "Add more works" }).click();
    await expect(page.getByRole("combobox")).toHaveCount(2);
    await fillWorkBlock(page, { scope: "Second work scope.", materialCost: "100", duration: "2", workIndex: 1 });

    await page.getByRole("button", { name: "Submit" }).click();

    await expect(page.getByText("Step 3 of 3: Submitted")).toBeVisible({ timeout: 15000 });
    await expect(page.getByRole("heading", { name: "Quote submitted" })).toBeVisible();
  });

  test("product combobox auto-fills scope and supports independent work blocks", async ({ page }) => {
    await mockProductsApi(page);
    const payload = {
      source: "eworks",
      quote_number: "Q-E2E-PROD",
      job_number: `JOB-E2E-PROD-${Date.now()}`,
      client: "Lambert Chartered Surveyors",
      trade: "Carpenter",
      property_address: "The Factory, 1 Nile Street",
      congestion_required: true,
      congestion_amount: 18,
      travel: 0,
      expires_at: futureExpiryIso(),
    };
    const { raw, sig } = makeSignedLink(payload);

    const url = `${FRONTEND}/eworks/calculate?payload=${encodeURIComponent(raw)}&sig=${encodeURIComponent(sig)}`;
    await page.goto(url, { waitUntil: "networkidle", timeout: 60000 });
    await page.getByRole("button", { name: "Continue" }).click();
    await expect(page.getByRole("combobox").first()).toBeVisible();

    await expandWorkBlock(page, 0);
    await selectProduct(page, "Plant Room · PR-0011", 0);
    const scopeTextarea = page.locator("textarea").first();
    await expect(scopeTextarea).toHaveValue("Inspect plant room equipment and report findings.");

    await scopeTextarea.fill("Custom manual scope for work one.");
    await expect(scopeTextarea).toHaveValue("Custom manual scope for work one.");

    await page.getByRole("button", { name: "Add more works" }).click();
    await expandWorkBlock(page, 1);
    await selectProduct(page, "Window Repair · WR-001", 1);
    await expect(page.locator("textarea").nth(1)).toHaveValue("");

    await page.getByRole("button", { name: "Reword with AI" }).first().click();
    await expect(page.getByRole("button", { name: "Reword with AI" }).first()).toBeEnabled();
  });

  test("prompts before replacing manual scope and supports reset from product", async ({ page }) => {
    await mockProductsApi(page);
    const payload = {
      source: "eworks",
      quote_number: "Q-E2E-SCOPE",
      job_number: `JOB-E2E-SCOPE-${Date.now()}`,
      client: "Lambert Chartered Surveyors",
      trade: "Carpenter",
      property_address: "The Factory, 1 Nile Street",
      congestion_required: true,
      congestion_amount: 18,
      travel: 0,
      expires_at: futureExpiryIso(),
    };
    const { raw, sig } = makeSignedLink(payload);

    await page.goto(`${FRONTEND}/eworks/calculate?payload=${encodeURIComponent(raw)}&sig=${encodeURIComponent(sig)}`, {
      waitUntil: "networkidle",
      timeout: 60000,
    });
    await page.getByRole("button", { name: "Continue" }).click();
    await expandWorkBlock(page, 0);

    await page.getByTestId("work-scope-0").fill("Manual scope written by estimator.");
    await selectProduct(page, "Plant Room · PR-0011", 0);

    await expect(page.getByTestId("scope-replace-dialog")).toBeVisible();
    await page.getByTestId("scope-replace-keep").click();
    await expect(page.getByTestId("work-scope-0")).toHaveValue("Manual scope written by estimator.");

    await selectProduct(page, "Plant Room · PR-0011", 0);
    await expect(page.getByTestId("scope-replace-dialog")).toBeVisible();
    await page.getByTestId("scope-replace-confirm").click();
    await expect(page.getByTestId("work-scope-0")).toHaveValue("Inspect plant room equipment and report findings.");

    await page.getByTestId("work-scope-0").fill("Edited again by estimator.");
    await page.getByTestId("reset-scope-work-0").click();
    await expect(page.getByTestId("work-scope-0")).toHaveValue("Inspect plant room equipment and report findings.");
  });

  test("work 2 product selection does not change work 1 scope", async ({ page }) => {
    await mockProductsApi(page);
    const payload = {
      source: "eworks",
      quote_number: "Q-E2E-W2",
      job_number: `JOB-E2E-W2-${Date.now()}`,
      client: "Lambert Chartered Surveyors",
      trade: "Carpenter",
      property_address: "The Factory, 1 Nile Street",
      congestion_required: true,
      congestion_amount: 18,
      travel: 0,
      expires_at: futureExpiryIso(),
    };
    const { raw, sig } = makeSignedLink(payload);
    await page.goto(`${FRONTEND}/eworks/calculate?payload=${encodeURIComponent(raw)}&sig=${encodeURIComponent(sig)}`, {
      waitUntil: "networkidle",
      timeout: 60000,
    });
    await page.getByRole("button", { name: "Continue" }).click();

    await expandWorkBlock(page, 0);
    await selectProduct(page, "Plant Room · PR-0011", 0);
    await expect(page.getByTestId("work-scope-0")).toHaveValue("Inspect plant room equipment and report findings.");

    await page.getByRole("button", { name: "Add more works" }).click();
    await expandWorkBlock(page, 1);
    await selectProduct(page, "Window Repair · WR-001", 1);
    await expect(page.getByTestId("work-scope-1")).toHaveValue("");
    await expect(page.getByTestId("work-scope-0")).toHaveValue("Inspect plant room equipment and report findings.");
  });

  test("selected product name is shown as primary work title", async ({ page }) => {
    await mockProductsApi(page);
    const payload = {
      source: "eworks",
      quote_number: "Q-E2E-LABEL",
      job_number: `JOB-E2E-LABEL-${Date.now()}`,
      client: "Lambert Chartered Surveyors",
      trade: "Carpenter",
      property_address: "The Factory, 1 Nile Street",
      congestion_required: true,
      congestion_amount: 18,
      travel: 0,
      expires_at: futureExpiryIso(),
    };
    const { raw, sig } = makeSignedLink(payload);
    await page.goto(`${FRONTEND}/eworks/calculate?payload=${encodeURIComponent(raw)}&sig=${encodeURIComponent(sig)}`, {
      waitUntil: "networkidle",
      timeout: 60000,
    });
    await page.getByRole("button", { name: "Continue" }).click();
    await expandWorkBlock(page, 0);
    await selectProduct(page, "Plant Room · PR-0011", 0);
    await expect(page.getByTestId("work-block-0")).toContainText("Plant Room · PR-0011");
    await expect(page.getByTestId("work-block-0")).toContainText("Work 1");
  });

  test("from-link API accepts signed payload for Lambert Carpenter", async ({ request }) => {
    const payload = {
      source: "eworks",
      quote_number: "Q-API-001",
      job_number: "JOB-API-001",
      client: "Lambert Chartered Surveyors",
      trade: "Carpenter",
      property_address: "1 Nile Street",
      expires_at: futureExpiryIso(),
    };
    const { raw, sig } = makeSignedLink(payload);
    const res = await request.post(`${API}/api/v1/calculation-session/from-link`, {
      data: { payload: raw, sig },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.data.step1.client_name).toBe("Lamberts Chartered Surveyors");
    expect(body.data.step1.trade_name).toBe("Carpenter");
    expect(body.data.resolved.formula_source).toBe("xlsx");
  });

  test("supplier card shows supplier name field without duplicate header title", async ({ page }) => {
    await mockProductsApi(page);
    const sessionId = "e2e-supplier-ui";
    const sessionToken = "e2e-supplier-token";
    await mockQuestionnaireSessionRoutes(page, sessionId, sessionToken, "", 1);
    await page.goto(`${FRONTEND}/eworks/calculate?session_id=${sessionId}&token=${sessionToken}`, {
      waitUntil: "networkidle",
      timeout: 60000,
    });
    await expect(page.getByText("Step 2 of 3: Estimating Questionnaire")).toBeVisible({ timeout: 15000 });
    await expandWorkBlock(page, 0);

    const card = page.getByTestId("supplier-card-0");
    const nameInput = card.getByTestId("supplier-name-0");
    await expect(nameInput).toHaveAttribute("placeholder", "Supplier 1");
    await expect(card.locator("span.text-sm.font-semibold.text-gray-900")).toHaveCount(0);

    await nameInput.fill("Travis Perkins");
    await expect(nameInput).toHaveValue("Travis Perkins");

    await page.getByRole("button", { name: "+ Add supplier" }).click();
    await expect(page.getByTestId("supplier-card-1")).toBeVisible();
    await page.getByTestId("supplier-card-1").getByRole("button", { name: "Remove Supplier 2" }).click();
    await expect(page.getByTestId("supplier-card-1")).toHaveCount(0);
  });

  test("renders malformed quote description when resuming session", async ({ page }) => {
    await mockSessionResume(page, MALFORMED_QUOTE_DESCRIPTION);
    await page.goto(
      `${FRONTEND}/eworks/calculate?session_id=e2e-session-malformed-html&token=e2e-token-malformed-html`,
      { waitUntil: "networkidle", timeout: 60000 }
    );

    const richText = page.getByTestId("quote-description-rich-text");
    await expect(richText).toBeVisible({ timeout: 15000 });
    await expect(richText).toContainText("Access");
    await expect(richText).toContainText("Quote");
    await expect(richText).toContainText("Velux window replacement");
    await expect(richText).not.toContainText("<span");
    await expect(richText).not.toContainText("</span");
    await expect(richText).not.toContainText("<br");
    await expect(richText).not.toContainText("&nbsp;");
  });

  test("renders HTML quote description as formatted text on step 1", async ({ page }) => {
    await mockProductsApi(page);
    const htmlDescription =
      '<span style="text-decoration: underline;"><strong>Access</strong></span><br />&nbsp;<br />' +
      "TT mum will be home<br /><br />" +
      '<span style="text-decoration: underline;"><strong>Quote</strong></span><br />' +
      "QUOTE ONLY Fire door inspection remedial works<br /><br />" +
      '<span style="text-decoration: underline;"><strong>Info</strong></span><br />' +
      "Booked by MICHAEL" +
      '<script>alert("xss")</script>';
    const payload = {
      source: "eworks",
      quote_number: "Q-E2E-HTML",
      job_number: `JOB-E2E-HTML-${Date.now()}`,
      client: "Lambert Chartered Surveyors",
      trade: "Carpenter",
      property_address: "The Factory, 1 Nile Street",
      quote_description: htmlDescription,
      congestion_required: true,
      congestion_amount: 18,
      travel: 0,
      expires_at: futureExpiryIso(),
    };
    const { raw, sig } = makeSignedLink(payload);
    await page.goto(`${FRONTEND}/eworks/calculate?payload=${encodeURIComponent(raw)}&sig=${encodeURIComponent(sig)}`, {
      waitUntil: "networkidle",
      timeout: 60000,
    });

    const richText = page.getByTestId("quote-description-rich-text");
    await expect(richText).toBeVisible();
    await expect(richText).toContainText("Access");
    await expect(richText).toContainText("Quote");
    await expect(richText).toContainText("QUOTE ONLY Fire door inspection remedial works");
    await expect(richText).toContainText("Booked by MICHAEL");
    await expect(richText).not.toContainText("<span");
    await expect(richText).not.toContainText("<br");
    await expect(richText).not.toContainText("&nbsp;");
    await expect(richText).not.toContainText("alert(");
  });

  test("strips HTML from scope textarea and product auto-fill", async ({ page }) => {
    await mockProductsApi(page);
    const payload = {
      source: "eworks",
      quote_number: "Q-E2E-SCOPE-HTML",
      job_number: `JOB-E2E-SCOPE-HTML-${Date.now()}`,
      client: "Lambert Chartered Surveyors",
      trade: "Carpenter",
      property_address: "The Factory, 1 Nile Street",
      scope: HTML_SCOPE,
      congestion_required: true,
      congestion_amount: 18,
      travel: 0,
      expires_at: futureExpiryIso(),
    };
    const { raw, sig } = makeSignedLink(payload);
    await page.goto(`${FRONTEND}/eworks/calculate?payload=${encodeURIComponent(raw)}&sig=${encodeURIComponent(sig)}`, {
      waitUntil: "networkidle",
      timeout: 60000,
    });
    await page.getByRole("button", { name: "Continue" }).click();
    await expandWorkBlock(page, 0);

    const scopeTextarea = page.getByTestId("work-scope-0");
    const scopeValue = await scopeTextarea.inputValue();
    expect(scopeValue).toContain("Inspect");
    expect(scopeValue).toContain("Item one");
    expect(scopeValue).not.toContain("<strong>");
    expect(scopeValue).not.toContain("&nbsp;");

    await selectProduct(page, "HTML Product · HTML-001", 0);
    const productScopeValue = await scopeTextarea.inputValue();
    expect(productScopeValue).toContain("Inspect");
    expect(productScopeValue).not.toMatch(/<span|<br|&nbsp;|<ol/i);
    await expect(page.getByTestId("work-block-0")).toContainText("HTML Product · HTML-001");
    await expect(page.getByTestId("work-block-0")).not.toContainText("<strong>");
  });
});

test("alias /calculate redirects preserving query string", async ({ page }) => {
  await page.goto(`${FRONTEND}/calculate?payload=test&sig=abc`);
  await expect(page).toHaveURL(/\/eworks\/calculate\?payload=test&sig=abc/);
});
