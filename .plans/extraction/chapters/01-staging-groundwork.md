---
name: "Chapter E1 — Staging groundwork"
overview: "The API-side places for what extraction produces: the llm_extract task kind, the issued role, mention conditions and tag columns, a candidate edge table with a machine route, the taxonomy vocabulary route, and the aggregated tag suggestions used by candidate detail and emit."
todos:
  - id: migration
    content: "Enum labels, mention columns, discovery_candidate_edge, migration heads"
    status: pending
  - id: mentions
    content: "Mention items accept condition, is_optional and codes; unknown codes are dropped and counted"
    status: pending
  - id: edges
    content: "POST /machine/candidates/edges and the admin edge read"
    status: pending
  - id: taxonomy
    content: "GET /machine/taxonomy"
    status: pending
  - id: tags
    content: "Pure tag aggregate, used by candidate detail and by the emit tag hook"
    status: pending
isProject: false
---

# Chapter E1 — Staging groundwork

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/extraction-staging` · **Status:** planned

**Depends on:** crawlers [06](../../crawlers/chapters/06-candidate-staging-model-and-api.md) (merged), [11](../../crawlers/chapters/11-candidate-emit.md), [23](../../crawlers/chapters/23-free-tier-guards.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/extraction`

## Goal

Give the extraction output somewhere to land without touching the worker: one migration, one batch route for edges, one vocabulary route, and one pure function that turns many mentions into a tag suggestion for a candidate. Everything is additive (invariant 3).

## Contract

**Migration** (one file; update the hard-coded heads in `tests/test_discovery_staging_migration_retry.py` and `tests/test_check_migrations_script.py`; round trip through `scripts/check_migrations.sh`):

- `ALTER TYPE discovery_task_kind ADD VALUE IF NOT EXISTS 'llm_extract'` and the same for the native enum behind `DiscoveryMentionRole` with `'issued'`, each in `op.get_context().autocommit_block()`. The downgrade leaves the labels (enum labels cannot be removed), as in crawlers chapter 3.
- `discovery_candidate_mention` gains nullable `condition Text`, `is_optional Boolean`, `domain_codes ARRAY(String(64))`, `situation_codes ARRAY(String(64))`.
- New table `discovery_candidate_edge` (enum `DiscoveryEdgeBasis` = `explicit|derived_single_issued`): `id`, `parent_candidate_id` and `required_candidate_id` (FK cascade), `catalogue_service_id` (FK cascade), `condition Text NULL`, `is_optional Boolean NULL`, `excerpt Text`, `basis`, `extractor String(64)`, `extractor_version String(32)`, `created_at`. Unique `(parent_candidate_id, required_candidate_id, catalogue_service_id)`; check `parent_candidate_id <> required_candidate_id`.

**Kind safety.** `llm_extract` is **not** in `LEGACY_TASK_KINDS`; the default claim ignores it (crawlers chapter 3). The worker's `DiscoveryTaskKind` literal is extended in chapter E6.

**Mention batch route** (crawlers chapter 6 route, extended): items gain optional `condition` (at most 300 characters), `is_optional`, `domain_codes` (at most 2) and `situation_codes` (at most 3). Codes are checked against the `domain` and `life_situation` tables: unknown codes are **dropped and counted** in the response (`unknown_codes`), never a batch failure, so a taxonomy change cannot strand a run. Existing items without the new fields behave as before. LLM mentions use a fixed `source_field = "llm"`, so a re-run updates the mention in place (decision X13).

**Edge route.** `POST /api/v1/discovery/machine/candidates/edges` with `{items: [...]}` (at most 100). Each item: `catalogue_service_id`, `parent_title_i18n`, `required_title_i18n`, `basis`, `condition?`, `is_optional?`, `excerpt`, `extractor`, `extractor_version`. Endpoints are resolved by `candidate_key` within the catalogue row's jurisdiction and must **already exist** (the worker posts mentions first). An unresolvable endpoint, equal endpoints or a blank excerpt are reported per item (`skipped` with a reason), not as a 4xx; an existing edge is updated in place. Response: counts of edges created, updated and skipped. The route is guarded by `require_db_headroom` (crawlers chapter 23).

