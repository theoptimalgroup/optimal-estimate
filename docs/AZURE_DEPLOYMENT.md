# Azure production deployment

Manual deploy uses `deploy.sh` (local copy; see `deploy.sh.example` in repo). Local development keeps dev auth via root `.env`.

## Auth model

| Environment | Backend | Frontend build | Login |
|-------------|---------|------------------|-------|
| Local dev | `AUTH_PROVIDER=dev`, `DEV_AUTH_ENABLED=true` | `NEXT_PUBLIC_AUTH_PROVIDER=dev` | Auto dev user |
| Production | `AUTH_PROVIDER=azure`, `DEV_AUTH_ENABLED=false` | `NEXT_PUBLIC_AUTH_PROVIDER=azure` | Microsoft Entra ID |

Production **must not** leave `DEV_AUTH_ENABLED=true` — that auto-authenticates every API request as the dev user.

## One-time setup

### 1. Entra ID app registrations

1. **Backend API app** — expose scope `access_as_user`; note `AZURE_API_CLIENT_ID`.
2. **Frontend SPA app** — note `NEXT_PUBLIC_AZURE_CLIENT_ID`; add redirect URI: production web origin only (e.g. `https://optimal-estimate-web….azurecontainerapps.io`, not `/login`).

### 2. Production env file

```bash
cp .env.production.example .env.production
# Edit .env.production — fill tenant ID, API client ID, SPA client ID
```

Required in `.env.production`:

```env
AUTH_PROVIDER=azure
DEV_AUTH_ENABLED=false
AZURE_TENANT_ID=<tenant-id>
AZURE_API_CLIENT_ID=<backend-api-client-id>
BACKEND_CORS_ORIGINS=https://<production-frontend-url>

# eWorks — required for Admin → eWorks Sync (manual + background worker)
EWORKS_API_ENABLED=true
EWORKS_BASE_URL=https://your-eworks-host/7.0
EWORKS_API_KEY=<your-api-key>
EWORKS_SYNC_ATTACHMENTS_ENABLED=true
EWORKS_SYNC_ATTACHMENT_FILES_ENABLED=false
EWORKS_SYNC_LOOKBACK_DAYS=7
EWORKS_SYNC_JOB_DETAILS_ENABLED=true
EWORKS_SYNC_JOB_DETAILS_ONLY_WITH_APPOINTMENTS=true

NEXT_PUBLIC_AUTH_PROVIDER=azure
NEXT_PUBLIC_API_URL=<production-api-url>
NEXT_PUBLIC_AZURE_TENANT_ID=<tenant-id>
NEXT_PUBLIC_AZURE_CLIENT_ID=<frontend-spa-client-id>
NEXT_PUBLIC_AZURE_API_SCOPE=api://<backend-api-client-id>/access_as_user
```

`BACKEND_CORS_ORIGINS` is mapped to `CORS_ORIGINS` on both `optimal-estimate-api` and `optimal-estimate-sync-worker`. It must be the production web origin only — **never** `localhost` or `127.0.0.1`. `./deploy.sh` fails early if production CORS contains local origins.

When `EWORKS_API_ENABLED=true`, `./deploy.sh` requires `EWORKS_BASE_URL` and `EWORKS_API_KEY` in `.env.production` and syncs the same eWorks settings to **both** Container Apps. The API handles manual sync buttons; the worker runs scheduled background sync. Prefer Azure Container App secrets for `EWORKS_API_KEY` (`secretref:...`) in long-term production hardening.

| Variable | Required when `EWORKS_API_ENABLED=true` | Synced to |
|----------|----------------------------------------|-----------|
| `EWORKS_API_ENABLED` | Yes | API + worker |
| `EWORKS_BASE_URL` | Yes | API + worker |
| `EWORKS_API_KEY` | Yes | API + worker |
| `EWORKS_SYNC_ATTACHMENTS_ENABLED` | Recommended | API + worker |
| `EWORKS_SYNC_JOB_DETAILS_ENABLED` | Recommended | API + worker |
| `EWORKS_SYNC_JOB_DETAILS_ONLY_WITH_APPOINTMENTS` | Recommended | API + worker |
| `EWORKS_SYNC_LOOKBACK_DAYS` | Optional (default 7) | API + worker |
| `EWORKS_SYNC_ATTACHMENT_FILES_ENABLED` | Optional (default false) | API + worker |

### 3. Users table

Each staff Microsoft account **must exist** in the `users` table before they can sign in:

| Column | Requirement |
|--------|-------------|
| `email` | Must match Microsoft account email (case-insensitive) |
| `role` | `admin`, `manager`, `estimator`, or `engineer` |
| `is_active` | `true` |

Roles always come from the database — Entra app roles are not used.

## Deploy

```bash
./deploy.sh
```

