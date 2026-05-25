# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: rules-page.spec.ts >> Rules page >> filters update table
- Location: e2e/rules-page.spec.ts:55:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('link', { name: 'global-fallback-1.0' })
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for getByRole('link', { name: 'global-fallback-1.0' })

```

```yaml
- alert
- banner:
  - paragraph: Optimal Estimate Calculator
  - paragraph: Admin User · admin
  - button "Logout"
- complementary:
  - navigation:
    - link "Dashboard":
      - /url: /dashboard
    - link "Jobs":
      - /url: /jobs
    - link "Quotes":
      - /url: /quotes
    - link "Clients":
      - /url: /clients
    - link "Trades":
      - /url: /trades
    - link "Rules":
      - /url: /rules
- main:
  - heading "Rate Rules" [level=1]
  - paragraph: Pricing rules by client and trade. Global fallback applies when no match is found.
  - link "New Rule":
    - /url: /rules/new
  - textbox "Search client, alias, trade, version, or XLSX name"
  - combobox:
    - option "All clients" [selected]
    - option "Allen Heritage"
    - option "Apna Ghar"
    - option "Apnar Ghar"
    - option "Aspire"
    - option "Atkinson McLeod"
    - option "BPS"
    - option "Barnard & Marcus"
    - option "Barnard Marcus"
    - option "Bective"
    - option "Beresford Residential"
    - option "Berkshire Hathaway"
    - option "Blinkleys"
    - option "Blocshpere"
    - option "Blocsphere Property Management"
    - option "Bold & Reeces"
    - option "Bold and Reeces"
    - option "Brik Property Ltd"
    - option "Brinkley Estates"
    - option "Butler & Stag"
    - option "Butler & Stag LTD"
    - option "CAYSH"
    - option "CBRE"
    - option "CHISEL"
    - option "Campden Estates"
    - option "CareTech"
    - option "Caretech"
    - option "Carey Gardens Co-operative Ltd"
    - option "Carlisle"
    - option "Carter Gem"
    - option "Casa Londra"
    - option "Chamberland Residential"
    - option "Chelsea Heritage"
    - option "Chesterton"
    - option "Chisel"
    - option "Coopers of London"
    - option "Countrywide"
    - option "Daniel Watney"
    - option "Daniel Watney LLP"
    - option "Davies & Davies"
    - option "Dexters"
    - option "Direct Residential"
    - option "Dobbin and Sullivan Ltd"
    - option "Dolce Vita"
    - option "Douglas & Gordon"
    - option "Druce"
    - option "Easthaus"
    - option "Eddison White"
    - option "Emma's Estate Agents"
    - option "Evolve"
    - option "Evolve Housing"
    - option "Felicity J Lord"
    - option "First Union"
    - option "Fletchers"
    - option "Foster & Edward"
    - option "Foster & Edwards"
    - option "Frank Harris"
    - option "Garrett Whitelock"
    - option "Garrington"
    - option "Go View"
    - option "Hamptons"
    - option "Hamptons International"
    - option "Harrison Housing"
    - option "Hello Neighbour"
    - option "Henry Wiltshire"
    - option "Hestia"
    - option "Heywood & Partners"
    - option "Horniman"
    - option "ILGS Ltd T/A Newbrix"
    - option "ILGS Ltd TA Newbrix"
    - option "JC Living"
    - option "JD Group"
    - option "JDW"
    - option "JLL"
    - option "JSE"
    - option "JSE Property Management"
    - option "Jackson Stops & Staff"
    - option "Jacksons"
    - option "John D Wood"
    - option "Johns & CO"
    - option "Johns & Co"
    - option "KFH"
    - option "Key Property Consultants"
    - option "Kinleigh Folkard And Hayward (Block)"
    - option "Kinleigh Folkard and Hayward"
    - option "LDG"
    - option "Lamberts Chartered Surveyors"
    - option "Landstones"
    - option "Lee Abbey London"
    - option "Leo Estates Management"
    - option "Life Residential"
    - option "Lionsgate"
    - option "Lock Terrace"
    - option "Lurot Brand"
    - option "Lurot Brand DO NOT USE - BLACKLISTED"
    - option "MIH"
    - option "Maddison Brook"
    - option "Madison Brook"
    - option "Manage My Property"
    - option "Management Habitat Investments"
    - option "Marler & Marler"
    - option "Marsh & Parsons"
    - option "Martin & Co"
    - option "Mason & Fifth"
    - option "Mission Housing Limited"
    - option "NHS"
    - option "NHS Property Services"
    - option "Napier Watt"
    - option "Newbrix"
    - option "OIG"
    - option "Oliver Burn"
    - option "Oliver Burn Residential"
    - option "Oliver Jacques"
    - option "Oliver Jaques"
    - option "Orchard & Shipman"
    - option "Orlando Reid"
    - option "Portico"
    - option "Portico / Leaders"
    - option "Private Customer"
    - option "Property Maintenance & Management Services Ltd"
    - option "Purple Bricks"
    - option "Rampton Baseley"
    - option "Rampton Baseley Limited"
    - option "Rayners"
    - option "Referral Fee (5%)"
    - option "Regent Property"
    - option "Rendall & Rittner"
    - option "Right Now Residential"
    - option "Robertson Smith & Kempson"
    - option "Roupell Park"
    - option "Russell Simpson"
    - option "SW9"
    - option "SW9 Community Housing."
    - option "SWA Ltd"
    - option "Sigma / Simple Life"
    - option "Simple Life"
    - option "Sovreign Network Group"
    - option "Spurgeons"
    - option "Square Quarters"
    - option "Stirling Ackroyd"
    - option "Strangford Residence Management"
    - option "Strettons"
    - option "Strutt and Parker"
    - option "Swishbrook"
    - option "TLC"
    - option "TLC Estate Agents"
    - option "The Address"
    - option "Touchstone"
    - option "Trent Park Properties LLP"
    - option "Trotters Estates"
    - option "Victor Michael Limited"
    - option "WHR Property Management"
    - option "Warren Ltd"
    - option "Winkworth - Battersea"
    - option "Winkworth - Battersea, Clapham, Kennington, Pimlico & Westminster"
    - option "Winkworth - Newcross & Forest Hill"
    - option "Winkworth - Queens Park"
    - option "Winkworth - South Ken"
    - option "Winkworth - South Kensington"
  - combobox:
    - option "All trades" [selected]
    - option "Carpenter"
    - option "Doors, Windows & Locks"
    - option "Drains & Blockages"
    - option "Electrical"
    - option "Electrician"
    - option "Fencing & Decking"
    - option "Fire Certificate"
    - option "Gardening"
    - option "Gas Safe"
    - option "General Maintenance"
    - option "HVAC"
    - option "Handyman"
    - option "Leak Investigation"
    - option "Multi-trader"
    - option "Painter & Decorator"
    - option "Paths & Patios"
    - option "Plasterer & Tiller"
    - option "Plumber"
    - option "Plumbing"
    - option "Roof Investigation"
    - option "Roofer"
  - combobox:
    - option "All formula sources" [selected]
    - option "XLSX"
    - option "Simplified"
  - combobox:
    - option "All statuses"
    - option "Active" [selected]
    - option "Inactive"
  - textbox "Search by version": global-fallback
  - table:
    - rowgroup:
      - row "Client Trade Formula Version Hourly Rate Half-Day Rate Day Rate Material Markup VAT Rate Active From Active To Status Actions":
        - columnheader "Client"
        - columnheader "Trade"
        - columnheader "Formula"
        - columnheader "Version"
        - columnheader "Hourly Rate"
        - columnheader "Half-Day Rate"
        - columnheader "Day Rate"
        - columnheader "Material Markup"
        - columnheader "VAT Rate"
        - columnheader "Active From"
        - columnheader "Active To"
        - columnheader "Status"
        - columnheader "Actions"
    - rowgroup:
      - row "No rules match your filters.":
        - cell "No rules match your filters."
  - text: 0 rules
  - button "Previous" [disabled]
  - text: Page 1 of 0
  - button "Next" [disabled]
