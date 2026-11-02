---
name: "Chapter I5 — API and ingest contract"
overview: "Detect drift between the hand-mirrored ingest wire models and the API's Pydantic models with a checked-in contract fixture exported from the API and compared by ingest tests (field names, optionality, bounds, enum value sets, routes, recorded request bodies)."
todos:
  - id: exporter
    content: "API script that exports the machine contract fixture, plus an API test that the checked-in fixture is current"
    status: pending
  - id: comparator
    content: "Directional comparator in ingest tests with its own tests proving it can fail"
    status: pending
  - id: contract-tests
    content: "Pair table of 40 model pairs, enum sets, routes and recorded request bodies"
    status: pending
  - id: fix-drift
    content: "Close the one real drift found (RunFinishRequest bounds) and wire the CI path filter"
    status: pending
isProject: false
---

# Chapter I5 — API and ingest contract

**Repo:** `redtape` · **Branch:** `refactor/api-ingest-contract` · **Status:** planned

**Depends on:** I1 · **Architecture:** [../00-audit-report.md](../00-audit-report.md) D7 · **Rollout:** [../01-rollout.md](../01-rollout.md) · **Decision:** D1 in [../gaps-and-decisions.md](../gaps-and-decisions.md)

**Loop branch:** `feat/plans-codebase-audit` · **Release branch:** `main`

**Touches:** `ingest` model tests, read-only against `api/schema/discovery/machine.py` (rollout table). This chapter also adds one API script, one API test and one JSON fixture, edits `discovery-ingest-ci.yml` path filters, and makes one three-line fix in `schemas.py`; see "Files".

**Findings:** D7.

> **Operator approval (2026-11-02):** the API script, API test and checked-in fixture this chapter adds outside the ingest app are approved.

## Goal

A new value, field or bound on one side of the ingest-to-API wire cannot go unnoticed on the other. Today `apps/discovery-ingest/discovery_ingest/{schemas,artifacts,mentions,edges,emit_models,budget_models,candidate_sources}.py` hand-copy `apps/api/app/schema/discovery/{machine,artifacts,budgets,candidate_edges,candidate_emit,candidate_sources,candidates,emit,read}.py`, and the Literals (`DiscoveryTaskKind`, `StopReason`, `DiscoverySource`, ...) copy the API's `StrEnum`s in `app/models/discovery/enums.py`. A value added on the API is rejected by ingest's `model_validate` only at run time (callers catch `ValidationError`, so it looks like an outage, not a bug).

## Decision D1 for this chapter

D1 offered a shared package, generated clients, or contract tests; the recommendation (contract tests now, generate clients on the third drift bug) stands. Within contract tests there are two ways to reach the API side. I recommend the second.

| Option | Verdict |
| --- | --- |
| Import the API package in the ingest tests and compare the classes | Not possible. The API package is named `app`, its machine schemas import `app.models.discovery` (SQLAlchemy ORM) and `app.schema.suggestion`, and the API needs litestar, sqlalchemy, psycopg, boto3 (`apps/api/pyproject.toml`). The ingest CI job (`.github/workflows/discovery-ingest-ci.yml`) runs `pip install -e ".[dev]"` of `apps/discovery-ingest` only (httpx, pydantic, pydantic-settings, selectolax). Making API importable there would turn a light job into the API install and couple two packages' environments. |
| Compare against the API's OpenAPI document checked in as a fixture | Workable but lossy. Verified by generating it (`create_app().openapi_schema.to_schema()`, no database needed): Litestar renders `dict[str, str]` fields wrongly (`title_i18n` becomes an array of `oneOf` strings with `minLength`), qualifies clashing component names (`discovery_read_CandidateListResponse`), and drops the validation/serialization distinction. |
| **Recommended: a checked-in contract fixture exported from the API's Pydantic models, compared by ingest tests** | Exact (`model_json_schema(mode=...)` of the real classes), small, deterministic, and it follows a precedent that already exists: `apps/api/tests/fixtures/steckbrief_key_cases.json` is read by `apps/discovery-ingest/tests/test_fim_keys.py:14` and by `apps/api/tests/test_discovery_fanout.py:40`, and `discovery-ingest-ci.yml` lists it in its `paths:` filters. The route list in the same fixture comes from the OpenAPI document, where Litestar is accurate (methods and paths). |

The OpenAPI document stays the right input for the web half of D1 (chapter W3); this chapter's exporter is machine-routes only and does not block W3.

