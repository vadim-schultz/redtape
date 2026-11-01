---
name: "Chapter 2 — Life situation groups"
overview: "Add a new LifeSituationGroup tier above the 18 existing situation codes — a pure partition into 8 groups — so default browsing never shows more than ~8 choices. Presentation-only: no situation code's meaning, mentions, or consensus data changes."
todos:
  - id: group-model
    content: "Add LifeSituationGroup (TaxonomyTermMixin) and LifeSituation.group_id FK"
    status: pending
  - id: migration
    content: "Migration: create life_situation_group table, add nullable group_id to life_situation"
    status: pending
  - id: seed-data
    content: "Add the 8 groups and a situation-code -> group-code map to seed_data/taxonomy.py"
    status: pending
  - id: seed-script
    content: "Extend seed_taxonomy.py to upsert groups, then set each LifeSituation.group_id"
    status: pending
  - id: repository-service
    content: "Extend TermModel, add TaxonomyRepository/TaxonomyService support for groups and a situation's group_code"
    status: pending
  - id: controller-schema
    content: "Add GET /life-situation-groups; add group_code to the life-situations read model"
    status: pending
  - id: tests
    content: "Seed-integrity test (every situation has exactly one group), repository/service/controller tests"
isProject: false
---

# Chapter 2 — Life situation groups

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/situation-tag-hierarchy-life-situation-groups` · **Status:** planned

**Depends on:** none · **Decisions:** D3 (`../gaps-and-decisions.md`) — the 8-group split this chapter seeds · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-situation-tag-hierarchy`

## Goal

Add one new tier above the existing 18 `life_situation` codes so a default browse/filter view never has to show more than ~8 choices. Pure addition: no `LifeSituation` row, mention, consensus computation, or document tag is touched. The 8 groups and their membership (`../00-architecture.md §4`):

| Group | Situation codes |
| --- | --- |
| `family-relationships` | `marriage`, `separation-divorce`, `birth-of-child`, `death-of-relative` |
| `home-housing` | `moving-house`, `renting-home`, `buying-property` |
| `work-career` | `new-job`, `job-loss`, `going-self-employed` |
| `education` | `studying`, `starting-school` |
| `vehicles-travel` | `buying-vehicle`, `getting-licence` |
| `residence-migration` | `immigration`, `naturalisation` |
| `health-care` | `illness-care` |
| `retirement` | `retirement` |

## Design

**Model.** `apps/api/app/models/taxonomy.py`: add `LifeSituationGroup(TaxonomyTermMixin, Base)` — the same shape `Domain`/`LifeSituation` already share (`code`, `name_i18n`, `description_i18n`, `icon`, `sort_order`), own table `life_situation_group`, same `UniqueConstraint`/`CheckConstraint` pattern on `code`. Add `LifeSituation.group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("life_situation_group.id"))`. Kept nullable at the schema level rather than `NOT NULL` — the taxonomy's content (which group each situation belongs to) is filled by the seed script after migration, the same deploy-order convention `name_i18n`/`description_i18n` already follow; a seed-integrity test, not a DB constraint, is what actually guarantees every situation has exactly one group (see Tests).

**Migration.** New Alembic migration: create `life_situation_group` (mirroring `domain`/`life_situation`'s existing shape), add `group_id` (nullable FK) to `life_situation`. No data in this migration — seeding is a separate, idempotent step, as today.

**Seed data.** `apps/api/scripts/seed_data/taxonomy.py`: add `SITUATION_GROUPS = _terms([...])` (the 8 rows above, same `(code, name_de, name_en, desc_de, desc_en, icon)` tuple shape `DOMAINS`/`SITUATIONS` already use) and `SITUATION_GROUP_CODES: dict[str, str]` mapping each of the 18 situation codes to its group's code (the table above, as a flat dict — simplest addition that doesn't require restructuring the existing `Term`/`_terms()` shape `SITUATIONS` already uses).

**Seed script.** `apps/api/scripts/seed_taxonomy.py`: upsert `SITUATION_GROUPS` into `LifeSituationGroup` (same `session.merge()` pattern as the existing domain/situation upsert) before upserting `SITUATIONS`; when upserting each `LifeSituation`, resolve `group_id` via `SITUATION_GROUP_CODES[code]` → `term_id(group_code)` (the existing deterministic `uuid5` helper, reused as-is — group and situation codes never collide as strings, so one shared namespace is safe).

**Repository/service.** `apps/api/app/features/taxonomy/repository.py`: widen `TermModel` to `type[Domain] | type[LifeSituation] | type[LifeSituationGroup]` so the existing generic `list_terms()` covers groups for free. `apps/api/app/features/taxonomy/service.py`: add `list_situation_groups(*, locale, enabled_locales) -> list[TermRead]` (one more call to the existing `_list()` helper, same as `list_domains`/`list_situations`). Add a situation-specific read path carrying the group: `list_situations_with_group(*, locale, enabled_locales) -> list[LifeSituationGroupedRead]`, backed by a new `TaxonomyRepository.list_situations_with_group()` joining `LifeSituation.group_id == LifeSituationGroup.id` and returning each situation alongside its group's `code`.

**Schema.** `apps/api/app/schema/taxonomy/read.py`: add `LifeSituationGroupedRead(TermRead)` with `group_code: str`.

**Controller.** `apps/api/app/features/taxonomy/controller.py`: add `GET /life-situation-groups` (mirrors `list_domains`/`list_life_situations`); change `GET /life-situations` to return `list[LifeSituationGroupedRead]` via the new `list_situations_with_group()` — the one breaking shape change in this chapter, needed so the frontend (chapter 4) can group situations client-side without a second round-trip per situation.

## Tests

- Seed-integrity test: after seeding, every one of the 18 `LifeSituation` rows has a non-null `group_id`, every `LifeSituationGroup` has at least one situation, and the partition exactly matches the table above (catches a future situation code added without a group assignment).
- `TaxonomyRepository.list_terms(LifeSituationGroup)` returns all 8 in `sort_order`.
- `list_situations_with_group()` returns the right `group_code` per situation.
- Controller test: `GET /life-situation-groups` returns 8 rows; `GET /life-situations` rows each carry a `group_code` that resolves to a real group.

## Verification

```bash
cd apps/api && ./ci.sh
pytest tests/test_taxonomy_repository.py tests/test_taxonomy_service.py tests/test_taxonomy_controller.py -v
```

## Refactor gate

Confirm `grep -rn "TermModel" apps/api/app` shows `LifeSituationGroup` included everywhere `Domain | LifeSituation` is matched today (the admin/document-filter call sites should need no change — they never touch groups).

## Commits

- `feat(api): add the life_situation_group taxonomy tier and seed the 8 starting groups`
- `feat(api): expose groups and a situation's group_code through the taxonomy API`

## Out of scope

Any reclassification of the 18 situation codes themselves; any UI (chapter 4); anything about PVOG or confidence scoring (chapters 3 and 1 respectively); enforcing `group_id` as `NOT NULL` at the DB layer (left to a future chapter if the seed-integrity test's guarantee ever turns out not to be enough).
