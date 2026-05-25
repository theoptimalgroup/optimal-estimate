# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: wizard-flow.spec.ts >> Quote wizard >> validation blocks invalid step submission
- Location: e2e/wizard-flow.spec.ts:109:7

# Error details

```
Test timeout of 120000ms exceeded.
```

```
Error: locator.selectOption: Test timeout of 120000ms exceeded.
Call log:
  - waiting for getByLabel(/^Client/)

```

# Page snapshot

```yaml
- generic [ref=e1]:
  - alert [ref=e2]
  - generic [ref=e3]:
    - banner [ref=e4]:
      - generic [ref=e5]:
        - generic [ref=e6]:
          - paragraph [ref=e7]: Optimal Estimate Calculator
          - paragraph [ref=e8]: Estimator User · estimator
        - button "Logout" [ref=e9] [cursor=pointer]
    - generic [ref=e10]:
      - complementary [ref=e11]:
        - navigation [ref=e12]:
          - link "Dashboard" [ref=e13] [cursor=pointer]:
            - /url: /dashboard
          - link "Jobs" [ref=e14] [cursor=pointer]:
            - /url: /jobs
          - link "Quotes" [ref=e15] [cursor=pointer]:
            - /url: /quotes
          - link "Clients" [ref=e16] [cursor=pointer]:
            - /url: /clients
          - link "Trades" [ref=e17] [cursor=pointer]:
            - /url: /trades
          - link "Rules" [ref=e18] [cursor=pointer]:
            - /url: /rules
      - main [ref=e19]:
        - generic [ref=e20]:
          - generic [ref=e21]:
            - generic [ref=e22]:
              - link "← Back to job" [ref=e23] [cursor=pointer]:
                - /url: /jobs/2cfc2068-9302-4d91-abb1-3e1ed5615332
              - heading "Estimate Wizard" [level=1] [ref=e24]
              - paragraph [ref=e25]: "Step 1 of 10: Job Details"
            - generic [ref=e27]: Saved at 10:31:29 PM
          - generic [ref=e28]:
            - button "1. Job Details" [ref=e29] [cursor=pointer]
            - button "2. Site Findings" [ref=e30] [cursor=pointer]
            - button "3. Scope" [ref=e31] [cursor=pointer]
            - button "4. Labour" [ref=e32] [cursor=pointer]
            - button "5. Materials" [ref=e33] [cursor=pointer]
            - button "6. Charges" [ref=e34] [cursor=pointer]
            - button "7. Calculation" [ref=e35] [cursor=pointer]
            - button "8. Review" [ref=e36] [cursor=pointer]
            - button "9. Approval" [ref=e37] [cursor=pointer]
            - button "10. Client Preview" [ref=e38] [cursor=pointer]
          - generic [ref=e39]:
            - generic [ref=e40]:
              - generic [ref=e41]:
                - paragraph [ref=e42]: Job number
                - paragraph [ref=e43]: JOB-VAL-1779647370551
              - generic [ref=e44]:
                - text: Client *
                - combobox "Search clients" [ref=e45]
                - text: Client is required
              - generic [ref=e46]:
                - text: Property address *
                - textbox "Property address * Property address is required" [ref=e47]
                - paragraph [ref=e48]: Property address is required
              - generic [ref=e49]:
                - text: Property manager
                - textbox "Property manager" [ref=e50]
              - generic [ref=e51]:
                - text: PM email
                - textbox "PM email" [ref=e52]
              - generic [ref=e53]:
                - text: PM phone
                - textbox "PM phone" [ref=e54]
              - generic [ref=e55]:
                - text: Tenant name
                - textbox "Tenant name" [ref=e56]
              - generic [ref=e57]:
                - text: Tenant phone
                - textbox "Tenant phone" [ref=e58]
              - generic [ref=e59]:
                - text: Access notes
                - textbox "Access notes" [ref=e60]
              - generic [ref=e61]:
                - text: Original job description
                - textbox "Original job description" [ref=e62]
              - generic [ref=e63]:
                - text: Engineer name
                - textbox "Engineer name" [ref=e64]
              - generic [ref=e65]:
                - text: Date visited
                - textbox "Date visited" [ref=e66]
              - generic [ref=e67]:
                - text: Travel time (minutes)
                - spinbutton "Travel time (minutes)" [ref=e68]: "0"
              - generic [ref=e69]:
                - paragraph [ref=e70]: Selected client
                - paragraph [ref=e71]: —
            - button "Save & Continue" [active] [ref=e72] [cursor=pointer]
```

