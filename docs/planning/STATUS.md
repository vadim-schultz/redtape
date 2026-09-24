# Project status

**This file is the source of truth for "what's done" and "what's next."** When a wave or milestone changes state, update this file rather than editing status markers scattered across [02-incremental-mvp-roadmap.md](02-incremental-mvp-roadmap.md) or the `directions/` docs (those keep their per-step detail; this page tracks the current, top-level picture).

Last updated: **2026-09-23**.

## Wave-by-wave state

| Wave | Plan says | Actual state | Evidence |
|---|---|---|---|
| Wave 0 — repo scaffolding + DB-backed i18n | Done (0a/0b, I1–I5); web/mobile providers drafted | **Done**, and further than the roadmap's own status table showed until this update: the web locale provider (I6) is a real, wired implementation, not a draft. Mobile (I7) is still genuinely a draft. | [`apps/api/app/locale_resolution.py`](../../apps/api/app/locale_resolution.py), [`apps/web/src/contexts/LocaleContext.tsx`](../../apps/web/src/contexts/LocaleContext.tsx) |
| Wave 1 — backend graph (`jurisdiction`, `document`, `document_requirement`) | — | **Done.** Migrations, models, and `GET /api/v1/documents`, `GET /api/v1/documents/{id}` implemented. | [`apps/api/alembic/versions/20260506_wave1_graph.py`](../../apps/api/alembic/versions/20260506_wave1_graph.py), [`apps/api/app/features/documents/`](../../apps/api/app/features/documents/) |
| *(not in original plan)* — OpenPLZ location import | Not mentioned anywhere in the roadmap or direction docs | **Done and shipped.** Full German location hierarchy (states/districts/municipalities/localities), 5 read endpoints, nightly GitHub Actions job, and a production data-repair migration for a duplicate-row incident. Now documented — see [directions/data-model-migrations/04-openplz-location-import.md](directions/data-model-migrations/04-openplz-location-import.md). | [`apps/api/app/features/locations/`](../../apps/api/app/features/locations/), [`.github/workflows/openplz-import.yml`](../../.github/workflows/openplz-import.yml) |
| Wave 2 — web MVP list/detail UI | — | **Done**, and beyond: documents list + detail, locale switcher, and a location-picker filter (state → district → city) riding on the OpenPLZ work above — not in the original Wave 2 deliverable list. | [`apps/web/src/features/`](../../apps/web/src/features/) |
| Wave 3 — deployment | Deploy MVP on Render + Cloudflare Pages, keep-alive cron | **Both hosts are live; CORS was broken between them and is being fixed, not yet reconfirmed end-to-end.** Frontend is deployed, but under a `workers.dev` domain (`https://redtape-web.vadim-schultz.workers.dev`), not the `pages.dev` domain assumed everywhere in config/docs — that mismatch caused the API to reject every frontend request (`400 Disallowed CORS Origin`). `CORS_ALLOWED_ORIGINS` in `render.yaml` has been corrected and pushed; a full click-through of the live frontend against the live API has not yet been confirmed. See "Verified deployment status" below. | [`render.yaml`](../../render.yaml), [`.github/workflows/keep-alive.yml`](../../.github/workflows/keep-alive.yml), [deployment-checklist.md](../operations/deployment-checklist.md) |
| Wave 4 — mobile (Flutter) | Read-only Flutter client | **Not started.** `apps/mobile` has only a README and one `.draft` provider file — no `pubspec.yaml`, no real Dart source. | [`apps/mobile/`](../../apps/mobile/) |
| Wave 5 — jurisdiction fallback resolution | Deferred by design (seed MVP edges to one municipality) | **Unverified.** A full jurisdiction hierarchy and document→jurisdiction breadcrumb already exist and are tested, but it hasn't been directly confirmed whether real municipality→region→country precedence resolution (per [directions/data-model-migrations/03-graph-resolution-and-views.md](directions/data-model-migrations/03-graph-resolution-and-views.md)) is implemented, or whether the deferred-MVP shortcut is still all there is. | [`apps/api/tests/test_document_jurisdiction_path.py`](../../apps/api/tests/test_document_jurisdiction_path.py) |
| Wave 6 — Supabase Auth | Auth after MVP, prep for social layer | **Not started.** No auth/session/JWT code anywhere in `apps/api`. | — |
| Wave 7+ — social/moderation/crawlers/GDPR | Later waves | **Not started.** No proposal/vote/audit tables, no discovery/freshness crawler, no consent/privacy code. | — |

