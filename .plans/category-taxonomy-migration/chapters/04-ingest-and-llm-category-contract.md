---
name: "Chapter 4 — Ingest and LLM category contract"
overview: "Move PVOG, LLM, manual curation, and discovery mention evidence from two taxonomy axes to canonical category codes without losing source or confidence."
id: C4
depends_on:
  - C1
  - C3
touches:
  - apps/api/app/models/discovery/
  - apps/api/app/features/discovery/
  - apps/api/app/schema/discovery/
  - apps/api/app/schema/suggestion/
  - apps/discovery-ingest/discovery_ingest/mentions.py
  - apps/discovery-ingest/discovery_ingest/pvog/
  - apps/discovery-ingest/discovery_ingest/extract/llm/
  - apps/discovery-ingest/discovery_ingest/curation.py
  - apps/discovery-ingest/tests/
  - apps/api/tests/
execution: chapter-implementer
todos:
  - id: mention-contract
    content: "Add canonical category codes to mention, candidate, suggestion, and curation contracts with compatibility handling."
    status: pending
  - id: pvog-harvest
    content: "Carry PVOG source path/leaf provenance and map source evidence to canonical categories."
    status: pending
  - id: llm-contract
    content: "Replace LLM dual-axis enums and grounding with the category vocabulary."
    status: pending
  - id: tests
    content: "Update mapping, schema, fixture, evaluation, unknown-code, and confidence parity tests."
    status: pending
---

# Chapter 4 — Ingest and LLM category contract

