# Incremental MVP roadmap (hour-sized steps)

This roadmap matches [00-master-summary.md](00-master-summary.md) and the strand docs under [directions/](directions/). Order is **backend → web → mobile**. Each step is scoped so a focused Cursor session (~**1 hour**) can complete it, including smoke checks.

## Consolidated free tier (recommended baseline)

Use **one Supabase project** for as much as possible:

| Concern | Supabase capability | When to touch it |
|--------|----------------------|------------------|
| PostgreSQL | Built-in | From step B3 onward (migrations + seed). |
| Auth (email/OAuth) + JWT | Built-in | After read-only graph MVP (wave 2); API validates JWT with project JWKS. |
| Object storage (screenshots, evidence) | Storage buckets | Social / crawler waves; not needed for the 1-city / 3-deps read MVP. |

**Still separate (typical):** Litestar API **hosting** (Fly.io, Render, Railway, or VPS)—Supabase does not run your Python app. **Web** static hosting (Supabase Hosting, Cloudflare Pages, Netlify, or Vercel). **Flutter** builds locally / store pipelines.

---

## MVP definition (smallest shippable slice)

- **One country** (Germany), **one Land**, **one municipality** (your example city).
- **Four documents** in the catalog: one *target* document and **three distinct dependencies** (edges: target → each required doc).
- **Read-only HTTP API** + **web** list/detail + **mobile** read same data.
- **No** social layer, **no** crawlers, **no** vault, **no** push reminders until later waves.

Jurisdiction **fallback** (city → Land → country) can be **seeded but unused** in the first slice: attach all MVP edges to the municipality row so resolution logic can wait one step.

---

## Wave 0 — Repository and contracts (optional precursors)

| Step | Outcome | Notes | Status |
|------|---------|--------|--------|
| 0a | Add monorepo folders `apps/api`, `apps/web`, `apps/mobile` (empty or placeholder README) | No framework yet; aligns with [devops-ci-cd](directions/devops-ci-cd/README.md). | Done — see [wave-0-repo-i18n](directions/wave-0-repo-i18n/README.md) |
| 0b | Root `.gitignore` + document Python/Node/Flutter ignores | Prevents noise in commits. | Done |

---

## Wave 0 (continued) — DB-backed i18n before user-facing copy

Aligns with [directions/i18n-localization/README.md](directions/i18n-localization/README.md). **MVP locales: `de` + `en` only** (both required for every shipped UI key and seeded domain JSONB).

| Step | Outcome | Notes | Status |
|------|---------|--------|--------|
| I1 | Migration: `supported_locale` + `ui_translation` (+ seed `de` / `en` rows enabled) | Enables locale picker and validation. | Done — [`apps/api/alembic/versions`](../../apps/api/alembic/versions) |
| I2 | Seed pipeline: nested JSON (or flat CSV) **imported into** `ui_translation` — files are authoring convenience, **not** a second runtime source | Keeps “DB only” for production behavior. | Done — [`apps/api/scripts/seed_data/translations`](../../apps/api/scripts/seed_data/translations) + [`seed_i18n.py`](../../apps/api/scripts/seed_i18n.py) |
| I3 | `GET /api/v1/translations?locale=` — returns `{ locale, translations: { key: value } }` | Long-cache headers when stable. | Done — [`apps/api/app/routes.py`](../../apps/api/app/routes.py) |
| I4 | `GET /api/v1/locales` — lists enabled locales for pickers | Driven by `supported_locale`. | Done |
| I5 | Locale resolution: `Accept-Language` + optional `?locale=` override; fallback **requested → `de` → `en`** | Document in [backend-api](directions/backend-api/README.md). | Done — [`apps/api/app/locale_resolution.py`](../../apps/api/app/locale_resolution.py) + middleware |
| I6 | Web: `LocaleProvider` / context — fetch bundle on load; `setLocale` refetches bundle + graph requests with new header | See [web-frontend](directions/web-frontend/README.md). | Done — [`apps/web/src/contexts/LocaleContext.tsx`](../../apps/web/src/contexts/LocaleContext.tsx) (landed with Wave 2 W2; the old `LocaleContext.tsx.draft` scaffold is stale and superseded) |
| I7 | Mobile: same pattern — provider + `Accept-Language` on API client | See [mobile-flutter](directions/mobile-flutter/README.md). | Draft — [`apps/mobile/lib/providers/locale_provider.dart.draft`](../../apps/mobile/lib/providers/locale_provider.dart.draft) (Wave 4 M2) |

