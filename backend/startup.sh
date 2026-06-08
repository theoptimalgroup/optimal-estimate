#!/usr/bin/env bash
set -euo pipefail

cd /app

echo "[startup] Environment: ${ENVIRONMENT:-development}"
echo "[startup] Storage backend: ${STORAGE_BACKEND:-local}"
echo "[startup] Run seed: ${RUN_SEED:-false}"

wait_for_database() {
  python <<'PY'
import os
import sys
import time

from sqlalchemy import create_engine, text

database_url = os.environ.get("DATABASE_URL")
if not database_url:
    print("[startup] DATABASE_URL is not set", file=sys.stderr)
    sys.exit(1)

engine = create_engine(database_url, pool_pre_ping=True)
for attempt in range(1, 31):
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("[startup] Database is ready")
        sys.exit(0)
    except Exception as exc:
        print(f"[startup] Waiting for database ({attempt}/30): {exc}")
        time.sleep(2)

print("[startup] Database not ready after 60 seconds", file=sys.stderr)
sys.exit(1)
PY
}

wait_for_database

echo "[startup] Running Alembic migrations..."
./scripts/deploy-migrate.sh

if [[ "${RUN_SEED:-false}" == "true" ]]; then
  if [[ "${ENVIRONMENT:-development}" == "production" && "${ALLOW_PRODUCTION_SEED:-false}" != "true" ]]; then
    echo "[startup] Refusing to seed production without ALLOW_PRODUCTION_SEED=true" >&2
    exit 1
  fi
  echo "[startup] Seeding database..."
  python -m app.db.seed
fi

WORKERS="${WEB_CONCURRENCY:-2}"
PORT="${PORT:-8000}"

if [[ "${RUN_BACKGROUND_WORKER:-false}" == "true" ]]; then
  WORKERS=1
  echo "[startup] Background worker mode: forcing WEB_CONCURRENCY=1"
fi

echo "[startup] RUN_BACKGROUND_WORKER=${RUN_BACKGROUND_WORKER:-false}"
echo "[startup] EWORKS_BACKGROUND_SYNC_ENABLED=${EWORKS_BACKGROUND_SYNC_ENABLED:-false}"
echo "[startup] Starting Gunicorn with ${WORKERS} workers on port ${PORT}..."
exec gunicorn app.main:app \
  --workers "${WORKERS}" \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind "0.0.0.0:${PORT}" \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