# Test source

```ts
  32  |   const jobRes = await request.post(`${API}/api/v1/jobs`, {
  33  |     headers,
  34  |     data: {
  35  |       job_number: `JOB-WIZ-${Date.now()}`,
  36  |       client_id: client.id,
  37  |       property_address: "10 Regression Street",
  38  |     },
  39  |   });
  40  |   expect(jobRes.ok()).toBeTruthy();
  41  |   return (await jobRes.json()).data;
  42  | }
  43  | 
  44  | test.describe("Quote wizard", () => {
  45  |   test("estimator can complete all 10 steps with regression total", async ({ page, request }) => {
  46  |     const token = await apiLogin(request, USERS.estimator.email, USERS.estimator.password);
  47  |     const job = await createJobWithClient(request, token);
  48  |     const trades = (await (await request.get(`${API}/api/v1/trades`, { headers: { Authorization: `Bearer ${token}` } })).json()).data;
  49  |     const plumbing = trades.find((t: { name: string }) => t.name === "Plumbing");
  50  |     expect(plumbing).toBeTruthy();
  51  | 
  52  |     await login(page, USERS.estimator.email, USERS.estimator.password);
  53  |     await page.goto(`/jobs/${job.id}/quote`);
  54  |     await expect(page.getByRole("heading", { name: "Estimate Wizard" })).toBeVisible();
  55  |     await expect(page.getByText("Step 1 of 10")).toBeVisible();
  56  | 
  57  |     // Step 1 Job Details - client/address pre-filled from job
  58  |     await page.getByRole("button", { name: "Save & Continue" }).click();
  59  |     await expect(page.getByText("Step 2 of 10")).toBeVisible();
  60  | 
  61  |     // Step 2 Findings
  62  |     await page.getByPlaceholder("Engineer findings").fill("Access confirmed. Valve leaking.");
  63  |     await page.getByRole("button", { name: "Save & Continue" }).click();
  64  |     await expect(page.getByText("Step 3 of 10")).toBeVisible();
  65  | 
  66  |     // Step 3 Scope
  67  |     await page.getByLabel(/Scope of works/).fill("Replace faulty valve and test system");
  68  |     await page.getByRole("button", { name: "Save & Continue" }).click();
  69  |     await expect(page.getByText("Step 4 of 10")).toBeVisible();
  70  | 
  71  |     // Step 4 Labour
  72  |     await page.getByLabel(/^Trade/).selectOption(plumbing.id);
  73  |     await page.getByRole("button", { name: "Save & Continue" }).click();
  74  |     await expect(page.getByText("Step 5 of 10")).toBeVisible();
  75  | 
  76  |     // Step 5 Materials - defaults include regression values
  77  |     await page.getByRole("button", { name: "Save & Continue" }).click();
  78  |     await expect(page.getByText("Step 6 of 10")).toBeVisible();
  79  | 
  80  |     // Step 6 Charges - defaults include parking
  81  |     await page.getByRole("button", { name: "Save & Continue" }).click();
  82  |     await expect(page.getByText("Step 7 of 10")).toBeVisible();
  83  | 
  84  |     // Step 7 Calculation
  85  |     await page.getByRole("button", { name: "Preview Calculation" }).click();
  86  |     await expect(page.getByText("Final: £314.39")).toBeVisible({ timeout: 15000 });
  87  |     await page.getByRole("button", { name: "Finalize Calculation" }).click();
  88  |     await expect(page.getByText("Final: £314.39")).toBeVisible();
  89  | 
  90  |     // Step 8 Review
  91  |     await page.getByRole("button", { name: "8. Review" }).click();
  92  |     await expect(page.getByText("Labour (hourly):")).toBeVisible();
  93  | 
  94  |     // Step 9 Approval
  95  |     await page.getByRole("button", { name: "9. Approval" }).click();
  96  |     await page.getByRole("button", { name: "Submit for Approval" }).click();
  97  | 
  98  |     // Step 10 Client Preview + PDF
  99  |     await page.getByRole("button", { name: "10. Client Preview" }).click();
  100 |     await page.getByRole("button", { name: "Draft PDF" }).click();
  101 |     await expect(page.getByText("Draft PDF generated successfully")).toBeVisible({ timeout: 10000 });
  102 |     await expect(page.getByRole("button", { name: "Download draft PDF" })).toBeVisible();
  103 | 
  104 |     await page.getByRole("button", { name: "Final PDF" }).click();
  105 |     await expect(page.getByText("Final PDF generated successfully")).toBeVisible({ timeout: 10000 });
  106 |     await expect(page.getByText("Final PDF ready")).toBeVisible();
  107 |   });
  108 | 
  109 |   test("validation blocks invalid step submission", async ({ page, request }) => {
  110 |     const token = await apiLogin(request, USERS.estimator.email, USERS.estimator.password);
  111 |     const headers = { Authorization: `Bearer ${token}` };
  112 |     const jobRes = await request.post(`${API}/api/v1/jobs`, {
  113 |       headers,
  114 |       data: {
  115 |         job_number: `JOB-VAL-${Date.now()}`,
  116 |         property_address: "",
  117 |       },
  118 |     });
  119 |     expect(jobRes.ok()).toBeTruthy();
  120 |     const job = (await jobRes.json()).data;
  121 | 
  122 |     await login(page, USERS.estimator.email, USERS.estimator.password);
  123 |     await page.goto(`/jobs/${job.id}/quote`);
  124 |     await expect(page.getByText("Step 1 of 10")).toBeVisible();
  125 | 
  126 |     await page.getByRole("button", { name: "Save & Continue" }).click();
  127 |     await expect(page.getByText("Client is required")).toBeVisible();
  128 |     await expect(page.getByText("Property address is required")).toBeVisible();
  129 |     await expect(page.getByText("Step 1 of 10")).toBeVisible();
  130 | 
  131 |     const clients = (await (await request.get(`${API}/api/v1/clients`, { headers })).json()).data;
> 132 |     await page.getByLabel(/^Client/).selectOption(clients[0].id);
      |                                      ^ Error: locator.selectOption: Test timeout of 120000ms exceeded.
  133 |     await page.getByLabel(/Property address/).fill("1 Validation Street");
  134 |     await page.getByRole("button", { name: "Save & Continue" }).click();
  135 |     await expect(page.getByText("Step 2 of 10")).toBeVisible();
  136 |     await page.getByRole("button", { name: "Save & Continue" }).click();
  137 |     await expect(page.getByText("Findings are required")).toBeVisible();
  138 |   });
  139 | 
  140 |   test("auto-save restores draft on reload", async ({ page, request }) => {
  141 |     const token = await apiLogin(request, USERS.estimator.email, USERS.estimator.password);
  142 |     const job = await createJobWithClient(request, token);
  143 | 
  144 |     await login(page, USERS.estimator.email, USERS.estimator.password);
  145 |     await page.goto(`/jobs/${job.id}/quote`);
  146 |     await expect(page.getByText("Step 1 of 10")).toBeVisible();
  147 | 
  148 |     const uniqueScope = `Unique scope ${Date.now()}`;
  149 |     await page.getByRole("button", { name: "2. Site Findings" }).click();
  150 |     await expect(page.getByText("Step 2 of 10")).toBeVisible();
  151 |     await page.getByPlaceholder("Engineer findings").fill("Draft finding text");
  152 |     await page.getByRole("button", { name: "3. Scope" }).click();
  153 |     await expect(page.getByText("Step 3 of 10")).toBeVisible();
  154 |     await page.getByLabel(/Scope of works/).fill(uniqueScope);
  155 |     await expect(page.getByText(/^Saved/)).toBeVisible({ timeout: 15000 });
  156 | 
  157 |     await page.reload();
  158 |     await page.getByRole("button", { name: "3. Scope" }).click();
  159 |     await expect(page.getByLabel(/Scope of works/)).toHaveValue(uniqueScope);
  160 |   });
  161 | 
  162 |   test("engineer cannot access quote wizard", async ({ page, request }) => {
  163 |     const estToken = await apiLogin(request, USERS.estimator.email, USERS.estimator.password);
  164 |     const job = await createJobWithClient(request, estToken);
  165 | 
  166 |     await login(page, USERS.engineer.email, USERS.engineer.password);
  167 |     await page.goto(`/jobs/${job.id}`);
  168 |     await expect(page.getByRole("link", { name: "Open Quote Wizard" })).toHaveCount(0);
  169 |     await page.goto(`/jobs/${job.id}/quote`);
  170 |     await expect(page).toHaveURL(new RegExp(`/jobs/${job.id}$`));
  171 |   });
  172 | 
  173 |   test("manager approval works after wizard submit", async ({ page, request }) => {
  174 |     const estToken = await apiLogin(request, USERS.estimator.email, USERS.estimator.password);
  175 |     const mgrToken = await apiLogin(request, USERS.manager.email, USERS.manager.password);
  176 |     const headers = (t: string) => ({ Authorization: `Bearer ${t}` });
  177 | 
  178 |     const job = await createJobWithClient(request, estToken);
  179 |     const trades = (await (await request.get(`${API}/api/v1/trades`, { headers: headers(estToken) })).json()).data;
  180 |     const plumbing = trades.find((t: { name: string }) => t.name === "Plumbing");
  181 | 
  182 |     const quoteRes = await request.post(`${API}/api/v1/quotes`, {
  183 |       headers: headers(estToken),
  184 |       data: {
  185 |         quote_number: `Q-MGR-${Date.now()}`,
  186 |         job_id: job.id,
  187 |         scope_items: [{ description: "Replace valve", client_visible: true }],
  188 |         labour_items: [{ trade_id: plumbing.id, labour_type: "hourly", number_of_engineers: 1, hours_on_site: 2 }],
  189 |         material_items: [{ material_name: "Valve", quantity: 1, unit_cost: 82.49, markup_type: "percentage", markup_value: 20 }],
  190 |         charges: { parking_required: true, parking_type: "hourly", parking_rate_per_hour: 6.5, parking_hours: 2 },
  191 |       },
  192 |     });
  193 |     const quote = (await quoteRes.json()).data;
  194 | 
  195 |     await request.post(`${API}/api/v1/calculations/finalize`, { headers: headers(estToken), data: { quote_id: quote.id } });
  196 |     await request.post(`${API}/api/v1/quotes/${quote.id}/submit-for-approval`, { headers: headers(estToken), data: {} });
  197 | 
  198 |     const approve = await request.post(`${API}/api/v1/quotes/${quote.id}/approve`, {
  199 |       headers: headers(mgrToken),
  200 |       data: { reason: "Approved in wizard test" },
  201 |     });
  202 |     expect(approve.ok()).toBeTruthy();
  203 |     expect((await approve.json()).data.status).toBe("approved");
  204 | 
  205 |     const snaps = await request.get(`${API}/api/v1/quotes/${quote.id}/snapshots`, { headers: headers(estToken) });
  206 |     expect(snaps.ok()).toBeTruthy();
  207 |     const snapBody = await snaps.json();
  208 |     expect(snapBody.data[0].formula_breakdown).toBeTruthy();
  209 |     expect(snapBody.data[0].input_snapshot).toBeTruthy();
  210 |     expect(snapBody.data[0].rule_snapshot).toBeTruthy();
  211 |     expect(snapBody.data[0].output_snapshot).toBeTruthy();
  212 |     expect(snapBody.data[0].calculated_by).toBeTruthy();
  213 |     expect(snapBody.data[0].calculated_at).toBeTruthy();
  214 |   });
  215 | });
  216 | 
```