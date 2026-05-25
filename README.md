# Optimal Estimate Calculator — eWorks Estimation

Public-facing estimation calculator for Optimal Group, embedded in eWorks via signed calculation links.

## Stack

- **Frontend:** Next.js 14, TypeScript, Tailwind CSS, React Hook Form
- **Backend:** FastAPI, SQLAlchemy, Alembic, PostgreSQL
- **PDF:** WeasyPrint (session PDF download)
- **Auth:** None — sessions are token-based via signed eWorks links

## Quick Start

```bash
cp .env.example .env
docker compose up --build
```

Services:

| Service   | URL                        |
|-----------|----------------------------|
| Frontend  | http://localhost:3000      |
| Backend   | http://localhost:8000      |
| API Docs  | http://localhost:8000/docs |

Open the app at `/eworks/calculate` (or `/` which redirects there). In development, use **Dev bootstrap** on the calculate page or generate a test link:

```bash
python scripts/generate_eworks_link.py
# writes docs/test-eworks-link.txt
```

## Rate rules (Lambert / XLSX)

Import client/trade rate rules from the master workbook after migrations:

```bash
cd backend
alembic upgrade head
python ../scripts/import_quote_calculator_rules.py --client Lambert
```

Full import (all clients from `docs/1.7 MASTER HELPER.xlsx`):

```bash
python ../scripts/import_quote_calculator_rules.py
```

## Development

### Backend only

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload
```

### Frontend only

```bash
cd frontend
npm install
npm run dev
```

### Tests

```bash
cd backend
pytest

cd frontend
npx playwright test e2e/eworks-calculate.spec.ts
```

## Features

- Signed eWorks link bootstrap (`POST /api/v1/calculation-session/from-link`)
- 4-step wizard: Estimation Form → Questionnaire → Charges → Results
- Multi-work estimates with per-work breakdown and combined totals
- Session progress autosave and resume (idempotency key + `ui_state`)
- Attachment uploads (local disk, per work block)
- PDF download for completed estimates
- XLSX-backed rate rules (Lambert pilot and full master import)

## API (estimation)

| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/calculation-session/from-link` | Open session from signed payload |
| `POST /api/v1/calculation-session/dev-bootstrap` | Dev-only test session |
| `GET/PATCH /api/v1/calculation-session/{id}` | Load/save wizard progress |
| `POST /api/v1/calculation-session/{id}/attachments` | Upload photos/files |
| `POST /api/v1/calculation-session/{id}/calculate` | Run calculation |
| `POST /api/v1/calculation-session/{id}/pdf` | Download estimate PDF |
| `GET /api/v1/trades` | Skill dropdown (read-only) |

See `docs/EWORKS_CALCULATION_LINK.md` for link format and session headers.

## Project Structure

```
backend/app/
  api/v1/calculation_session.py   eWorks session API
  api/v1/trades.py                read-only trades list
  engines/                        calculation, rules, XLSX formulas
  services/                       session, link, PDF, merge logic
frontend/src/
  app/eworks/calculate/           estimation wizard
  components/eworks-*.tsx         wizard UI
  lib/eworks-session.ts           session client
```
