#!/usr/bin/env bash
# local_import_xlsx_rules.sh — Run XLSX rate-rule import from the host Mac terminal.
#
# The Docker Compose DATABASE_URL uses hostname "postgres" which only resolves
# inside the Docker network.  This script detects the mapped localhost port and
# rewrites DATABASE_URL to postgresql+psycopg2://<user>:<pass>@localhost:<port>/<db>
# before calling scripts/import_quote_calculator_rules.py.
#
# Usage:
#   ./scripts/local_import_xlsx_rules.sh --dry-run
#   ./scripts/local_import_xlsx_rules.sh --overwrite
#   ./scripts/local_import_xlsx_rules.sh --overwrite --deactivate-existing
#   ./scripts/local_import_xlsx_rules.sh --dry-run --client "Acme"
#
# All flags are forwarded to import_quote_calculator_rules.py.
# --overwrite triggers a backup reminder + YES confirmation before the Python
# script runs; --confirm-destructive is then added automatically to skip
# Python's own interactive prompt.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
XLSX_PATH="${PROJECT_ROOT}/docs/1.7 MASTER HELPER.xlsx"
PYTHON_SCRIPT="${SCRIPT_DIR}/import_quote_calculator_rules.py"

# Prefer the backend virtual-env Python (has psycopg2, openpyxl, sqlalchemy, etc.)
# Fall back to whatever python3 is on PATH.
VENV_PYTHON="${PROJECT_ROOT}/backend/.venv/bin/python3"
if [ -x "$VENV_PYTHON" ]; then
  PYTHON="$VENV_PYTHON"
else
  PYTHON="python3"
fi

# ---------------------------------------------------------------------------
# Parse flags — track --dry-run and --overwrite; forward everything else.
# ---------------------------------------------------------------------------
DRY_RUN=false
OVERWRITE=false
PASS_THROUGH=()

for arg in "$@"; do
  case "$arg" in
    --dry-run)   DRY_RUN=true  ;;
    --overwrite) OVERWRITE=true ;;
  esac
  PASS_THROUGH+=("$arg")
done

# ---------------------------------------------------------------------------
# Check that the postgres container is running.
# ---------------------------------------------------------------------------
POSTGRES_UP=false
if docker compose -f "${PROJECT_ROOT}/docker-compose.yml" ps postgres 2>/dev/null \
    | grep -qiE "(running|healthy|up)"; then
  POSTGRES_UP=true
fi

# ---------------------------------------------------------------------------
# Read actual credentials from the running container (not from .env).
# This is the authoritative source — avoids stale/wrong .env values.
# ---------------------------------------------------------------------------
POSTGRES_USER=""
POSTGRES_PASSWORD=""
POSTGRES_DB=""
POSTGRES_PORT="5432"

if [ "$POSTGRES_UP" = "true" ]; then
  POSTGRES_USER="$(docker compose -f "${PROJECT_ROOT}/docker-compose.yml" exec -T postgres \
    sh -c 'printf "%s" "$POSTGRES_USER"' 2>/dev/null)" || POSTGRES_USER=""
  POSTGRES_PASSWORD="$(docker compose -f "${PROJECT_ROOT}/docker-compose.yml" exec -T postgres \
    sh -c 'printf "%s" "$POSTGRES_PASSWORD"' 2>/dev/null)" || POSTGRES_PASSWORD=""
  POSTGRES_DB="$(docker compose -f "${PROJECT_ROOT}/docker-compose.yml" exec -T postgres \
    sh -c 'printf "%s" "$POSTGRES_DB"' 2>/dev/null)" || POSTGRES_DB=""

  DYNAMIC_PORT=""
  DYNAMIC_PORT="$(docker compose -f "${PROJECT_ROOT}/docker-compose.yml" port postgres 5432 2>/dev/null \
    | awk -F: '{print $NF}' | tr -d '[:space:]')" || true
  if [ -n "$DYNAMIC_PORT" ] && [[ "$DYNAMIC_PORT" =~ ^[0-9]+$ ]]; then
    POSTGRES_PORT="$DYNAMIC_PORT"
  fi