**Repo:** `redtape` (`apps/api`, `apps/discovery-ingest`)
**Depends on:** [Chapter 1](01-pvog-taxonomy-contract.md) and [Chapter 3](03-category-api-and-backend-filters.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

## Goal

Change all new discovery evidence to speak one category vocabulary. PVOG and LLM evidence must still retain their origin, quote, extractor version, direct confidence, and external identifiers. During the compatibility window, old payloads may be read and translated, but new writers must not create an untraceable domain/situation-only assertion.

## Design decisions

- `category_codes` is the canonical list on mention and extraction payloads.
- `domain_codes` and `situation_codes` are compatibility input fields only while old workers drain; they are not emitted by the new LLM schema or PVOG mapper.
- The machine taxonomy endpoint supplies the category enum and its digest. Workers do not hardcode category labels.
- PVOG leaf/root/parent data is carried as source metadata. It is mapped to product categories by the frozen artifact, not by numeric-prefix guesses in the harvest function.
- The LLM may propose only active category codes. Grounding validates and scores those codes; it never turns a raw source label into a product category without a mapping.
- Existing continuous confidence/noisy-OR behavior remains. There is no category-level accept/reject gate added to compensate for the taxonomy merge.
- Re-ingest is forward-compatible and idempotent. Existing mentions retain their historical extractor/source version and are backfilled only under an explicit operator command.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/models/discovery/discovery_candidate_mention.py` | Add/replace category code storage and preserve PVOG/source/confidence fields during transition. |
| `apps/api/app/schema/discovery/candidates.py` | Validate category mention payloads and define compatibility/deprecation behavior. |
| `apps/api/app/features/discovery/candidate_codes.py` | Validate/filter category codes and count unknown inputs. |
| `apps/api/app/features/discovery/candidate_emit_payload.py` | Build category suggestions and confidence payloads. |
| `apps/api/app/schema/suggestion/payload.py` | Replace dual-axis suggestion fields with category fields while keeping a bounded compatibility reader if required. |
| `apps/api/app/features/discovery/tags.py` | Apply the existing score model to category evidence without axis-specific thresholds. |
| `apps/api/app/features/discovery/repository/candidate_tag_scores.py` | Key score aggregation by category code and preserve parity with the Python scorer. |
| `apps/discovery-ingest/discovery_ingest/mentions.py` | Add canonical category fields to mention DTOs and preserve source metadata. |
| `apps/discovery-ingest/discovery_ingest/pvog/models.py` | Retain PVOG path/label/version information where present. |
| `apps/discovery-ingest/discovery_ingest/pvog/client.py` | Pass source path/context through the row mapping without changing crawl budget/dedupe semantics accidentally. |
| `apps/discovery-ingest/discovery_ingest/pvog/situation_mapping.py` | Replace old situation mapping output with category mapping from the chapter 1 artifact. |
| `apps/discovery-ingest/discovery_ingest/pvog/domain_mapping.py` | Remove old domain output after all entries have a category disposition. |
| `apps/discovery-ingest/discovery_ingest/harvest/pvog.py` | Draft category codes, direct confidence, and PVOG external classification together. |
| `apps/discovery-ingest/discovery_ingest/extract/llm/schema.py` | Replace `domain_codes`/`situation_codes` schema fields and enums with bounded `category_codes`. |
| `apps/discovery-ingest/discovery_ingest/extract/llm/taxonomy.py` | Read the category machine vocabulary and calculate a category digest. |
| `apps/discovery-ingest/discovery_ingest/extract/llm/mapping.py` | Map grounded category output into mention payloads. |
| `apps/discovery-ingest/discovery_ingest/extract/llm/ground.py` | Ground category assertions against the active vocabulary and evidence. |
| `apps/discovery-ingest/discovery_ingest/curation.py` | Validate manual category codes and compatibility files. |
| `apps/discovery-ingest/tests/test_pvog_harvest.py` | Test category/source mapping, leaf retention, and missing PVOG path. |
| `apps/discovery-ingest/tests/test_pvog_situation_mapping.py` | Replace axis mapping assertions with crosswalk assertions. |
| `apps/discovery-ingest/tests/test_extraction_schema.py` | Test category enum schema, bounds, and forbidden legacy output. |
| `apps/discovery-ingest/tests/test_extraction_mapping.py` | Test category evidence mapping and source preservation. |
| `apps/discovery-ingest/tests/test_llm_eval_*.py` | Update category metrics and gold fixtures without changing evaluation meaning. |
| `apps/api/tests/test_candidate_completeness_tags.py` | Verify internal score/completeness behavior is not accidentally changed by public field removal. |
| `apps/api/tests/test_discovery_candidate_emit_payload.py` | Test category suggestion payloads and confidence. |

## Red tests

### Happy path

- `mention · accepts canonical category codes and preserves PVOG source facts` asserts category codes, leaf code, source path, quote, and direct confidence survive the API boundary.
- `pvog harvest · maps a known parent/leaf through the frozen crosswalk` asserts the expected category evidence without exposing the leaf as a product category.
- `llm schema · offers only active category codes` asserts the generated JSON schema contains canonical category enums and the expected maximum.
- `grounding · emits category evidence with the existing confidence curve` asserts Python and SQL/category scoring remain aligned.

### Negative path

- `mention · rejects unknown category codes` asserts invalid categories are rejected or counted through the documented compatibility path.
- `pvog harvest · missing path retains leaf provenance but emits no invented category` asserts source loss is not converted into false certainty.
- `llm schema · rejects legacy domain/situation output` asserts new workers cannot silently repopulate the old axes.
- `manual curation · rejects a category from another taxonomy version` asserts stale or inactive codes are diagnosable.

Run API and ingest tests before implementation and confirm failures are contract failures.

## Green

1. Add canonical category fields and compatibility parsing to API and ingest DTOs.
2. Move PVOG harvest and mapping through the frozen crosswalk while preserving raw external data.
3. Change LLM taxonomy loading, generated schema, grounding, mapping, and evaluation fixtures.
4. Update candidate score aggregation and suggestion payloads to use category evidence.
5. Add a versioned re-ingest/backfill command for existing mentions; do not run it automatically in deploy migrations.

## Refactor gate

Audit the complete evidence pipeline:

- one category validation path is shared by API, LLM, PVOG, and curation boundaries;
- PVOG source capture, product mapping, and mention drafting are separate named units;
- no source mapper contains a domain/situation/category branch chain;
- score aggregation has one category-keyed implementation and one parity test;
- compatibility fields are translated at the boundary and do not leak into new DTOs;
- source provenance is not carried in a loosely typed catch-all payload;
- all changed public models have precise types and docstrings.

Report the refactor outcome and rerun the narrow suites after each extraction.

## Verification

```bash
cd apps/discovery-ingest
uv run pytest tests/test_pvog_harvest.py tests/test_pvog_situation_mapping.py \
  tests/test_extraction_schema.py tests/test_extraction_mapping.py \
  tests/test_llm_eval_document_level.py tests/test_llm_eval_metrics.py
uv run ruff format --check . && uv run ruff check . && uv run mypy discovery_ingest
./ci.sh

cd ../api
uv run pytest tests/test_discovery_candidate_emit_payload.py \
  tests/test_candidate_completeness_tags.py tests/test_discovery_candidates_api.py
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
```

Record schema digest, category coverage, unknown-code counts, score parity, and re-ingest behavior in [../run-ledger.md](../run-ledger.md).

## Out of scope

Product category naming, target database schema, public web UI, deleting old fields, embeddings, entity identification, and live PVOG crawling in CI.

## Git workflow

```bash
git checkout feat/plans-category-taxonomy-migration && git pull
git checkout -b feat/category-ingest-contract
```

```text
test(ingest): describe canonical category evidence contracts
feat(ingest): emit category-backed PVOG and LLM mentions
```
