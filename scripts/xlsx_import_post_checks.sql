-- Post-import verification queries for XLSX rate rule rollout.
-- Run against staging/production after scripts/import_quote_calculator_rules.py.

-- 1) Rules by formula_source
SELECT formula_source, COUNT(*) AS rule_count
FROM rate_rules
GROUP BY formula_source
ORDER BY formula_source;

-- 2) Active vs inactive rules
SELECT is_active, COUNT(*) AS rule_count
FROM rate_rules
GROUP BY is_active
ORDER BY is_active DESC;

-- 3) Deactivated simplified rules (expected after full rollout with --deactivate-existing)
SELECT COUNT(*) AS deactivated_simplified_rules
FROM rate_rules
WHERE formula_source = 'simplified'
  AND is_active = FALSE;

-- 4) Active XLSX rules for master helper version
SELECT COUNT(*) AS active_xlsx_rules
FROM rate_rules
WHERE formula_source = 'xlsx'
  AND version = 'xlsx-master-helper-1.7'
  AND is_active = TRUE;

-- Expected: active_xlsx_rules = 2528

-- 5) Lambert + Carpenter sanity check
SELECT
    rr.id,
    c.name AS client_name,
    t.name AS trade_name,
    rr.formula_source,
    rr.is_active,
    rr.hourly_rate,
    rr.direct_daily_cost,
    rr.client_fee_pct,
    rr.version
FROM rate_rules rr
JOIN clients c ON c.id = rr.client_id
JOIN trades t ON t.id = rr.trade_id
WHERE c.name ILIKE '%Lambert%'
  AND t.name = 'Carpenter'
ORDER BY rr.is_active DESC, rr.created_at DESC;

-- 6) Duplicate active client/trade pairs (should return zero rows)
SELECT client_id, trade_id, COUNT(*) AS active_count
FROM rate_rules
WHERE is_active = TRUE
GROUP BY client_id, trade_id
HAVING COUNT(*) > 1;

-- 7) Latest XLSX import audit entry
SELECT id, action, entity_type, new_value, created_at
FROM audit_logs
WHERE action IN ('xlsx_import_started', 'xlsx_import_completed', 'xlsx_import_failed')
ORDER BY created_at DESC
LIMIT 5;