## Verified baseline

A scratch comparison (read-only, not committed) of the 40 pairs below, with the directional rules defined in this chapter, gives:

- 39 pairs match exactly.
- **Real drift 1:** `RunFinishRequest` — the API bounds `claimed_count`, `completed_count`, `failed_count`, `skipped_count`, `remaining_count` with `ge=0` and `error_detail` with `max_length=1000`; the ingest model has none (`worker/run.py:_MAX_ERROR_DETAIL` truncates by hand). Fix in ingest (3 lines in `schemas.py`).
- **Structural gap 2:** `BudgetRead.resource` is a plain `str` in the API (`app/schema/discovery/budgets.py`), while the API enum `BudgetResource` (`app/features/discovery/budget_resources.py`) and ingest's `BudgetResource` Literal (`budget_models.py:10`) are enums. The row model cannot be compared field to field, so the enum is compared through the fixture's `enums` section.
- Subset reads are intended and pass: `RunStartResponse` reads only `id` of `RunRead`; ingest `ArtifactRead` omits `storage_key` and `created_at`; `CandidatePage`/`CandidateSummary` read part of `CandidateListResponse`/`CandidateListItemRead`.

## Design

### The fixture

`apps/api/tests/fixtures/discovery_machine_contract.json`, produced by `python -m scripts.export_machine_contract` (new file `apps/api/scripts/export_machine_contract.py`, run from `apps/api`):

```json
{
  "generated_by": "python -m scripts.export_machine_contract",
  "routes":  [{"method": "POST", "path": "/api/v1/discovery/machine/claims"}],
  "models":  {"machine.ClaimAppendRequest": {"schema": {"...": "model_json_schema(mode='validation')"}, "mode": "validation"}},
  "enums":   {"DiscoveryTaskKind": ["fetch_url", "..."], "BudgetResource": ["r2_class_a", "..."]},
  "forms":   {"ArtifactUploadForm": ["file", "kind", "source_url", "final_url", "fetched_at"]}
}
```

- `routes`: every method and path under `/api/v1/discovery/machine` from the generated OpenAPI document (29 today).
- `models`: only the API classes named in the pair table; request models in `validation` mode, response models in `serialization` mode (so a defaulted response field counts as always present). Keys are `<module>.<Class>` (for example `read.CandidateListResponse`), which avoids the Litestar component-name clashes.
- `enums`: value lists of `DiscoverySource`, `DiscoveryTaskKind`, `DiscoveryTaskStatus`, `DiscoveryClaimKind`, `DiscoveryMentionRole`, `DiscoveryArtifactKind`, `DiscoveryEdgeBasis`, `DiscoveryRunKind` (`app/models/discovery/enums.py`), `BudgetResource` (`app/features/discovery/budget_resources.py`), `LEGACY_TASK_KINDS` as a list, and the two Literals `StopReason` (`machine.py`) and `EdgeSkipReason` (`candidate_edges.py`), read with `get_args`.
- `forms`: field names of the `ArtifactUploadForm` dataclass (`artifacts.py`), because a dataclass holding `UploadFile` has no Pydantic schema.
- Output is `json.dumps(..., indent=1, sort_keys=True)` plus a trailing newline so diffs are readable and stable.

**Freshness (API side):** `apps/api/tests/test_machine_contract_fixture.py::test_the_checked_in_fixture_is_current` regenerates the document in memory and compares it to the file; the failure message prints the regeneration command. This is the guard that turns an API schema change into a visible fixture diff in the same PR. It needs no database.

**Visibility (ingest side):** `.github/workflows/discovery-ingest-ci.yml` gets `apps/api/tests/fixtures/discovery_machine_contract.json` in both `paths:` lists (push and pull_request), exactly like `steckbrief_key_cases.json`, so a fixture change runs the ingest tests.

### The comparator

`apps/discovery-ingest/tests/contract_compare.py`: a pure function `compare(ingest: JsonObject, api: JsonObject, direction: Direction, enums: Mapping[str, list[str]]) -> list[str]` returning human-readable problems (empty means compatible). It reads only `properties`, `required`, `anyOf` nullability, `$defs`/`$ref` enums, and the scalar bounds `maxLength minLength maxItems minItems minimum maximum`. No `jsonschema` dependency is added.

Rules, per direction (these are the rules the baseline run used):