**Checkpoint:** Switching `de`/`en` updates UI chrome and API-returned domain strings without redeploy.

---

## Wave 1 — Backend (`apps/api`): skeleton to seeded graph

**Update, 2026-11-02:** the web document list is now candidate-backed (the sample documents below are removed); see [STATUS.md](STATUS.md) and the [document-browse-confidence](../../.plans/document-browse-confidence/00-architecture.md) plan. The steps below are kept as history.

**Status: Done.** B1–B13 all landed — see [`apps/api/app/`](../../apps/api/app/), migration [`20260506_wave1_graph.py`](../../apps/api/alembic/versions/20260506_wave1_graph.py), and [`apps/api/scripts/seed_jurisdictions.py`](../../apps/api/scripts/seed_jurisdictions.py). Live status detail: [STATUS.md](STATUS.md).

| Step | Outcome | Notes |
|------|---------|--------|
| B1 | `pyproject.toml` (or Poetry) with Litestar, uvicorn, pydantic-settings, SQLAlchemy 2.x, asyncpg or psycopg, alembic | Pin loosely; upgrade later. |
| B2 | Minimal Litestar app: `GET /health` → JSON `{ "status": "ok" }` | Run locally with uvicorn. |
| B3 | `.env.example`: `DATABASE_URL` (Supabase connection string), optional `SUPABASE_URL` / keys for later | **Manual:** create Supabase project, copy **Session mode** URI if using SQLAlchemy server-side. |
| B4 | `Settings` via pydantic-settings; load `.env`; wire Litestar **lifespan** to create/dispose DB engine | No routes except health yet. |
| B5 | SQLAlchemy **declarative base** + `sessionmaker`; Litestar dependency provides `AsyncSession` (or sync session if you keep stack simpler for hour-1) | Pick one style and stay consistent. |
| B6 | Alembic initialized; `env.py` reads `DATABASE_URL`; `alembic revision --autogenerate` workflow documented | First revision can be empty `pass` to verify chain. |
| B7 | **Migration:** unified `jurisdiction` (`id`, `kind` enum: COUNTRY \| REGION \| MUNICIPALITY, `parent_id` self-FK, `code`, `levels` text[] for “which administrative levels this unit satisfies”, `name_i18n` JSONB) | Matches [01-jurisdiction-hierarchy](directions/data-model-migrations/01-jurisdiction-hierarchy.md) + discussion (e.g. Dresden `levels` including DISTRICT+MUNICIPALITY). |
| B8 | **Migration:** `document` (`title_i18n`, `description_i18n` JSONB, `jurisdiction_id`, `slug`, …) + `requirement` / `document_requirement` (`parent_document_id`, `required_document_id`, `jurisdiction_id`, `notes_i18n` JSONB optional, `source`, `valid_from` / `valid_to`) | Matches [02-documents-and-requirements](directions/data-model-migrations/02-documents-and-requirements.md); list/detail responses expose **resolved** `title`/`description` strings for the request locale, not raw JSONB. |
| B9 | **Seed script** (idempotent): insert DE, one Land, one city, **4 documents** (each `title_i18n` / `description_i18n` with **both** `de` and `en`), **3** requirement rows for one target | Use stable UUIDs or natural keys so re-runs do not duplicate. |
| B10 | `GET /api/v1/documents` — returns MVP documents with **localized** titles for `Accept-Language` | Same session can add `?jurisdiction_id=` filter; pagination stub OK. |
| B11 | `GET /api/v1/documents/{id}` — document + **direct** `requirements[]` (localized titles/notes) | Join or second query; no full tree yet. |
| B12 | **CORS** plugin: allow local Vite origin + production web origin env var | Required before web app hits API. |
| B13 | Enable Litestar **OpenAPI** / Swagger UI for manual QA | Helps web/mobile contract alignment. |

