# XLSX Import Runbook

Operational guide for rolling out XLSX rate rules from `docs/1.7 MASTER HELPER.xlsx` into staging and production.

**Related assets**

| Asset | Purpose |
|-------|---------|
| `scripts/import_quote_calculator_rules.py` | Import clients, trades, and 2,528 XLSX rules |
| `scripts/export_rate_rules.py` | Pre-import JSON backup of `rate_rules` |
| `scripts/xlsx_import_post_checks.sql` | Post-import SQL verification |
| `backend/alembic/versions/002_xlsx_rate_rule_fields.py` | Schema migration (must run first) |
| `docs/XLSX_RULE_GAP_ANALYSIS.md` | Formula parity reference |

**Expected full import size:** 158 clients × 16 trades = **2,528 active XLSX rules** (`formula_source = xlsx`, version `xlsx-master-helper-1.7`).

---

## 1. Prerequisites

- [ ] Migration `002` applied: `cd backend && alembic upgrade head`
- [ ] Workbook present: `docs/1.7 MASTER HELPER.xlsx`
- [ ] Backend venv active and `DATABASE_URL` points at target environment
- [ ] Admin access to staging/production database
- [ ] XLSX parity tests passing locally: `cd backend && pytest tests/unit/test_xlsx_regression.py -q`

### Environment variables

```bash
# Local docker compose
export DATABASE_URL=postgresql+psycopg2://estimate:estimate_dev@localhost:5432/estimate_tool

# Staging (example — use Key Vault / CI secret in practice)
export DATABASE_URL='postgresql+psycopg2://estimate_app:<password>@estimate-staging.postgres.database.azure.com:5432/estimate_tool?sslmode=require'

# Optional: recorded in audit_logs.new_value.initiated_by
export IMPORT_INITIATED_BY="your.name@optimal.example"
```

---

## 2. Pre-import backup / export

**Do not skip.** Full rollout uses `--deactivate-existing`, which sets `is_active = false` on every existing rule.

### Option A — Application JSON export (recommended for rollback)

```bash
cd /path/to/Estimate_tool
export DATABASE_URL='...'
python scripts/export_rate_rules.py \
  --output backups/rate_rules_pre_xlsx_$(date +%Y%m%d_%H%M%S).json
```

Verify row count in the export file matches current DB:

```bash
python -c "import json,sys; d=json.load(open(sys.argv[1])); print(d['row_count'])" backups/rate_rules_*.json
```

### Option B — PostgreSQL table dump

```bash
pg_dump "$DATABASE_URL" \
  --table=rate_rules \
  --data-only \
  --column-inserts \
  --file=backups/rate_rules_$(date +%Y%m%d_%H%M%S).sql
```

### Option C — Full database snapshot (production)

Use Azure PostgreSQL backup / point-in-time restore capability before production import. Document the restore window in your change ticket.

### Pre-import baseline counts (record in change ticket)

```sql
SELECT formula_source, is_active, COUNT(*) FROM rate_rules GROUP BY 1, 2 ORDER BY 1, 2;
SELECT COUNT(*) FROM rate_rules WHERE is_active = TRUE;
```

---

## 3. Dry-run (no DB writes)

Parse the workbook and confirm expected dimensions **before** touching the database.

```bash
cd /path/to/Estimate_tool
python scripts/import_quote_calculator_rules.py --dry-run
```

**Expected output:**

```
[DRY RUN] clients=158 trades=16 created=0 updated=0 would_create=2528 deactivated=0
```

Optional scoped dry-runs:

```bash
# Lambert only (16 rules)
python scripts/import_quote_calculator_rules.py --dry-run --client Lambert

# Carpenter only (158 rules)
python scripts/import_quote_calculator_rules.py --dry-run --trade Carpenter
```

---

## 4. Staging import

### 4.1 Pilot import (Lambert + Carpenter only)

Validate end-to-end on staging before full rollout:

```bash
export DATABASE_URL='...staging...'
export IMPORT_INITIATED_BY="your.name@optimal.example"

python scripts/export_rate_rules.py --output backups/staging_pre_lambert_pilot.json

python scripts/import_quote_calculator_rules.py \
  --client Lambert \
  --trade Carpenter \
  --overwrite
```

Complete **Section 6 UI checklist** and API preview checks before proceeding.

### 4.2 Full staging rollout

```bash
python scripts/export_rate_rules.py --output backups/staging_pre_xlsx_full.json

python scripts/import_quote_calculator_rules.py \
  --deactivate-existing \
  --overwrite \
  --confirm-destructive
```

> **Destructive import guard:** Without `--confirm-destructive`, the script prompts interactively — type `YES` to proceed. This is required whenever `--deactivate-existing` is used or a full import runs with `--overwrite`.