## Verified deployment status

Checked directly (not inferred from config) on 2026-08-22:

- **Backend** — `https://redtape-api.onrender.com/health` returned **HTTP 503 with a `Retry-After` header**, twice in a row. That's consistent with a real Render free-tier service that exists but is currently asleep or unhealthy — it is *not* a DNS/not-found failure. Could not confirm a clean `200 {"status":"ok"}` in this session.
- **Frontend** — `https://redtape-web.pages.dev` **failed to resolve in DNS at all** (`ENOTFOUND`). This means the Cloudflare Pages project referenced throughout `render.yaml`'s CORS list, `.env.example`, and the deployment checklist either was never created or was deleted. **Treat the frontend as not deployed.**

Wave 3's backend steps (D1–D4, D7, D8) look genuinely done from config; frontend steps (D5–D6) do not — Cloudflare Pages needs to actually be set up and connected before D9 (smoke tests) can mean anything.

**Update, 2026-09-23** — user reports the Render API host is now reachable (not independently re-checked in this session). A Cloudflare Pages deploy attempt for the frontend surfaced two real issues:

1. `npm error enoent ... Could not read package.json` at `/opt/buildhome/repo/package.json` — the Pages project's **Root directory** setting is not pointed at `apps/web` (this repo is not an npm-workspace monorepo, so there is no root `package.json`; this is a dashboard setting, not something fixable in-repo). **Still needs to be set by hand in the Cloudflare Pages project settings.**
2. `npm` could not resolve a private registry host — [`apps/web/package-lock.json`](../../apps/web/package-lock.json) had 468 `resolved` URLs pointing at that mirror instead of the public npm registry, almost certainly from a lockfile generated on a machine with a private npm proxy configured. `npm ci`/`npm install` fetches from the exact `resolved` URL regardless of the configured registry, so Cloudflare's sandboxed build (no route to that host) failed. **Fixed**: lockfile regenerated from scratch against `registry.npmjs.org`; `npm run build` verified locally.

Neither issue has been re-tested against an actual Cloudflare Pages build yet — that requires the Root directory fix above, then a fresh deploy.

**Update, 2026-09-23 (later same day)** — frontend is now actually deployed and reachable: `https://redtape-web.vadim-schultz.workers.dev` returns `200`. This is a **`workers.dev` domain, not `pages.dev`** — Cloudflare served this Pages project's static assets through Workers rather than the classic `*.pages.dev` subdomain. Every place in this repo that assumed `redtape-web.pages.dev` (`render.yaml`'s `CORS_ALLOWED_ORIGINS`, `apps/api/app/middleware/cors.py`'s hardcoded fallback, `apps/api/.env.example`) was therefore wrong, and the API was rejecting all frontend requests at the CORS preflight stage (confirmed directly: `OPTIONS /api/v1/documents` with `Origin: https://redtape-web.vadim-schultz.workers.dev` returned `400 Disallowed CORS Origin`). Fixed:
- `render.yaml` — `CORS_ALLOWED_ORIGINS` now lists the real `workers.dev` origin (pushed to `main`).
- `apps/api/app/middleware/cors.py` — removed the hardcoded, now-wrong `pages.dev` fallback the code always appended regardless of config; `CORS_ALLOWED_ORIGINS` is the sole source of truth now (with a test covering this).
- `apps/api/.env.example` — example updated to the real origin.

