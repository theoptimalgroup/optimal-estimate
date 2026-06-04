import { test, expect } from "@playwright/test";
import crypto from "crypto";

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
  await combobox.fill(productLabel.split(" — ")[0]);
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
    await expect(page.getByText("This estimation form is supplied by your eWorks link and cannot be edited here.")).toBeVisible();
    await expect(page.locator("input, textarea, select")).toHaveCount(0);
    await expect(page.getByText("Engineer Name")).toBeVisible();
    await expect(page.getByText("Description of what quoting for")).toBeVisible();
    await expect(page.getByText("Lamberts Chartered Surveyors")).toBeVisible();

    await page.getByRole("button", { name: "Continue" }).click();
    await expect(page.getByText("Step 2 of 3: Estimating Questionnaire")).toBeVisible();

    await fillWorkBlock(page, { scope: "Replace architrave and make good." });

    await page.getByRole("button", { name: "Submit" }).click();

    await expect(page.getByText("Step 3 of 3: Submitted")).toBeVisible({ timeout: 15000 });
    await expect(page.getByRole("heading", { name: "Quote submitted" })).toBeVisible();
    await expect(page.getByText(/has been submitted successfully/i)).toBeVisible();
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
    await selectProduct(page, "Plant Room — PR-0011", 0);
    const scopeTextarea = page.locator("textarea").first();
    await expect(scopeTextarea).toHaveValue("Inspect plant room equipment and report findings.");

    await scopeTextarea.fill("Custom manual scope for work one.");
    await expect(scopeTextarea).toHaveValue("Custom manual scope for work one.");

    await page.getByRole("button", { name: "Add more works" }).click();
    await expandWorkBlock(page, 1);
    await selectProduct(page, "Window Repair — WR-001", 1);
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
    await selectProduct(page, "Plant Room — PR-0011", 0);

    await expect(page.getByTestId("scope-replace-dialog")).toBeVisible();
    await page.getByTestId("scope-replace-keep").click();
    await expect(page.getByTestId("work-scope-0")).toHaveValue("Manual scope written by estimator.");

    await selectProduct(page, "Plant Room — PR-0011", 0);
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
    await selectProduct(page, "Plant Room — PR-0011", 0);
    await expect(page.getByTestId("work-scope-0")).toHaveValue("Inspect plant room equipment and report findings.");

    await page.getByRole("button", { name: "Add more works" }).click();
    await expandWorkBlock(page, 1);
    await selectProduct(page, "Window Repair — WR-001", 1);
    await expect(page.getByTestId("work-scope-1")).toHaveValue("");
    await expect(page.getByTestId("work-scope-0")).toHaveValue("Inspect plant room equipment and report findings.");
  });

  test("alias /calculate redirects preserving query string", async ({ page }) => {
    await page.goto(`${FRONTEND}/calculate?payload=test&sig=abc`);
    await expect(page).toHaveURL(/\/eworks\/calculate\?payload=test&sig=abc/);
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
});
