# XLSX Rule Gap Analysis

Source workbook: [`docs/1.7 MASTER HELPER.xlsx`](../docs/1.7%20MASTER%20HELPER.xlsx)  
Reference implementation: `backend/app/engines/xlsx_quote_calculator.py`  
Regression tests: `backend/tests/unit/test_xlsx_regression.py`  
Import script: `scripts/import_quote_calculator_rules.py`

**Status: XLSX rules are NOT complete in the application engine.**  
The reference calculator and regression tests pass; the production calculation engine still diverges (see §7).

---

## 1. Workbook structure

| Sheet | Purpose |
|-------|---------|
| **QUOTE CALCULATOR** | Primary hourly / daily / subcontractor quote logic |
| **SLA TABLE** | Client commission/fee %, invoice rules, payment terms |
| **SUPPLY CHAIN** | Subcontractor directory (not used in calc engine today) |
| **EXTERNAL DELIVERY CHECKER** | External delivery pricing helper |
| **QUOTE STICKY NOTES** | Customer-facing note templates |
| **OPTIMAL CLEANING PRICES** | Cleaning price list |
| **HOMERUN CALL OUT CHARGES** | Postcode call-out fees |

---

## 2. Extracted master data

### 2.1 Clients (QUOTE CALCULATOR `AY:AZ` + SLA TABLE column A/F)

**95 clients** in QUOTE CALCULATOR lookup, **158 unique clients** when merged with SLA TABLE.

| Client | Client fee % |
|--------|--------------|
| Lambert Chartered Surveyors | 0% |
| Atkinson McLeod | 15% |
| Barnard & Marcus | 20% |
| Oliver Jaques | 0% (+ 10% client charge uplift) |
| Napier Watt | 0% |
| Private Customer | 0% |
| … | … |

Full list is imported by `scripts/import_quote_calculator_rules.py --dry-run` (158 clients × 16 trades = 2,528 rule rows).

### 2.2 Trades (`AN:AO` client hourly charge, `AP:AR` subcontractor cost, `AS:AT` direct cost)

| Trade | Hourly client rate (£) | Daily direct/subby cost (£) | Direct hourly cost (£) |
|-------|------------------------|-----------------------------|-------------------------|
| Carpenter | 95 | 239.40 | 30 |
| Doors, Windows & Locks | 95 | 239.40 | 30 |
| Drains & Blockages | 150 | 378.00 | 63 |
| Electrician | 110 | 277.20 | 46.20 |
| Fencing & Decking | 95 | 239.40 | 30 |
| Fire Certificate | 150 | 378.00 | 30 |
| Gardening | 95 | 239.40 | 30 |
| Gas Safe | 120 | 302.40 | 39.90 |
| Leak Investigation | 150 | 378.00 | 30 |
| Multi-trader | 95 | 239.40 | 30 |
| Painter & Decorator | 95 | 239.40 | 30 |
| Paths & Patios | 95 | 239.40 | 30 |
| Plasterer & Tiller | 95 | 239.40 | 30 |
| Plumber | 95 | 239.40 | 30 |
| Roof Investigation | 190 | 478.80 | 79.80 |
| Roofer | 100 | 252.00 | 42.00 |

**Subcontractor cost rule:** `subby_hourly = client_hourly × 42%`; `subby_daily = subby_hourly × 6`.

### 2.3 Overhead percentages (`AU:AV`)

| Mode | Overhead % |
|------|------------|
| Hourly (internal) | 30% |
| Daily up to 2 days | 20% |
| Daily 3+ days | 15% |
| Subcontractor hourly | 30% |
| Subcontractor daily | 20% |
| Subcontractor daily 3+ days | 15% |

### 2.4 Labourer direct costs (`AW:AX`)

| Item | Value |
|------|-------|
| Direct cost labourer (daily) | £150 |
| Direct cost labourer (hourly) | £18.75 |
| Total charge for labourer | £340 |

### 2.5 Other constants

| Rule | Value |
|------|-------|
| Material/parking/CC markup denominator | 20% (used as `(1 - client_fee - 0.20)`) |
| EAF hourly add-on | £1 |
| Oliver Jaques / OIG uplift | 10% on client charges |
| NHS overhead uplift | 15% multiplier on overhead |
| Client charge rounding | `MROUND(..., 5)` to nearest £5 |
| VAT | Not in QUOTE CALCULATOR core (app adds 20% separately) |

---

## 3. XLSX formulas vs application

### 3.1 Hourly labour (columns C–F)

