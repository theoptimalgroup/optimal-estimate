# XLSX Full Import Runbook

Operational guide to import **all 158 clients**, **16 trades**, and **2,528 XLSX rate rules** from `docs/1.7 MASTER HELPER.xlsx`.

## Expected outcome

| Entity | Count |
|--------|------:|
| Clients (canonical names) | 158 |
| Trades | 16 |
| XLSX rate rules | 2,528 |
| Lambert alias | `Lambert Chartered Surveyors` → `Lamberts Chartered Surveyors` |

Every imported XLSX rule must have:

- `formula_source = 'xlsx'`
- `client_id` NOT NULL
- `trade_id` NOT NULL
- `xlsx_client_name` preserved from workbook
- `xlsx_trade_name` preserved from workbook

---

## 1. Backup / export

```bash
cd /path/to/Estimate_tool
python scripts/export_rate_rules.py \
  --output backups/rate_rules_pre_full_xlsx_$(date +%Y%m%d_%H%M%S).json
```

Optional PostgreSQL dump:

```bash
docker exec estimate_tool-postgres-1 pg_dump -U estimate -d estimate_tool \
  --table=rate_rules --data-only --column-inserts \
  > backups/rate_rules_$(date +%Y%m%d_%H%M%S).sql
```

---

## 2. Apply migrations

Required revisions:

- `002` — XLSX rate rule fields
- `003` — `client_aliases`
- `004` — search indexes

```bash
docker exec estimate_tool-backend-1 alembic upgrade head
docker exec estimate_tool-backend-1 alembic current
# Expected: 004 (head)
```

---

## 3. Dry run

```bash
python scripts/import_quote_calculator_rules.py --dry-run
```

Expected summary:

```text
clients=158 trades=16 rules_would_create=2528
```

Pilot (Lambert only):

```bash
python scripts/import_quote_calculator_rules.py --dry-run --client Lambert
# clients=1 trades=16 rules_would_create=16
```

---

## 4. Full import (Docker)

Because host port `5432` may not reach the Docker Postgres role, run inside the backend container:

```bash
docker exec estimate_tool-backend-1 mkdir -p /import/scripts /import/docs
docker cp scripts/import_quote_calculator_rules.py estimate_tool-backend-1:/import/scripts/
docker cp "docs/1.7 MASTER HELPER.xlsx" estimate_tool-backend-1:/import/docs/

docker exec -w /app estimate_tool-backend-1 python -c "
from pathlib import Path
import importlib.util
spec = importlib.util.spec_from_file_location('iqcr', '/import/scripts/import_quote_calculator_rules.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.XLSX_PATH = Path('/import/docs/1.7 MASTER HELPER.xlsx')
stats = mod.import_rules(
    dry_run=False,
    overwrite=True,
    deactivate_existing=True,
    initiated_by='full-import-runbook',
)
print(mod._format_summary(stats, dry_run=False))
"
```

For non-interactive full rollout from host (when `DATABASE_URL` reaches Docker Postgres):

```bash
python scripts/import_quote_calculator_rules.py \
  --overwrite \
  --deactivate-existing \
  --confirm-destructive
```

---

## 5. Post-import SQL checks

```sql
SELECT COUNT(*) FROM clients;
SELECT COUNT(*) FROM trades;
SELECT COUNT(*) FROM rate_rules WHERE formula_source = 'xlsx' AND is_active = TRUE;

SELECT COUNT(*) FROM rate_rules
WHERE formula_source = 'xlsx' AND (client_id IS NULL OR trade_id IS NULL);

SELECT name FROM clients WHERE LOWER(name) LIKE '%lambert%';
SELECT alias_name FROM client_aliases WHERE LOWER(alias_name) LIKE '%lambert%';

SELECT COUNT(*) FROM rate_rules
WHERE LOWER(xlsx_client_name) LIKE '%lambert%' AND formula_source = 'xlsx';
```

Expected:

- clients ≈ 158 (+ any seed clients if not removed)
- trades ≈ 16 (+ seed trades)
- xlsx active rules = 2528 (+ any seed rules if not deactivated)
- null client_id/trade_id on xlsx rules = 0
- Lambert canonical client = `Lamberts Chartered Surveyors`

---

## 6. API checks

```bash
curl "http://localhost:8000/api/v1/clients?search=lambert"
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/rules?search=lambert&formula_source=xlsx"
curl "http://localhost:8000/api/v1/trades?search=carpenter"
```

---

## 7. UI checks

- [ ] `/clients` — search `lambert` shows **Lamberts Chartered Surveyors**
- [ ] Quote wizard — client search finds Lamberts; trade search finds Carpenter
- [ ] `/rules` — filter formula source `xlsx`, search `lambert`, paginate through results
- [ ] Alex row 11 internal notes parity still passes

---

## 8. Rollback

1. Restore `rate_rules` from JSON export or SQL dump.
2. Optionally deactivate all XLSX rules:

```sql
UPDATE rate_rules SET is_active = FALSE WHERE formula_source = 'xlsx';
```

3. Re-activate previous rules from backup if needed.

---

## 9. Automated verification

```bash
cd backend
pytest tests/integration/test_xlsx_full_import.py -q
pytest tests/integration/test_alex_xlsx_app_parity.py -q
pytest tests/integration/test_internal_notes.py -q
```