`deploy.sh` will:

1. Load `.env.production`
2. Validate `BACKEND_CORS_ORIGINS` (reject localhost / 127.0.0.1 in production)
3. Validate eWorks vars when `EWORKS_API_ENABLED=true` (`EWORKS_BASE_URL`, `EWORKS_API_KEY` required)
4. Build frontend with Azure `NEXT_PUBLIC_*` auth args (baked into the image)
5. Set API and worker env: `ENVIRONMENT=production`, `CORS_ORIGINS`, auth vars, shared eWorks settings; worker also gets scheduler flags and `DATABASE_URL` copied from API
6. Push images to ACR and update Container Apps

Options:

- `--skip-auth-env` — image deploy only; do not change API auth env vars
- `--dev-frontend` — build frontend with dev auth (not for production)
- `--frontend-only` / `--backend-only` — partial deploy

### Manual backend auth env (if needed)

```bash
az containerapp update \
  --name optimal-estimate-api \
  --resource-group rg-optimal-estimate \
  --set-env-vars \
    ENVIRONMENT=production \
    CORS_ORIGINS=https://<production-frontend-url> \
    AUTH_PROVIDER=azure \
    DEV_AUTH_ENABLED=false \
    AZURE_TENANT_ID=<tenant-id> \
    AZURE_API_CLIENT_ID=<backend-api-client-id>
```

### Production CORS (API + worker)

Backend validates `ENVIRONMENT=production` with `CORS_ORIGINS` — localhost origins cause startup failure. Set CORS from `.env.production` only; do not copy local dev `CORS_ORIGINS`.

**Fix CORS on both apps manually** (replace with your web URL):

```bash
WEB_ORIGIN="https://optimal-estimate-web.wonderfulpebble-655f8f4d.northeurope.azurecontainerapps.io"

az containerapp update \
  --name optimal-estimate-api \
  --resource-group rg-optimal-estimate \
  --set-env-vars \
    ENVIRONMENT=production \
    CORS_ORIGINS="$WEB_ORIGIN"

az containerapp update \
  --name optimal-estimate-sync-worker \
  --resource-group rg-optimal-estimate \
  --set-env-vars \
    ENVIRONMENT=production \
    CORS_ORIGINS="$WEB_ORIGIN"
```

Verify worker `DATABASE_URL` matches API:

```bash
az containerapp show -n optimal-estimate-api -g rg-optimal-estimate \
  --query "properties.template.containers[0].env[?name=='DATABASE_URL'].value | [0]" -o tsv
az containerapp show -n optimal-estimate-sync-worker -g rg-optimal-estimate \
  --query "properties.template.containers[0].env[?name=='DATABASE_URL'].value | [0]" -o tsv
```

Or run `./deploy.sh --skip-build <existing-tag>` after setting `BACKEND_CORS_ORIGINS` in `.env.production`.

### Manual eWorks env (API + worker)

When not using `./deploy.sh`, apply the **same** eWorks credentials to both apps:

```bash
az containerapp update \
  --name optimal-estimate-api \
  --resource-group rg-optimal-estimate \
  --set-env-vars \
    EWORKS_API_ENABLED=true \
    EWORKS_BASE_URL=https://your-eworks-host/7.0 \
    EWORKS_API_KEY=<your-api-key> \
    EWORKS_SYNC_ATTACHMENTS_ENABLED=true \
    EWORKS_SYNC_JOB_DETAILS_ENABLED=true \
    EWORKS_SYNC_JOB_DETAILS_ONLY_WITH_APPOINTMENTS=true \
    EWORKS_SYNC_LOOKBACK_DAYS=7

az containerapp update \
  --name optimal-estimate-sync-worker \
  --resource-group rg-optimal-estimate \
  --set-env-vars \
    EWORKS_API_ENABLED=true \
    EWORKS_BASE_URL=https://your-eworks-host/7.0 \
    EWORKS_API_KEY=<your-api-key> \
    EWORKS_SYNC_ATTACHMENTS_ENABLED=true \
    EWORKS_SYNC_JOB_DETAILS_ENABLED=true \
    EWORKS_SYNC_JOB_DETAILS_ONLY_WITH_APPOINTMENTS=true \
    EWORKS_SYNC_LOOKBACK_DAYS=7
```

After deploy, Admin → eWorks Sync should show the API as enabled and manual sync buttons should be active.

## Post-deploy validation

1. Open `{WEB_URL}/internal/auth-test` **before** signing in:
   - `frontend provider` = `azure`
   - `azure configured` = `true`
   - `isAuthenticated` = `false`

2. Open `{WEB_URL}/login` — **Sign in with Microsoft** button visible.

3. Sign in with a registered staff account.

4. Revisit `/internal/auth-test`:
   - `isAuthenticated` = `true`
   - `role` = role from `users` table