| Step | XLSX formula | Application today |
|------|--------------|-------------------|
| Base labour | `F16 = hourly_rate × engineers × hours` | `engineers × hours × hourly_rate` ✓ |
| Overhead | `E21 = F16 × 30%` (×1.15 if NHS) | **Missing** |
| Client fee | `D22 = VLOOKUP(client)` | **Missing** |
| Charge to client (labour) | `MROUND(F16 / (1 - fee) × OJ_uplift, 5)` | Uses rate directly, no fee divisor, no MROUND ✗ |
| Cost to Optimal (labour) | `E26 = E17 + E21 - inputs + fee_allocation` | Not calculated ✗ |

### 3.2 Daily labour up to 2 days (columns I–M)

| Step | XLSX formula | Application today |
|------|--------------|-------------------|
| Direct cost | `M16 = daily_cost × engineers × days` | `engineers × days × day_rate` (partial — uses rule day_rate not XLSX direct cost) |
| Labourers | `M19 = AX5 × labourers × days` | Supported in `calculate_combined_labour` but rates not from rules |
| Overhead | `K25 = L22 × 20%` where `L22 = K21 / (1 - 0.2 - 0.2)` | **Missing** |
| Client labour charge | `M23 = MROUND(M22 / (1 - fee - 0.2), 5)` | Uses day_rate only ✗ |

### 3.3 Materials / parking / congestion

| Step | XLSX formula | Application today |
|------|--------------|-------------------|
| Input costs | `K22` parking, `K23` CC, `K24` materials | `QuoteCharge` + `QuoteMaterial` ✓ (inputs) |
| Client charge | `L25 = SUM(inputs) / (1 - fee - 0.2)` then `MROUND` | Materials: `% markup on cost`; parking/CC: flat/hourly — **no shared denominator** ✗ |
| Cost to Optimal | `K31 = SUM(inputs) + client_fee_allocation` | Charges passed through ✓ (no fee allocation) |

### 3.4 Profit

| Metric | XLSX | Application today |
|--------|------|-------------------|
| Profit £ | `client_total - cost_labour - cost_materials` | Not exposed; only material markup margin |
| Profit % | `profit / client_total` | `calculate_margin` on materials only |

### 3.5 Internal notes

XLSX builds strings like:

```
{client} Comms @ {fee}%
HOURLY QUOTE HELPER USED
BUDGET: Materials: £… / Parking: £… / CC: £… / OH: £…
TOTAL COST TO OPTIMAL: Labour etc: £… / Materials etc: £…
TOTAL CHARGE TO CLIENT: Labour: £… / Materials etc: £…
PROFIT ON JOB: £… / …%
```

Application stores free-text `internal_notes` on quotes but **does not auto-generate** these strings.

### 3.6 Subcontractor calculator (columns Y–AC)

Separate flow with OH rates on subcontractor charges (hourly 30%, daily 20%, 3+ days 15%), validation flag, and “who provides materials”. **Not implemented** in app.

---

## 4. Gap summary

### 4.1 Already supported

- Trade-specific hourly/day rate lookup via `rate_rules`
- Client + trade rule matching (`rules_engine.find_active_rule`)
- Basic hourly/day/half-day labour arithmetic
- Material quantity × unit cost + percentage/fixed markup
- Parking hourly/fixed, congestion/ULEZ/waste/travel/other charges as pass-through
- VAT on subtotal
- Combined engineer + labourer labour lines (engine only)
- Manual rate override with approval flag
- Minimum hours / minimum charge on labour

### 4.2 Partially supported

| Rule | Gap |
|------|-----|
| Day rate | App `day_rate` ≠ XLSX client charge; XLSX derives client charge via overhead + denominator |
| Labourer costs | Engine supports extra labourers; XLSX rates (£150/day, £18.75/hr) not in schema/seed |
| Material markup | App uses markup on cost; XLSX uses `(1 - client_fee - 0.20)` denominator on parking/materials/CC combined |
| Client list | Seed has 3 clients; XLSX has 158 |
| Trade list | Seed has 6 trades; XLSX has 16 |
| Margin / profit | App computes material markup margin only, not job-level profit |
| Internal notes | Manual entry only |

### 4.3 Missing

- Client fee / commission % per client (`AY:AZ`, SLA column F)
- Overhead % by labour mode (30% hourly, 20% daily, 15% extended daily)
- Oliver Jaques / OIG 10% client charge uplift
- NHS 15% overhead uplift
- EAF £1 hourly add-on
- `MROUND(..., 5)` client charge rounding
- Separate direct cost vs client charge rates (`AT` vs `AO`)
- Subcontractor 42% / ×6 cost derivation
- Daily 3+ days reduced overhead (15%)
- Subcontractor calculator (columns Y–AC)
- Auto-generated internal note blocks
- FIXFLO upload reminders from client lookup (`AY:BA`)
- Cleaning / Homerun call-out / external delivery pricing sheets

