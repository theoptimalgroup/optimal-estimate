# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: eworks-calculate.spec.ts >> eWorks calculate link flow >> opens public wizard, completes questionnaire, and calculates without profit in client view
- Location: e2e/eworks-calculate.spec.ts:20:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByText('Estimating Questionnaire')
Expected: visible
Error: strict mode violation: getByText('Estimating Questionnaire') resolved to 3 elements:
    1) <p class="text-sm text-slate-500">…</p> aka getByText('Step 2 of 4: Estimating')
    2) <button type="button" class="rounded-full px-3 py-1 text-xs bg-blue-900 text-white">2. Estimating Questionnaire</button> aka getByRole('button', { name: 'Estimating Questionnaire' })
    3) <h2 class="text-sm font-semibold uppercase tracking-wide text-amber-700">Estimating Questionnaire</h2> aka getByRole('heading', { name: 'Estimating Questionnaire' })

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for getByText('Estimating Questionnaire')

```

# Page snapshot

```yaml
- generic [ref=e1]:
  - main [ref=e2]:
    - generic [ref=e4]:
      - heading "eWorks Estimate Calculator" [level=1] [ref=e5]
      - paragraph [ref=e6]: "Step 2 of 4: Estimating Questionnaire"
      - paragraph [ref=e7]: Job JOB-E2E-1779647249207 · Quote Q-E2E-001
    - generic [ref=e8]:
      - button "1. Estimation Form" [ref=e9] [cursor=pointer]
      - button "2. Estimating Questionnaire" [ref=e10] [cursor=pointer]
      - button "3. Charges" [disabled] [ref=e11]
      - button "4. Results" [disabled] [ref=e12]
    - generic [ref=e14]:
      - generic [ref=e15]:
        - heading "Estimating Questionnaire" [level=2] [ref=e16]
        - generic [ref=e17]: OPTIMAL GROUP
      - generic [ref=e18]:
        - button "▾ Work 1" [expanded] [ref=e20] [cursor=pointer]:
          - generic [ref=e21]: ▾
          - generic [ref=e22]: Work 1
        - generic [ref=e24]:
          - generic [ref=e25]:
            - heading "Scope of Works" [level=2] [ref=e26]
            - textbox [ref=e27]
          - generic [ref=e28]:
            - heading "Materials to Order and Cost" [level=2] [ref=e29]
            - table [ref=e31]:
              - rowgroup [ref=e32]:
                - row "Link Quantity Cost (£)" [ref=e33]:
                  - columnheader "Link" [ref=e34]
                  - columnheader "Quantity" [ref=e35]
                  - columnheader "Cost (£)" [ref=e36]
                  - columnheader [ref=e37]
              - rowgroup [ref=e38]:
                - row "Remove" [ref=e39]:
                  - cell [ref=e40]:
                    - textbox [ref=e41]
                  - cell [ref=e42]:
                    - spinbutton [ref=e43]: "1"
                  - cell [ref=e44]:
                    - spinbutton [ref=e45]: "0"
                  - cell "Remove" [ref=e46]:
                    - button "Remove" [ref=e47] [cursor=pointer]
            - button "Add material row" [ref=e48] [cursor=pointer]
          - generic [ref=e49]:
            - heading "Materials bought off the Shelf and Cost" [level=2] [ref=e50]
            - table [ref=e52]:
              - rowgroup [ref=e53]:
                - row "Item Quantity Cost (£)" [ref=e54]:
                  - columnheader "Item" [ref=e55]
                  - columnheader "Quantity" [ref=e56]
                  - columnheader "Cost (£)" [ref=e57]
                  - columnheader [ref=e58]
              - rowgroup [ref=e59]:
                - row "Remove" [ref=e60]:
                  - cell [ref=e61]:
                    - textbox [ref=e62]
                  - cell [ref=e63]:
                    - spinbutton [ref=e64]: "1"
                  - cell [ref=e65]:
                    - spinbutton [ref=e66]: "0"
                  - cell "Remove" [ref=e67]:
                    - button "Remove" [ref=e68] [cursor=pointer]
            - button "Add material row" [ref=e69] [cursor=pointer]
          - generic [ref=e70]:
            - generic [ref=e71]:
              - text: Skill Required
              - textbox "Skill Required" [ref=e72]: Carpenter
            - generic [ref=e73]:
              - text: Best Engineer
              - textbox "Best Engineer" [ref=e74]
            - generic [ref=e75]:
              - text: Subcontractors
              - textbox "Subcontractors" [ref=e76]
          - generic [ref=e78]:
            - checkbox "Engineer needed" [ref=e79]
            - text: Engineer needed
          - generic [ref=e80]:
            - heading "Any Other Notes" [level=2] [ref=e81]
            - textbox [ref=e82]
          - generic [ref=e83]:
            - heading "Photos / Videos" [level=2] [ref=e84]
            - generic [ref=e85]:
              - button "Take photo" [ref=e86] [cursor=pointer]
              - button "Record video" [ref=e87] [cursor=pointer]
              - button "Choose files" [ref=e88] [cursor=pointer]
            - paragraph [ref=e89]: Use the camera on your phone or choose existing photos and videos (max 50MB each).
      - button "Add more works" [ref=e90] [cursor=pointer]
    - generic [ref=e91]:
      - button "Back" [ref=e92] [cursor=pointer]
      - button "Continue" [active] [ref=e93] [cursor=pointer]
  - alert [ref=e94]
