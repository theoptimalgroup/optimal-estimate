import { test, expect } from "@playwright/test";
import crypto from "crypto";

const API = "http://localhost:8000";
const FRONTEND = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000";

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

test.describe("eWorks calculate link flow", () => {
  test("opens public wizard, completes questionnaire, and calculates without profit in client view", async ({ page }) => {
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

    await page.goto(`${FRONTEND}/eworks/calculate?payload=${encodeURIComponent(raw)}&sig=${encodeURIComponent(sig)}`);

    await expect(page.getByText("Step 1 of 4")).toBeVisible();
    await expect(page.getByText("This estimation form is supplied by your eWorks link and cannot be edited here.")).toBeVisible();
    await expect(page.locator("input, textarea, select")).toHaveCount(0);
    await expect(page.getByText("Engineer Name")).toBeVisible();
    await expect(page.getByText("Description of what quoting for")).toBeVisible();
    await expect(page.getByText("Lamberts Chartered Surveyors")).toBeVisible();

    await page.getByRole("button", { name: "Continue" }).click();
    await expect(page.getByText("Step 2 of 4")).toBeVisible();
    await expect(page.getByText("Estimating Questionnaire")).toBeVisible();

    await page.locator("textarea").first().fill("Replace architrave and make good.");
    await page.getByLabel("Skill Required").first().selectOption("Carpenter");
    await page.locator('input[type="number"]').nth(1).fill("190");
    await page.getByLabel("Hours or Days").first().selectOption("hours");
    await page.getByLabel("Duration").first().fill("1.5");

    await page.getByRole("button", { name: "Continue" }).click();
    await expect(page.getByText("Step 3 of 4")).toBeVisible();

    await page.getByRole("button", { name: "Calculate" }).click();

    await expect(page.getByText("Step 4 of 4")).toBeVisible({ timeout: 15000 });
    await expect(page.getByRole("heading", { name: "Combined quote" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Client-safe summary" })).toBeVisible();
    await expect(page.getByText("Unexpected profit field exposed in client view")).toHaveCount(0);

    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: "Download PDF" }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/document_.*\.(pdf|html)$/);
  });

  test("adds second work block and shows combined results", async ({ page }) => {
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

    await page.goto(`${FRONTEND}/eworks/calculate?payload=${encodeURIComponent(raw)}&sig=${encodeURIComponent(sig)}`);

    await page.getByRole("button", { name: "Continue" }).click();
    await expect(page.getByText("Work 1")).toBeVisible();

    await page.locator("textarea").first().fill("First work scope.");
    await page.getByLabel("Skill Required").first().selectOption("Carpenter");
    await page.locator('input[type="number"]').nth(1).fill("190");
    await page.getByLabel("Hours or Days").first().selectOption("hours");
    await page.getByLabel("Duration").first().fill("1.5");

    await page.getByRole("button", { name: "Add more works" }).click();
    await expect(page.getByRole("button", { name: /^▾ Work 2/ })).toBeVisible();
    await expect(page.locator("textarea")).toHaveCount(1);

    await page.locator("textarea").fill("Second work scope.");
    await page.getByLabel("Skill Required").selectOption("Carpenter");
    await page.locator('input[type="number"]').nth(1).fill("100");
    await page.getByLabel("Hours or Days").selectOption("hours");
    await page.getByLabel("Duration").fill("2");

    await page.getByRole("button", { name: "Continue" }).click();
    await page.getByRole("button", { name: "Calculate" }).click();

    await expect(page.getByText("Step 4 of 4")).toBeVisible({ timeout: 15000 });
    await expect(page.getByRole("heading", { name: "Per-work breakdown" })).toBeVisible();
    await expect(page.getByText("Work 1")).toBeVisible();
    await expect(page.getByText("Work 2")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Combined quote" })).toBeVisible();
    await expect(page.getByText(/total across 2 works/i)).toBeVisible();
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
