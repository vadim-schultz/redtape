# Stack and free-tier hosting

This document aligns **your stated preferences** with **free-tier–friendly** managed services and calls out **fallbacks** when “always free” is insufficient for production-like load or crawler workloads.

## Application stack (as agreed)

| Layer | Choice |
|-------|--------|
| API | [Litestar](https://litestar.dev/) (ASGI), Pydantic for IO models, SQLAlchemy ORM |
| Database | PostgreSQL |
| Web app | Vite + React + TypeScript + Chakra UI |
| Mobile | Flutter (iOS + Android) |

**Localization:** domain and UI strings are stored in **Postgres** (JSONB + `ui_translation`); the API serves localized payloads and translation bundles. See [directions/i18n-localization/README.md](directions/i18n-localization/README.md).

## Hosting and data services (free tier first)

Prices and limits change; treat the links as authoritative.

### API (Litestar + Uvicorn/Hypercorn, etc.)

| Option | Free-tier notes | Caveat |
|--------|-----------------|--------|
| [Fly.io](https://fly.io/docs/about/pricing/) | Allowances for small VMs | Crawlers/long jobs should not block the web process; use a separate process or machine. |
| [Render](https://render.com/docs/free) | Free web services exist | Instances **sleep** when idle; cold starts. |
| [Railway](https://railway.app/pricing) | Trial / limited credits | Good for prototypes; watch billing after trial. |

**Alternative (paid):** single small VPS (Hetzner, DigitalOcean, etc.) for API + worker if you want predictable uptime without sleep.

### PostgreSQL

| Option | Free-tier notes |
|--------|-----------------|
| [Neon](https://neon.tech/docs/introduction/free-tier) | Serverless Postgres, branching useful for dev/staging |
| [Supabase](https://supabase.com/pricing) | Postgres + optional Auth/Storage if you consolidate |
| [ElephantSQL](https://www.elephantsql.com/plans.html) | Tiny free instances (legacy-style) |

**Consolidation tip:** one [Supabase](https://supabase.com/) project can cover **Postgres + authentication + object storage** (screenshots later) on the free tier; the Litestar API still runs elsewhere. See [02-incremental-mvp-roadmap.md](02-incremental-mvp-roadmap.md) for a phased build order.

**Alternative:** managed Postgres on the same cloud as the API (often paid after trial).

### Static web (Vite SPA)

| Option | Free-tier notes |
|--------|-----------------|
| [Cloudflare Pages](https://developers.cloudflare.com/pages/platform/pricing/) | Generous static hosting |
| [Netlify](https://www.netlify.com/pricing/) | Free tier for personal/small projects |
| [Vercel](https://vercel.com/pricing) | Hobby tier for frontend |

Configure **CORS** and environment-specific **API base URLs** for a separate API origin.

### Object storage (screenshots, crawler artifacts)

| Option | Free-tier notes | Caveat |
|--------|-----------------|--------|
| [Cloudflare R2](https://developers.cloudflare.com/r2/pricing/) | No egress to Workers; free tier caps | Read current caps; large crawl volume may exceed free. |
| Supabase Storage | Bundled with Supabase project | Same quota limits as project tier. |

**Alternative when free is insufficient:** smallest paid object storage bucket on R2, S3-compatible provider, or Supabase paid tier.

### Cache / job queue (optional for MVP)

| Option | Role |
|--------|------|
| [Upstash](https://upstash.com/pricing) Redis | Rate limiting, short-lived locks, optional queue |
| **Postgres-only MVP** | Job table + `FOR UPDATE SKIP LOCKED` + cron triggers | Zero extra vendors; good for low throughput. |

### Push notifications (reminders)

| Option | Notes |
|--------|------|
| [Firebase Cloud Messaging](https://firebase.google.com/pricing) | Common with Flutter; generous free tier for typical usage |
| **Local notifications only** | No server; strongest privacy for reminder text; no cross-device sync of reminder state. |

### Crawlers and scheduled jobs

| Option | Notes |
|--------|------|
| [GitHub Actions](https://docs.github.com/en/billing/managing-billing-for-github-actions/about-billing-for-github-actions) | `schedule` workflows for batch crawl | Minute/month limits; not “always on.” |
| Worker on Fly / same VPS as API | Separate entrypoint (e.g. CLI invoked by cron) | May need paid tier for 24/7 scheduling depending on provider. |

**Reality check:** continuous discovery crawling is the hardest to run entirely on free tiers; a **hybrid** (scheduled batches + manual triggers + queue depth limits) is realistic.

## Ranked fallbacks (when free tier does not fit)

1. **Object storage:** smallest paid R2 or S3-compatible bucket.
2. **Always-on worker:** one small VM or a paid Render/Railway background worker.
3. **Database:** Neon/Supabase paid when connections or storage exceed free.

## Monorepo direction (implementation)

Default: **monorepo** with `apps/api`, `apps/web`, optional `apps/mobile`, and `packages/contracts` (e.g. OpenAPI generated from Pydantic). Details: [directions/devops-ci-cd/README.md](directions/devops-ci-cd/README.md).
