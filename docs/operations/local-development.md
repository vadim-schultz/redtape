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
python -m scripts.seed_documents
cd ../..

# Web, from the repo root. Optional: copy .env.example to .env and set
# NPM_REGISTRY there when the public registry is unreachable. That file is
# gitignored; scripts/npm.sh is the only reader.
./scripts/npm.sh install
```

No `apps/api/.env` or `apps/web/.env` is required for this path — both apps'
built-in defaults already point at the local stack (see "Why this mirrors
Render/Cloudflare" below). A repo-root `.env` is optional. When `NPM_REGISTRY`
is set, `scripts/npm.sh` uses it for the install and rewrites
`apps/web/package-lock.json` back to `https://registry.npmjs.org`. Committed
files stay on the public registry.

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

## Resetting / reseeding the local database

- **Reseed only** (fast, keeps schema/data structure): re-run the seed
  scripts — both are idempotent (`seed_i18n.py` upserts, `seed_documents.py`
  uses `session.merge()` with stable UUIDs), safe to run repeatedly:
  ```bash
  cd apps/api
  python -m scripts.seed_i18n
  python -m scripts.seed_documents
  ```
- **Full reset** (wipes all local data, including the volume):
  ```bash
  docker compose down -v
  docker compose up -d db
  cd apps/api && alembic upgrade head
  python -m scripts.seed_i18n
  python -m scripts.seed_documents
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
- **Frontend**: `apps/web/.env.production` (committed) is only read by
  `vite build` — the command Cloudflare Workers Build runs. `npm run dev`
  runs plain `vite`, which loads `.env`/`.env.development` only, never
  `.env.production`. So local dev cannot accidentally hit the production API;
  `VITE_API_URL` already defaults to `http://localhost:8000` in code
  (`apps/web/src/services/api.ts`, `apps/web/src/contexts/LocaleContext.tsx`)
  with zero configuration.

## Known gaps (not addressed by this setup)

- CI (`.github/workflows/api-lint-test.yml`) still runs tests against
  `sqlite:///test.db`; DB-backed tests silently skip there (see
  `apps/api/tests/conftest.py` and `docs/planning/STATUS.md`). Wiring CI to a
  real Postgres service container is a reasonable follow-up but is out of
  scope here.
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
