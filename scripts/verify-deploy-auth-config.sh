#!/usr/bin/env bash
# Verify deploy.sh.example wires Azure auth for production builds.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_EXAMPLE="$ROOT/deploy.sh.example"

require_pattern() {
  local pattern=$1
  local label=$2
  if ! grep -q "$pattern" "$DEPLOY_EXAMPLE"; then
    echo "FAIL: deploy.sh.example missing $label ($pattern)" >&2
    exit 1
  fi
  echo "OK: $label"
}

require_pattern 'FRONTEND_AUTH_PROVIDER="azure"' 'frontend azure auth build arg'
require_pattern 'NEXT_PUBLIC_AZURE_TENANT_ID=' 'frontend tenant build arg'
require_pattern 'NEXT_PUBLIC_AZURE_CLIENT_ID=' 'frontend client build arg'
require_pattern 'NEXT_PUBLIC_AZURE_API_SCOPE=' 'frontend api scope build arg'
require_pattern '"AUTH_PROVIDER=azure"' 'backend azure auth env'
require_pattern '"DEV_AUTH_ENABLED=false"' 'backend dev auth disabled'
require_pattern '\.env\.production' 'production env file reference'

echo "deploy auth wiring looks correct."
