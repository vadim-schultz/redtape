---
name: "Chapter 6 — Candidate staging model and API"
overview: "Persist deduplicated document candidates and their mentions, with a promotion-aligned key, a batch machine route to record mentions, and read-only admin endpoints."
todos:
  - id: key
    content: "Pure candidate-key function equal to the promotion slug rule"
    status: pending
  - id: models
    content: "discovery_document_candidate and discovery_candidate_mention models and migration"
    status: pending
  - id: machine-route
    content: "POST /machine/candidates/mentions (batch, idempotent)"
    status: pending
  - id: admin-read
    content: "GET /admin/candidates and /admin/candidates/{id}"
    status: pending
isProject: false
---

# Chapter 6 — Candidate staging model and API

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/crawlers-candidate-staging` · **Status:** planned

**Depends on:** [03](03-kind-filtered-claim.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/crawlers`

## Goal

The dependency graph needs document nodes before edges. Existing claims are keyed per entity and emit one suggestion per claim, so the same document ("Personalausweis") mentioned by two hundred procedures would produce two hundred suggestions. Candidates deduplicate nodes; mentions keep provenance and the procedure-to-document `requires` relation.

## Contract

**Key.** `candidate_key(title_i18n)` returns `slugify(pick_title(title_i18n))` from [slugs.py](../../../apps/api/app/features/suggestions/slugs.py), the exact rule `NewDocumentHandler.promote` uses. A title with no usable characters is rejected (422 at the route, not a 500). The function is pure and has no database access.

**Tables** (models under `apps/api/app/models/discovery/`, exported from `__init__.py`; new enums `DiscoveryCandidateStatus` = `staged|emitted`, `DiscoveryMentionRole` = `required|form`):

- `discovery_document_candidate`: `id`, `jurisdiction_id` (FK, restrict), `key String(200)`, `title_i18n JSONB`, `official_url String(500) NULL`, `status`, `suggestion_id UUID NULL` (no FK to `suggestion`; the table is another feature's), `created_at`, `updated_at`. Unique `(jurisdiction_id, key)`.
- `discovery_candidate_mention`: `id`, `candidate_id` (FK, cascade), `catalogue_service_id` (FK, cascade), `role`, `excerpt Text`, `source_field String(200)`, `artifact_id UUID NULL` (FK added in chapter 14), `extractor String(64)`, `extractor_version String(32)`, `created_at`. Unique `(candidate_id, catalogue_service_id, role, source_field)`.

**Repository.** A new `CandidateRepository` mixed into `DiscoveryRepository` ([composite.py](../../../apps/api/app/features/discovery/repository/composite.py)). A `CandidateService` owns the upsert policy.

**Machine route.** `POST /api/v1/discovery/machine/candidates/mentions` with `{items: [...]}`, at most 100 items; each item has `catalogue_service_id`, `title_i18n`, `role`, `excerpt`, `source_field`, `extractor`, `extractor_version`, optional `official_url` and `artifact_id`. The candidate's jurisdiction is the catalogue row's. Behaviour per item:

- find or create the candidate by `(jurisdiction, key)`;
- merge `title_i18n` (add missing locales, never overwrite an existing value); set `official_url` only if the candidate has none;
- find or create the mention by its unique key; an existing mention is updated in place (excerpt, extractor version);
- an `emitted` candidate still accepts mentions but keeps its status.

Response: counts of candidates created, mentions created, mentions updated. The whole batch is one transaction; an unknown catalogue row is a 404 for the batch.

**Admin routes** (existing guards): `GET /api/v1/discovery/admin/candidates` with `status`, `offset`, `limit`, returning candidates with `mention_count`; `GET /api/v1/discovery/admin/candidates/{id}` returning the candidate and its mentions with the procedure's title, source and `portal_url`. DTOs in [read.py](../../../apps/api/app/schema/discovery/read.py).

Pipeline stages (T0 to T4) track claims and are **not** advanced by mentions. The pipeline detail shows candidate counts separately (chapter 8).

## TDD loops

### Loop A — Key

**Red** (`apps/api/tests/test_discovery_candidate_key.py`)

1. `candidate key matches the promotion slug for the same title` — table of German titles with umlauts, punctuation and mixed locales.
2. `candidate key rejects a title with no usable characters` — raises.
3. `candidate key is stable across whitespace and case` — two spellings, one key.

**Green:** delegate to `slugify` and `pick_title`; no second implementation.

**Refactor:** none expected; keep the module a few lines.

### Loop B — Model and migration

**Red** (`test_discovery_models.py` additions)

1. `candidate unique per jurisdiction and key` — duplicate insert raises.
2. `mention unique per candidate service role and field` — duplicate insert raises.
3. `deleting a catalogue row cascades its mentions` and `deleting a candidate cascades its mentions`.

**Green:** models and an additive migration; `scripts/check_migrations.sh` stays green (single head, round trip, no drift).

**Refactor:** share timestamp mixins with the other discovery models.

### Loop C — Machine route

**Red** (`apps/api/tests/test_discovery_candidates_api.py`)

1. `mentions batch creates a candidate and a mention` — counts in the response.
2. `mentions batch is idempotent` — replay creates nothing new.
3. `two services mentioning one title share one candidate` — one candidate, two mentions.
4. `title locales merge without overwriting` and `official_url is set once`.
5. `batch with an unknown catalogue row is rejected whole` — 404, nothing written.
6. `batch over 100 items or with a blank title is rejected` — 422.
7. `route requires the machine API key`.

**Green:** service method per concern (resolve candidate, merge fields, upsert mention).

**Refactor:** keep each service method about five lines; no nested loops in the controller.

### Loop D — Admin read

**Red**

1. `admin candidate list returns mention counts and filters by status`.
2. `admin candidate detail returns mentions with procedure titles`.
3. `admin candidate routes reject non-admins` and `unknown candidate is 404`.

**Green:** repository queries with a grouped count; DTOs.

**Refactor:** reuse the paging dependency used by the other admin lists.

## Verification

```bash
cd apps/api && python -m pytest tests/test_discovery_candidate_key.py tests/test_discovery_candidates_api.py tests/test_discovery_models.py
cd apps/api && alembic upgrade head && alembic downgrade -1 && alembic upgrade head
gh pr checks --watch
```

Live gate: none until chapter 7 produces mentions; the migration is applied on the next Render deploy and `GET /admin/candidates` returns an empty list. Record that observation.

## Out of scope

Producing mentions (chapters 7 and 18), emit (chapter 11), admin UI (chapters 10 and 20), resolving mentions to canonical documents.
