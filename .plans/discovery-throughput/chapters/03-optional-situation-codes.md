---
name: "Chapter 3 — Optional situation codes"
overview: "Stop discarding an entire LLM page extraction because situation_codes alone was omitted or empty."
todos:
  - id: schema
    content: "Give situation_codes a default_factory=list in PageExtraction"
    status: pending
  - id: tests
    content: "Add the omitted-key and json-schema-required tests"
    status: pending
isProject: false
---

# Chapter 3 — Optional situation codes

**Repo:** `redtape` (`apps/discovery-ingest`) · **Branch:** `feat/discovery-throughput-optional-situation-codes` · **Status:** planned

**Depends on:** none · **Decisions:** D4 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-throughput`

## Goal

Stop discarding an entire LLM page extraction — documents, dependencies, and the domain code included — merely because the model omitted `situation_codes`. Every downstream consumer already tolerates an empty or missing situation classification; only the schema's requiredness causes the rejection.

## Design

- `apps/discovery-ingest/discovery_ingest/extract/llm/schema.py:71` —
  ```python
  situation_codes: list[Code] = Field(max_length=MAX_SITUATION_CODES)
  ```
  becomes
  ```python
  situation_codes: list[Code] = Field(default_factory=list, max_length=MAX_SITUATION_CODES)
  ```
- No change to line 70 (`domain_codes`), per D4 — scope is exactly the user's literal ask.
- No change to `build_json_schema` (lines 83-88): Pydantic's `model_json_schema()` already excludes a field with a default from the generated `required` array, so `_restrict_codes` keeps working unmodified; this chapter adds a test asserting that behavior rather than changing the function.
- No downstream code changes needed — already confirmed tolerant of empty/absent situation codes: `apps/discovery-ingest/discovery_ingest/extract/llm/ground.py:24-31` (`_codes`), `mapping.py:34-48`, `apps/api/app/schema/discovery/candidates.py:35` and `mentions.py:40` (both already `list[Code] | None = Field(default=None)`), `apps/api/app/schema/discovery/read.py:302,325` (`mention.situation_codes or []`).

## Tests

Extend `apps/discovery-ingest/tests/test_extraction_schema.py`:

- `test_situation_codes_omitted_from_the_payload_still_parses` — build a payload from the existing base fixture with the `situation_codes` key deleted entirely, assert `PageExtraction.model_validate(payload).situation_codes == []`. Fails today with a Pydantic "field required" error.
- `test_the_json_schema_no_longer_requires_situation_codes` — `schema = build_json_schema(taxonomy())`; assert `"situation_codes" not in schema["required"]` and `"domain_codes" in schema["required"]` (pins the D4 scope boundary in the same test).

Red: both tests fail against the unchanged schema. Green: the one-line `default_factory=list` change makes both pass.

Also check `apps/discovery-ingest/tests/test_llm_eval_gold_set.py` (or equivalent gold-set fixture file) for any case that assumes `situation_codes` is always present; if the eval harness would otherwise regress, add one gold-set case with it empty.

## Verification

```bash
cd apps/discovery-ingest && ./ci.sh
python -c "
from discovery_ingest.extract.llm.schema import PageExtraction
print(PageExtraction.model_validate({'page_kind':'service','domain_codes':['housing'],'documents':[],'dependencies':[]}).situation_codes)
"
# expect: []
```

No live gate needed — this is a pure parsing/schema change, provable with unit tests. A later real `llm_extract` drain (outside this suite) should show fewer `Invalid` outcomes, but that is an observation, not a verification step this chapter blocks on.

## Refactor gate

None needed — a single field-default change.

## Commits

- `fix(discovery-ingest): accept a missing or empty situation_codes in LLM extraction output`

## Out of scope

`domain_codes` leniency (flagged as an open seam, not done here); re-running or re-scoring historical `llm_extract` failures caused by this bug (operational cleanup, not a chapter).
