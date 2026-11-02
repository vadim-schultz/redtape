---
name: "Chapter B5 — List query params"
overview: "Discovery list handlers take one query object built by a provide_*_query dependency, like documents and suggestions already do; the legacy parameters stay on the wire and live in one place."
todos:
  - id: characterize
    content: "Pin accepted legacy params, canonical precedence, 422 bodies and OpenAPI parameter names"
    status: pending
  - id: client-check
    content: "Run the legacy-parameter client check and record the result"
    status: pending
  - id: providers
    content: "provide_*_query dependencies for candidates, tasks, catalogue, candidate sources, machine candidates"
    status: pending
  - id: budget
    content: "Add the discovery handlers to the three-parameter budget test"
    status: pending
isProject: false
---

# Chapter B5 — List query params

**Repo:** `redtape` · **Branch:** `refactor/list-query-params` · **Status:** planned

**Depends on:** B3 (layering and guards) · **Architecture:** [../00-audit-report.md](../00-audit-report.md) (L10, L14 admin part) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-codebase-audit` · **Release branch:** `main`

**Touches:** `api/features/discovery/*_controller.py` (plus the new provider code in the existing `*_list_query.py` modules)

**Findings:** L10, L14 (admin part)

## Goal

No discovery list handler takes more than three parameters. Each builds its filter and page from one injected query object, the pattern of `features/documents/query.py` (`DocumentListQuery` + `provide_document_list_query`) and `features/suggestions/query.py`. Every parameter name, type, default, status code (422 for bad values in the discovery routers) and response body stays as it is today (decision D4: keep the legacy parameters). The legacy surface becomes one provider function per resource instead of loose handler arguments.

## Verified facts

Handlers over the three-parameter budget (`self` excluded), counted from the source:

| Handler | File:line | Params | Parameters |
| --- | --- | --- | --- |
| `list_candidates` | `candidate_admin_controller.py:31` | 8 | service, `page`, `list_query`, legacy `status`, `min_mentions`, `role`, `source`, `sort` |
| `list_tasks` | `admin_controller.py:34` | 6 | service, `page`, `list_query`, legacy `status`, `source`, `kind` |
| `list_catalogue` | `admin_controller.py:47` | 4 | service, `page`, `list_query`, legacy `source` |
| `select_candidate_sources` | `candidate_machine_controller.py:65` | 6 | service, `page`, `missing`, `host`, `candidate_id`, `service_ids` |
| `select_candidates` (machine) | `candidate_machine_controller.py:52` | 4 | service, `page`, `status`, `min_mentions` |
| `list_artifacts` (machine) | `artifact_machine_controller.py:70` | 4 | service, `page`, `kind`, `host` |

The audit counted three of these (`list_candidates` 8, `select_candidate_sources` 6, `list_tasks` 6). The other three are the same smell in the same files.

How the canonical and legacy parameters combine today: the controller builds a legacy filter object from the loose parameters, then `candidate_filter_from` / `task_filter_from` / `catalogue_filter_from` (`candidate_list_query.py:63`, `task_list_query.py:98`, `catalogue_list_query.py:127`) overlay the canonical `ListQuery` on top (`filter_or(name, Type, legacy.value)`; canonical wins). The legacy combined `sort` (`CandidateSort`, `LEGACY_SORTS` in `repository/candidate_sort.py:35-47`) is translated in the controller at `candidate_admin_controller.py:42`. Existing tests pin this: `tests/test_discovery_candidates_list_contract.py:250` (`test_legacy_parameters_still_work_and_canonical_ones_win`), `tests/test_discovery_admin_list_query.py:114` and `:186`, `tests/test_discovery_candidates_admin_api.py:310-318` (four bad legacy values all answer 422).

The machine `GET /candidates/` (`select_candidates`) takes `status` and `min_mentions` as its **only** parameters (no canonical form exists on that route) and `apps/discovery-ingest/discovery_ingest/api_client.py:151-156` calls it with `status=staged&min_mentions=N`. They are not legacy; they never go away.

## D4: client check (run before changing anything, record the output in the PR)

Purpose: decide whether the admin legacy parameters can ever be deleted. Default per D4: keep. Deleting them is a separate, optional commit that needs a clean check **and** the operator's yes.

```bash
# 1. Web admin: does any request still send a legacy name? (expect: only filter[...], sort_by, sort_order, q)
grep -rnE "(status|source|kind|role|min_mentions|sort)=" apps/web/src --include=*.ts --include=*.tsx | grep -v "\.test\." | grep -i "discovery"
sed -n 1,60p apps/web/src/services/listQuery/params.ts      # toListParams emits filter[<field>] and sort_by
# 2. Ingest: which admin routes does it call? (expect: none; it only uses /machine/*)
grep -rn "discovery/admin" apps/discovery-ingest/discovery_ingest
# 3. Operators and CI: docs and workflows that show a legacy call
grep -rnE "admin/(candidates|tasks|catalogue)\?[a-z_]*=" docs .github
grep -rn "discovery/admin" .github/workflows
# 4. Tests that would have to change if the params go away
grep -rnE 'params=\{[^}]*"(status|source|kind|role|min_mentions|sort)"' apps/api/tests/test_discovery_candidates_admin_api.py apps/api/tests/test_discovery_admin_api.py apps/api/tests/test_discovery_candidates_list_contract.py
```

Result at planning time (read-only greps on `0e713cc`): the web sends the canonical shape through `toListParams` (`discoveryAdminApi.ts:50,64,116`); the ingest client calls no admin route; `docs/operations/discovery-layer.md:336-338` documents the legacy names as "still accepted"; only API tests use them. The implementer must re-run the greps; a hit in step 1 or 2 means keep (and open a web or ingest ticket), no hit means the legacy parameters are *removable* but still not removed in this chapter unless the operator says so. Access logs are not available from the repo, so zero hits here proves nothing about operators using `curl`; that is why the default is keep.

## Design

Reuse the existing pattern, with one generic carrier instead of four near-identical classes (four uses, so the rule of three is met):

```python
@dataclass(frozen=True, slots=True)
class DiscoveryListQuery(Generic[FilterT]):
    """A repository filter plus the page to read, built once per request."""
    filters: FilterT
    page: Page
```

in a new `features/discovery/list_query.py`. Providers sit next to their specs, in the existing modules:

| Provider | Module | Replaces handler parameters | Notes |
| --- | --- | --- | --- |
| `provide_candidate_query(page, list_query, status, min_mentions, role, source, sort)` | `candidate_list_query.py` | the 8 of `list_candidates` | translates `sort` through `LEGACY_SORTS` and calls `candidate_filter_from`; `page` is converted to the repository `Page` once here |
| `provide_task_query(page, list_query, status, source, kind)` | `task_list_query.py` | the 6 of `list_tasks` | |
| `provide_catalogue_query(page, list_query, source)` | `catalogue_list_query.py` | the 4 of `list_catalogue` | |
| `provide_candidate_source_query(page, missing, host, candidate_id, service_ids)` | new `candidate_source_query.py` or beside `CandidateSourceFilter` usage | the 6 of `select_candidate_sources` | `missing == "screenshot"` and `service_ids or ()` move here |
| `provide_machine_candidate_query(page, status, min_mentions)` | `candidate_list_query.py` | the 4 of `select_candidates` | no `list_query` |
| `provide_artifact_query(page, kind, host)` | beside `ArtifactFilter` | the 4 of `list_artifacts` | |

Each controller registers its providers in `dependencies` next to the existing `provide_list_query(...)` entry (controller-level for candidates, handler-level for the two admin handlers, as today). The handlers become `(self, service, query: DiscoveryListQuery[...])` and call `service.list_x(query.filters, query.page)`. The `Parameter(...)` objects move verbatim, so bounds (`ge=0`, `min_length`, `max_items=20`) and enum validation are identical.

Risk to check first (spike in the Red phase): Litestar's handling of a **generic** dataclass as a dependency return annotation. If the signature model rejects `DiscoveryListQuery[CandidateFilter]`, fall back to marking it `Annotated[..., Dependency(skip_validation=True)]` as `suggestions/submission.py:31` does, and only if that fails to one frozen dataclass per resource. Record which was used.

Also keep the admin routers' behaviour that `ValidationException` answers 422 (`discovery/router.py:_invalid_payload_is_422`): validation failures raised while resolving a dependency's parameters must still reach it. The characterisation tests below prove it.

## Files

- `apps/api/app/features/discovery/candidate_admin_controller.py`, `admin_controller.py`, `candidate_machine_controller.py`, `artifact_machine_controller.py`: handlers and `dependencies`.
- `apps/api/app/features/discovery/candidate_list_query.py`, `task_list_query.py`, `catalogue_list_query.py`: providers (and the removal of the "legacy" filter object construction from the controllers).
- New `apps/api/app/features/discovery/list_query.py` (the carrier) and, if separate, the sources and artifacts providers.
- `apps/api/tests/test_shared_paging_locale.py`: extend `BUDGETED_HANDLERS` with `DiscoveryAdminController.list_tasks`, `list_catalogue`, `DiscoveryCandidateAdminController.list_candidates`, `DiscoveryCandidateMachineController.select_candidates`, `select_candidate_sources`, `DiscoveryArtifactMachineController.list_artifacts` (the controllers are importable; the test asserts at most three parameters).
- Not touched: `repository/*` filter classes, `app/shared/list_query/*`, services, response schemas.

## TDD loop

### Red

Characterise on the unchanged code first (all green, committed before any refactor):

1. OpenAPI pin: `test_discovery_list_endpoints_expose_the_same_query_parameter_names` builds `create_app().openapi_schema`, collects the sorted query parameter names of `GET /api/v1/discovery/admin/{candidates,tasks,catalogue}`, `GET /api/v1/discovery/machine/candidates`, `/machine/candidates/sources`, `/machine/artifacts`, and compares to a literal. Run once on `main` to write the literal. This is what proves the legacy parameters survive the move.
2. Behaviour pins that do not exist yet: `test_task_list_accepts_each_legacy_filter_alone`, `test_candidate_list_accepts_legacy_role_and_source_alone`, `test_candidate_list_legacy_sort_values_map_to_key_and_direction` (`mentions_desc`, `title_asc`, `newest`; extends `test_discovery_candidates_admin_api.py:300`), `test_candidate_sources_list_filters_by_host_missing_and_ids`, `test_artifact_list_filters_by_kind_and_host`.
3. Negative pins: `test_task_list_rejects_unknown_legacy_status_with_422_and_lists_the_parameter`, `test_candidate_sources_rejects_missing_value_other_than_screenshot`, `test_candidate_sources_rejects_more_than_twenty_service_ids`, `test_machine_candidate_list_rejects_negative_min_mentions`, `test_admin_list_without_credentials_is_still_401_and_non_admin_403` (guards unchanged).
4. Existing pins stay: `test_legacy_parameters_still_work_and_canonical_ones_win`, `test_machine_candidate_list_is_unchanged`, the 422 quartet at `test_discovery_candidates_admin_api.py:310`.

Then the red tests for the new shape:

5. `test_discovery_list_handlers_take_at_most_three_parameters` (the extended `BUDGETED_HANDLERS`): fails today for six handlers.
6. `test_provide_candidate_query_translates_legacy_sort_and_lets_canonical_win` (unit test of the provider function, no HTTP), plus the same pair for the task and catalogue providers.

### Green

1. Add the carrier and one provider; convert one handler (`list_tasks`, the smallest); run the pinned suite; resolve the generic-annotation risk here.
2. Convert the remaining five handlers one commit each.
3. Extend the budget test.

### Refactor

Gate: judge by responsibility, not line count. A provider should be describable as "turn the query string into a filter and a page" with no business rule; the legacy-to-canonical overlay stays in the existing `*_filter_from` functions (do not copy it into the providers). Check the rule of three before adding any shared helper beyond the carrier; one nesting level; no one-line wrappers (a controller method that only forwards `query.filters, query.page` is the intended shape, not a smell); no new `Any`; imperative docstrings on every new public symbol; remove `D` and `ANN401` baseline entries for the touched controllers and list-query modules. Report `Refactor gate: smells found -> ..., refactorings applied -> ...` with the handler parameter counts before and after (8, 6, 6, 4, 4, 4 to at most 3).

## Verification

```bash
cd apps/api
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
uv run pytest tests/test_discovery_list_params_openapi.py tests/test_shared_paging_locale.py tests/test_discovery_admin_list_query.py \
  tests/test_discovery_candidates_list_contract.py tests/test_discovery_candidates_admin_api.py tests/test_discovery_candidate_sources_api.py \
  tests/test_discovery_artifacts_api.py tests/test_discovery_admin_api.py tests/test_discovery_candidate_emit.py
cd ../..
./ci.sh
```

The admin API files are slow; run them in the background. Also `cd apps/web && npm test -- discovery-admin` to confirm the canonical requests still pass (read-only).

## Parallel notes

Runs in batch 3 alongside I3, I5 and B7 (if approved). B5 is `After: B3`, which changed the `candidate_admin_service`, `admin_service` and read mappers: build on them. Do not touch `apps/discovery-ingest` (I3, I5), `api/models`, `api/alembic` or `features/documents` (B7), or `features/discovery/{service,url_normalize,stage_sync,pipeline_rows,task_enqueue}.py` (B3, B4, merged earlier). G1 (test gaps) runs after this chapter and relies on the extended budget test. Any ingest client change that drops a legacy name from `api_client.py` belongs to I1, not here.