**Taxonomy route.** `GET /api/v1/discovery/machine/taxonomy` returns `{domains: [{code, name_i18n, description_i18n}], situations: [...]}` ordered by `sort_order`, from the existing taxonomy service. Machine key required. The worker injects it into the prompt and hashes it for `extractor_version`.

**Tag aggregate.** A pure function `aggregate_tags(mentions, min_procedures=2, min_share=0.5)` in `apps/api/app/features/discovery/tags.py`. For each code it counts **distinct** `catalogue_service_id` values over mentions that carry that code, and divides by the number of distinct procedures that carry any code; it returns `[{code, procedures, share, accepted}]`, `accepted` meaning both thresholds are met. The thresholds are settings with these defaults.

- `GET /admin/candidates/{id}` (crawlers chapter 6) adds `suggested_domain_codes` and `suggested_situation_codes` (the aggregate), and mentions show `condition`, `is_optional` and their codes.
- `GET /admin/candidates/{id}/edges` lists edges with the other end's title and the procedure.
- The emit `suggested_tags(candidate)` hook of crawlers chapter 11 now returns the accepted codes, so `NewDocumentPayload.domain_codes` and `situation_codes` are filled when consensus exists and left empty otherwise.

## TDD loops

### Loop A — Migration and models

**Red** (`test_discovery_models.py`, `test_discovery_staging_migration_retry.py`)

1. `llm_extract and issued labels exist, and the default claim does not return llm_extract tasks`.
2. `edge unique per parent, required and procedure; equal endpoints rejected; deleting a candidate cascades its edges`.
3. `migration round trip passes and the head constants are updated`.

**Green:** models, migration, exports. **Refactor:** share timestamp mixins; enums exported in `__init__.py`.

### Loop B — Mentions

**Red** (`test_discovery_candidates_api.py`)

1. `mention items accept condition, is_optional and codes and store them`.
2. `unknown codes are dropped and counted, valid codes kept` — negative and happy pair.
3. `a re-posted llm mention updates in place instead of adding a row`.
4. `items without the new fields behave exactly as before`.
5. `more than 2 domain codes or 3 situation codes is a 422`.

**Green:** schema fields and a code filter in `CandidateService`. **Refactor:** one vocabulary lookup per batch, not per item.

### Loop C — Edges

**Red** (`test_discovery_candidate_edges_api.py`)

1. `edge batch creates edges between existing candidates and reports counts`.
2. `an edge with an unknown endpoint is skipped with a reason and does not fail the batch`.
3. `an equal-endpoint edge is skipped; a replay updates in place`.
4. `edge batch requires the machine key and is refused with 507 database_soft_limit above the limit`.
5. `admin edges lists parent, required, procedure and basis`.

**Green:** `EdgeRepository` mixed into `DiscoveryRepository`, service method, controller. **Refactor:** reuse `candidate_key` and the batch-size dependency from chapter 6.

### Loop D — Taxonomy and tags

**Red** (`test_discovery_taxonomy_route.py`, `test_discovery_tags.py`, `test_discovery_candidate_emit.py`)

1. `taxonomy route returns the vocabulary in sort order and requires the machine key`.
2. `aggregate counts distinct procedures, not mentions, and accepts a code at 2 procedures and 50 percent`.
3. `aggregate does not accept a code seen on one procedure or below the share` — negative.
4. `candidate detail shows suggested codes; emit payload carries accepted codes and none when there is no consensus`.

**Green:** pure function plus wiring. **Refactor:** the function takes plain tuples, no ORM objects.

## Verification

```bash
cd apps/api && python -m pytest tests/test_discovery_models.py tests/test_discovery_candidates_api.py tests/test_discovery_candidate_edges_api.py tests/test_discovery_taxonomy_route.py tests/test_discovery_tags.py tests/test_discovery_candidate_emit.py
cd apps/api && alembic upgrade head && alembic downgrade -1 && alembic upgrade head
gh pr checks --watch
```

Live gate: none that exercises extraction. After deploy, `GET /machine/taxonomy` returns 13 domains and 18 situations, and `GET /admin/candidates/<id>` shows empty suggested codes. Record the counts.

## Out of scope

Edge emit, `new_requirement` suggestions, per-document tag columns, editing staged items, any worker code.
