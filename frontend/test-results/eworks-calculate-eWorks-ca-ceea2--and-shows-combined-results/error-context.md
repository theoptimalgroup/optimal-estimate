# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: eworks-calculate.spec.ts >> eWorks calculate link flow >> adds second work block and shows combined results
- Location: e2e/eworks-calculate.spec.ts:64:7

# Error details

```
Test timeout of 120000ms exceeded.
```

```
Error: locator.selectOption: Test timeout of 120000ms exceeded.
Call log:
  - waiting for getByLabel('Hours or Days').first()

```

# Page snapshot

```yaml
- generic [ref=e1]:
  - main [ref=e2]:
    - generic [ref=e3]:
      - generic [ref=e4]:
        - heading "eWorks Estimate Calculator" [level=1] [ref=e5]
        - paragraph [ref=e6]: "Step 2 of 4: Estimating Questionnaire"
        - paragraph [ref=e7]: Job JOB-E2E-MW-1779647251285 · Quote Q-E2E-002
      - generic [ref=e8]: Saved
    - generic [ref=e9]:
      - button "1. Estimation Form" [ref=e10] [cursor=pointer]
      - button "2. Estimating Questionnaire" [ref=e11] [cursor=pointer]
      - button "3. Charges" [disabled] [ref=e12]
      - button "4. Results" [disabled] [ref=e13]
    - generic [ref=e15]:
      - generic [ref=e16]:
        - heading "Estimating Questionnaire" [level=2] [ref=e17]
        - generic [ref=e18]: OPTIMAL GROUP
      - generic [ref=e19]:
        - button "▾ Work 1" [expanded] [ref=e21] [cursor=pointer]:
          - generic [ref=e22]: ▾
          - generic [ref=e23]: Work 1
        - generic [ref=e25]:
          - generic [ref=e26]:
            - heading "Scope of Works" [level=2] [ref=e27]
            - textbox [ref=e28]: First work scope.
          - generic [ref=e29]:
            - heading "Materials to Order and Cost" [level=2] [ref=e30]
            - table [ref=e32]:
              - rowgroup [ref=e33]:
                - row "Link Quantity Cost (£)" [ref=e34]:
                  - columnheader "Link" [ref=e35]
                  - columnheader "Quantity" [ref=e36]
                  - columnheader "Cost (£)" [ref=e37]
                  - columnheader [ref=e38]
              - rowgroup [ref=e39]:
                - row "Remove" [ref=e40]:
                  - cell [ref=e41]:
                    - textbox [ref=e42]
                  - cell [ref=e43]:
                    - spinbutton [active] [ref=e44]: "190"
                  - cell [ref=e45]:
                    - spinbutton [ref=e46]: "0"
                  - cell "Remove" [ref=e47]:
                    - button "Remove" [ref=e48] [cursor=pointer]
            - button "Add material row" [ref=e49] [cursor=pointer]
          - generic [ref=e50]:
            - heading "Materials bought off the Shelf and Cost" [level=2] [ref=e51]
            - table [ref=e53]:
              - rowgroup [ref=e54]:
                - row "Item Quantity Cost (£)" [ref=e55]:
                  - columnheader "Item" [ref=e56]
                  - columnheader "Quantity" [ref=e57]
                  - columnheader "Cost (£)" [ref=e58]
                  - columnheader [ref=e59]
              - rowgroup [ref=e60]:
                - row "Remove" [ref=e61]:
                  - cell [ref=e62]:
                    - textbox [ref=e63]
                  - cell [ref=e64]:
                    - spinbutton [ref=e65]: "1"
                  - cell [ref=e66]:
                    - spinbutton [ref=e67]: "0"
                  - cell "Remove" [ref=e68]:
                    - button "Remove" [ref=e69] [cursor=pointer]
            - button "Add material row" [ref=e70] [cursor=pointer]
          - generic [ref=e71]:
            - generic [ref=e72]:
              - text: Skill Required
              - textbox "Skill Required" [ref=e73]: Carpenter
            - generic [ref=e74]:
              - text: Best Engineer
              - textbox "Best Engineer" [ref=e75]
            - generic [ref=e76]:
              - text: Subcontractors
              - textbox "Subcontractors" [ref=e77]
          - generic [ref=e79]:
            - checkbox "Engineer needed" [ref=e80]
            - text: Engineer needed
          - generic [ref=e81]:
            - heading "Any Other Notes" [level=2] [ref=e82]
            - textbox [ref=e83]
          - generic [ref=e84]:
            - heading "Photos / Videos" [level=2] [ref=e85]
            - generic [ref=e86]:
              - button "Take photo" [ref=e87] [cursor=pointer]
              - button "Record video" [ref=e88] [cursor=pointer]
              - button "Choose files" [ref=e89] [cursor=pointer]
            - paragraph [ref=e90]: Use the camera on your phone or choose existing photos and videos (max 50MB each).
      - button "Add more works" [ref=e91] [cursor=pointer]
    - generic [ref=e92]:
      - button "Back" [ref=e93] [cursor=pointer]
      - button "Continue" [ref=e94] [cursor=pointer]
  - alert [ref=e95]
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
  46  |     await expect(page.getByText("Estimating Questionnaire")).toBeVisible();
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
> 86  |     await page.getByLabel("Hours or Days").first().selectOption("hours");
      |                                                    ^ Error: locator.selectOption: Test timeout of 120000ms exceeded.
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