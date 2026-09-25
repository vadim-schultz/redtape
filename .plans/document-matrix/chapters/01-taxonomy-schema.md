---
name: "Chapter 1 — Taxonomy schema"
overview: "Add domain, life_situation, document_domain and document_life_situation tables as SQLAlchemy models plus one reversible Alembic migration; no data, no API."
todos:
  - id: models
    content: "Domain and LifeSituation models; association tables; exported from app.models"
    status: completed
  - id: migration
    content: "Alembic revision creating four tables, unique codes, composite PKs, cascading FKs"
    status: completed
  - id: tests
    content: "Model tests: code uniqueness, cascade on document delete, association uniqueness"
    status: completed
isProject: false
---

# Chapter 1 — Taxonomy schema

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/matrix-taxonomy-schema` · **Status:** done

**Depends on:** none · **Architecture:** [../00-architecture.md](../00-architecture.md) §3 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

The database can store domains, life situations, and their many-to-many links to documents. Nothing
reads or seeds them yet. `alembic upgrade head` and `downgrade -1` both work.

## Design decisions

**`code`, not `slug`.** The column is a language-neutral identifier (English-derived, never translated,
never renamed), see [../gaps-and-decisions.md](../gaps-and-decisions.md) D8. A `CHECK` constraint enforces
lowercase ASCII kebab-case (`^[a-z][a-z0-9]*(-[a-z0-9]+)*$`) so a translated or accented code cannot enter.

**Two entity models, two association tables.** `Domain` and `LifeSituation` are structurally
identical; keep them as two classes (different tables, different future behavior) sharing a small
mixin for `code`, `name_i18n`, `description_i18n`, `icon`, `sort_order`. Alternative: one `taxonomy_term`
table with a `kind` column — rejected, it blurs the two axes the product names separately.

**Association tables as plain `Table` objects**, not mapped classes: they carry no attributes.
Relationships `Document.domains` and `Document.life_situations` are added with `secondary=`.

**No `document` column changes.** Only relationships are added on the Python side.

**Follow existing model style** in [document.py](../../../apps/api/app/models/document.py): `Uuid(as_uuid=True)`,
`JSONB` with `server_default`, `from __future__ import annotations`.

## Files

**Add**

| Path | Contents |
| --- | --- |
| `apps/api/app/models/taxonomy.py` | `TaxonomyTermMixin`, `Domain`, `LifeSituation`, `document_domain`, `document_life_situation` |
| `apps/api/alembic/versions/20260625_taxonomy.py` | Revision after `20260610_fix_dup_juris`; create/drop four tables |
| `apps/api/tests/test_taxonomy_models.py` | Behavior tests below |

**Edit**

| Path | Change |
| --- | --- |
| `apps/api/app/models/document.py` | `domains` and `life_situations` relationships via `secondary=` |
| `apps/api/app/models/__init__.py` | Export `Domain`, `LifeSituation` |

**Do not edit** — routers, services, seed scripts, existing migrations.

## Red tests

| Test | Asserts |
| --- | --- |
| `domain · persists with de and en names` | Round-trip JSONB name |
| `domain · duplicate code is rejected` | `IntegrityError` on second insert |
| `domain · non-kebab or accented code is rejected` | `IntegrityError` for `Umzüge`, `moving house`, empty string |
| `life_situation · duplicate code is rejected` | Same for the other axis |
| `document · tagging with a domain and a situation links both` | `document.domains` / `.life_situations` contain the rows |
| `document · tagging the same domain twice is rejected` | Composite PK violation |
| `document · deleting a document removes its links but keeps the domain` | Cascade on association rows only |
| `domain · deleting a domain still linked is allowed to cascade links` | No orphan association rows |

Tests use the session fixture from [conftest.py](../../../apps/api/tests/conftest.py).

## Green

1. Write the mixin and two models; run the code tests.
2. Add association tables and relationships; run the tagging and cascade tests.
3. Autogenerate the migration, then hand-edit to match constraint names; verify upgrade/downgrade.

## Refactor gate

- `taxonomy.py` must stay under ~100 LOC; if the mixin and tables grow, split association tables into
  `models/taxonomy_links.py`.
- Confirm the mixin removes duplication rather than adding indirection (rule: only if both models
  genuinely share all five columns).
- `document.py` gains two relationship lines only; no logic.

Report outcome per touched class.

## Verification

```bash
cd apps/api
python -m pytest tests/test_taxonomy_models.py
alembic upgrade head && alembic downgrade -1 && alembic upgrade head
cd ../.. && ./ci.sh
```

## Out of scope

Seed data (chapter 2), any endpoint (chapters 3–5), indexes beyond PKs and unique codes unless a test
demands one.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/matrix-taxonomy-schema
```

```text
test(api): describe taxonomy tables and tagging behavior

feat(api): add domain and life situation taxonomy tables
```

## Outcome

- `taxonomy.py` is 55 LOC. The mixin shares all its columns between both models, so it removes duplication.
  The association tables come from one `_link_table` helper in the same file.
- `document.py` gained two relationship lines and one import; no logic.
- Migration `20260625_taxonomy` upgrades, downgrades and re-upgrades cleanly on Postgres; `alembic check` reports no drift on the new tables.
- The CHECK constraint uses Postgres `~`. DB-backed tests skip under the SQLite `ci.sh` run, like the existing DB tests, so they were verified against a local Postgres.