```

# Test source

```ts
  1   | import { test, expect } from "@playwright/test";
  2   | 
  3   | const API = "http://localhost:8000";
  4   | 
  5   | const USERS = {
  6   |   admin: { email: "admin@optimal.example", password: "admin12345" },
  7   |   estimator: { email: "estimator@optimal.example", password: "estimate12345" },
  8   | };
  9   | 
  10  | const EMPTY_STATE_MESSAGE =
  11  |   "No client-specific rules found. Add rate rules for each client and trade.";
  12  | 
  13  | async function login(page, email: string, password: string) {
  14  |   await page.goto("/login");
  15  |   await page.getByLabel("Email").fill(email);
  16  |   await page.getByLabel("Password").fill(password);
  17  |   await page.getByRole("button", { name: "Login" }).click();
  18  |   await expect(page).toHaveURL(/\/dashboard/);
  19  | }
  20  | 
  21  | async function apiLogin(request, email: string, password: string) {
  22  |   const res = await request.post(`${API}/api/v1/auth/login`, { data: { email, password } });
  23  |   expect(res.ok()).toBeTruthy();
  24  |   return (await res.json()).data.access_token as string;
  25  | }
  26  | 
  27  | async function fetchMasterData(request, token: string) {
  28  |   const headers = { Authorization: `Bearer ${token}` };
  29  |   const clients = (await (await request.get(`${API}/api/v1/clients`, { headers })).json()).data;
  30  |   const trades = (await (await request.get(`${API}/api/v1/trades`, { headers })).json()).data;
  31  |   return { clients, trades };
  32  | }
  33  | 
  34  | test.describe("Rules page", () => {
  35  |   test("admin sees actions", async ({ page }) => {
  36  |     await login(page, USERS.admin.email, USERS.admin.password);
  37  |     await page.goto("/rules");
  38  | 
  39  |     await expect(page.getByRole("link", { name: "New Rule" })).toBeVisible();
  40  |     await expect(page.getByRole("link", { name: "View rule" }).first()).toBeVisible();
  41  |     await expect(page.getByRole("link", { name: "Edit rule" }).first()).toBeVisible();
  42  |     await expect(page.getByRole("button", { name: /Deactivate rule|Activate rule/ }).first()).toBeVisible();
  43  |   });
  44  | 
  45  |   test("estimator does not see edit actions", async ({ page }) => {
  46  |     await login(page, USERS.estimator.email, USERS.estimator.password);
  47  |     await page.goto("/rules");
  48  | 
  49  |     await expect(page.getByRole("link", { name: "View rule" }).first()).toBeVisible();
  50  |     await expect(page.getByRole("link", { name: "New Rule" })).toHaveCount(0);
  51  |     await expect(page.getByRole("link", { name: "Edit rule" })).toHaveCount(0);
  52  |     await expect(page.getByRole("button", { name: /Deactivate rule|Activate rule/ })).toHaveCount(0);
  53  |   });
  54  | 
  55  |   test("filters update table", async ({ page, request }) => {
  56  |     const token = await apiLogin(request, USERS.admin.email, USERS.admin.password);
  57  |     const { clients, trades } = await fetchMasterData(request, token);
  58  |     const atkinson = clients.find((c: { name: string }) => c.name === "Atkinson McLeod");
  59  |     const multiTrader = trades.find((t: { name: string }) => t.name === "Multi-trader");
  60  | 
  61  |     await login(page, USERS.admin.email, USERS.admin.password);
  62  |     await page.goto("/rules");
  63  |     await expect(page.getByRole("link", { name: "View rule" }).first()).toBeVisible();
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
> 83  |     await expect(page.getByRole("link", { name: "global-fallback-1.0" })).toBeVisible();
      |                                                                           ^ Error: expect(locator).toBeVisible() failed
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
  164 |     expect(body.data.find((r: { client_name: null }) => r.client_name === null)).toBeTruthy();
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