| Direction | Meaning | Rules |
| --- | --- | --- |
| `request` | ingest sends, API validates (13 pairs) | every ingest field exists in the API model (an unknown field is silently ignored by the API, which is drift); every API-required field exists in the ingest model; an API-required field is required or has a non-null default in ingest; ingest enum values are a subset of the API's; ingest bounds are at least as strict as the API's (`max*` not larger, `min*` not smaller) |
| `response` | API sends, ingest validates (27 pairs) | every ingest field exists in the API model; an ingest-required field is required in the API's serialization schema; a nullable API field is nullable in ingest; the API's enum values are a subset of ingest's (ingest must accept every value the API can send) |

Subsets are legal in the response direction (ingest reads fewer fields); the extra API fields are listed in the pair table as `reads: subset`, not hidden.

### Pair table (40 pairs; ingest model, API model, direction)

| Ingest (module.Class) | API (module.Class, `app/schema/discovery/` unless noted) | Direction |
| --- | --- | --- |
| `schemas.CatalogueBatchItem` | `machine.CatalogueBatchItem` | request |
| `schemas.CatalogueBatchRequest` | `machine.CatalogueBatchRequest` | request |
| `schemas.CatalogueMachineRead` | `machine.CatalogueMachineRead` | response |
| `schemas.EntityUpsertRequest` / `EntityUpsertResponse` | `machine.EntityUpsertRequest` / `EntityUpsertResponse` | request / response |
| `schemas.ClaimAppendRequest` / `ClaimAppendResponse` | `machine.ClaimAppendRequest` / `ClaimAppendResponse` | request / response |
| `schemas.TaskClaimRequest` / `TaskClaimResponse` | `machine.TaskClaimRequest` / `TaskClaimResponse` | request / response |
| `schemas.ClaimedTask` | `machine.ClaimedTaskRead` | response |
| `schemas.TaskSummary` | `machine.TaskSummaryResponse` | response |
| `schemas.TaskEnqueueRequest` / `TaskEnqueueResponse` | `machine.TaskEnqueueRequest` / `TaskEnqueueResponse` | request / response |
| `schemas.FetchLogAppendRequest` | `machine.FetchLogAppendRequest` | request |
| `schemas.RunStartResponse` | `machine.RunRead` | response, `reads: subset` (id only) |
| `schemas.RunFinishRequest` | `machine.RunFinishRequest` | request (**drift 1**) |
| `artifacts.ArtifactRead` | `artifacts.ArtifactRead` | response, `reads: subset` (no `storage_key`, `created_at`) |
| `artifacts.ArtifactPage` | `artifacts.ArtifactListResponse` | response |
| `artifacts.ArtifactStatus` | `artifacts.ArtifactStatusResponse` | response |
| `mentions.MentionItem` | `candidates.CandidateMentionItem` | request |
| `mentions.MentionsRequest` / `MentionsResponse` | `candidates.CandidateMentionsRequest` / `CandidateMentionsResponse` | request / response |
| `edges.EdgeItem` | `candidate_edges.CandidateEdgeItem` | request |
| `edges.EdgesRequest` / `EdgesResponse` | `candidate_edges.CandidateEdgesRequest` / `CandidateEdgesResponse` | request / response |
| `edges.EdgeSkip` | `candidate_edges.EdgeSkip` | response |
| `emit_models.EmitRequest` | `candidate_emit.CandidateEmitRequest` | request |
| `emit_models.EmitResponse` | `candidate_emit.CandidateEmitResponse` | response |
| `emit_models.EmitItem` | `candidate_emit.CandidateEmitItemResult` | response |
| `emit_models.EmitConflict` | `candidate_emit.EmitConflictRead` | response |
| `emit_models.EmitPreview` | `candidate_emit.CandidateEmitPreview` | response (`suggestion` is a free dict in ingest; typed `SuggestionCreate` in the API, not compared deeper) |
| `emit_models.CandidatePage` | `read.CandidateListResponse` | response, `reads: subset` (no `offset`, `limit`) |
| `emit_models.CandidateSummary` | `read.CandidateListItemRead` | response, `reads: subset` |
| `budget_models.BudgetRow` | `budgets.BudgetRead` | response; `resource` compared with `enums["BudgetResource"]` (**structural gap 2**) |
| `budget_models.BudgetSnapshot` | `budgets.BudgetListResponse` | response |
| `budget_models.BudgetReservation` | `budgets.BudgetReserveResponse` | response |
| `candidate_sources.CandidateSourceRead` / `CandidateSourcePage` | `candidate_sources.CandidateSourceRead` / `CandidateSourceListResponse` | response |
| `extract.llm.taxonomy.Taxonomy` / `TaxonomyTerm` | `app/schema/taxonomy/read.py` `VocabularyResponse` / `VocabularyTerm` (key `taxonomy_read.*`) | response |

