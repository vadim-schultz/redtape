# Project status

**This file is the source of truth for "what's done" and "what's next."** When a wave or milestone changes state, update this file rather than editing status markers scattered across [02-incremental-mvp-roadmap.md](02-incremental-mvp-roadmap.md) or the `directions/` docs (those keep their per-step detail; this page tracks the current, top-level picture).

Last updated: **2026-09-22**. No application commits since `c9a36fe` (2026-08-22).

## Resume here

Waves 0–2 are done, plus an OpenPLZ location import that was not in the original roadmap. The API is live on Render and returns `{"status":"ok"}` after the free-tier cold start. The web app is not deployed: [https://redtape-web.pages.dev](https://redtape-web.pages.dev) is the planned Cloudflare Pages URL and is not reachable, because that Pages project was never created.

**Next session:** Wave 3 steps D5–D6 — create the Cloudflare Pages project, connect the repo, set `VITE_API_URL` to the Render API, then run [deployment-checklist.md](../operations/deployment-checklist.md).

## Wave-by-wave state

| Wave | Actual state | Evidence |
|---|---|---|
| Wave 0 — repo scaffolding + DB-backed i18n | **Done** for API and web (I1–I6). Mobile provider (I7) is still a draft. | [`apps/api/app/locale_resolution.py`](../../apps/api/app/locale_resolution.py), [`apps/web/src/contexts/LocaleContext.tsx`](../../apps/web/src/contexts/LocaleContext.tsx) |
| Wave 1 — backend graph (`jurisdiction`, `document`, `document_requirement`) | **Done.** Migrations, models, and `GET /api/v1/documents`, `GET /api/v1/documents/{id}`. | [`apps/api/alembic/versions/20260506_wave1_graph.py`](../../apps/api/alembic/versions/20260506_wave1_graph.py), [`apps/api/app/features/documents/`](../../apps/api/app/features/documents/) |
| *(not in original plan)* — OpenPLZ location import | **Done and shipped.** German location hierarchy, 5 read endpoints, nightly GitHub Actions job, and a production data-repair migration for a duplicate-row incident. | [`apps/api/app/features/locations/`](../../apps/api/app/features/locations/), [`.github/workflows/openplz-import.yml`](../../.github/workflows/openplz-import.yml), [04-openplz-location-import.md](directions/data-model-migrations/04-openplz-location-import.md) |
| Wave 2 — web MVP list/detail UI | **Done**, and beyond the original list: documents list + detail, locale switcher, and a location-picker filter (state → district → city). | [`apps/web/src/features/`](../../apps/web/src/features/) |
| Wave 3 — deployment | **Backend live; frontend not deployed.** Render serves `/health` after cold start. Cloudflare Pages (D5–D6) was never set up. | [`render.yaml`](../../render.yaml), [`.github/workflows/keep-alive.yml`](../../.github/workflows/keep-alive.yml) |
| Wave 4 — mobile (Flutter) | **Not started.** `apps/mobile` has only a README and one `.draft` provider file — no `pubspec.yaml`, no real Dart source. | [`apps/mobile/`](../../apps/mobile/) |
| Wave 5 — jurisdiction fallback resolution | **Not started.** Documents are filtered by an exact jurisdiction, and detail returns only that document's direct outgoing edges. The parent walk is a breadcrumb, not municipality → region → country requirement inheritance. | [`apps/api/app/features/documents/service.py`](../../apps/api/app/features/documents/service.py), [`apps/api/app/features/documents/repository.py`](../../apps/api/app/features/documents/repository.py) |
| Wave 6 — Supabase Auth | **Not started.** No auth/session/JWT code in `apps/api`. | — |
| Wave 7+ — social/moderation/crawlers/GDPR | **Not started.** No proposal/vote/audit tables, no discovery/freshness crawler, no consent/privacy code. | — |

## Verified deployment status

Checked on **2026-09-22**:

- **Backend (Render)** — [https://redtape-api.onrender.com/health](https://redtape-api.onrender.com/health) returns `{"status":"ok"}` after the free-tier startup delay. The August 2026 HTTP 503 with `Retry-After` was the service asleep, not a missing host. Backend steps D1–D4, D7, and D8 are in place (`render.yaml`, CORS for the planned Pages origin, keep-alive workflow).
- **Frontend (Cloudflare Pages)** — [https://redtape-web.pages.dev](https://redtape-web.pages.dev) is the hostname the repo already allows in CORS and documents as the production web origin. It is not reachable. The Pages project was not created, so D5–D6 are still open and D9 (production smoke tests) cannot run yet.

## Next step

**Deploy the web app to Cloudflare Pages (Wave 3, D5–D6),** then re-run [deployment-checklist.md](../operations/deployment-checklist.md) against both live URLs.

Known follow-ups, not the next session:

- Wave 4: Flutter read-only client (roadmap M1–M4). I7 stays a draft until then.
- Wave 5: implement municipality → region → country requirement resolution (roadmap R1–R2, [03-graph-resolution-and-views.md](directions/data-model-migrations/03-graph-resolution-and-views.md)).
- Before Wave 6: write `directions/backend-api/03-auth-and-roles.md` (still TBD).
- API CI ([`.github/workflows/api-lint-test.yml`](../../.github/workflows/api-lint-test.yml)) uses SQLite while the schema needs Postgres (JSONB, native enums). The DB-backed tests likely skip in CI.
- Stale files left in place: `apps/web/src/contexts/LocaleContext.tsx.draft`, `apps/mobile/lib/providers/locale_provider.dart.draft`, unused `apps/web/src/features/locations/components/LocationPicker.tsx`.

## How to update this file

After a session that changes a wave's state, edit the resume paragraph, the matching table row, and the next step. Leave per-step checklists in the roadmap and direction docs alone.
