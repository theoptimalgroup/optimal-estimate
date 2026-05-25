#!/usr/bin/env bash
# Run Alembic migrations against the target database (staging/production).
# Usage:
#   DATABASE_URL='postgresql+psycopg2://...' ./scripts/deploy-migrate.sh
#   ./scripts/deploy-migrate.sh --check   # exit 1 if migrations are pending

set -euo pipefail

cd "$(dirname "$0")/.."

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL must be set" >&2
  exit 1
fi

if [[ "${1:-}" == "--check" ]]; then
  echo "Checking migration status..."
  alembic check
  exit $?
fi

CURRENT="$(alembic current 2>/dev/null | tail -n 1 || true)"
HEAD="$(alembic heads | tail -n 1 || true)"
echo "Current revision: ${CURRENT:-none}"
echo "Head revision: ${HEAD:-unknown}"
echo "Applying Alembic migrations..."
alembic upgrade head
echo "Migrations complete."
