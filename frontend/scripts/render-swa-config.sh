#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <backend-url-without-trailing-slash>" >&2
  exit 1
fi

BACKEND_URL="${1%/}"
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TEMPLATE="${ROOT_DIR}/staticwebapp.config.template.json"
OUTPUT="${ROOT_DIR}/staticwebapp.config.json"

sed "s|__BACKEND_URL__|${BACKEND_URL}|g" "${TEMPLATE}" > "${OUTPUT}"
echo "Wrote ${OUTPUT} with backend URL ${BACKEND_URL}"
