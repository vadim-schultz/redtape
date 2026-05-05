# RedTape API (`apps/api`)

Litestar backend for RedTape. **Wave 1** expands this into the full app (health, DB session, documents graph, CORS, OpenAPI).

## Wave 0 (this folder)

- Alembic migrations for i18n tables (`supported_locale`, `ui_translation`)
- Minimal Litestar app: `GET /health`, `GET /api/v1/locales`, `GET /api/v1/translations`
- Locale resolution middleware (`Accept-Language`, optional `?locale=`, fallback `requested → de → en`)

## Quick start

```bash
cd apps/api
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e .
copy .env.example .env   # set DATABASE_URL
alembic upgrade head
python -m scripts.seed_i18n
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

See [../../docs/planning/02-incremental-mvp-roadmap.md](../../docs/planning/02-incremental-mvp-roadmap.md) for wave order.
