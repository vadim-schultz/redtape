# Wave 0 — Repo layout + DB-backed i18n (implementation notes)

Normative roadmap steps live in [../../02-incremental-mvp-roadmap.md](../../02-incremental-mvp-roadmap.md) (steps **0a–0b**, **I1–I7**).

## What shipped in the repo

| Area | Location | Notes |
|------|-----------|--------|
| Monorepo shells | [`apps/api`](../../../../apps/api), [`apps/web`](../../../../apps/web), [`apps/mobile`](../../../../apps/mobile) | Web/mobile include **draft** snippets only until Waves 2–3. |
| API + migrations | [`apps/api`](../../../../apps/api) | Litestar + Alembic + `supported_locale` / `ui_translation` + seed JSON → DB. |
| Locale rules | [`apps/api/app/locale_resolution.py`](../../../../apps/api/app/locale_resolution.py), middleware in [`apps/api/app/main.py`](../../../../apps/api/app/main.py) | `?locale=` override, `Accept-Language`, fallback **requested → de → en**. |

## Smoke checks

From `apps/api` (with `DATABASE_URL` set, Postgres reachable):

```bash
alembic upgrade head
python -m scripts.seed_i18n
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then:

- `GET /health` → `{"status":"ok"}`
- `GET /api/v1/locales` → enabled rows from `supported_locale`
- `GET /api/v1/translations?locale=de` (or rely on `Accept-Language`) → `{ locale, translations }` with `Cache-Control` for long cache

## Related direction strands

- [../i18n-localization/README.md](../i18n-localization/README.md)
- [../backend-api/README.md](../backend-api/README.md)
- [../devops-ci-cd/README.md](../devops-ci-cd/README.md)