Not paired, with the reason: `schemas.DrainReport` (a CLI report, never on the wire), `mentions.MentionDraft` (base of `MentionItem`, covered through it), `artifacts.ArtifactUpload`/`StoredArtifact`/`ArtifactContent` (client-side dataclasses).

### Enum value sets

Equality (both directions) between the fixture's `enums` and ingest's `get_args(...)`:

| Ingest | API |
| --- | --- |
| `DiscoverySource` | `DiscoverySource` |
| `DiscoveryTaskKind` (also `TASK_KINDS`) | `DiscoveryTaskKind` |
| `DiscoveryTaskStatus` | `DiscoveryTaskStatus` |
| `DiscoveryClaimKind` | `DiscoveryClaimKind` |
| `MentionRole` | `DiscoveryMentionRole` |
| `ArtifactKind` | `DiscoveryArtifactKind` |
| `EdgeBasis` | `DiscoveryEdgeBasis` |
| `StopReason` | `machine.StopReason` |
| `EdgeSkipReason` | `candidate_edges.EdgeSkipReason` |
| `BUDGET_RESOURCES` | `BudgetResource` |
| the literal `"worker_drain"` sent by `runs.start` | `DiscoveryRunKind` |
| `LEGACY_TASK_KINDS` | `LEGACY_TASK_KINDS` (`app/models/discovery/enums.py`, exported as a list) |

### Routes and recorded request bodies

Several request bodies have no ingest model (raw dicts built in the client): `complete` (`{"note"}`), `release` (`{"reason", "not_before"}`), `fail` (`{"error", "retryable"}`), run start (`{"kind"}`), budget reserve (`{"amount"}`) and adjust (`{"delta"}`). The contract therefore also checks what ingest actually sends:

- `test_every_client_route_exists_in_the_api`: every `(method, path template)` of I1's route table (`tests/test_machine_routes.py`) is in `routes`.
- `test_recorded_request_bodies_satisfy_the_api_request_schema`: the MockTransport recordings of that route table are validated against the paired API request model (an explicit `ROUTE_BODY` dict maps `(method, path)` to the API model key; 16 routes carry a JSON body). The mini-validator checks keys against `properties`, `required` against keys, and enum membership of scalar values. A separate small test checks the multipart upload field names against `forms["ArtifactUploadForm"]`.

## Files

Create:

- `apps/api/scripts/export_machine_contract.py` (exporter; verified `scripts/` is a package in `apps/api/pyproject.toml` `include = ["app*", "scripts*"]`).
- `apps/api/tests/fixtures/discovery_machine_contract.json` (generated).
- `apps/api/tests/test_machine_contract_fixture.py`.
- `apps/discovery-ingest/tests/contract_compare.py`, `tests/test_contract_compare.py`, `tests/test_api_contract.py`.

Edit:

- `.github/workflows/discovery-ingest-ci.yml`: add the fixture to both `paths:` lists (a CI file, edited in the implementation PR, not by this plan).
- `apps/discovery-ingest/discovery_ingest/schemas.py`: `RunFinishRequest` gets `ge=0` on the five counts and `max_length=1000` on `error_detail` (drift 1). `worker/run.py:_MAX_ERROR_DETAIL` should import the same constant; do that only if I3 has not already moved it.

Read-only inputs: `apps/discovery-ingest/discovery_ingest/{schemas,artifacts,mentions,edges,emit_models,budget_models,candidate_sources}.py`, `extract/llm/taxonomy.py`, and the API modules named in the pair table.

## TDD loop

### Red

