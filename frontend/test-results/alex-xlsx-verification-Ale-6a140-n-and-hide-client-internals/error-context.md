# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: alex-xlsx-verification.spec.ts >> Alex XLSX UI verification >> hourly, daily, and 3+ day quotes show XLSX internal breakdown and hide client internals
- Location: e2e/alex-xlsx-verification.spec.ts:182:7

# Error details

```
Error: expect(received).toBeTruthy()

Received: false
```

# Test source

```ts
  1   | import { test, expect } from "@playwright/test";
  2   | 
  3   | const API = "http://localhost:8000";
  4   | 
  5   | const USERS = {
  6   |   estimator: { email: "estimator@optimal.example", password: "estimate12345" },
  7   | };
  8   | 
  9   | async function apiLogin(request, email: string, password: string) {
  10  |   const res = await request.post(`${API}/api/v1/auth/login`, { data: { email, password } });
  11  |   expect(res.ok()).toBeTruthy();
  12  |   return (await res.json()).data.access_token as string;
  13  | }
  14  | 
  15  | async function ensureLambertCarpenterRule(request, token: string) {
  16  |   const headers = { Authorization: `Bearer ${token}` };
  17  |   let clients = (await (await request.get(`${API}/api/v1/clients`, { headers })).json()).data;
  18  |   let client = clients.find((c: { name: string }) => c.name.toLowerCase().includes("lambert"));
  19  |   if (!client) {
  20  |     const createClient = await request.post(`${API}/api/v1/clients`, {
  21  |       headers,
  22  |       data: { name: "Lamberts Chartered Surveyors", default_vat_rate: 20 },
  23  |     });
> 24  |     expect(createClient.ok()).toBeTruthy();
      |                               ^ Error: expect(received).toBeTruthy()
  25  |     client = (await createClient.json()).data;
  26  |   }
  27  | 
  28  |   let trades = (await (await request.get(`${API}/api/v1/trades`, { headers })).json()).data;
  29  |   let trade = trades.find((t: { name: string }) => t.name === "Carpenter");
  30  |   if (!trade) {
  31  |     const createTrade = await request.post(`${API}/api/v1/trades`, {
  32  |       headers,
  33  |       data: { name: "Carpenter", description: "Alex XLSX verification" },
  34  |     });
  35  |     expect(createTrade.ok()).toBeTruthy();
  36  |     trade = (await createTrade.json()).data;
  37  |   }
  38  | 
  39  |   const rulesRes = await request.get(`${API}/api/v1/rules`, { headers });
  40  |   const rules = (await rulesRes.json()).data;
  41  |   const existing = rules.find(
  42  |     (r: { client_id?: string; trade_id?: string; formula_source?: string }) =>
  43  |       r.client_id === client.id && r.trade_id === trade.id && r.formula_source === "xlsx",
  44  |   );
  45  |   if (!existing) {
  46  |     const createRule = await request.post(`${API}/api/v1/rules`, {
  47  |       headers,
  48  |       data: {
  49  |         client_id: client.id,
  50  |         trade_id: trade.id,
  51  |         version: "alex-e2e-xlsx",
  52  |         formula_source: "xlsx",
  53  |         hourly_rate: 95,
  54  |         day_rate: 239.4,
  55  |         direct_hourly_cost: 30,
  56  |         direct_daily_cost: 239.4,
  57  |         client_fee_pct: 0,
  58  |         hourly_overhead_pct: 0.3,
  59  |         daily_overhead_pct: 0.2,
  60  |         daily_overhead_long_job_pct: 0.15,
  61  |         labourer_hourly_cost: 18.75,
  62  |         labourer_daily_cost: 150,
  63  |         material_charge_denominator: 0.2,
  64  |         parking_charge_denominator: 0.2,
  65  |         congestion_charge_denominator: 0.2,
  66  |         mround_increment: 5,
  67  |         oj_uplift_pct: 10,
  68  |         nhs_overhead_uplift_pct: 15,
  69  |         eaf_flat_fee: 1,
  70  |         xlsx_client_name: "Lambert Chartered Surveyors",
  71  |         xlsx_trade_name: "Carpenter",
  72  |         material_markup_value: 20,
  73  |         vat_rate: 20,
  74  |         active_from: "2024-01-01",
  75  |         is_active: true,
  76  |       },
  77  |     });
  78  |     expect(createRule.ok()).toBeTruthy();
  79  |   }
  80  | 
  81  |   return { client, trade };
  82  | }
  83  | 
  84  | async function createQuoteFromPreview(
  85  |   request,
  86  |   token: string,
  87  |   clientId: string,
  88  |   tradeId: string,
  89  |   scenario: {
  90  |     label: string;
  91  |     labourType: "hourly" | "day";
  92  |     hours?: number;
  93  |     days?: number;
  94  |     labourers?: number;
  95  |     labourerDays?: number;
  96  |     materials?: number;
  97  |     congestion?: number;
  98  |   },
  99  | ) {
  100 |   const headers = { Authorization: `Bearer ${token}` };
  101 |   const jobRes = await request.post(`${API}/api/v1/jobs`, {
  102 |     headers,
  103 |     data: {
  104 |       job_number: `JOB-ALEX-${scenario.label}-${Date.now()}`,
  105 |       client_id: clientId,
  106 |       property_address: "The Factory, 1 Nile Street",
  107 |     },
  108 |   });
  109 |   expect(jobRes.ok()).toBeTruthy();
  110 |   const job = (await jobRes.json()).data;
  111 | 
  112 |   const labourItem: Record<string, unknown> = {
  113 |     labour_type: scenario.labourType,
  114 |     number_of_engineers: 1,
  115 |     number_of_labourers: scenario.labourers ?? 0,
  116 |     trade_id: tradeId,
  117 |   };
  118 |   if (scenario.labourType === "hourly") {
  119 |     labourItem.hours_on_site = scenario.hours ?? 1.5;
  120 |   } else {
  121 |     labourItem.days_on_site = scenario.days ?? 1;
  122 |     labourItem.labourer_days = scenario.labourerDays ?? scenario.days ?? 1;
  123 |   }
  124 | 
```