Run post-import SQL checks (Section 5), then UI checklist (Section 6).

---

## 5. Post-import SQL checks

Run against staging (then production after go-live):

```bash
psql "$DATABASE_URL" -f scripts/xlsx_import_post_checks.sql
```

Or run queries individually:

### 5.1 Count rules by `formula_source`

```sql
SELECT formula_source, COUNT(*) AS rule_count
FROM rate_rules
GROUP BY formula_source
ORDER BY formula_source;
```

**Expected after full rollout:** ~2,528 rows with `formula_source = 'xlsx'` (plus any inactive simplified rows).

### 5.2 Count active rules

```sql
SELECT is_active, COUNT(*) AS rule_count
FROM rate_rules
GROUP BY is_active
ORDER BY is_active DESC;
```

**Expected:** `is_active = true` count ≈ **2,528** (active XLSX rules).

### 5.3 Count deactivated simplified rules

```sql
SELECT COUNT(*) AS deactivated_simplified_rules
FROM rate_rules
WHERE formula_source = 'simplified'
  AND is_active = FALSE;
```

**Expected:** equals the number of previously active simplified rules (seed + manual rules).

### 5.4 Verify 2,528 XLSX rules imported

```sql
SELECT COUNT(*) AS active_xlsx_rules
FROM rate_rules
WHERE formula_source = 'xlsx'
  AND version = 'xlsx-master-helper-1.7'
  AND is_active = TRUE;
```

**Pass criteria:** `active_xlsx_rules = 2528`

### 5.5 Lambert + Carpenter rule sanity

```sql
SELECT c.name, t.name, rr.formula_source, rr.is_active, rr.hourly_rate,
       rr.direct_daily_cost, rr.client_fee_pct, rr.version
FROM rate_rules rr
JOIN clients c ON c.id = rr.client_id
JOIN trades t ON t.id = rr.trade_id
WHERE c.name ILIKE '%Lambert%'
  AND t.name = 'Carpenter'
ORDER BY rr.is_active DESC, rr.created_at DESC;
```

**Expected (active row):**

| Field | Value |
|-------|-------|
| `formula_source` | `xlsx` |
| `hourly_rate` | 95.00 |
| `direct_daily_cost` | 239.40 |
| `client_fee_pct` | 0 |
| `version` | `xlsx-master-helper-1.7` |

### 5.6 No duplicate active client/trade pairs

```sql
SELECT client_id, trade_id, COUNT(*) AS active_count
FROM rate_rules
WHERE is_active = TRUE
GROUP BY client_id, trade_id
HAVING COUNT(*) > 1;
```

**Pass criteria:** zero rows.

### 5.7 Import audit log entries

```sql
SELECT action, new_value->>'initiated_by' AS initiated_by,
       new_value->'stats' AS stats, created_at
FROM audit_logs
WHERE action IN ('xlsx_import_started', 'xlsx_import_completed', 'xlsx_import_failed')
ORDER BY created_at DESC
LIMIT 5;
```

**Pass criteria:** matching `xlsx_import_started` + `xlsx_import_completed` pair for the rollout, with stats showing expected counts.

---

## 6. UI verification checklist — Lambert + Carpenter

Use staging after pilot or full import. Log in as **Estimator** or **Admin** (not Engineer for internal view).

### 6.1 Create / open a quote

- [ ] Client: **Lambert Chartered Surveyors**
- [ ] Trade: **Carpenter**
- [ ] Labour: hourly, 1 engineer, 2 hours
- [ ] No materials, no charges

### 6.2 Calculation preview API / wizard

- [ ] Preview returns `formula_source: "xlsx"`
- [ ] `labour_charge_to_client` = **£190.00**
- [ ] `overhead_cost` = **£57.00**
- [ ] `profit_gbp` = **£132.00**
- [ ] `profit_pct` = **69.47%**
- [ ] `internal_notes` contains `HOURLY QUOTE HELPER USED`

**API smoke test:**

```bash
curl -s -X POST "$API_BASE/api/v1/calculations/preview" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "<lambert_client_uuid>",
    "trade_id": "<carpenter_trade_uuid>",
    "labour_items": [{"labour_type":"hourly","number_of_engineers":1,"hours_on_site":2}],
    "material_items": [],
    "charges": null
  }' | jq '.data | {formula_source, labour_charge_to_client, profit_gbp, profit_pct}'
```

### 6.3 Daily + congestion scenario

- [ ] Labour: day, 1 engineer, 1 day
- [ ] Congestion: £15
- [ ] `labour_charge_to_client` = **£400.00**
- [ ] `materials_parking_cc_charge` = **£20.00**
- [ ] `profit_gbp` = **£85.80**

### 6.4 Finalize + internal view

