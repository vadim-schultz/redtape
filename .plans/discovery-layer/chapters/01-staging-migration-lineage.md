---
name: "Chapter 1 — Staging migration + lineage"
overview: "Alembic migration for staging tables, enums, and discovery_event lineage; SQLAlchemy models with no API yet."
todos:
  - id: enums
    content: "Postgres enums discovery_source, task status/kind, claim_kind, event_type"
    status: pending
  - id: models
    content: "Six staging models + discovery_event"
    status: pending
  - id: migration
    content: "Reversible Alembic revision"
    status: pending
isProject: false
---

# Chapter 1 — Staging migration + lineage

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/discovery-layer-staging-migration` · **Status:** planned

**Depends on:** none · **Contract:** [../02-staging-model-and-api.md](../02-staging-model-and-api.md) §2–3 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-layer` · **Release branch:** `main`

---

## Goal

Postgres can store the full staging graph and append-only lineage events. `alembic upgrade head` and
`downgrade -1` both work. No HTTP routes in this chapter.

## Design decisions

**Table names** match vocabulary in [00-architecture.md](../00-architecture.md) §2. Native Postgres enums
(not string columns) for status/source fields.

**`discovery_event`** is append-only; no update/delete from application code.

**Models** live under `app/models/discovery/` and export from `app.models` like other domains.

**`pipeline_stage`** on `catalogue_service` is a two-char string `T0`–`T4` with a CHECK constraint.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/models/discovery/*.py` | Models for six tables + event |
| `apps/api/app/models/__init__.py` | Export discovery models |
| `apps/api/alembic/versions/*_discovery_staging.py` | Migration |
| `apps/api/tests/test_discovery_models.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `CatalogueService · unique source + external_id rejects duplicate` | IntegrityError on second insert |
| `DiscoveryTask · defaults to pending status` | Happy path construction |
| `DiscoveryEntity · cascade delete when catalogue service removed` | Child rows gone |
| `DiscoveryEvent · records event_type and optional FKs` | Persist + load |
| `pipeline_stage CHECK · rejects T9` | Invalid stage rejected |

## Green

1. Enums + `CatalogueService`, `DiscoveryTask` models; tests 2 and 1.
2. Remaining models + relationships; tests 3–4.
3. Migration up/down; run round-trip manually; test 5 via model or migration integration.

## Refactor gate

One module per table under `models/discovery/`; shared mixins only for `created_at`/`updated_at`. Report outcome.

## Verification

```bash
cd apps/api
python -m pytest tests/test_discovery_models.py
alembic upgrade head && alembic downgrade -1 && alembic upgrade head
cd ../.. && ./ci.sh
```

## Out of scope

Discovery settings, routers, services, web admin.

## Git workflow

```bash
git checkout feat/plans-discovery-layer && git pull
git checkout -b feat/discovery-layer-staging-migration
```

```text
test(api): describe discovery staging models

feat(api): add discovery staging schema migration
```

Open PR into `feat/plans-discovery-layer`.
