# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: full-flow.spec.ts >> full estimator to manager quote flow
- Location: e2e/full-flow.spec.ts:11:5

# Error details

```
Error: expect(received).toBe(expected) // Object.is equality

Expected: "314.39"
Received: "134.39"
```

# Test source

```ts
  1   | import { test, expect } from "@playwright/test";
  2   | 
  3   | const API = "http://localhost:8000";
  4   | 
  5   | async function apiLogin(request, email: string, password: string) {
  6   |   const res = await request.post(`${API}/api/v1/auth/login`, { data: { email, password } });
  7   |   expect(res.ok()).toBeTruthy();
  8   |   return (await res.json()).data.access_token as string;
  9   | }
  10  | 
  11  | test("full estimator to manager quote flow", async ({ page, request }) => {
  12  |   const estimatorToken = await apiLogin(request, "estimator@optimal.example", "estimate12345");
  13  |   const managerToken = await apiLogin(request, "manager@optimal.example", "manager12345");
  14  |   const headers = (token: string) => ({ Authorization: `Bearer ${token}` });
  15  | 
  16  |   const clients = (await (await request.get(`${API}/api/v1/clients`, { headers: headers(estimatorToken) })).json()).data;
  17  |   const trades = (await (await request.get(`${API}/api/v1/trades`, { headers: headers(estimatorToken) })).json()).data;
  18  |   const plumbing = trades.find((t: { name: string }) => t.name === "Plumbing");
  19  | 
  20  |   const jobRes = await request.post(`${API}/api/v1/jobs`, {
  21  |     headers: headers(estimatorToken),
  22  |     data: {
  23  |       job_number: `JOB-E2E-${Date.now()}`,
  24  |       client_id: clients[0].id,
  25  |       property_address: "10 Napier Watt Street",
  26  |     },
  27  |   });
  28  |   expect(jobRes.ok()).toBeTruthy();
  29  |   const job = (await jobRes.json()).data;
  30  | 
  31  |   const quoteRes = await request.post(`${API}/api/v1/quotes`, {
  32  |     headers: headers(estimatorToken),
  33  |     data: {
  34  |       quote_number: `Q-E2E-${Date.now()}`,
  35  |       job_id: job.id,
  36  |       scope_items: [{ description: "Replace valve", client_visible: true }],
  37  |       labour_items: [{ trade_id: plumbing.id, labour_type: "hourly", number_of_engineers: 1, hours_on_site: 2 }],
  38  |       material_items: [{ material_name: "Valve", quantity: 1, unit_cost: 82.49, markup_type: "percentage", markup_value: 20 }],
  39  |       charges: { parking_required: true, parking_type: "hourly", parking_rate_per_hour: 6.5, parking_hours: 2 },
  40  |     },
  41  |   });
  42  |   expect(quoteRes.ok()).toBeTruthy();
  43  |   const quote = (await quoteRes.json()).data;
  44  | 
  45  |   const preview = await request.post(`${API}/api/v1/calculations/preview`, {
  46  |     headers: headers(estimatorToken),
  47  |     data: { quote_id: quote.id },
  48  |   });
  49  |   const breakdown = (await preview.json()).data;
> 50  |   expect(breakdown.final_total).toBe("314.39");
      |                                 ^ Error: expect(received).toBe(expected) // Object.is equality
  51  | 
  52  |   const finalize = await request.post(`${API}/api/v1/calculations/finalize`, {
  53  |     headers: headers(estimatorToken),
  54  |     data: { quote_id: quote.id },
  55  |   });
  56  |   expect(finalize.ok()).toBeTruthy();
  57  | 
  58  |   await request.post(`${API}/api/v1/quotes/${quote.id}/submit-for-approval`, {
  59  |     headers: headers(estimatorToken),
  60  |     data: {},
  61  |   });
  62  | 
  63  |   const approve = await request.post(`${API}/api/v1/quotes/${quote.id}/approve`, {
  64  |     headers: headers(managerToken),
  65  |     data: { reason: "E2E approved" },
  66  |   });
  67  |   expect(approve.ok()).toBeTruthy();
  68  | 
  69  |   const draftPdf = await request.post(`${API}/api/v1/documents/quote-pdf`, {
  70  |     headers: headers(managerToken),
  71  |     data: { quote_id: quote.id, is_draft: true },
  72  |   });
  73  |   expect(draftPdf.ok()).toBeTruthy();
  74  |   const draftDoc = (await draftPdf.json()).data;
  75  | 
  76  |   const finalPdf = await request.post(`${API}/api/v1/documents/quote-pdf`, {
  77  |     headers: headers(managerToken),
  78  |     data: { quote_id: quote.id, is_draft: false },
  79  |   });
  80  |   expect(finalPdf.ok()).toBeTruthy();
  81  | 
  82  |   const clientView = (await (await request.get(`${API}/api/v1/quotes/${quote.id}/client-view`, { headers: headers(estimatorToken) })).json()).data;
  83  |   expect(clientView.internal_notes).toBeUndefined();
  84  |   expect(clientView.margin_total).toBeUndefined();
  85  | 
  86  |   const engineerToken = await apiLogin(request, "engineer@optimal.example", "engineer12345");
  87  |   const internalBlocked = await request.get(`${API}/api/v1/quotes/${quote.id}/internal-view`, {
  88  |     headers: headers(engineerToken),
  89  |   });
  90  |   expect(internalBlocked.status()).toBe(403);
  91  | 
  92  |   const estimatorApprove = await request.post(`${API}/api/v1/quotes/${quote.id}/approve`, {
  93  |     headers: headers(estimatorToken),
  94  |     data: { reason: "nope" },
  95  |   });
  96  |   expect(estimatorApprove.status()).toBe(403);
  97  | 
  98  |   // UI: login as estimator and open client preview
  99  |   await page.goto("http://localhost:3000/login");
  100 |   await page.getByLabel("Email").fill("estimator@optimal.example");
  101 |   await page.getByLabel("Password").fill("estimate12345");
  102 |   await page.getByRole("button", { name: "Login" }).click();
  103 |   await expect(page).toHaveURL(/dashboard/);
  104 |   await page.goto(`http://localhost:3000/quotes/${quote.id}/client-preview`);
  105 |   await expect(page.getByText("Client-Safe Preview")).toBeVisible();
  106 |   expect(draftDoc.is_draft).toBe(true);
  107 | });
  108 | 
  109 | test("login page loads", async ({ page }) => {
  110 |   await page.goto("http://localhost:3000/login");
  111 |   await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  112 | });
  113 | 
```