- [ ] Finalize calculation succeeds
- [ ] Quote internal view (`/quotes/{id}/internal`) shows:
  - Direct labour cost
  - Overhead cost
  - Client fee %
  - Denominator used
  - Profit £ / Profit %
  - XLSX internal notes

### 6.5 Client view — no leakage

- [ ] Client preview / PDF does **not** show:
  - Direct cost, overhead, denominator
  - Profit £ / Profit %
  - Internal notes
  - Supplier cost, markup, `rate_used`

---

## 7. Production import

Repeat staging steps with production `DATABASE_URL`:

1. Azure DB snapshot / PITR note recorded
2. `python scripts/export_rate_rules.py --output backups/prod_pre_xlsx_full.json`
3. Dry-run: `python scripts/import_quote_calculator_rules.py --dry-run`
4. Full import:

```bash
python scripts/import_quote_calculator_rules.py \
  --deactivate-existing \
  --overwrite \
  --confirm-destructive
```

5. Run Section 5 SQL checks — all must pass
6. Run Section 6 UI checklist on one Lambert quote
7. Attach audit log query results to change ticket

---

## 8. Rollback

Choose one path depending on what was deployed.

### Option A — Restore `rate_rules` JSON export

1. Deactivate all current rules:

```sql
UPDATE rate_rules SET is_active = FALSE;
```

2. Restore from backup using a one-off script or manual re-insert from `backups/rate_rules_pre_xlsx_*.json`. Contact platform team if a restore script is not yet automated.

3. Verify simplified rules are active again:

```sql
SELECT formula_source, is_active, COUNT(*) FROM rate_rules GROUP BY 1, 2;
```

### Option B — Deactivate XLSX, reactivate simplified

Use when simplified rules still exist but were deactivated (not deleted):

```sql
-- Deactivate XLSX rollout rules
UPDATE rate_rules
SET is_active = FALSE
WHERE formula_source = 'xlsx'
  AND version = 'xlsx-master-helper-1.7';

-- Reactivate previous simplified rules
UPDATE rate_rules
SET is_active = TRUE
WHERE formula_source = 'simplified';
```

Then verify no duplicate active client/trade pairs (Section 5.6).

### Option C — Restore PostgreSQL table dump

```bash
psql "$DATABASE_URL" -f backups/rate_rules_YYYYMMDD_HHMMSS.sql
```

### Option D — Azure point-in-time restore

For production catastrophic rollback, restore the PostgreSQL server to the pre-import timestamp. This affects all tables — use only if import caused broader issues.

### Post-rollback verification

- [ ] Existing simplified regression still works (Atkinson McLeod / Plumbing £314.39 if that seed rule remains active)
- [ ] Lambert quotes no longer use XLSX engine (if XLSX rules deactivated)
- [ ] Record rollback in change ticket with audit log timestamp

---

## 9. Import audit logging

The import script writes summary entries to `audit_logs` (CLI imports have `user_id = NULL`):

| Action | When |
|--------|------|
| `xlsx_import_started` | Before any rule writes |
| `xlsx_import_completed` | After successful commit |
| `xlsx_import_failed` | On error (includes `error` in `new_value`) |

`entity_type = rate_rule_import`. Payload includes:

- `workbook`, `rule_version`, `initiated_by`
- `stats`: clients, trades, created, updated, deactivated
- `timestamp`

API-managed rate rule CRUD continues to use per-rule audit actions (`rate_rule_created`, `rate_rule_updated`, etc.) via the admin UI/API.

---

## 10. Destructive import warning

The import script **blocks** destructive runs unless confirmed:

| Flag combination | Behaviour |
|------------------|-----------|
| `--deactivate-existing` | Interactive prompt: type `YES` |
| Full import + `--overwrite` (no `--client` / `--trade`) | Interactive prompt: type `YES` |
| Either of above + `--confirm-destructive` | Non-interactive (CI/automation); prints warning |

**CI / automation example (staging only):**

```bash
IMPORT_INITIATED_BY="github-actions-staging" \
python scripts/import_quote_calculator_rules.py \
  --deactivate-existing \
  --overwrite \
  --confirm-destructive
```

---

## 11. Sign-off checklist

| Step | Staging | Production |
|------|---------|------------|
| Pre-import backup exported | ☐ | ☐ |
| Dry-run = 2528 rules | ☐ | ☐ |
| Migration 002 applied | ☐ | ☐ |
| Import completed | ☐ | ☐ |
| SQL: 2528 active XLSX rules | ☐ | ☐ |
| SQL: no duplicate active pairs | ☐ | ☐ |
| Audit log started/completed | ☐ | ☐ |
| Lambert + Carpenter UI checklist | ☐ | ☐ |
| Client view no leakage | ☐ | ☐ |
| Change ticket updated | ☐ | ☐ |

**Rollout complete when all production sign-off boxes are checked.**