5. Open `/admin/dashboard` (or role-appropriate dashboard) — loads after login.

6. Sign out / clear session — protected routes redirect to `/login`.

7. Confirm API rejects dev auth:

```bash
curl -sS "{API_URL}/api/v1/auth/me" | jq .
# Expected: 401 Not authenticated (no Bearer token, no dev bypass)
```

## Local dev unchanged

Root `.env` should keep:

```env
AUTH_PROVIDER=dev
DEV_AUTH_ENABLED=true
NEXT_PUBLIC_AUTH_PROVIDER=dev
```

Docker Compose and `npm run dev` continue to use dev auto-login.

## eWorks background sync worker

Use a **dedicated worker Container App** for scheduled eWorks sync. The API container serves user traffic only; manual sync buttons remain on the API.

| Container App | `RUN_BACKGROUND_WORKER` | `EWORKS_BACKGROUND_SYNC_ENABLED` | Replicas |
|---------------|---------------------------|----------------------------------|----------|
| `optimal-estimate-api` | `false` | `false` | scale as needed |
| `optimal-estimate-sync-worker` | `true` | `true` | min=1 max=1 |

Both use the **same backend Docker image** and `DATABASE_URL`. Sync coordination uses the `eworks_sync_locks` table (migration 026) plus `eworks_sync_runs` heartbeats.

### Recommended worker env

```bash
az containerapp update \
  --name optimal-estimate-sync-worker \
  --resource-group rg-optimal-estimate \
  --min-replicas 1 \
  --max-replicas 1 \
  --set-env-vars \
    ENVIRONMENT=production \
    CORS_ORIGINS=https://<production-frontend-url> \
    RUN_BACKGROUND_WORKER=true \
    EWORKS_BACKGROUND_SYNC_ENABLED=true \
    EWORKS_API_ENABLED=true \
    WEB_CONCURRENCY=1 \
    EWORKS_BACKGROUND_CUSTOMERS_ENABLED=true \
    EWORKS_CUSTOMERS_SYNC_INTERVAL_MINUTES=720 \
    EWORKS_BACKGROUND_QUOTES_ENABLED=true \
    EWORKS_QUOTES_SYNC_INTERVAL_MINUTES=15 \
    EWORKS_BACKGROUND_JOBS_ENABLED=true \
    EWORKS_JOBS_SYNC_INTERVAL_MINUTES=60 \
    EWORKS_BACKGROUND_PRODUCTS_ENABLED=true \
    EWORKS_PRODUCTS_SYNC_INTERVAL_MINUTES=1440 \
    EWORKS_SYNC_ATTACHMENTS_ENABLED=true \
    EWORKS_SYNC_JOB_DETAILS_ENABLED=true \
    EWORKS_SYNC_JOB_DETAILS_ONLY_WITH_APPOINTMENTS=true \
    EWORKS_SYNC_LOCK_TIMEOUT_MINUTES=30 \
    EWORKS_SYNC_LOCK_HEARTBEAT_SECONDS=60
```

Prefer Azure secrets for `DATABASE_URL`, `EWORKS_API_KEY`, and other sensitive values (`secretref:...`).

### API container env (disable scheduler)

```bash
az containerapp update \
  --name optimal-estimate-api \
  --resource-group rg-optimal-estimate \
  --set-env-vars \
    RUN_BACKGROUND_WORKER=false \
    EWORKS_BACKGROUND_SYNC_ENABLED=false
```

### Create worker Container App (first time)

If `optimal-estimate-sync-worker` does not exist yet, create it in the same Container Apps environment as the API (same image, ingress optional for `/health`):

```bash
az containerapp create \
  --name optimal-estimate-sync-worker \
  --resource-group rg-optimal-estimate \
  --environment <your-container-app-environment> \
  --image acroptimalestimate.azurecr.io/backend:<tag> \
  --target-port 8000 \
  --ingress internal \
  --min-replicas 1 \
  --max-replicas 1
```

Then apply the worker env vars above. `./deploy.sh` updates the worker image and env when the app exists.

### Lock behaviour

- Before sync starts: acquire row in `eworks_sync_locks` for sync type (`customers`, `quotes`, `jobs`, `products`, `all`)
- Fresh lock with recent `heartbeat_at` → skip duplicate run
- Stale lock (older than `EWORKS_SYNC_LOCK_TIMEOUT_MINUTES`) → marked failed and re-acquired
- Manual admin sync uses the same locks; returns **"A sync is already running. Try again shortly."** when blocked
- Admin → eWorks Sync shows worker status, active locks, and stale lock warnings

### Health

Worker exposes `GET /health` with:

- `database_ok`
- `background_worker_mode=true`
- `scheduler_running=true` when scheduler is active