1. **Comparator proves it can fail first** (`tests/test_contract_compare.py`, pure, no fixture): `test_a_new_api_enum_value_fails_a_response_pair`, `test_a_new_ingest_enum_value_fails_a_request_pair`, `test_an_api_required_field_missing_in_ingest_fails_a_request_pair`, `test_an_ingest_field_unknown_to_the_api_fails`, `test_a_looser_ingest_bound_fails_a_request_pair`, `test_a_nullable_api_field_must_be_nullable_in_ingest`, `test_an_ingest_required_field_the_api_may_omit_fails_a_response_pair`, plus the happy path `test_identical_schemas_and_a_subset_read_pass`. They fail because `contract_compare` does not exist.
2. **API freshness test** (`apps/api/tests/test_machine_contract_fixture.py`): `test_the_checked_in_fixture_is_current` (fails: no fixture), `test_every_route_in_the_fixture_is_under_the_machine_prefix`, `test_every_paired_model_is_exported` (negative: asks for an unknown key and expects `KeyError`).
3. **Ingest contract tests** (`tests/test_api_contract.py`): `test_model_pair_is_compatible[<ingest> <-> <api>]` (40 parametrised cases), `test_enum_sets_are_equal[<name>]` (12), `test_every_client_route_exists_in_the_api`, `test_recorded_request_bodies_satisfy_the_api_request_schema[<route>]`, `test_artifact_upload_form_fields_match`, `test_every_wire_model_in_ingest_is_paired_or_listed_as_unpaired` (negative guard: walks the ingest model modules and fails on a new `BaseModel` that is in neither list, so a new DTO cannot skip the contract). Most fail because the fixture is missing; once it exists, `test_model_pair_is_compatible[schemas.RunFinishRequest <-> machine.RunFinishRequest]` fails on the real drift 1, which is the intended red.

### Green

1. Write `scripts/export_machine_contract.py`; run it; commit the fixture. The API freshness tests pass.
2. Write `contract_compare.py` until its tests pass, then wire `test_api_contract.py` to the fixture.
3. Fix drift 1 in `schemas.py`; the whole contract suite is green.
4. Add the CI path filter.
5. Run each test once against a deliberately broken copy (add a value to a Literal in a scratch edit, or drop a field from a fixture copy) and confirm it turns red; record the observed failure message in the PR (this is the "red" evidence for the guard itself).

### Refactor

Judge by responsibility, not line count: the exporter only reads API classes and writes JSON; the comparator only compares two schema dicts; the test module only wires fixture, pairs and recordings. Look for: the pair table written twice (once in the ingest test, once in the exporter's model list: derive the exporter's list from one constant in the exporter and let the ingest test assert its pair keys are a subset of `models`), the direction rules duplicated for enums and fields (one helper), and an `ALLOWED_GAPS` dict growing silently (must stay empty; each entry needs a reason and a ticket line, and the PR reports its size). No `Any`: loaded JSON is typed with `JsonObject` from I2 (`discovery_ingest/json_types.py`) and narrowed with `isinstance`. Every new public function in `scripts/` and `contract_compare.py` has an imperative docstring (pydocstyle `D`, `pep257`; tests are exempt from `D` but the helper module is documented anyway). Report `Refactor gate: smells found -> ..., refactorings applied -> ...` with: pairs checked (40), enum sets checked (12), real drifts found (1) and fixed, unpaired ingest models listed.

## Verification

```bash
cd apps/api
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
uv run pytest tests/test_machine_contract_fixture.py
python -m scripts.export_machine_contract && git diff --exit-code tests/fixtures/discovery_machine_contract.json
cd ../discovery-ingest
uv run ruff format --check . && uv run ruff check . && uv run mypy discovery_ingest
uv run pytest tests/test_contract_compare.py tests/test_api_contract.py tests/test_machine_routes.py tests/test_worker_run.py
cd ../..
./ci.sh
```

The ingest CI job must pass with its current `pip install -e ".[dev]"` (no API import, no new dependency).

## Parallel notes

Batch 3 siblings: I3 (ingest operations; no model edits), B5 (admin controllers), B7 (optional migration). I5 starts after I1 and after the batch-2 API chapters (B3 touches `api/schema/discovery`).

- **B3** may move `from_row` classmethods out of `schema/discovery/read.py` and reshape imports; fields should not change. If B3 or a later chapter changes a wire field, the fixture freshness test fails in that PR and the author regenerates it; do not pre-empt B3's work here.
- **A2** (single emit pipeline) may turn `skip_reason: str | None` of `EmitOutcome` into a Literal; the contract test is then the place where ingest's `EmitItem.skip_reason` is updated to match.
- **I3** edits `worker/`, `operations/`, `config.py` only; no overlap, except the optional `_MAX_ERROR_DETAIL` constant move noted above.
- **W3** owns the web half of D1 (OpenAPI-derived checks for `apps/web`); do not add web files here.
- **Must not be touched:** the API schema modules themselves (no API contract change is in scope: the one drift is fixed on the ingest side), `apps/web/**`, other `.github/**` files, lock files, and the ingest client facade (I1).
