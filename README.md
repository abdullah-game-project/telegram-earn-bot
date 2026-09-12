# Telegram Earn Bot

A Telegram Mini App with a coin-earning / referral / withdrawal system, backed by a FastAPI service.

## Structure

- **`backend/`** — FastAPI + SQLAlchemy (async) + Postgres. JWT auth (access + refresh),
  rate limiting, admin panel routes, HMAC-signed postback endpoint for offerwall/CPA
  network integrations, Alembic migrations, structured logging, 20 passing pytest tests.
  See `backend/.env.example` for required config and `HANDOFF.md` for design notes and
  the original hardening pass's punch list.
- **`frontend/`** — React + TypeScript + Vite + Tailwind. Telegram Mini App UI: Home,
  Earn, Friends (referrals), Wallet (withdrawals), Leaderboard. Talks to the backend
  via `VITE_API_BASE` (see `frontend/.env.example`).

## How this repo came together

This merges two independent improvement passes on the original demo:

1. A **backend hardening pass** — real ledger/withdrawal logic, auth, rate limiting,
   admin routes, postback signature verification, tests, migrations scaffolding.
2. A **frontend rebuild** — a fully wired Mini App UI that already matched the
   hardened backend's exact API shape (`/api/auth`, `/api/me`, `/api/transactions`,
   `/api/withdrawals`, `/api/referrals/me`, `/api/leaderboard/*`).

I combined them (backend as-is + this frontend) and fixed two integration bugs found
while verifying the merge:

- `frontend/package.json` was missing `@types/react` / `@types/react-dom`, which broke
  the TypeScript build (every JSX file failed to typecheck). Added.
- `frontend/src/lib/api.ts` had the API base URL hardcoded to a specific Render
  deployment. Switched it to `import.meta.env.VITE_API_BASE` (see `.env.example`),
  with the old URL kept only as a fallback default.

Also added: root `.gitignore`, `backend/.env.example`, `frontend/.env.example`, and
a basic CI workflow (`.github/workflows/ci.yml`) that lints + tests the backend and
type-checks + builds the frontend on every push/PR.

**Verified locally before packaging:** backend — `ruff check` clean, `pytest` 20/20
passing. Frontend — `npm run build` succeeds (tsc + vite).

## Known follow-ups (not yet done)

From the backend's `HANDOFF.md`, still open:

- Wire up Alembic (`migrations/env.py` needs `target_metadata` pointed at
  `app.database.Base` and the DB URL pulled from settings) and generate the initial
  migration.
- `docker-compose.yml` at repo root for a one-command local Postgres + backend stack.
- The concurrency-safe balance lock (`SELECT ... FOR UPDATE`) is only tested against
  SQLite sequentially — needs an integration test against real Postgres before
  trusting it in production.
- The postback endpoint's signature scheme is a generic placeholder — adjust to
  whichever offerwall/CPA network you actually integrate.
- The frontend currently stores the full auth payload (incl. JWT) in `localStorage`,
  which is readable by any script on the page (XSS risk). Worth moving to in-memory
  state + the existing `/api/auth/refresh` endpoint for silent renewal, especially
  since real money withdrawals are involved.

## Running locally

```bash
# Backend
cd backend
cp .env.example .env   # fill in BOT_TOKEN, DATABASE_URL, JWT_SECRET, CORS_ORIGINS
pip install -r requirements-dev.txt
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
cp .env.example .env   # VITE_API_BASE=http://localhost:8000
npm install
npm run dev
```
