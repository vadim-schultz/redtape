# Local Development Setup

How to run RedTape's three pieces (Postgres, API, web) entirely locally.

## Prerequisites

- Docker Desktop, OrbStack, or Colima — anything providing `docker compose`
  (Compose V2 CLI plugin; not the standalone `docker-compose` v1 binary)
- Python 3.11+ and `pip` (or `uv`)
- Node.js 20+ and `npm`
- Optional: a `psql` client, for inspecting the local DB directly

## One-time setup

```bash
git clone <repo> && cd redtape

# Database
docker compose up -d db
docker compose ps   # wait for "healthy"

# API
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
python -m scripts.seed_i18n
python -m scripts.seed_jurisdictions
python -m scripts.seed_taxonomy
cd ../..

# Web, from the repo root. Copy .env.example to .env and set NPM_REGISTRY
# on the corporate network; otherwise this uses the public npm registry.
./scripts/npm.sh install
```

No `apps/api/.env` or `apps/web/.env` is required for this path — both apps'
built-in defaults already point at the local stack (see "Why this mirrors
Render/Cloudflare" below). A repo-root `.env` is optional and only selects
the corporate npm mirror.

## Day-to-day workflow

### One command

After the one-time setup above, `scripts/dev-up.sh` starts db + api + web
together:

```bash
./scripts/dev-up.sh
```

It waits for Postgres to be healthy, then starts the API (`--reload`) and web
dev server, streaming both logs to your terminal (also written to
`.dev-logs/api.log` and `.dev-logs/web.log`). Press Ctrl+C to stop the API
and web processes; the `db` container is left running (stop it separately
with `docker compose down`). It exits with an error up front if Docker isn't
running or if the one-time `apps/api/.venv` / `apps/web/node_modules` setup
hasn't been done yet.

### Manual (three terminals)

Equivalent to the above, run by hand — useful if you want each piece in its
own terminal tab/pane:

| Piece | Command | Notes |
|---|---|---|
| Database | `docker compose up -d db` (repo root) | Idempotent; `docker compose down` to stop, keeps data |
| API | `cd apps/api && source .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` | Auto-reloads on file changes |
| Web | `cd apps/web && npm run dev` | Vite dev server, default `http://localhost:5173` |

## Running the API test suite

```bash
docker compose up -d --wait db
cd apps/api
python -m pytest
```

DB-backed tests need Postgres (JSONB/ARRAY/native enum aren't available on
SQLite); the `db_session` fixture creates its own schema via
`Base.metadata.create_all`, so no migration or seed step is required first.
If Postgres isn't reachable, those tests skip with a reason instead of
failing; set `REQUIRE_DB=1` to fail instead (CI and `./ci.sh` always set it).
`./ci.sh` runs this same suite alongside lint/typecheck/build, starting the
compose `db` service itself if nothing is listening on 5432 yet.

If you keep a remote `DATABASE_URL` in `apps/api/.env` for day-to-day dev
against Supabase or another hosted Postgres, that file still applies when you
run `uvicorn` or ad-hoc `pytest` from `apps/api`. **`./ci.sh` and GitHub Actions
override it** for the API test run: they always set
`DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/redtape`
and `REQUIRE_DB=1`, matching [`.github/workflows/api-lint-test.yml`](../../.github/workflows/api-lint-test.yml),
so DB-backed tests never hit a remote database during CI.

## Checking migrations

```bash
docker compose up -d --wait db
cd apps/api
DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/redtape_migrations bash scripts/check_migrations.sh
```

[`scripts/check_migrations.sh`](../../apps/api/scripts/check_migrations.sh) asserts, against an empty
database: exactly one Alembic head, `alembic upgrade head` succeeds, the newest revision's
`downgrade`/`upgrade` round-trips cleanly, and `alembic check` reports no drift between the models and the
migration chain. Point `DATABASE_URL` at a database separate from the one pytest uses — the script drops
nothing itself, but running it against your dev database leaves it mid-round-trip. `./ci.sh` runs this same
script against its own throwaway `redtape_migrations` database, and CI runs it as a separate workflow job.

## Resetting / reseeding the local database

- **Reseed only** (fast, keeps schema/data structure): re-run the seed
  scripts — all are idempotent (`seed_i18n.py` upserts, `seed_jurisdictions.py`
  uses `session.merge()` with stable UUIDs, `seed_taxonomy.py` upserts by code), safe to run repeatedly:
  ```bash
  cd apps/api
  python -m scripts.seed_i18n
  python -m scripts.seed_jurisdictions
  python -m scripts.seed_taxonomy
  ```
- **Full reset** (wipes all local data, including the volume):
  ```bash
  docker compose down -v
  docker compose up -d db
  cd apps/api && alembic upgrade head
  python -m scripts.seed_i18n
  python -m scripts.seed_jurisdictions
  python -m scripts.seed_taxonomy
  ```
  If the API is already running, restart it after a full reset — its
  connection pool holds handles to the old (now-deleted) database and will
  return `500`s until restarted.

## Why this mirrors Render/Cloudflare

- **API**: Render's `render.yaml` runs the API as a native Python process
  (`env: python`, `pip install -e .` + `uvicorn app.main:app`) — not Docker.
  Running `uvicorn app.main:app --reload` locally from the same venv-installed
  package is the same execution model, so "works locally" reliably predicts
  "works on Render."
- **Database**: Supabase is managed Postgres. The schema genuinely depends on
  Postgres-specific features — `JSONB` (`app/models/document.py`,
  `locality.py`), `ARRAY` and a native `ENUM` (`app/models/jurisdiction.py`),
  and a Postgres upsert (`scripts/seed_i18n.py`). Running `postgres:16-alpine`
  locally gives the same dialect instead of fighting portability against
  SQLite.
- **Frontend**: `npm run dev` uses development mode and `apiOrigin()` →
  `http://localhost:8000` (override with `apps/web/.env` if needed). Start
  the API locally (`./scripts/dev-up.sh` or `uvicorn` in `apps/api`). Committed
  `apps/web/.env.production` intentionally omits `VITE_API_URL` so `vite build`
  (Cloudflare Workers Build) bakes same-origin `/api` URLs; the Worker proxies
  to Render. After deploy, the browser must not call `redtape-api.onrender.com`
  directly — only `…workers.dev/api/v1/…`.

## Known gaps (not addressed by this setup)

- `apps/web/vite.config.ts`'s `/api` dev proxy (`VITE_DEV_API_PROXY`) is
  effectively unused — `apiRequest` always builds a fully-qualified URL from
  `VITE_API_URL` and never routes through it. Harmless; not touched here.

## Troubleshooting

- **Port 5432 already in use**: something else (native Postgres, another
  project's container) is bound to it. Either stop that service, or locally
  (uncommitted) change `docker-compose.yml`'s `ports:` mapping (e.g.
  `"5433:5432"`) and set `DATABASE_URL` in `apps/api/.env` to match on port
  5433.
- **`alembic upgrade head` / API can't connect**: the container may not be
  healthy yet — run `docker compose ps` and wait for `healthy` before
  continuing.
- **Weird schema state**: `docker compose down -v` to drop the volume and
  start clean (see "Full reset" above).
- **Render: `DuplicateObject: type "discovery_source" already exists`**: the
  discovery staging tables may already exist while `alembic_version` is still on
  `20260929b_suggestion_event`. Confirm all six `discovery_*` / `catalogue_service`
  tables exist, run `alembic check` against production with a **session/direct**
  `DATABASE_URL`, then deploy a build with the idempotent
  `20261012_discovery_staging` migration (it no-ops when tables exist and records
  head), or run `alembic stamp 20261012_discovery_staging` before deploy. Do not
  `DROP TYPE discovery_source` while those tables exist.
