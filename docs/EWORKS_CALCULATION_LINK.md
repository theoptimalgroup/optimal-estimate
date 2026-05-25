# eWorks Calculation Link

Public signed deep links open the estimate calculator at `/eworks/calculate` without app login. eWorks passes job context in the URL; the backend validates the link, resolves client/trade/XLSX rules, and runs the existing calculation engine.

Alias route: `/calculate?...` redirects to `/eworks/calculate?...` with the same query string.

## URL format

```
https://app.example/eworks/calculate?payload={base64_json}&sig={hmac_hex}
```

- `payload` — URL-safe base64 encoding of a JSON object (raw string is signed; do not decode before signing).
- `sig` — HMAC-SHA256 hex digest of the raw `payload` string using the shared secret.

## Payload JSON

Required fields:

| Field | Type | Description |
|-------|------|-------------|
| `source` | string | eWorks source identifier |
| `quote_number` | string | Quote reference |
| `job_number` | string | Job reference |
| `client` | string | Client name or alias (e.g. `Lambert Chartered Surveyors`) |
| `trade` | string | Trade name (e.g. `Carpenter`) |
| `property_address` | string | Site address |
| `expires_at` | ISO8601 datetime | Link expiry (UTC recommended) |

Optional fields:

| Field | Type |
|-------|------|
| `engineer_name` | string |
| `property_manager` | string |
| `property_manager_email` | string |
| `property_manager_phone` | string |
| `tenant_name` | string |
| `tenant_phone` | string |
| `access_notes` | string |
| `original_job_description` | string |
| `booked_by` | string |
| `contact` | string |
| `quote_screening_answers` | string |
| `date_visited` | ISO date (`YYYY-MM-DD`) |
| `travel_time_minutes` | integer (default `0`) |
| `travel_notes` | string |
| `parking_notes` | string |
| `total_time_for_job` | string |
| `quote_description` | string (optional override; otherwise built from access/quote/info/travel/contact/screening fields) |
| `findings_report` | string |
| `external_job_id` | string (optional; defaults to `source`) |
| `congestion_required` | boolean (default `false`) |
| `congestion_amount` | number (default `0`) |
| `travel` | number (default `0`) |

## Page 1 — Estimation form (all from link)

Step 1 is read-only and matches the PDF estimation form layout. eWorks should populate the link with:

| Form field | Link JSON field(s) |
|------------|-------------------|
| Engineer Name | `engineer_name` |
| Quote Number | `quote_number` |
| Job Number | `job_number` |
| Property Address | `property_address` |
| Congestion Charge | `congestion_required` (shown as Yes/No) |
| Parking Notes | `parking_notes` |
| Total Time for job | `total_time_for_job` |
| Client | `client` |
| PM | `property_manager` |
| Date visited / Form completed | `date_visited` |
| Description of what quoting for | `quote_description` or assembled from `access_notes`, `original_job_description`, `booked_by`, `travel_notes`, `contact`, `quote_screening_answers` |
| Findings Report | `findings_report` |

`trade` is required in the payload for rate-rule resolution but is shown only as metadata on page 1.

## Signing example (Python)

```python
import base64
import hashlib
import hmac
import json

secret = "your-shared-secret"

payload = {
    "source": "eworks",
    "quote_number": "Q-123",
    "job_number": "JOB-456",
    "client": "Lambert Chartered Surveyors",
    "trade": "Carpenter",
    "property_address": "The Factory, 1 Nile Street",
    "expires_at": "2026-12-31T23:59:59Z",
    "congestion_required": True,
    "congestion_amount": 18,
    "travel": 0,
}

raw = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
sig = hmac.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest()

url = f"https://app.example/eworks/calculate?payload={raw}&sig={sig}"
```

## API flow

1. `POST /api/v1/calculation-session/from-link` — decode payload, verify signature/expiry, resolve client/trade/rule, create session. Returns `session_id`, `session_token`, Step 1 fields, resolved rule metadata.
2. `PATCH /api/v1/calculation-session/{id}` — autosave Step 2+ inputs (header `X-Session-Token`).
3. `POST /api/v1/calculation-session/{id}/calculate` — run XLSX calculation; returns breakdown, internal view, internal notes, client-safe view.
4. `GET /api/v1/calculation-session/{id}` — reload session (optional).

No JWT is required on these endpoints. Session token + link expiry protect follow-up calls.

## Configuration

| Variable | Description |
|----------|-------------|
| `EWORKS_LINK_SECRET` | HMAC secret (falls back to `SECRET_KEY` in dev if unset) |
| `EWORKS_LINK_SIG_REQUIRED` | Require signature (`false` in development for local testing) |
| `EWORKS_SESSION_EXPIRE_MINUTES` | Reserved for future session TTL tuning |

Set `EWORKS_LINK_SIG_REQUIRED=true` in staging and production.

## Client alias example

Payload client `Lambert Chartered Surveyors` resolves to canonical **Lamberts Chartered Surveyors** via the alias table. XLSX rules match on resolved `client_id` + `trade_id`; rule metadata may still show `xlsx_client_name = Lambert Chartered Surveyors`.

## Error responses

| Code | HTTP | Meaning |
|------|------|---------|
| `MISSING_PAYLOAD` | 400 | No payload in request |
| `INVALID_PAYLOAD` | 400 | Base64/JSON validation failed |
| `INVALID_SIGNATURE` | 401 | Missing or wrong HMAC |
| `EXPIRED_LINK` | 410 | `expires_at` in the past |
| `CLIENT_NOT_FOUND` | 404 | Client/alias not found |
| `TRADE_NOT_FOUND` | 404 | Trade not found |
| `RULE_NOT_FOUND` | 404 | No active rate rule |

This flow does not read or write `jobs` or `quotes`.