---

## 5. Schema changes required

Extend `rate_rules` and/or add `client_quote_settings`:

```sql
-- Proposed additions
client_fee_percentage NUMERIC(5,4)      -- on client or rate_rule
overhead_hourly_percentage NUMERIC(5,2)  -- default 30
overhead_daily_percentage NUMERIC(5,2)   -- default 20
overhead_daily_extended_percentage NUMERIC(5,2) -- default 15
direct_hourly_cost NUMERIC(12,2)        -- AT column
direct_day_cost NUMERIC(12,2)           -- AR column
labourer_hourly_cost NUMERIC(12,2)      -- default 18.75
labourer_day_cost NUMERIC(12,2)         -- default 150
client_charge_uplift_multiplier NUMERIC(4,2) -- 1.10 for OJ/OIG
material_charge_denominator NUMERIC(4,2)  -- default 0.20
apply_mround_to_fives BOOLEAN DEFAULT true
```

Extend `quotes` / calculation output:

```sql
profit_gbp NUMERIC(12,2)
profit_percentage NUMERIC(5,2)
cost_to_optimal_labour NUMERIC(12,2)
cost_to_optimal_materials NUMERIC(12,2)
overhead_total NUMERIC(12,2)
client_fee_total NUMERIC(12,2)
generated_internal_notes TEXT
```

---

## 6. Calculation engine changes required

1. Add `xlsx_quote_calculator` parity layer or refactor `build_calculation_breakdown` to:
   - Apply overhead before client charge
   - Divide by `(1 - client_fee - material_denominator)` for client-facing lines
   - Split **cost to Optimal** vs **charge to client**
   - Compute job-level profit £ and %
2. Wire client fee from client/rule record
3. Apply OJ/OIG and NHS modifiers from client name or flags
4. Apply `MROUND` to client charges
5. Generate internal notes from templates
6. Keep VAT as post-profit layer (XLSX sheet is ex-VAT; app adds VAT after subtotal)

---

## 7. Seed / import changes required

| Action | Status |
|--------|--------|
| Import 16 trades from XLSX | Script ready |
| Import 158 clients + fee % | Script ready (fee stored in future schema) |
| Import 2,528 client×trade rate rows | Script ready (`--dry-run` verified) |
| Map Lambert Chartered Surveyors + Carpenter | In XLSX; not in current seed |
| Deactivate legacy seed rules after import | Manual step post-import |

```bash
# Preview
python scripts/import_quote_calculator_rules.py --dry-run

# Import Lambert only (requires running Postgres)
python scripts/import_quote_calculator_rules.py --client Lambert

# Full import
python scripts/import_quote_calculator_rules.py
```

---

## 8. Regression tests (XLSX reference)

| Scenario | Expected (XLSX reference) | App engine |
|----------|---------------------------|------------|
| Lambert + Carpenter + hourly (1 eng, 2 hr) | Labour charge £190, profit £132 (69.47%) | ✗ £190 labour, no profit model |
| Lambert + Carpenter + daily 1 day | Labour charge £400, profit £80.80 (20.20%) | ✗ £239.40 day rate only |
| Lambert + Carpenter + daily + CC £15 | Materials charge £20, profit £85.80 | ✗ not matching |
| Material/parking denominator | Parking £65 + materials £292 → charge £445 | ✗ separate markups |
| Profit £ / % (OJ hourly sanity) | Charge £210, profit £152 (72.38%) | ✗ |

Run tests:

```bash
cd backend && pytest tests/unit/test_xlsx_regression.py -q
```

**Result:** 7 passed — reference calculator matches XLSX totals; app engine gap tests confirm divergence.

---

## 9. Acceptance checklist

| Item | Complete? |
|------|-----------|
| Gap analysis document | ✓ |
| XLSX data extracted (clients, trades, rates, OH, fees) | ✓ |
| Reference calculator | ✓ |
| Regression tests match XLSX totals | ✓ |
| Import script | ✓ |
| App calculation engine parity | **✗ Not complete** |
| Schema migration for new fields | **✗ Not started** |
| Full client/trade seed from XLSX | **✗ Script only** |

**Do not mark XLSX rules complete for production quoting until app engine tests replace `TestAppEngineXlsxGap` failures with parity assertions.**
