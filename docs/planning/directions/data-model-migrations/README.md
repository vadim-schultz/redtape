# Strand: Data model and migrations

## Scope

- PostgreSQL schema for **jurisdictions** (country → region → municipality, extensible), **documents**, **requirements** (directed edges), **sources** and provenance.
- **Fallback resolution** at read time: explicit precedence (e.g. municipality → Bundesland → country) with optional caching or materialized helpers.
- **Graph representation:** adjacency list in relational tables for MVP; optional later optimizations (closure, paths).
- **i18n:** localized names/descriptions (columns or JSONB per locale).
- **Alembic** (or chosen tool) migration strategy and seed data for dev.

## Dependencies on other strands

- **social-moderation:** proposal and vote tables reference documents and users; audit log schema.
- **crawlers-jobs:** crawl targets, fetch logs, object storage keys for screenshots.
- **backend-api:** exposes what the schema supports; avoid orphan entities.

## Child plans

| File | Topic |
|------|--------|
| [01-jurisdiction-hierarchy.md](01-jurisdiction-hierarchy.md) | Countries, regions, municipalities, codes, ordering. |
| [02-documents-and-requirements.md](02-documents-and-requirements.md) | Document entities, directed requirements, scope attachment. |
| [03-graph-resolution-and-views.md](03-graph-resolution-and-views.md) | Query patterns, tree expansion, performance notes. |

## Links

- Master: [../../00-master-summary.md](../../00-master-summary.md)
- Stack: [../../01-stack-and-free-tier.md](../../01-stack-and-free-tier.md)
