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

NEXT_PUBLIC_AUTH_PROVIDER=azure
NEXT_PUBLIC_API_URL=<production-api-url>
NEXT_PUBLIC_AZURE_TENANT_ID=<tenant-id>
NEXT_PUBLIC_AZURE_CLIENT_ID=<frontend-spa-client-id>
NEXT_PUBLIC_AZURE_API_SCOPE=api://<backend-api-client-id>/access_as_user
```

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
2. Build frontend with Azure `NEXT_PUBLIC_*` auth args (baked into the image)
3. Set backend Container App env: `AUTH_PROVIDER=azure`, `DEV_AUTH_ENABLED=false`, tenant + API client ID
4. Push images to ACR and update Container Apps

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
    AUTH_PROVIDER=azure \
    DEV_AUTH_ENABLED=false \
    AZURE_TENANT_ID=<tenant-id> \
    AZURE_API_CLIENT_ID=<backend-api-client-id>
```

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
