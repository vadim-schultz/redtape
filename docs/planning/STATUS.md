# Project status

**This file is the source of truth for "what's done" and "what's next."** When a wave or milestone changes state, update this file rather than editing status markers scattered across [02-incremental-mvp-roadmap.md](02-incremental-mvp-roadmap.md) or the `directions/` docs (those keep their per-step detail; this page tracks the current, top-level picture).

Last updated: **2026-08-22**.

## Wave-by-wave state

| Wave | Plan says | Actual state | Evidence |
|---|---|---|---|
| Wave 0 — repo scaffolding + DB-backed i18n | Done (0a/0b, I1–I5); web/mobile providers drafted | **Done**, and further than the roadmap's own status table showed until this update: the web locale provider (I6) is a real, wired implementation, not a draft. Mobile (I7) is still genuinely a draft. | [`apps/api/app/locale_resolution.py`](../../apps/api/app/locale_resolution.py), [`apps/web/src/contexts/LocaleContext.tsx`](../../apps/web/src/contexts/LocaleContext.tsx) |
| Wave 1 — backend graph (`jurisdiction`, `document`, `document_requirement`) | — | **Done.** Migrations, models, and `GET /api/v1/documents`, `GET /api/v1/documents/{id}` implemented. | [`apps/api/alembic/versions/20260506_wave1_graph.py`](../../apps/api/alembic/versions/20260506_wave1_graph.py), [`apps/api/app/features/documents/`](../../apps/api/app/features/documents/) |
| *(not in original plan)* — OpenPLZ location import | Not mentioned anywhere in the roadmap or direction docs | **Done and shipped.** Full German location hierarchy (states/districts/municipalities/localities), 5 read endpoints, nightly GitHub Actions job, and a production data-repair migration for a duplicate-row incident. Now documented — see [directions/data-model-migrations/04-openplz-location-import.md](directions/data-model-migrations/04-openplz-location-import.md). | [`apps/api/app/features/locations/`](../../apps/api/app/features/locations/), [`.github/workflows/openplz-import.yml`](../../.github/workflows/openplz-import.yml) |
| Wave 2 — web MVP list/detail UI | — | **Done**, and beyond: documents list + detail, locale switcher, and a location-picker filter (state → district → city) riding on the OpenPLZ work above — not in the original Wave 2 deliverable list. | [`apps/web/src/features/`](../../apps/web/src/features/) |
| Wave 3 — deployment | Deploy MVP on Render + Cloudflare Pages, keep-alive cron | **Infra configured, live status unconfirmed/negative.** See "Verified deployment status" below — the API host may exist but isn't confirmed healthy, and the frontend does not appear deployed at all. | [`render.yaml`](../../render.yaml), [`.github/workflows/keep-alive.yml`](../../.github/workflows/keep-alive.yml), [deployment-checklist.md](../operations/deployment-checklist.md) |
| Wave 4 — mobile (Flutter) | Read-only Flutter client | **Not started.** `apps/mobile` has only a README and one `.draft` provider file — no `pubspec.yaml`, no real Dart source. | [`apps/mobile/`](../../apps/mobile/) |
| Wave 5 — jurisdiction fallback resolution | Deferred by design (seed MVP edges to one municipality) | **Unverified.** A full jurisdiction hierarchy and document→jurisdiction breadcrumb already exist and are tested, but it hasn't been directly confirmed whether real municipality→region→country precedence resolution (per [directions/data-model-migrations/03-graph-resolution-and-views.md](directions/data-model-migrations/03-graph-resolution-and-views.md)) is implemented, or whether the deferred-MVP shortcut is still all there is. | [`apps/api/tests/test_document_jurisdiction_path.py`](../../apps/api/tests/test_document_jurisdiction_path.py) |
| Wave 6 — Supabase Auth | Auth after MVP, prep for social layer | **Not started.** No auth/session/JWT code anywhere in `apps/api`. | — |
| Wave 7+ — social/moderation/crawlers/GDPR | Later waves | **Not started.** No proposal/vote/audit tables, no discovery/freshness crawler, no consent/privacy code. | — |

## Verified deployment status

Checked directly (not inferred from config) on 2026-08-22:

- **Backend** — `https://redtape-api.onrender.com/health` returned **HTTP 503 with a `Retry-After` header**, twice in a row. That's consistent with a real Render free-tier service that exists but is currently asleep or unhealthy — it is *not* a DNS/not-found failure. Could not confirm a clean `200 {"status":"ok"}` in this session.
- **Frontend** — `https://redtape-web.pages.dev` **failed to resolve in DNS at all** (`ENOTFOUND`). This means the Cloudflare Pages project referenced throughout `render.yaml`'s CORS list, `.env.example`, and the deployment checklist either was never created or was deleted. **Treat the frontend as not deployed.**

Wave 3's backend steps (D1–D4, D7, D8) look genuinely done from config; frontend steps (D5–D6) do not — Cloudflare Pages needs to actually be set up and connected before D9 (smoke tests) can mean anything.

## Known documentation/code drift (fixed in this pass)

- `docs/operations/gitlab-schedules.md` described a `.gitlab-ci.yml` job that never existed — there is no GitLab anywhere in this project. Renamed/rewritten as [`docs/operations/scheduled-jobs.md`](../operations/scheduled-jobs.md), describing the real GitHub Actions workflow.
- Roadmap's I6 status was stale ("Draft") — corrected to "Done."
- `apps/mobile/README.md` said "Wave 3" for the Flutter client; the roadmap calls it Wave 4 — mobile doc corrected to match.
- Stale/dead files not yet cleaned up (left alone for now — hygiene, not documentation): `apps/web/src/contexts/LocaleContext.tsx.draft`, `apps/mobile/lib/providers/locale_provider.dart.draft`, unused `apps/web/src/features/locations/components/LocationPicker.tsx`.

## Next step

**Get the frontend actually deployed to Cloudflare Pages (Wave 3, D5–D6),** then re-run [deployment-checklist.md](../operations/deployment-checklist.md) for real against both live URLs. Until that's done, "Wave 3 complete" isn't a safe claim regardless of how complete the config looks.

Known follow-ups, not yet scheduled:
- Confirm the Render API host is actually reachable (wake it from a browser, check the Render dashboard directly — this session's `Retry-After` result is ambiguous).
- Verify Wave 5 fallback-resolution behavior by reading the documents service directly.
- Before starting Wave 6 (Supabase Auth): write `directions/backend-api/03-auth-and-roles.md`, still marked TBD.
- The `apps/api` CI (`api-lint-test.yml`) runs against SQLite while the schema needs Postgres (JSONB, native enums) — the two DB-backed test files likely skip silently in CI. Not fixed in this pass (out of scope — documentation only); flagged here for a future session.