**Checkpoint:** Postman or browser can load document with three dependencies against local or Supabase-hosted DB.

**Note:** an additional, undocumented-until-now subsystem also shipped alongside Wave 1/2 — a full German location hierarchy (`locality` table + `/countries`/`/states`/`/districts`/`/cities`/`/localities` endpoints) imported from the OpenPLZ API. See [directions/data-model-migrations/04-openplz-location-import.md](directions/data-model-migrations/04-openplz-location-import.md).

---

## Wave 2 — Web (`apps/web`): Vite + React + Chakra

**Status: Done**, and beyond W1–W7: the shipped app also includes a location-picker filter (state → district → city) backed by the OpenPLZ endpoints, which isn't part of this wave's original deliverable list. See [`apps/web/src/`](../../apps/web/src/) and [STATUS.md](STATUS.md).

| Step | Outcome | Notes |
|------|---------|--------|
| W1 | `npm create vite@latest` (React + TS) in `apps/web`; install `@chakra-ui/react` + peers | Follow Chakra v3 docs if that is current default. |
| W2 | `ChakraProvider` + **LocaleProvider** (or equivalent) wrapping router root; basic theme | LocaleProvider loads `GET /api/v1/translations` (see Wave 0 continued). |
| W3 | `VITE_API_URL` in `.env.example`; small `fetch` helper with typed errors; **default `Accept-Language` from locale state** | Points to `http://localhost:8000` during dev. |
| W4 | **Locale switcher** (header): `de` / `en`; triggers bundle + data refetch | Must not hardcode user-visible strings in components. |
| W5 | Route `/documents` — fetch `GET /documents`, render **SimpleList** (localized titles + links to detail) | Expect 4 rows from seed. |
| W6 | Route `/documents/:id` — fetch `GET /documents/:id`, show localized title + **List** of three dependencies (each links to its id) | Smallest navigation loop. |
| W7 | Optional: breadcrumb “Germany / Land / City” from **static** copy or tiny `GET /jurisdictions/mvp` if you add a 1-hour endpoint | Can be hardcoded for true 1-hour cap; prefer localized jurisdiction names from API when available. |

**Checkpoint:** Click through target → dependency → back; matches backend seed.

---

## Wave 3 — Deployment & Production Readiness

This wave deploys the already-built MVP slice on free-tier–friendly services.

| Step | Outcome | Notes |
|------|---------|-------|
| D1 | Render account + API Web service created | Manual dashboard work |
| D2 | `render.yaml` committed at repo root | Agent step |
| D3 | Render environment variables configured | Manual: `DATABASE_URL`, secrets |
| D4 | Backend deployed + health endpoint verified | Manual: push + check logs |
| D5 | Cloudflare Pages project created and connected | Manual dashboard work |
| D6 | Frontend deployed + `VITE_API_URL` configured | Manual: set env var + rebuild |
| D7 | CORS allows the Pages frontend origin | Agent step (production origin) |
| D8 | External pinger on `/health` (Render free tier) | Operator step: UptimeRobot or cron-job.org monitor |
| D9 | Production smoke tests pass for list/detail | Use the deployment checklist |
| D10 | Environment/URL notes captured for later waves | Record Render + Pages URLs |
| D11 | Deployment checklist document updated | Agent step |
| D12 | Optional: monitoring/log retention setup | Manual or agent as time allows |

**Checkpoint:** Backend + frontend are live; browser API calls work without CORS failures.

---
## Wave 4 — Mobile (`apps/mobile`): Flutter read-only

| Step | Outcome | Notes |
|------|---------|--------|
| M1 | `flutter create` in `apps/mobile`; add `http` (or `dio`) dependency | Same API base via `--dart-define` or config file (gitignored). |
| M2 | **Locale state**: load `GET /api/v1/translations`; set `Accept-Language` on client | Matches web Wave 0 continued. |
| M3 | One **screen**: hardcode target document UUID/slug from seed OR call list and pick first | Fastest path: hardcoded id. |
| M4 | Parse JSON; show **AppBar** title + `ListView` of three dependency titles (localized) | Tap opens second route with placeholder body or same pattern as web. |
| M5 | Optional: second screen `DocumentDetailScreen(id)` reusing fetch | Second hour if M3–M4 finished early. |

