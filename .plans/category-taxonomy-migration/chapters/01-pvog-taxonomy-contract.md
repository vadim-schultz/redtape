---
name: "Chapter 1 — PVOG-grounded category contract"
overview: "Freeze the small product category tree, preserve PVOG hierarchy/provenance, and publish the crosswalk that every later migration chapter consumes."
id: C1
depends_on: []
touches:
  - apps/api/scripts/seed_data/
  - apps/discovery-ingest/discovery_ingest/pvog/
  - apps/discovery-ingest/tests/
  - .plans/category-taxonomy-migration/
execution: chapter-implementer
todos:
  - id: category-inventory
    content: "Freeze root/subcategory codes, localized labels, parent relations, ordering, and lifecycle rules."
    status: pending
  - id: pvog-source-path
    content: "Capture PVOG root/parent/leaf identifiers and source version without changing the product category boundary."
    status: pending
  - id: crosswalk
    content: "Publish old-axis and PVOG crosswalks with explicit mapped, unmapped, and review states."
    status: pending
  - id: tests
    content: "Add vocabulary integrity, PVOG path, crosswalk parity, and unknown-source tests."
    status: pending
---

# Chapter 1 — PVOG-grounded category contract

**Repo:** `redtape` (`apps/api`, `apps/discovery-ingest`)
**Depends on:** none · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Decisions:** [../gaps-and-decisions.md](../gaps-and-decisions.md)

## Goal

Create the authoritative category inventory and mapping artifact before any schema or API migration. The result defines a small curated root set, a small set of subcategories under each root, stable codes, localized copy, and the source evidence for each mapping.

The chapter must correct the current information loss: PVOG's `PersonalMatterNode` currently traverses leaf codes, while labels and parent paths are not retained as structured ingest data. The product taxonomy must remain smaller than the complete PVOG leaf vocabulary.

## Design decisions

- The product tree is curated from PVOG citizen parent categories, not a direct dump of all PVOG parents or leaves.
- The final inventory is a versioned data artifact consumed by API seeds, machine vocabulary, LLM enums, web fixtures, and the migration crosswalk.
- Product category codes are stable English-derived kebab-case identifiers. PVOG numeric codes remain external identifiers.
- Every old `domain` and `life_situation` code receives exactly one mapping state: mapped, intentionally unmapped, or manual-review. A many-to-many mapping is allowed only when the artifact records why and how scores combine.
- Business-branch PVOG leaves are preserved as source metadata but do not enter the citizen-facing product tree unless a later product decision explicitly expands scope.
- The ten currently unmapped citizen leaves remain unmapped or source-only until a category decision supplies evidence; this chapter must not force them into a convenient category.

## Files and artifacts

| Path | Change |
| --- | --- |
| `apps/api/scripts/seed_data/taxonomy.py` | Replace the dual-axis seed description with the frozen category inventory and source mapping data. |
| `apps/api/tests/test_seed_taxonomy.py` | Assert root/child uniqueness, complete parent assignment, localized copy, and crosswalk parity. |
| `apps/discovery-ingest/discovery_ingest/pvog/models.py` | Preserve parent/root path and labels when the v7 bootstrap supplies them; retain leaf-only crawl behavior. |
| `apps/discovery-ingest/discovery_ingest/pvog/client.py` | Thread the discovering PVOG path/version into the mapped record without changing pagination or dedupe policy accidentally. |
| `apps/discovery-ingest/discovery_ingest/pvog/situation_mapping.py` | Replace axis-specific output mappings with the versioned category crosswalk. |
| `apps/discovery-ingest/discovery_ingest/pvog/domain_mapping.py` | Retire the domain-specific mapping after its entries are represented in the crosswalk. |
| `apps/discovery-ingest/tests/test_pvog_situation_mapping.py` | Characterize every mapped, ambiguous, and unmapped source entry. |
| `apps/discovery-ingest/tests/test_pvog_domain_mapping.py` | Prove no domain-only mapping disappears without an explicit disposition. |
| `.plans/situation-tag-coverage/lr3-personal-matters-mapping.md` | Cite the live PVOG evidence; do not silently rewrite historical measurements. |
| `.plans/category-taxonomy-migration/` | Add the versioned inventory/crosswalk artifact or a precise reference to the seed source. |

## Red tests

### Happy path

- `taxonomy · every active subcategory has one active root` asserts the frozen inventory has no orphan, duplicate code, duplicate parent relation, or cycle.
- `pvog · bootstrap path preserves root, parent, leaf and source version` asserts a complete fixture becomes a source classification while the crawl still yields the same leaf codes.
- `crosswalk · every legacy domain and situation code has a disposition` asserts the migration artifact covers all old codes and maps approved entries to active categories.

### Negative path

- `taxonomy · duplicate or cyclic category inventory is rejected` asserts seed validation fails before any partial taxonomy is written.
- `pvog · missing parent metadata does not invent a product category` asserts a leaf-only payload retains its leaf/source fact and produces no unsupported category hint.
- `crosswalk · unknown target or duplicate conflicting mapping is rejected` asserts bad mappings fail loudly rather than dropping a document tag.

Run the narrow tests and confirm the failures are caused by the absent target vocabulary/path contract, not fixture mistakes.

## Green

1. Add the frozen category inventory, localized copy, parent relation, stable ordering, source mapping, and old-code crosswalk.
2. Extend PVOG parsing only enough to preserve source path/version alongside the existing leaf crawl behavior.
3. Replace axis-specific mapping output with category evidence while retaining confidence and raw PVOG identifiers.
4. Add validation at the seed/mapping boundary and make all fixtures use the same artifact.

## Refactor gate

Audit the entire category seed and PVOG mapping entities:

- category inventory is data, not a long conditional chain;
- one parser owns PVOG path normalization;
- source mapping, product category assignment, and evidence preservation are separate concerns;
- no boolean mode selects “domain” versus “situation” behavior;
- no mapping table duplicates the final crosswalk;
- all public symbols and changed modules have required docstrings/types;
- the source path is optional only where PVOG genuinely omits it, never as a shortcut.

Report `Refactor gate: smells found -> ...; refactorings applied -> ...` and rerun the narrow suite after each extraction.

## Verification

```bash
cd apps/api
uv run pytest tests/test_seed_taxonomy.py tests/test_taxonomy_models.py
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts

cd ../discovery-ingest
uv run pytest tests/test_pvog_situation_mapping.py tests/test_pvog_domain_mapping.py tests/test_pvog_harvest.py
uv run ruff format --check . && uv run ruff check . && uv run mypy discovery_ingest
```

Record the inventory version, old-code coverage, PVOG counts, and review exceptions in [../run-ledger.md](../run-ledger.md).

## Out of scope

Database schema changes, public API changes, frontend changes, all-118-leaf product exposure, business taxonomy design, embeddings, and entity identification.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/category-taxonomy-contract
```

```text
test(taxonomy): describe the frozen category and PVOG crosswalk
feat(taxonomy): add the PVOG-grounded category vocabulary
```