fi

# Build DATABASE_URL from container-sourced credentials.
# Fall back to docker-compose.yml static values only if exec failed.
PG_USER="${POSTGRES_USER:-estimate}"
PG_PASS="${POSTGRES_PASSWORD:-estimate_dev}"
PG_DB="${POSTGRES_DB:-estimate_tool}"

export DATABASE_URL="postgresql+psycopg2://${PG_USER}:${PG_PASS}@localhost:${POSTGRES_PORT}/${PG_DB}"

# ---------------------------------------------------------------------------
# Validate required files.
# ---------------------------------------------------------------------------
ERRORS=0
if [ ! -f "$PYTHON_SCRIPT" ]; then
  echo "ERROR: Python script not found: ${PYTHON_SCRIPT}" >&2
  ERRORS=$((ERRORS + 1))
fi
if [ ! -f "$XLSX_PATH" ]; then
  echo "ERROR: XLSX workbook not found: ${XLSX_PATH}" >&2
  ERRORS=$((ERRORS + 1))
fi
[ "$ERRORS" -gt 0 ] && exit 1

# ---------------------------------------------------------------------------
# Handle postgres not running.
# ---------------------------------------------------------------------------
if [ "$POSTGRES_UP" = "false" ]; then
  echo "WARNING: postgres container does not appear to be running." >&2
  echo "  Start it with: docker compose up -d postgres" >&2
  if [ "$DRY_RUN" = "false" ]; then
    echo "ERROR: Cannot import without a running database. Use --dry-run for XLSX-only parsing." >&2
    exit 1
  fi
  echo "  Continuing in --dry-run mode (XLSX parsing only — no DB connection needed)." >&2
fi

# ---------------------------------------------------------------------------
# Detect if a non-Docker process is also listening on the mapped port.
# A native postgres (e.g. Homebrew/Postgres.app) would intercept connections
# to localhost:<port> before Docker's port mapping is reached.
# ---------------------------------------------------------------------------
PORT_CONFLICT=false
if [ "$POSTGRES_UP" = "true" ]; then
  # lsof -iTCP:<port> -sTCP:LISTEN lists all listeners; filter out Docker entries.
  # Note: lsof truncates command names to 10 chars, so com.docker.backend → com.docke.
  NON_DOCKER_LISTENER="$(lsof -iTCP:"${POSTGRES_PORT}" -sTCP:LISTEN 2>/dev/null \
    | grep -v 'com\.docke\|com\.docker\|docker\|dockerd' | tail -n +2)" || true
  if [ -n "$NON_DOCKER_LISTENER" ]; then
    PORT_CONFLICT=true
    echo "WARNING: A non-Docker process is listening on port ${POSTGRES_PORT}:" >&2
    echo "$NON_DOCKER_LISTENER" | awk '{print "  " $0}' >&2
    echo "  This native postgres will intercept host connections to localhost:${POSTGRES_PORT}." >&2
    echo "  To use Docker postgres from the host, either:" >&2
    echo "    a) Stop the native postgres service, OR" >&2
    echo "    b) Change the host port in docker-compose.yml (e.g. \"5433:5432\")" >&2
    echo "  The connection test below uses 'docker compose exec' to verify credentials" >&2
    echo "  inside the container, which is unaffected by the host port conflict." >&2
  fi
fi

# ---------------------------------------------------------------------------
# Connection test — run inside the container via 'docker compose exec' so it
# is unaffected by any host-side port conflicts.  Skip in --dry-run.
# ---------------------------------------------------------------------------
MASKED_URL="$(echo "$DATABASE_URL" | sed -E 's|://([^:]+):[^@]+@|://\1:***@|')"