**Checkpoint:** Android emulator or device shows the same graph as web for the MVP document.

---

## Wave 5 — Jurisdiction resolution (still small)

| Step | Outcome | Notes |
|------|---------|--------|
| R1 | Document in DB a **second** requirement only at `region` level for a spare doc; implement **single** resolution function: municipality → region → country | Align with [03-graph-resolution-and-views](directions/data-model-migrations/03-graph-resolution-and-views.md). |
| R2 | `GET /documents/{id}?municipality_id=` merges inherited edges without duplicates | **Tests:** unit test resolver only (fast). |

---

## Wave 6 — Supabase Auth + protected writes (prep for social)

**Status: Done.** Shipped as twelve chapters, well beyond this wave's original three-step sketch — roles
(`user`/`moderator`/`admin`), hashed machine API keys, and a web login/account UI were not part of A1–A3 but
were needed for the suggestion/voting/crawler suites that depend on auth. See
[`.plans/auth/`](../../.plans/auth/00-architecture.md) and
[directions/backend-api/03-auth-and-roles.md](directions/backend-api/03-auth-and-roles.md) for the shipped
design, and [docs/operations/auth-setup.md](../operations/auth-setup.md) for the setup runbook.

| Step | Outcome | Notes | Status |
|------|---------|--------|--------|
| A1 | Enable email provider in Supabase; document **JWT** validation steps for Litestar | Use JWKS URL from Supabase. | Done — [chapters 1–3](../../.plans/auth/chapters/) |
| A2 | Middleware/guard: optional auth; `GET` stays public | Matches public knowledge + future accounts. | Done — [chapters 4–6, 8](../../.plans/auth/chapters/), expressed as dependencies/guards rather than middleware (D5) |
| A3 | Web: Supabase JS client; login form; store session; attach `Authorization` on mutating routes (later) | Hour may be tight—split A3a login UI / A3b session storage. | Done — [chapters 9–11](../../.plans/auth/chapters/) |

---

## Wave 7+ — Toward full product (each item stays ≤ ~1h if scoped tightly)

Repeat pattern: **migration → seed/fixture → endpoint → one UI surface → test**.

Examples of **single-hour** slices:

- **(After i18n wave)** Add or adjust `ui_translation` rows + cache headers for `GET /api/v1/translations`.
- Add `proposal` + `proposal_vote` tables (no storage yet); `POST` proposal behind auth (title + URL only).
- Supabase **Storage** bucket + signed upload URL endpoint for one screenshot.
- **Audit log** table + decorator logging votes only.
- **Tree endpoint** `GET /documents/{id}/tree?max_depth=` BFS in Python (cap depth 10).
- Web: **React Flow** (or similar) minimal tree for same JSON.
- Flutter: **local-only** “saved document ids” with `shared_preferences` (no vault files yet).
- Flutter: **local notification** scheduled from one hardcoded reminder row.
- Crawler: **one** GitHub Action workflow that `curl`s a stored URL and writes `last_checked_at` (no parsing).

---

## Suggested Cursor session order (next 5 sessions)

1. **0a–0b + I1–I5** (repo + i18n schema + translation API + locale rules on the API).
2. **B1–B6 + B7–B9** (tooling + health + DB connection + unified jurisdiction + localized document/requirement schema + seed).
3. **B10–B13** (read API returns localized fields + CORS + OpenAPI).
4. **I6–I7 + W1–W6** (web locale wiring + list + detail).
5. **M1–M4** (Flutter list/detail with locale + `Accept-Language`).

---

## Related planning files

- Stack and hosting: [01-stack-and-free-tier.md](01-stack-and-free-tier.md) — update mentally: **Supabase = Postgres + Auth + Storage** hub; API host remains separate.
- Data model detail: [directions/data-model-migrations/](directions/data-model-migrations/).
- **Localization:** [directions/i18n-localization/README.md](directions/i18n-localization/README.md) — DB-only MVP (`de`/`en`); same wave order as **Wave 0 (continued)** above.
- API strand: [directions/backend-api/](directions/backend-api/).