**Not yet done:** re-confirm the live preflight succeeds after Render redeploys with the new env var (Render can take a few minutes, or may need a manual Blueprint sync, to pick up a `render.yaml` env var change), then click through the actual deployed frontend end-to-end.

**Update, 2026-09-23 (third pass)** — with CORS fixed, the browser console showed a second, unrelated bug: every API call from the deployed frontend targeted `localhost:8000` (`ERR_CONNECTION_REFUSED`), meaning `VITE_API_URL` was never actually baked into the production bundle, so Vite fell back to its dev default ([apps/web/src/services/api.ts](../../apps/web/src/services/api.ts)). Root cause: **this Cloudflare project is a git-connected Workers Build, not classic Pages** (hence the `workers.dev` domain) — dashboard-set variables on these only apply to the deployment you set them on and get reset on the next git-triggered build, because Workers Builds re-syncs config from a `wrangler.toml`/`wrangler.jsonc` **in the repo**, which didn't exist. This is also why the earlier "Root directory" fix and the CORS origin were both real, separate config gaps rather than one root cause — three independent deploy-config issues stacked on the same rollout.

Fixed: added [`apps/web/wrangler.jsonc`](../../apps/web/wrangler.jsonc), committing `name` (`redtape-web`), `assets.directory` (`./dist`, confirmed against a local `npm run build`), `assets.not_found_handling: single-page-application` (so direct navigation to client routes like `/documents` doesn't 404), and `vars.VITE_API_URL` pointing at the Render API. This makes the config durable across future Workers Builds deploys instead of dashboard-only.

**Not yet done:** confirm a fresh deploy picks up `wrangler.jsonc` and the frontend successfully calls the API end-to-end (no `ERR_CONNECTION_REFUSED`, no CORS errors).

## Known documentation/code drift (fixed in this pass)

- `docs/operations/gitlab-schedules.md` described a `.gitlab-ci.yml` job that never existed — there is no GitLab anywhere in this project. Renamed/rewritten as [`docs/operations/scheduled-jobs.md`](../operations/scheduled-jobs.md), describing the real GitHub Actions workflow.
- Roadmap's I6 status was stale ("Draft") — corrected to "Done."
- `apps/mobile/README.md` said "Wave 3" for the Flutter client; the roadmap calls it Wave 4 — mobile doc corrected to match.
- Stale/dead files not yet cleaned up (left alone for now — hygiene, not documentation): `apps/web/src/contexts/LocaleContext.tsx.draft`, `apps/mobile/lib/providers/locale_provider.dart.draft`, unused `apps/web/src/features/locations/components/LocationPicker.tsx`.

## Next step

**Confirm the live frontend can actually talk to the live API (Wave 3, D9 smoke tests):** wait for Render to pick up the corrected `CORS_ALLOWED_ORIGINS`, re-check the preflight, then click through `https://redtape-web.vadim-schultz.workers.dev` end-to-end against `https://redtape-api.onrender.com`. Then re-run [deployment-checklist.md](../operations/deployment-checklist.md) for real against both live URLs (update its URLs first — it still references the old `pages.dev` assumption). Until that's done, "Wave 3 complete" isn't a safe claim regardless of how complete the config looks.

Known follow-ups, not yet scheduled:
- Confirm whether Render auto-deploys on `render.yaml` env var changes for this service, or whether a manual Blueprint sync is required — unclear from this session.
- Verify Wave 5 fallback-resolution behavior by reading the documents service directly.
- Before starting Wave 6 (Supabase Auth): write `directions/backend-api/03-auth-and-roles.md`, still marked TBD.
- The `apps/api` CI (`api-lint-test.yml`) runs against SQLite while the schema needs Postgres (JSONB, native enums) — the two DB-backed test files likely skip silently in CI. Not fixed in this pass (out of scope — documentation only); flagged here for a future session.