if [ "$POSTGRES_UP" = "true" ]; then
  if [ "$PORT_CONFLICT" = "true" ]; then
    echo "DATABASE_URL: ${MASKED_URL} (host port shadowed by native postgres — see warning above)"
  else
    echo "DATABASE_URL: ${MASKED_URL}"
  fi

  # Test the connection from inside the container (bypasses any host port conflict).
  CONN_TEST_OUT="$(docker compose -f "${PROJECT_ROOT}/docker-compose.yml" exec -T postgres \
    psql -U "${PG_USER}" -d "${PG_DB}" -c "select current_user, current_database();" 2>&1)" || CONN_TEST_EXIT=$?
  CONN_TEST_EXIT="${CONN_TEST_EXIT:-0}"

  if [ "$CONN_TEST_EXIT" -eq 0 ]; then
    echo "  DB connection OK (verified inside container) — user=${PG_USER}, database=${PG_DB}"
  else
    echo "" >&2
    echo "ERROR: Could not connect to PostgreSQL inside the container." >&2
    echo "  Attempted user:     ${PG_USER}" >&2
    echo "  Attempted database: ${PG_DB}" >&2
    echo "  Mapped port:        ${POSTGRES_PORT}" >&2
    echo "  psql output: ${CONN_TEST_OUT}" >&2
    echo "" >&2
    echo "  Hint: docker compose up -d postgres" >&2
    echo "  Credentials are read live from the running container via 'docker compose exec'." >&2
    exit 1
  fi

  # Warn if Python import will hit native postgres instead of Docker postgres.
  if [ "$PORT_CONFLICT" = "true" ] && [ "$DRY_RUN" = "false" ]; then
    echo "" >&2
    echo "ERROR: Cannot run --overwrite/import while a native postgres shadows port ${POSTGRES_PORT}." >&2
    echo "  The Python import script connects from the host and would write to the wrong database." >&2
    echo "  Stop the native postgres or remap Docker's port, then retry." >&2
    exit 1
  fi
else
  echo "DATABASE_URL: ${MASKED_URL} (connection check skipped — container not running)"
fi

# ---------------------------------------------------------------------------
# Overwrite guard — backup reminder + manual YES confirmation.
# After confirmation, append --confirm-destructive so Python skips its own prompt.
# ---------------------------------------------------------------------------
if [ "$OVERWRITE" = "true" ] && [ "$DRY_RUN" = "false" ]; then
  echo ""
  echo "Recommended: run scripts/export_rate_rules.py or pg_dump before overwrite."
  echo ""
  printf "Type YES to confirm overwrite and proceed: "
  read -r BASH_CONFIRM
  if [ "$BASH_CONFIRM" != "YES" ]; then
    echo "Import aborted."
    exit 1
  fi
  # Python's internal interactive prompt is skipped via --confirm-destructive.
  PASS_THROUGH+=("--confirm-destructive")
fi

# ---------------------------------------------------------------------------
# Execute the Python import script.
# ---------------------------------------------------------------------------
echo "Python:       ${PYTHON}"
echo "Running:      ${PYTHON} ${PYTHON_SCRIPT} ${PASS_THROUGH[*]:-}"
echo ""

cd "${PROJECT_ROOT}"
"$PYTHON" "$PYTHON_SCRIPT" "${PASS_THROUGH[@]}"
IMPORT_STATUS=$?

# ---------------------------------------------------------------------------
# Post-import verification hint (non-dry-run success only).
# ---------------------------------------------------------------------------
if [ "$DRY_RUN" = "false" ] && [ "$IMPORT_STATUS" -eq 0 ]; then
  echo ""
  echo "Verify the import:"
  echo "  psql \"\${DATABASE_URL}\" -c \\"
  echo "    \"SELECT COUNT(*) AS total_rules,\\"
  echo "            COUNT(*) FILTER (WHERE is_active) AS active_rules,\\"
  echo "            COUNT(DISTINCT client_id) AS clients,\\"
  echo "            COUNT(DISTINCT trade_id) AS trades\\"
  echo "       FROM rate_rules\\"
  echo "      WHERE version = 'xlsx-master-helper-1.7';\""
fi

exit "$IMPORT_STATUS"