```

# Test source

```ts
  1   | import { test, expect } from "@playwright/test";
  2   | import crypto from "crypto";
  3   | 
  4   | const API = "http://localhost:8000";
  5   | const FRONTEND = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000";
  6   | 
  7   | function futureExpiryIso(days = 30) {
  8   |   const date = new Date();
  9   |   date.setUTCDate(date.getUTCDate() + days);
  10  |   return date.toISOString().replace(/\.\d{3}Z$/, "Z");
  11  | }
  12  | 
  13  | function makeSignedLink(payload: Record<string, unknown>, secret = "dev-secret-key-change-in-production") {
  14  |   const raw = Buffer.from(JSON.stringify(payload)).toString("base64url");
  15  |   const sig = crypto.createHmac("sha256", secret).update(raw).digest("hex");
  16  |   return { raw, sig };
  17  | }
  18  | 
  19  | test.describe("eWorks calculate link flow", () => {
  20  |   test("opens public wizard, completes questionnaire, and calculates without profit in client view", async ({ page }) => {
  21  |     const payload = {
  22  |       source: "eworks",
  23  |       quote_number: "Q-E2E-001",
  24  |       job_number: `JOB-E2E-${Date.now()}`,
  25  |       client: "Lambert Chartered Surveyors",
  26  |       trade: "Carpenter",
  27  |       property_address: "The Factory, 1 Nile Street",
  28  |       congestion_required: true,
  29  |       congestion_amount: 18,
  30  |       travel: 0,
  31  |       expires_at: futureExpiryIso(),
  32  |     };
  33  |     const { raw, sig } = makeSignedLink(payload);
  34  | 
  35  |     await page.goto(`${FRONTEND}/eworks/calculate?payload=${encodeURIComponent(raw)}&sig=${encodeURIComponent(sig)}`);
  36  | 
  37  |     await expect(page.getByText("Step 1 of 4")).toBeVisible();
  38  |     await expect(page.getByText("This estimation form is supplied by your eWorks link and cannot be edited here.")).toBeVisible();
  39  |     await expect(page.locator("input, textarea, select")).toHaveCount(0);
  40  |     await expect(page.getByText("Engineer Name")).toBeVisible();
  41  |     await expect(page.getByText("Description of what quoting for")).toBeVisible();
  42  |     await expect(page.getByText("Lamberts Chartered Surveyors")).toBeVisible();
  43  | 
  44  |     await page.getByRole("button", { name: "Continue" }).click();
  45  |     await expect(page.getByText("Step 2 of 4")).toBeVisible();
> 46  |     await expect(page.getByText("Estimating Questionnaire")).toBeVisible();
      |                                                              ^ Error: expect(locator).toBeVisible() failed
  47  | 
  48  |     await page.locator("textarea").first().fill("Replace architrave and make good.");
  49  |     await page.locator('input[type="number"]').first().fill("190");
  50  |     await page.getByLabel("Hours or Days").first().selectOption("hours");
  51  |     await page.getByLabel("Time Frame").first().fill("1.5");
  52  | 
  53  |     await page.getByRole("button", { name: "Continue" }).click();
  54  |     await expect(page.getByText("Step 3 of 4")).toBeVisible();
  55  | 
  56  |     await page.getByRole("button", { name: "Calculate" }).click();
  57  | 
  58  |     await expect(page.getByText("Step 4 of 4")).toBeVisible({ timeout: 15000 });
  59  |     await expect(page.getByRole("heading", { name: "Combined quote" })).toBeVisible();
  60  |     await expect(page.getByRole("heading", { name: "Client-safe summary" })).toBeVisible();
  61  |     await expect(page.getByText("Unexpected profit field exposed in client view")).toHaveCount(0);
  62  |   });
  63  | 
  64  |   test("adds second work block and shows combined results", async ({ page }) => {
  65  |     const payload = {
  66  |       source: "eworks",
  67  |       quote_number: "Q-E2E-002",
  68  |       job_number: `JOB-E2E-MW-${Date.now()}`,
  69  |       client: "Lambert Chartered Surveyors",
  70  |       trade: "Carpenter",
  71  |       property_address: "The Factory, 1 Nile Street",
  72  |       congestion_required: true,
  73  |       congestion_amount: 18,
  74  |       travel: 0,
  75  |       expires_at: futureExpiryIso(),
  76  |     };
  77  |     const { raw, sig } = makeSignedLink(payload);
  78  | 
  79  |     await page.goto(`${FRONTEND}/eworks/calculate?payload=${encodeURIComponent(raw)}&sig=${encodeURIComponent(sig)}`);
  80  | 
  81  |     await page.getByRole("button", { name: "Continue" }).click();
  82  |     await expect(page.getByText("Work 1")).toBeVisible();
  83  | 
  84  |     await page.locator("textarea").first().fill("First work scope.");
  85  |     await page.locator('input[type="number"]').first().fill("190");
  86  |     await page.getByLabel("Hours or Days").first().selectOption("hours");
  87  |     await page.getByLabel("Time Frame").first().fill("1.5");
  88  | 
  89  |     await page.getByRole("button", { name: "Add more works" }).click();
  90  |     await expect(page.getByRole("button", { name: /^▾ Work 2/ })).toBeVisible();
  91  |     await expect(page.locator("textarea")).toHaveCount(1);
  92  | 
  93  |     await page.locator("textarea").fill("Second work scope.");
  94  |     await page.locator('input[type="number"]').first().fill("100");
  95  |     await page.getByLabel("Hours or Days").selectOption("hours");
  96  |     await page.getByLabel("Time Frame").fill("2");
  97  | 
  98  |     await page.getByRole("button", { name: "Continue" }).click();
  99  |     await page.getByRole("button", { name: "Calculate" }).click();
  100 | 
  101 |     await expect(page.getByText("Step 4 of 4")).toBeVisible({ timeout: 15000 });
  102 |     await expect(page.getByRole("heading", { name: "Per-work breakdown" })).toBeVisible();
  103 |     await expect(page.getByText("Work 1")).toBeVisible();
  104 |     await expect(page.getByText("Work 2")).toBeVisible();
  105 |     await expect(page.getByRole("heading", { name: "Combined quote" })).toBeVisible();
  106 |   });
  107 | 
  108 |   test("alias /calculate redirects preserving query string", async ({ page }) => {
  109 |     await page.goto(`${FRONTEND}/calculate?payload=test&sig=abc`);
  110 |     await expect(page).toHaveURL(/\/eworks\/calculate\?payload=test&sig=abc/);
  111 |   });
  112 | 
  113 |   test("from-link API accepts signed payload for Lambert Carpenter", async ({ request }) => {
  114 |     const payload = {
  115 |       source: "eworks",
  116 |       quote_number: "Q-API-001",
  117 |       job_number: "JOB-API-001",
  118 |       client: "Lambert Chartered Surveyors",
  119 |       trade: "Carpenter",
  120 |       property_address: "1 Nile Street",
  121 |       expires_at: futureExpiryIso(),
  122 |     };
  123 |     const { raw, sig } = makeSignedLink(payload);
  124 |     const res = await request.post(`${API}/api/v1/calculation-session/from-link`, {
  125 |       data: { payload: raw, sig },
  126 |     });
  127 |     expect(res.ok()).toBeTruthy();
  128 |     const body = await res.json();
  129 |     expect(body.data.step1.client_name).toBe("Lamberts Chartered Surveyors");
  130 |     expect(body.data.step1.trade_name).toBe("Carpenter");
  131 |     expect(body.data.resolved.formula_source).toBe("xlsx");
  132 |   });
  133 | });
  134 | 
```