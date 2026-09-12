# Handoff Notes — Industry-Grade Pass

This picks up the original demo and hardens the payment-critical paths first.
Everything below marked ✅ is written **and passing tests against the real
FastAPI app** (20/20, run with `cd backend && pytest`). Everything marked 🔲
is scoped but not yet built — this file is your punch list.

## ✅ Done

- **`app/config.py`** — env-validated settings: revenue share, CORS origins,
  admin ID list, rate limits, postback/webhook secrets. No more hardcoded
  90/10 split or `allow_origins=["*"]`.
- **`app/models.py`** — signed ledger (`Transaction.amount`, `.balance_after`),
  `WithdrawalRequest`, `PostbackLog` (audit trail of *every* inbound
  callback — valid or not, for fraud investigation), `AdminAuditLog`,
  referral fields on `User`.
- **`app/services/balance.py`** — `adjust_balance()`: row-locks the user
  (`SELECT ... FOR UPDATE`), rejects duplicate `network_tx_id` with 409
  instead of silently no-op'ing, blocks debits that would go negative.
  `credit_ad_revenue()` applies the revenue split and referral bonus.
- **`app/services/withdrawal.py`** — hold-then-settle: balance is debited the
  moment a withdrawal is requested (so it can't be spent twice while
  pending), idempotency key on the request itself, admin
  approve/reject(+refund)/mark-paid flow.
- **`app/services/postback.py` + `app/routers/postback.py`** — generic
  HMAC-SHA256-signed webhook at `POST /postback/{provider}`. Provider-
  agnostic by design since you haven't picked one yet — swap
  `verify_signature()` and the payload field names once you do.
- **`app/routers/admin.py`** — admin-gated (`ADMIN_TELEGRAM_IDS` env var)
  withdrawal review, manual balance adjustment, ban/unban, all written to
  `AdminAuditLog`.
- **`app/auth.py`** — access + refresh JWTs, `get_current_admin` dependency,
  stopped logging bot-token fragments.
- **`app/main.py`** — CORS locked to `CORS_ORIGINS`, slowapi rate limiting,
  structured JSON logging, request-ID middleware, global exception handler
  (no more stack traces leaking to clients).
- **`backend/tests/`** — 20 tests: ledger arithmetic/idempotency, withdrawal
  hold/refund, postback signature + replay rejection, full signed-initData
  auth flow, admin-route gating. `pytest.ini` configured.
- Lint-clean via `ruff check app/ tests/`.
- **`backend/migrations/`** — `alembic init -t async` has been run
  (`alembic.ini`, `migrations/env.py` scaffolded). **Not yet wired up.**

## 🔲 Next up (in the order I'd do them)

1. **Finish Alembic**
   - In `migrations/env.py`, import `app.database.Base` and `app.config.get_settings()`,
     set `target_metadata = Base.metadata`, and pull the DB URL from settings
     instead of `alembic.ini`.
   - `alembic revision --autogenerate -m "initial schema"`, eyeball the
     generated file, then `alembic upgrade head` against a real Postgres to confirm.
   - In `main.py`, production mode already skips `create_all` and expects
     migrations — just needs the migration itself to exist.

2. **`docker-compose.yml`** at repo root — Postgres + backend, so `docker
   compose up` gives a working local stack. Mount `.env`, expose 8000,
   depends_on with a healthcheck on Postgres.

3. **CI** (`.github/workflows/ci.yml`) — on push/PR: `ruff check`, `pytest`,
   and a `docker build` of `backend/Dockerfile` to catch breakage early.

4. **Dockerfile polish** — add a `HEALTHCHECK` hitting `/health`, pin the
   base image by digest if you want reproducible builds.

5. **Frontend** (`frontend/src/`):
   - `lib/api.ts` has `API_BASE` hardcoded to a Render URL — switch to
     `import.meta.env.VITE_API_BASE_URL`.
   - `hooks/useAuth.ts` stores the JWT in `localStorage` (XSS-exposed) —
     move to in-memory state + the refresh-token endpoint that now exists
     (`POST /api/auth/refresh`) for silent renewal instead.
   - Wire up real calls for the withdraw and transactions endpoints that now
     exist server-side (`getTransactions()` in `api.ts` is still a stub
     returning `[]`).

6. **`.env.example`** for both `backend/` and `frontend/`, and a rewritten
   root `README.md` covering setup, architecture, and deployment.

## Design notes worth knowing

- **Ledger is signed, not typed-with-magnitude.** `balance = sum(Transaction.amount)`
  conceptually; earns/referral bonuses are positive, withdrawals negative.
  This is what made the leaderboard and withdrawal-hold logic simple to get
  right — keep this convention if you extend it.
- **The concurrency test in `test_balance.py`** deliberately does *not* use
  `asyncio.gather()` on a shared SQLite connection — I tried that first and
  it silently dropped writes because SQLite's single test connection can't
  reproduce Postgres's per-row locking. Rather than paper over it, the test
  is sequential and the docstring says plainly that the actual lock
  (`with_for_update()` in `_lock_user`) needs an integration test against
  real Postgres before you trust it in production. Worth doing before launch.
- **Postback endpoint is a skeleton for whichever offerwall you pick.** The
  signature scheme (`HMAC-SHA256` over the raw body) is a reasonable
  default but most providers do it differently (some sign a query string,
  some use a static token param) — check their docs before going live.
