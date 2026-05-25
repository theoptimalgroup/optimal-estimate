# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: rules-page.spec.ts >> Rules API >> list includes client_name, trade_name, and status filters
- Location: e2e/rules-page.spec.ts:156:7

# Error details

```
Error: expect(received).toBeTruthy()

Received: undefined
```

# Test source

```ts
  64  | 
  65  |     const dataRows = page.locator("tbody tr").filter({ has: page.getByRole("link", { name: "View rule" }) });
  66  |     const initialCount = await dataRows.count();
  67  |     expect(initialCount).toBeGreaterThan(1);
  68  | 
  69  |     await page.locator("select").nth(0).selectOption(atkinson.id);
  70  |     await expect(page.getByRole("cell", { name: "Atkinson McLeod" }).first()).toBeVisible();
  71  |     await expect(page.getByRole("cell", { name: "Napier Watt" })).toHaveCount(0);
  72  |     const clientFilteredCount = await dataRows.count();
  73  |     expect(clientFilteredCount).toBeLessThan(initialCount);
  74  | 
  75  |     await page.locator("select").nth(1).selectOption(multiTrader.id);
  76  |     await expect(page.getByRole("cell", { name: "Carpenter" })).toHaveCount(0);
  77  |     const tradeFilteredCount = await dataRows.count();
  78  |     expect(tradeFilteredCount).toBeLessThan(clientFilteredCount);
  79  | 
  80  |     await page.locator("select").nth(0).selectOption("");
  81  |     await page.locator("select").nth(1).selectOption("");
  82  |     await page.getByPlaceholder("Search by version").fill("global-fallback");
  83  |     await expect(page.getByRole("link", { name: "global-fallback-1.0" })).toBeVisible();
  84  |     await expect(dataRows).toHaveCount(1);
  85  |   });
  86  | 
  87  |   test("empty state renders", async ({ page }) => {
  88  |     await page.route("**/api/v1/rules**", async (route) => {
  89  |       await route.fulfill({
  90  |         status: 200,
  91  |         contentType: "application/json",
  92  |         body: JSON.stringify({
  93  |           success: true,
  94  |           data: [
  95  |             {
  96  |               id: "00000000-0000-0000-0000-000000000001",
  97  |               client_id: null,
  98  |               trade_id: null,
  99  |               client_name: null,
  100 |               trade_name: null,
  101 |               version: "global-fallback-1.0",
  102 |               hourly_rate: "65.00",
  103 |               half_day_rate: "240.00",
  104 |               day_rate: "450.00",
  105 |               material_markup_type: "percentage",
  106 |               material_markup_value: "10.00",
  107 |               vat_rate: "20.00",
  108 |               active_from: "2024-01-01",
  109 |               active_to: null,
  110 |               is_active: true,
  111 |             },
  112 |           ],
  113 |           meta: { page: 1, page_size: 50, total: 1, total_pages: 1, client_specific_count: 0 },
  114 |         }),
  115 |       });
  116 |     });
  117 | 
  118 |     await login(page, USERS.admin.email, USERS.admin.password);
  119 |     await page.goto("/rules");
  120 | 
  121 |     await expect(page.getByText(EMPTY_STATE_MESSAGE)).toBeVisible();
  122 |     await expect(page.locator("tbody td").filter({ hasText: /^Global$/ }).first()).toBeVisible();
  123 |   });
  124 | 
  125 |   test("client and trade names appear", async ({ page }) => {
  126 |     await login(page, USERS.admin.email, USERS.admin.password);
  127 |     await page.goto("/rules");
  128 | 
  129 |     await expect(page.getByRole("cell", { name: "Atkinson McLeod" }).first()).toBeVisible();
  130 |     await expect(page.getByRole("cell", { name: "Multi-trader" }).first()).toBeVisible();
  131 |     await expect(page.locator("tbody td").filter({ hasText: /^Global$/ }).first()).toBeVisible();
  132 |     await expect(page.locator("tbody td").filter({ hasText: /^All trades$/ }).first()).toBeVisible();
  133 |   });
  134 | 
  135 |   test("active and inactive status displays correctly", async ({ page }) => {
  136 |     await login(page, USERS.admin.email, USERS.admin.password);
  137 |     await page.goto("/rules");
  138 | 
  139 |     const activeBadges = page.locator("tbody span").filter({ hasText: /^Active$/ });
  140 |     const inactiveBadges = page.locator("tbody span").filter({ hasText: /^Inactive$/ });
  141 | 
  142 |     await expect(activeBadges.first()).toBeVisible();
  143 |     await expect(inactiveBadges).toHaveCount(0);
  144 | 
  145 |     await page.locator("select").nth(2).selectOption("false");
  146 |     await expect(inactiveBadges.first()).toBeVisible();
  147 |     await expect(activeBadges).toHaveCount(0);
  148 | 
  149 |     await page.locator("select").nth(2).selectOption("all");
  150 |     await expect(activeBadges.first()).toBeVisible();
  151 |     await expect(inactiveBadges.first()).toBeVisible();
  152 |   });
  153 | });
  154 | 
  155 | test.describe("Rules API", () => {
  156 |   test("list includes client_name, trade_name, and status filters", async ({ request }) => {
  157 |     const token = await apiLogin(request, USERS.admin.email, USERS.admin.password);
  158 |     const headers = { Authorization: `Bearer ${token}` };
  159 | 
  160 |     const body = await (await request.get(`${API}/api/v1/rules`, { headers })).json();
  161 |     const named = body.data.find((r: { client_name?: string | null }) => r.client_name);
  162 |     expect(named.client_name).toBeTruthy();
  163 |     expect(named.trade_name).toBeTruthy();
> 164 |     expect(body.data.find((r: { client_name: null }) => r.client_name === null)).toBeTruthy();
      |                                                                                  ^ Error: expect(received).toBeTruthy()
  165 | 
  166 |     const active = await (await request.get(`${API}/api/v1/rules?is_active=true`, { headers })).json();
  167 |     expect(active.data.every((r: { is_active: boolean }) => r.is_active)).toBe(true);
  168 | 
  169 |     const inactive = await (await request.get(`${API}/api/v1/rules?is_active=false`, { headers })).json();
  170 |     if (inactive.data.length > 0) {
  171 |       expect(inactive.data.every((r: { is_active: boolean }) => !r.is_active)).toBe(true);
  172 |     }
  173 |   });
  174 | });
  175 | 
```