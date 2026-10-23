# Project status

**This file is the source of truth for "what's done" and "what's next."** When a wave or milestone changes state, update this file rather than editing status markers scattered across [02-incremental-mvp-roadmap.md](02-incremental-mvp-roadmap.md) or the `directions/` docs (those keep their per-step detail; this page tracks the current, top-level picture).

Last updated: **2026-10-15**.

## Wave-by-wave state

| Wave | Plan says | Actual state | Evidence |
|---|---|---|---|
| Wave 0 — repo scaffolding + DB-backed i18n | Done (0a/0b, I1–I5); web/mobile providers drafted | **Done**, and further than the roadmap's own status table showed until this update: the web locale provider (I6) is a real, wired implementation, not a draft. Mobile (I7) is still genuinely a draft. | [`apps/api/app/locale_resolution.py`](../../apps/api/app/locale_resolution.py), [`apps/web/src/contexts/LocaleContext.tsx`](../../apps/web/src/contexts/LocaleContext.tsx) |
| Wave 1 — backend graph (`jurisdiction`, `document`, `document_requirement`) | — | **Done.** Migrations, models, and `GET /api/v1/documents`, `GET /api/v1/documents/{id}` implemented. | [`apps/api/alembic/versions/20260506_wave1_graph.py`](../../apps/api/alembic/versions/20260506_wave1_graph.py), [`apps/api/app/features/documents/`](../../apps/api/app/features/documents/) |
| *(not in original plan)* — OpenPLZ location import | Not mentioned anywhere in the roadmap or direction docs | **Done and shipped.** Full German location hierarchy (states/districts/municipalities/localities), 5 read endpoints, nightly GitHub Actions job, and a production data-repair migration for a duplicate-row incident. Now documented — see [directions/data-model-migrations/04-openplz-location-import.md](directions/data-model-migrations/04-openplz-location-import.md). | [`apps/api/app/features/locations/`](../../apps/api/app/features/locations/), [`.github/workflows/platform-maintenance.yml`](../../.github/workflows/platform-maintenance.yml) |
| Wave 2 — web MVP list/detail UI | — | **Done**, and beyond: documents list + detail, locale switcher, and a location-picker filter (state → district → city) riding on the OpenPLZ work above — not in the original Wave 2 deliverable list. | [`apps/web/src/features/`](../../apps/web/src/features/) |
| Wave 3 — deployment | Deploy MVP on Render + Cloudflare Pages, external pinger on /health | **Both hosts are live; CORS was broken between them and is being fixed, not yet reconfirmed end-to-end.** Frontend is deployed, but under a `workers.dev` domain (`https://redtape-web.vadim-schultz.workers.dev`), not the `pages.dev` domain assumed everywhere in config/docs — that mismatch caused the API to reject every frontend request (`400 Disallowed CORS Origin`). `CORS_ALLOWED_ORIGINS` in `render.yaml` has been corrected and pushed; a full click-through of the live frontend against the live API has not yet been confirmed. See "Verified deployment status" below. | [`render.yaml`](../../render.yaml), [deployment-checklist.md § External pinger](../operations/deployment-checklist.md#external-pinger-render-free-tier) |
| Wave 4 — mobile (Flutter) | Read-only Flutter client | **Not started.** `apps/mobile` has only a README and one `.draft` provider file — no `pubspec.yaml`, no real Dart source. | [`apps/mobile/`](../../apps/mobile/) |
| Wave 5 — jurisdiction fallback resolution | Deferred by design (seed MVP edges to one municipality) | **Unverified.** A full jurisdiction hierarchy and document→jurisdiction breadcrumb already exist and are tested, but it hasn't been directly confirmed whether real municipality→region→country precedence resolution (per [directions/data-model-migrations/03-graph-resolution-and-views.md](directions/data-model-migrations/03-graph-resolution-and-views.md)) is implemented, or whether the deferred-MVP shortcut is still all there is. | [`apps/api/tests/test_document_jurisdiction_path.py`](../../apps/api/tests/test_document_jurisdiction_path.py) |
| Wave 6 — Supabase Auth | Auth after MVP, prep for social layer | **Done.** Supabase JWT verification, `app_user` roles (`user`/`moderator`/`admin`), hashed machine API keys, and the web login UI, account menu and route guard are all shipped across twelve chapters. | [`apps/api/app/features/auth/`](../../apps/api/app/features/auth/), [`apps/web/src/features/auth/`](../../apps/web/src/features/auth/), [`.plans/auth/`](../../.plans/auth/00-architecture.md) |
| Wave 7+ — social/moderation/crawlers/GDPR | Later waves | **Started.** The suggestion interface is **shipped** ([`docs/operations/suggestion-api.md`](../operations/suggestion-api.md)). The **discovery layer** — staging ingest (`apps/discovery-ingest`), machine and admin discovery APIs, `/admin/discovery/*` review UI, and machine emit to **`pending`** suggestions — is **shipped** on loop branch `feat/plans-discovery-layer` (release PR to `main` pending). Chapters 16 (claim evidence), 20 (crawler frontier), and 21 (LLM extract) stay **deferred**. Suggestions still never write canonical `document`/`document_requirement` rows. Voting/promotion (`voting-moderation`), evidence storage, the crawlers suite, and consent/privacy code are still **not started**. | Suggestions: [`apps/api/app/features/suggestions/`](../../apps/api/app/features/suggestions/), [`.plans/suggestion-interface/`](../../.plans/suggestion-interface/00-architecture.md). Discovery: [`apps/api/app/features/discovery/`](../../apps/api/app/features/discovery/), [`apps/discovery-ingest/`](../../apps/discovery-ingest/), [`apps/web/src/features/discovery-admin/`](../../apps/web/src/features/discovery-admin/), runbook [`docs/operations/discovery-layer.md`](../operations/discovery-layer.md), [`.plans/discovery-layer/`](../../.plans/discovery-layer/00-architecture.md) |

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

**Update, 2026-09-24 (fourth pass)** — production browsers on some networks (e.g. corporate Zscaler) returned **403** on direct calls to `redtape-api.onrender.com` while the Workers frontend loaded fine. That is not a CORS allowlist gap (`render.yaml` already lists the `workers.dev` origin; Litestar would return **400** for a bad CORS origin). Fix: **same-origin API** — the Cloudflare Worker in [`apps/web/src/worker.ts`](../../apps/web/src/worker.ts) proxies `/api/*` to Render (`API_ORIGIN` in [`apps/web/wrangler.jsonc`](../../apps/web/wrangler.jsonc)); the SPA uses [`apps/web/src/services/apiOrigin.ts`](../../apps/web/src/services/apiOrigin.ts) so production builds call `/api/v1/...` on the Workers host. Render `CORS_ALLOWED_ORIGINS` stays for direct clients (local dev, curl). **Not yet done:** deploy and confirm Network tab shows `…workers.dev/api/v1/…` with `200`s.

**Update, 2026-09-26 — document matrix shipped.** Documents are organized on two independent axes, domain × life situation (13 domains, 18 situations, seeded for Germany with `de`/`en` names and existing documents tagged). API: `GET /api/v1/domains`, `/life-situations`, `/matrix`, plus `domain` / `situation` filters on `GET /api/v1/documents`. Web: `/matrix` page, URL-backed list filters, tags on document detail. Deferred: tags on list cards, curation. Details: [`.plans/document-matrix/`](../../.plans/document-matrix/00-architecture.md).

## Known documentation/code drift (fixed in this pass)

- `docs/operations/gitlab-schedules.md` described a `.gitlab-ci.yml` job that never existed — there is no GitLab anywhere in this project. Renamed/rewritten as [`docs/operations/scheduled-jobs.md`](../operations/scheduled-jobs.md), describing the real GitHub Actions workflow.
- Roadmap's I6 status was stale ("Draft") — corrected to "Done."
- `apps/mobile/README.md` said "Wave 3" for the Flutter client; the roadmap calls it Wave 4 — mobile doc corrected to match.
- Stale/dead files not yet cleaned up (left alone for now — hygiene, not documentation): `apps/web/src/contexts/LocaleContext.tsx.draft`, `apps/mobile/lib/providers/locale_provider.dart.draft`, unused `apps/web/src/features/locations/components/LocationPicker.tsx`.

**Update, 2026-09-27 — CI foundation shipped.** `apps/api` tests now run against a real Postgres service in
both GitHub Actions and local `./ci.sh` (no more silent SQLite skip); a missing database fails the run when
`REQUIRE_DB=1` (always set in CI) instead of skipping quietly. A second workflow job, and `./ci.sh` locally,
run [`apps/api/scripts/check_migrations.sh`](../../apps/api/scripts/check_migrations.sh) against a fresh
database on every PR: single Alembic head, `upgrade head`, downgrade/upgrade round trip of the newest
revision, and `alembic check` for model/migration drift. Details: [`.plans/ci-foundation/`](../../.plans/ci-foundation/00-architecture.md).

**Update, 2026-09-27 — auth shipped.** Supabase Auth (email magic link) is verified by the API via JWT/JWKS;
`app_user` carries a `user`/`moderator`/`admin` role, never read from the token; hashed API keys
(`rt_…`, SHA-256 only) authenticate machine clients such as crawlers. Web gained a Supabase session, a login
page, an account menu item and a `RequireAuth` route guard. All twelve chapters done; nothing changes for an
environment with no Supabase project configured. Details: [`.plans/auth/`](../../.plans/auth/00-architecture.md),
runbook: [`docs/operations/auth-setup.md`](../operations/auth-setup.md).

**Update, 2026-10-15 — discovery layer shipped (loop).** GovData and PVOG catalogue ingest, FIM/LeiKa enrich,
admin pipeline UI, coverage metrics, and machine emit to pending suggestions are on `feat/plans-discovery-layer`.
Canon and fixtures: [`docs/discovery/government-data-sources.md`](../discovery/government-data-sources.md).
Operator steps: [`docs/operations/discovery-layer.md`](../operations/discovery-layer.md). Twenty in-loop plan
chapters are **shipped**; evidence-backed claims (16), crawler frontier adapter (20), and LLM extract (21)
remain deferred for `evidence-storage` and `crawlers`. Details:
[`.plans/discovery-layer/`](../../.plans/discovery-layer/00-architecture.md).

## Next step

**Confirm the live frontend can actually talk to the live API (Wave 3, D9 smoke tests):** deploy the Worker + SPA (same-origin `/api` proxy), then click through `https://redtape-web.vadim-schultz.workers.dev` and confirm DevTools → Network shows same-origin `…/api/v1/…` requests succeeding. Re-run [deployment-checklist.md](../operations/deployment-checklist.md) against both live URLs. Until that's done, "Wave 3 complete" isn't a safe claim regardless of how complete the config looks.

Known follow-ups, not yet scheduled:
- Confirm whether Render auto-deploys on `render.yaml` env var changes for this service, or whether a manual Blueprint sync is required — unclear from this session.
- Verify Wave 5 fallback-resolution behavior by reading the documents service directly.
