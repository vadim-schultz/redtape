# RedTape API (`apps/api`)

Litestar backend for RedTape. **Wave 1** adds the read-only documents graph (jurisdictions, documents, requirements), CORS, OpenAPI, and `GET /api/v1/documents`.

## Wave 0 (this folder)

- Alembic migrations for i18n tables (`supported_locale`, `ui_translation`)
- Minimal Litestar app: `GET /health`, `GET /api/v1/locales`, `GET /api/v1/translations`
- Locale resolution middleware (`Accept-Language`, optional `?locale=`, fallback `requested → de → en`)

## Wave 1

- Alembic: `jurisdiction`, `document`, `document_requirement`
- Seed: `python -m scripts.seed_documents` (idempotent; stable UUIDs)
- API: `GET /api/v1/documents`, `GET /api/v1/documents/{id}` (localized `title` / `description` / `notes`)
- CORS: `CORS_ALLOWED_ORIGINS` (comma-separated); OpenAPI: `/schema` (Litestar default)

## Supabase `DATABASE_URL` (IPv6 vs IPv4)

This section only applies to the Supabase alternative below; the local Postgres path needs no `DATABASE_URL` at all.

The dashboard **direct** URI (`db.<project>.supabase.co:5432`) is often labeled **not IPv4 compatible**. If `alembic` or the app cannot connect from your machine, use the **Session pooler** connection string from the same Supabase page (typically `*.pooler.supabase.com` port **6543** and user `postgres.<project-ref>`).

Use **`postgresql+psycopg://`** (not `postgresql://`) for this app, and append **`?sslmode=require`** unless your copied URI already includes `sslmode`.

Alembic and `app.db` also pass `sslmode=require` via `connect_args` when the host is Supabase and the URL omits `sslmode`.

## Quick start

For the full walkthrough (DB + API + web together), see [`docs/operations/local-development.md`](../../docs/operations/local-development.md).

### Local Postgres (default, recommended)

No `.env` file needed — `DATABASE_URL` already defaults to this local database
(`postgresql+psycopg://postgres:postgres@127.0.0.1:5432/redtape`).

```bash
# 1) Start local Postgres (from repo root)
docker compose up -d db

# 2) Set up and run the API
cd apps/api
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
alembic upgrade head
python -m scripts.seed_i18n
python -m scripts.seed_documents
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then open `http://127.0.0.1:8000/schema/swagger` for OpenAPI UI.

### Alternative: shared Supabase DB

Use this only if you need to test against real Supabase-hosted data (staging
verification, debugging a Supabase-specific issue) — most day-to-day work
should use the local Postgres path above.

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env   # Windows: copy .env.example .env
# set DATABASE_URL (+ optional CORS_ALLOWED_ORIGINS) in .env
alembic upgrade head
python -m scripts.seed_i18n
python -m scripts.seed_documents
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

See [../../docs/planning/02-incremental-mvp-roadmap.md](../../docs/planning/02-incremental-mvp-roadmap.md) for wave order.

## Development / CI checks

Install dev tooling:
```bash
cd apps/api
pip install -e ".[dev]"
```

Run the standard checks (these mirror the GitHub Actions workflow):
```bash
ruff format --check .
ruff check .
mypy app scripts
pytest -v
```
