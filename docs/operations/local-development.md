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
override it** for the API test run, and `REQUIRE_DB` defaults to `1`, so DB-backed tests never hit a remote
database during CI:

- `./ci.sh` uses the compose `db` service on `127.0.0.1:5432`. When Docker is available, it drops and recreates two
  throwaway databases on every run: `redtape_pytest` for pytest and `redtape_migrations` for the migration check. It
  never touches your local `redtape` database.
- GitHub Actions uses its own throwaway Postgres service containers, one in each job, as set in
  [`.github/workflows/api-lint-test.yml`](../../.github/workflows/api-lint-test.yml). The pytest job's database is
  named `redtape`, and the migration job's is `redtape_migrations`. Neither is your local compose database.

## pgvector

Search stores embeddings with the [pgvector](https://github.com/pgvector/pgvector) extension, so every Postgres the
API talks to must offer `vector` (and the contrib extension `unaccent`):

- **Local and CI**: `docker-compose.yml` and both Postgres services in
  [`.github/workflows/api-lint-test.yml`](../../.github/workflows/api-lint-test.yml) use `pgvector/pgvector:pg16`,
  the same Postgres 16 as before with the extension files installed. `docker compose up -d db` recreates an
  existing `db` container on the new image and keeps the `pgdata` volume. The image is Debian-based, where the old
  one was Alpine, so Postgres may warn about a collation version mismatch on databases created earlier; the local
  database is disposable, so rebuild it from migrations and seeds (see "Full reset") if you want the warning gone.
- **Tests**: `apps/api/tests/conftest.py` runs `CREATE EXTENSION IF NOT EXISTS vector` and `unaccent` before
  `Base.metadata.create_all`, so models that use `Vector` work without Alembic. A database whose server lacks the
  extension fails there loudly (`REQUIRE_DB=1`) instead of skipping.
- **Real databases** (Supabase): the search-schema migration creates the same extensions. Confirm that `vector` is
  offered first: `select name, default_version from pg_available_extensions where name = 'vector'`. Version 0.8 or
  later is needed for the iterative HNSW scan used with category filters; `halfvec` needs 0.7 or later.
- **Embedding model probe**: `python -m discovery_ingest embed probe` (needs `CLOUDFLARE_ACCOUNT_ID` and
  `CLOUDFLARE_AI_API_TOKEN`) prints one JSON report with the model's output dimension, the reduced dimensions its
  `dimensions` parameter honours, the largest accepted batch, latency, tokens and neurons. It calls Workers AI
  outside the neuron ledger, so it counts against the account's free allocation but not the budget table; a full run
  costs a few neurons. The report fixes `EMBEDDING_DIM` (API setting) and the column type for the search schema.
  The recorded run: dimension 1024, the model ignores `dimensions` (no reduced size is available), batches up to 256
  accepted; so `EMBEDDING_DIM=1024` with a `halfvec(1024)` column.

- **Translation probe**: `python -m discovery_ingest translate probe --locale <code> --sample 50 --engine llm` (run
  from `apps/discovery-ingest`; needs `DISCOVERY_API_URL`, which it only reads the public candidate list from,
  plus `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_AI_API_TOKEN`) translates a fixed, reproducible sample of the real cards
  (German title and card description) with the chosen engine, validates every result and prints one JSON report: pass
  rate per check, usage per unit in the engine's own unit, latency, and the projected usage and days for the whole
  corpus. It writes nothing to a database; the spot-check sheet for native speakers lands in
  `translation-probe/<engine>-<locale>.csv` (override with `--sheet`; the folder is git-ignored). Like the embedding
  probe it calls Workers AI outside the neuron ledger; `--max-usage` (default 3000 neurons) caps what one run may spend.

The new API settings (`EMBEDDING_MODEL`, `EMBEDDING_DIM`, `SEARCH_HYBRID_ENABLED`, `RRF_K`, `SEARCH_TOP_N`,
`SEARCH_FUSED_TOP_K`, `SEARCH_MIN_SIMILARITY`, `SEARCH_CONFIDENCE_WEIGHT`, `QUERY_EMBED_TIMEOUT_S`, `QUERY_EMBED_CACHE_SIZE`,
`QUERY_EMBED_NEURONS`, `QUERY_EMBED_BREAKER_FAILURES`, `QUERY_EMBED_BREAKER_COOLDOWN_S`,
`SEARCH_VECTOR_INDEX_ENABLED`, `SEARCH_RATE_LIMIT_PER_MINUTE`, `TRUSTED_PROXY_HOPS`,
`CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_AI_API_TOKEN`) are listed with their defaults in
[`apps/api/.env.example`](../../apps/api/.env.example). None is needed locally: with the defaults hybrid search is off.

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
  and a Postgres upsert (`scripts/seed_i18n.py`). Running Postgres 16
  locally (the `pgvector/pgvector:pg16` image, see "pgvector" below) gives the
  same dialect instead of fighting portability against SQLite.
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
