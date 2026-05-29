import { test, expect } from "@playwright/test";
import crypto from "crypto";

const API = process.env.PLAYWRIGHT_API_URL ?? "http://127.0.0.1:8000";
const FRONTEND = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3001";

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

async function fillWorkBlock(
  page: import("@playwright/test").Page,
  {
    scope,
    materialCost = "190",
    skill = "Carpenter",
    duration = "1.5",
    workIndex = 0,
  }: { scope: string; materialCost?: string; skill?: string; duration?: string; workIndex?: number },
) {
  if (workIndex > 0) {
    await page.getByRole("button", { name: new RegExp(`Work ${workIndex + 1}`) }).click();
  }
  const block = workIndex > 0 ? page.locator("main") : page;
  await block.locator("textarea").first().fill(scope);
  await block.getByLabel("Skill Required").first().selectOption(skill);
  await block.locator('input[type="number"]').nth(1).fill(materialCost);
  await block.getByRole("checkbox", { name: "Engineer needed" }).first().check();
  await block.getByLabel("Number of engineers").first().fill("1");
  await block.getByLabel("Hours or Days").first().selectOption("hours");
  await block.getByLabel("Duration").first().fill(duration);
}

test.describe.configure({ mode: "serial" });

test.describe("eWorks calculate link flow", () => {
  test("opens public wizard, completes questionnaire, and submits quote", async ({ page }) => {
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
    await expect(page.getByText("Work 1")).toBeVisible();

    await fillWorkBlock(page, { scope: "First work scope." });

    await page.getByRole("button", { name: "Add more works" }).click();
    await expect(page.getByRole("button", { name: /Work 2/ })).toBeVisible();
    await fillWorkBlock(page, { scope: "Second work scope.", materialCost: "100", duration: "2", workIndex: 1 });

    await page.getByRole("button", { name: "Submit" }).click();

    await expect(page.getByText("Step 3 of 3: Submitted")).toBeVisible({ timeout: 15000 });
    await expect(page.getByRole("heading", { name: "Quote submitted" })).toBeVisible();
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
