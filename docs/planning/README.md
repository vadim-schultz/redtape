# Redtape planning documents

This directory holds the **hierarchical product and implementation plans** for Redtape: a bureaucracy dependency graph (Germany-first, extensible), a social proposal and voting layer, and a mobile personal-document vault with reminders.

## Reading order

1. [00-master-summary.md](00-master-summary.md) — vision, pillars, scope boundaries, glossary.
2. [01-stack-and-free-tier.md](01-stack-and-free-tier.md) — technology choices and hosting/storage options (free tier first).
3. [02-incremental-mvp-roadmap.md](02-incremental-mvp-roadmap.md) — smallest MVP (1 city, 1 document, 3 deps), hour-sized backend → web → mobile steps, Supabase consolidation, **and early DB-backed i18n** (de + en).
4. [directions/](directions/) — one folder per development strand; each contains a `README.md` overview and links to deeper chapters. See [directions/README.md](directions/README.md) for a strand index (includes [i18n-localization](directions/i18n-localization/README.md)).

## Directory layout

```text
docs/planning/
  README.md                 ← you are here
  00-master-summary.md
  01-stack-and-free-tier.md
  02-incremental-mvp-roadmap.md
  discussion.txt            ← informal design notes (cross-check with numbered docs)
  directions/
    backend-api/
    data-model-migrations/
    i18n-localization/
    web-frontend/
    mobile-flutter/
    crawlers-jobs/
    social-moderation/
    security-privacy-gdpr/
    devops-ci-cd/
```

## Conventions

- **Strand overview:** each `directions/<strand>/README.md` summarizes scope, dependencies on other strands, and a table of child plan files.
- **Chapters:** prefer numbered files under a strand (e.g. `01-…md`, `02-…md`) or a `phases/` subfolder for ordered implementation.
- **Cross-links:** link to sibling strands when an interface or contract is shared (API shapes, object storage keys, mobile sync boundaries).

## Next steps

Pick a strand and expand its child plans into implementation-ready chapters (schema DDL, endpoint list, screen list, job contracts). The [data-model-migrations](directions/data-model-migrations/) strand includes an initial drill-down example.
