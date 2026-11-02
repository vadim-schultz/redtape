---
name: "Chapter I1 — Ingest client facade"
overview: "Replace the 15-copy HTTP block of DiscoveryMachineClient with a DiscoveryIngestClient facade (one resource class per API area) over one long-lived httpx.Client, one request method, named timeouts, a SecretStr API key and a bounded, scrubbed error body."
todos:
  - id: characterize
    content: "Pin every machine route (method, path, query, body, headers) and the error-text behaviour against the current client"
    status: pending
  - id: facade
    content: "Add discovery_ingest/client/ with MachineHttpClient, six resource classes and the DiscoveryIngestClient facade"
    status: pending
  - id: switch-call-sites
    content: "Switch every call site to the facade, delete api_client.py, machine_client.py and _post_catalogue_batches"
    status: pending
  - id: secrets-and-errors
    content: "discovery_api_key becomes SecretStr; DiscoveryMachineApiError carries a bounded, key-scrubbed body"
    status: pending
isProject: false
---

# Chapter I1 — Ingest client facade

**Repo:** `redtape` · **Branch:** `refactor/ingest-client-facade` · **Status:** planned

**Depends on:** A3 (ingest run lifecycle) · **Architecture:** [../00-audit-report.md](../00-audit-report.md) D4, T6, L13 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-codebase-audit` · **Release branch:** `main`

**Touches:** `ingest/api_client.py`, new `ingest/client/` (rollout table). The call-site switch below reaches further; see "Parallel notes" and the inconsistency list in the hand-off.

**Findings:** D4, T6 (key and error text), L13 (client part), hygiene: `_post_catalogue_batches`, `_budget_call`.

## Goal

Every machine-API request goes through one `request` method on one long-lived `httpx.Client`. Callers reach the API through `client.<area>.<operation>(...)`, exactly as `rsb-test-storage-client` does (decision U1). No behaviour change on the wire: same routes, bodies, headers, status handling and `trust_env=True`. Three deliberate changes: the connection is reused, `discovery_api_key` is a `SecretStr`, and the error text is bounded and key-scrubbed.

Reference implementation (read before starting):

| Concern | Reference file in `/home/schult_v/projects/rsb-test-storage-client/src/rsb_test_storage_client/` |
| --- | --- |
| Facade: `self.campaigns = CampaignsAPI(self._client)` ... | `client/api_client.py` (`APIClient`) |
| One resource class, methods return typed models | `client/campaigns_api.py` (`CampaignsAPI`) |
| Shared HTTP client the resources receive | `client/http_client.py` |

## Verified current state

- `apps/discovery-ingest/discovery_ingest/api_client.py` (372 lines): `DiscoveryMachineApiError`, `DiscoveryMachineClient` (28 public methods), module function `_post_catalogue_batches` (imported privately by `cli.py:14`).
- 15 places open their own `with httpx.Client(trust_env=True, timeout=60.0)`: 14 methods (`_post_batch`, `get_catalogue`, `post_entity`, `post_claim`, `post_mentions`, `preview_candidate_emit`, `emit_candidates`, `claim_tasks`, `get_task_summary`, `enqueue_task`, `start_run`, `finish_run`, `append_fetch`, `fail_task`) plus `_call`, which the other 14 operations use (directly or through `_budget_call`). A new TCP and TLS handshake per request.
- `_call` has six keyword parameters (`json`, `params`, `data`, `files`, `allow`) plus method and path.
- `DiscoveryMachineApiError(status_code, detail)`: `detail` is `response.text` verbatim; `cli.py` prints it. `is_database_limit` is `status == 507 and "database_soft_limit" in detail` (API side: `apps/api/app/features/discovery/db_headroom.py:23,90`).
- `IngestSettings.discovery_api_key: str` (`config.py:58`); Cloudflare tokens already use `SecretStr` (`config.py:28`, `llm_settings.py:26`).
- Test seam today: 18 test modules (helpers and fakes included) monkeypatch the string `"discovery_ingest.api_client.httpx.Client"` with a factory that injects `httpx.MockTransport` (`test_budget_guard.py:38`, `test_artifact_client.py:28`, `ledger_fakes.py:72`, `render_fakes.py:168`, `curate_fakes.py:153`, `test_cli_budget.py:54`, `test_artifacts_cli.py:39`, `test_candidates_cli.py:94`, `test_capture_requeue.py:88`, `test_enrich_metadata_worker.py:38`, `test_fim_leika_enrich.py:29`, `test_govdata_cli.py:25`, `test_govdata_fetch.py:31`, `test_harvest_worker.py:75`, `test_llm_requeue.py:91`, `test_pvog_cli.py:36`, `test_worker_drain.py:38`, `test_worker_run.py:26`). The patch replaces the global `httpx.Client` attribute, so it also affects other modules; keep that in mind when choosing the new target string.

## Target design

### Module layout `discovery_ingest/client/`

| File | Contents |
| --- | --- |
| `__init__.py` | exports `DiscoveryIngestClient`, `DiscoveryMachineApiError` |
| `errors.py` | `DiscoveryMachineApiError` (name kept, 20 modules catch it), `MAX_ERROR_DETAIL_CHARS = 1000`, `DATABASE_LIMIT_DETAIL`, `HTTP_INSUFFICIENT_STORAGE`; `DiscoveryMachineApiError.from_response(response, secret)` |
| `http_client.py` | `MachineHttpClient`: owns the one `httpx.Client`, base URL, the `X-API-Key` default header, `REQUEST_TIMEOUT_SECONDS = 60.0`, `MACHINE_PREFIX = "/api/v1/discovery/machine"`; `request(...)`, `request_model(...)`, `close()` |
| `ingest_client.py` | `DiscoveryIngestClient` facade (the `APIClient` equivalent), context manager, `from_settings` |
| `runs_api.py` | `RunsAPI`: `start() -> UUID`, `finish(run_id, body)` |
| `catalogue_api.py` | `CatalogueAPI`: `upsert_batches(items, *, batch_size)`, `get(catalogue_id)`, `upsert_entity(body)`, `append_claim(body)` |
| `tasks_api.py` | `TasksAPI`: `claim(*, limit, kinds)`, `summary(*, kinds)`, `enqueue(body)`, `append_fetch(task_id, body)`, `complete(task_id, *, note)`, `release(task_id, reason, *, not_before)`, `fail(task_id, *, error, retryable)` |
| `candidates_api.py` | `CandidatesAPI`: `post_mentions(items)`, `post_edges(items)`, `list_staged(*, min_mentions, limit, offset)`, `preview_emit(candidate_id)`, `emit(candidate_ids)`, `list_sources(query: SourceQuery)`, `taxonomy()` |
| `artifacts_api.py` | `ArtifactsAPI`: `upload(task_id, upload)`, `status()`, `content(artifact_id)`, `list(query: ArtifactQuery)` |
| `budget_api.py` | `BudgetAPI`: `snapshot()`, `reserve(resource, amount)`, `adjust(resource, delta)`, `exhaust(resource)` |

Placement decisions: entities and claims hang under a catalogue row, so they live in `CatalogueAPI`. `GET /taxonomy` is consumed only by mention extraction (`worker/llm_setup.py`, `curation_command.py`, `extract/llm/evaluation/command.py`), so it lives in `CandidatesAPI`. The artifact upload route is `/tasks/{id}/artifacts` but the operation belongs to `ArtifactsAPI`.

### The facade

```python
class DiscoveryIngestClient:
    def __init__(self, base_url: str, api_key: SecretStr, *, transport: httpx.BaseTransport | None = None) -> None: ...
    runs: RunsAPI; catalogue: CatalogueAPI; tasks: TasksAPI
    candidates: CandidatesAPI; artifacts: ArtifactsAPI; budget: BudgetAPI
    @classmethod
    def from_settings(cls, settings: IngestSettings) -> DiscoveryIngestClient: ...
    def close(self) -> None: ...        # plus __enter__ / __exit__
```

- `transport` is the new test seam (`httpx.MockTransport`). `MachineHttpClient` builds `httpx.Client(base_url=..., headers={"X-API-Key": ...}, timeout=REQUEST_TIMEOUT_SECONDS, trust_env=True, transport=transport)` with **keyword arguments only**, so the legacy factory-style monkeypatch (`kwargs["transport"] = ...`) keeps working for tests that build the client inside a command.
- `from_settings` replaces `machine_client.py` and the eight copies of `DiscoveryMachineClient(settings.discovery_api_url, settings.discovery_api_key)`.
- The API key is held by the `httpx.Client` default header and, for scrubbing only, by `MachineHttpClient` as a private `SecretStr`. `repr()` of the facade never shows it.

### One request method

```python
class RequestOptions(TypedDict, total=False):
    json: JsonValue; params: Mapping[str, str | int | list[str]]
    data: Mapping[str, str]; files: Mapping[str, tuple[str, bytes, str]]
    allow: tuple[int, ...]            # statuses that are answers, not errors (budget reserve: 409)

def request(self, method: str, path: str, **options: Unpack[RequestOptions]) -> httpx.Response: ...
def request_model(self, model: type[M], method: str, path: str, **options: Unpack[RequestOptions]) -> M: ...
```

`request` raises `DiscoveryMachineApiError.from_response(...)` for status `>= 400` not in `allow`. `request_model` is `request` plus `model.model_validate(response.json())`; it exists because about 20 of today's methods end in exactly that pair (21 `model_validate` calls in `api_client.py`; rule of three). `json` is typed `JsonValue` (verified: `pydantic.JsonValue` imports in the pinned pydantic 2.14.1; `browser/client.py` already uses it). No `get`/`post` wrappers: they would be one-line delegations.

### Named constants

`REQUEST_TIMEOUT_SECONDS = 60.0` (was the literal `60.0` x15), `MAX_BATCH_SIZE = 50` (was a literal check in `post_catalogue_batches`), `MACHINE_PREFIX`, `MAX_ERROR_DETAIL_CHARS = 1000` (same bound `worker/run.py` uses for `error_detail`). `HTTP_CREATED = 201` and `HTTP_CONFLICT = 409` move next to their one user (`artifacts_api.py`, `budget_api.py`). The timeout value is unchanged: this is naming, not tuning.

### Query objects (L13, client part)

`list_candidate_sources` takes six keywords and `list_artifacts` four. Replace with frozen Pydantic or dataclass objects defined beside the existing models, so I5 can diff the same field names:

- `SourceQuery(host, missing, candidate_id, service_ids, offset, limit)` in `candidate_sources.py` (that file already defines `SourceMissing`, `CandidateSourcePage`). `CandidatesAPI.list_sources(query)` builds the params exactly as `list_candidate_sources` does today (omit `None`, `catalogue_service_id` repeated per id). Callers: `capture_requeue.py:60`, `curation_pages.py:21`.
- `ArtifactQuery(host, kind, offset, limit)` in `artifacts.py`. Callers: `artifacts_cli.py:47`, `curation_pages.py:33`, `latest_snapshots.py:19`.

The offset/limit paging loop is written five times (`artifacts_cli._artifacts`, `curation_pages` x2, `latest_snapshots._snapshots`, `capture_requeue._sources`). The stop conditions differ slightly (a caller limit versus the page total), so do **not** merge them in this chapter unless the Refactor step shows one generator expresses all five without a flag parameter.

### Errors (T6)

`DiscoveryMachineApiError(status_code, detail)` keeps its constructor, `str()` format (`discovery machine API {status}: {detail}`) and `is_database_limit` (existing tests build it directly: `test_budget_guard.py:139`). `from_response` produces `detail` as: response body text, with the API key replaced by `<redacted>`, cut to `MAX_ERROR_DETAIL_CHARS` and suffixed with a truncation mark. A 507 body is small JSON with the sentinel at the start, so `is_database_limit` stays correct after truncation; a test pins that.

The scrub helper is a three-line private function in `errors.py`. `browser/client.py:_scrub` and `extract/llm/redaction.scrub` are the other two copies; record "rule of three reached for secret scrubbing" in the PR and the run ledger instead of unifying across directories that A3 and I2 own.

### Settings

`IngestSettings.discovery_api_key: SecretStr` (`config.py:58`). Only `DiscoveryIngestClient.from_settings` calls `get_secret_value()`. The environment variable `DISCOVERY_API_KEY` is unchanged, so `.github/workflows/discovery-*.yml` need no edit.

## Files

Create (`apps/discovery-ingest/discovery_ingest/client/`): `__init__.py`, `errors.py`, `http_client.py`, `ingest_client.py`, `runs_api.py`, `catalogue_api.py`, `tasks_api.py`, `candidates_api.py`, `artifacts_api.py`, `budget_api.py`.

Delete: `discovery_ingest/api_client.py`, `discovery_ingest/machine_client.py`.

Edit (models): `candidate_sources.py` (add `SourceQuery`), `artifacts.py` (add `ArtifactQuery`), `config.py` (`SecretStr` key; line 58 only, I3 edits the rest of the file later).

Edit (docs links to the deleted file): `apps/discovery-ingest/README.md:107`, `docs/operations/discovery-online-production-setup.md:175`. Repoint to `discovery_ingest/client/`. (These two doc edits are part of the implementation PR, not of this planning task.)

### Call sites that must switch (all verified by grep)

**Client construction** (use `with DiscoveryIngestClient.from_settings(settings) as client:`; each currently builds an unclosed client per command):

| Site | Today |
| --- | --- |
| `cli.py:192, 254, 292, 321` | `DiscoveryMachineClient(settings.discovery_api_url, settings.discovery_api_key)` in `_fim_enrich`, `_worker_drain`, `_candidates_emit`, `_leika_enrich` |
| `cli.py:83, 133, 163` | `_post_catalogue_batches(url, key, items)` in `_govdata_run`, `_govdata_fetch_pages`, `_pvog_run`; becomes `client.catalogue.upsert_batches(items)` on one client per command (the `_govdata_fetch_pages` loop then reuses one connection for all pages) |
| `machine_client.py:12` (users: `candidates_cli.py:70`, `curation_command.py:102`) | delete the module, use `from_settings` |
| `llm_requeue.py:44`, `capture_requeue.py:89`, `artifacts_cli.py:40` (`_client`), `budget_cli.py:65` (`_guard`), `extract/llm/evaluation/command.py:55` | direct construction |

**Import and annotation rename** (`DiscoveryMachineClient` to `DiscoveryIngestClient`; `DiscoveryMachineApiError` imported from `discovery_ingest.client`): `requeue_common.py`, `curation_pages.py`, `candidates_cli.py`, `llm_requeue.py`, `budget.py`, `budget_cli.py`, `latest_snapshots.py`, `capture_requeue.py`, `artifacts_cli.py`, `cli_errors.py`, `curation_command.py`, `curation_staged.py`, `curation_run.py`, `candidate_emit.py`, `cli.py`, `worker/{llm_post,render_enqueue,browser_steps,extract_enqueue,llm_enqueue,run,settle,harvest,storage_guard,render,capture,extract,llm_steps,enrich_metadata,llm_extract,browser_setup,drain,llm_setup,fetch_url,capture_enqueue,mention_post,release,batch}.py`, `extract/llm/evaluation/command.py`.

**Method renames** (old to new; counts are production call sites):

| Old | New | Call sites |
| --- | --- | --- |
| `post_catalogue_batches` | `catalogue.upsert_batches` | `cli.py` x3 (via `_post_catalogue_batches`) |
| `get_catalogue` | `catalogue.get` | `worker/enrich_metadata.py`, `worker/harvest.py` |
| `post_entity`, `post_claim` | `catalogue.upsert_entity`, `catalogue.append_claim` | `cli.py` (x2 each), `worker/enrich_metadata.py` |
| `post_mentions`, `post_edges` | `candidates.post_mentions`, `candidates.post_edges` | `curation_run.py`, `worker/mention_post.py`, `worker/llm_post.py` |
| `list_staged_candidates` | `candidates.list_staged` | `candidate_emit.py`, `curation_staged.py` |
| `preview_candidate_emit`, `emit_candidates` | `candidates.preview_emit`, `candidates.emit` | `candidate_emit.py` |
| `list_candidate_sources` | `candidates.list_sources(SourceQuery(...))` | `capture_requeue.py`, `curation_pages.py` |
| `get_taxonomy` | `candidates.taxonomy` | `curation_command.py`, `worker/llm_setup.py`, `extract/llm/evaluation/command.py` |
| `claim_tasks`, `get_task_summary` | `tasks.claim`, `tasks.summary` | `worker/batch.py`, `worker/drain.py` |
| `enqueue_task` | `tasks.enqueue` | `requeue_common.py`, `worker/{capture_enqueue,extract_enqueue,llm_enqueue,render_enqueue}.py` |
| `append_fetch`, `complete_task`, `release_task`, `fail_task` | `tasks.append_fetch`, `tasks.complete`, `tasks.release`, `tasks.fail` | `worker/fetch_url.py`; `worker/{browser_steps,enrich_metadata,extract,fetch_url,harvest}.py`; `worker/release.py`; `worker/settle.py` x3 |
| `start_run`, `finish_run` | `runs.start`, `runs.finish` | `worker/run.py` |
| `upload_artifact`, `get_artifact_status`, `get_artifact_content`, `list_artifacts` | `artifacts.upload`, `artifacts.status`, `artifacts.content`, `artifacts.list(ArtifactQuery(...))` | `worker/browser_steps.py`; `worker/storage_guard.py`; `artifacts_cli.py`, `curation_pages.py`, `worker/extract.py`, `worker/llm_steps.py`; `artifacts_cli.py`, `curation_pages.py`, `latest_snapshots.py` |
| `get_budgets`, `reserve_budget`, `adjust_budget`, `exhaust_budget` | `budget.snapshot`, `budget.reserve`, `budget.adjust`, `budget.exhaust` | `budget.py`; `BudgetGuard` now takes `client.budget` (it uses nothing else), constructed in `budget_cli._guard` and `tests/ledger_fakes.guard_for` |

Narrowing other helpers to a single resource (for example `release_tasks` to `client.tasks`) is allowed but not required; the mechanical change passes the facade.

**Tests that must be migrated** (import path, type, and the monkeypatch target `"discovery_ingest.api_client.httpx.Client"` becomes `"discovery_ingest.client.http_client.httpx.Client"` for tests that build the client inside a command, or `DiscoveryIngestClient(..., transport=httpx.MockTransport(handler))` where the test builds the client itself): the 18 modules listed under "Test seam today", plus `test_llm_extract_worker.py`, `test_llm_extract_stops.py`, `test_llm_machine_client.py`, `llm_worker_fakes.py`, `render_fakes.py`, `ledger_fakes.py`, `curate_fakes.py`. Test helpers that build the client directly switch to the `transport=` argument and drop `_REAL_HTTPX_CLIENT`.

## TDD loop

### Red

Work in two commits so the behaviour is pinned before it moves.

1. **Characterise first (green against the old client).** New `tests/test_machine_routes.py`, parametrised over the whole route table with `httpx.MockTransport`, asserting method, path (including the `/api/v1/discovery/machine` prefix), query params, JSON or multipart body, and the `X-API-Key` header for each of the 28 operations. Names: `test_route_table_matches_the_wire[catalogue.upsert_batches]`, `...[tasks.claim]`, `...[budget.reserve]`, and so on (one id per operation). Extra characterisation: `test_enqueue_drops_none_fields`, `test_summary_sends_kinds_as_repeated_param`, `test_sources_query_omits_none_and_repeats_service_ids`, `test_upload_201_is_created_and_200_is_a_match`, `test_reserve_409_is_an_answer_not_an_error`, `test_error_status_raises_with_the_body_text`. Run against `DiscoveryMachineClient`; all pass.
2. **Port the same tests to the facade names** and add the new behaviour. They fail because `discovery_ingest.client` does not exist.

Happy path:

- `test_one_http_client_serves_every_request`: patch `httpx.Client` with a counting factory, make five calls across three resources, assert one construction.
- `test_every_request_carries_the_api_key_header` and `test_base_url_trailing_slash_is_normalised`.
- `test_catalogue_upsert_batches_dedupes_and_chunks_by_batch_size` (51 rows give two POSTs; duplicate `(source, external_id)` collapses, last wins).
- `test_source_query_and_artifact_query_build_the_same_params_as_before`.
- `test_from_settings_unwraps_the_secret_once` and `test_context_manager_closes_the_http_client`.
- `test_budget_guard_accepts_the_budget_resource` (the guard works with `client.budget`).

Negative path:

- `test_batch_size_outside_1_to_50_raises_value_error` and `test_empty_batch_raises` (existing behaviour of `post_catalogue_batches` and `dedupe_batch_items`).
- `test_error_detail_is_truncated_to_the_limit` (a 1 MB HTML body gives `len(detail) <= MAX_ERROR_DETAIL_CHARS + len(mark)`).
- `test_error_detail_never_contains_the_api_key` (a body that echoes the key gives `<redacted>`; also the exception `str()` and `repr()`).
- `test_database_limit_survives_truncation` (507 plus `database_soft_limit` still `is_database_limit`; 507 with another detail is not; 500 with the sentinel is not).
- `test_settings_repr_hides_the_key` (`repr(IngestSettings)` and `repr(DiscoveryIngestClient)` do not contain the key).
- `test_transport_error_is_not_wrapped` (a `httpx.ConnectError` from the transport propagates unchanged, because 8 callers catch `httpx.HTTPError` next to `DiscoveryMachineApiError`).
- `test_invalid_success_body_raises_validation_error` (callers catch `ValidationError`; do not convert).

Run the narrow suite: new tests fail on import; step-1 tests still pass.

### Green

1. Add `client/errors.py`, `http_client.py`, the six resource modules and `ingest_client.py`. Copy URLs, bodies and `allow` values from the old methods verbatim.
2. Add `SourceQuery`, `ArtifactQuery`; change `discovery_api_key` to `SecretStr`.
3. Switch the call sites in the order: `cli_errors.py` and models, `budget*`, `worker/*`, `curation*`, the `*_cli.py` modules, `cli.py` last. Update test helpers as each module moves. Delete `api_client.py`, `machine_client.py` and `_post_catalogue_batches` when `grep -rn "api_client\|machine_client\|_post_catalogue_batches" apps/discovery-ingest` is empty apart from docs.
4. Repoint the two doc links.

### Refactor

Audit the new package and the touched call sites per the refactor-step checklist, judging by responsibility, not line count. Look at: does `MachineHttpClient` do only transport and error mapping (no routes), does each resource class only build requests and parse one model (no policy), are there leftover one-line wrappers (`_budget_call`, `_post_catalogue_batches`, `machine_client()` must be gone), does the five-fold offset/limit loop pass the rule of three **with the same stop condition**, and are there new `Any` (none allowed; `RequestOptions` uses `JsonValue`). Every new public class and method gets an imperative docstring that states intent without repeating the signature (pydocstyle `D` with `pep257`); remove the `D` baseline entries of every file this chapter rewrites (`budget.py`, `candidate_sources.py` and the rewritten call sites). Report `Refactor gate: smells found -> ..., refactorings applied -> ...` with: `httpx.Client(` occurrences in `discovery_ingest/client` (expected 1), `timeout=60.0` literals (expected 0), `D` and `ANN401` counts of the touched files before and after.

## Verification

```bash
cd apps/discovery-ingest
uv run ruff format --check . && uv run ruff check . && uv run mypy discovery_ingest
uv run pytest tests/test_machine_routes.py tests/test_ingest_client.py tests/test_budget_guard.py \
  tests/test_artifact_client.py tests/test_llm_machine_client.py tests/test_worker_drain.py \
  tests/test_worker_run.py tests/test_cli_budget.py tests/test_artifacts_cli.py tests/test_govdata_cli.py \
  tests/test_pvog_cli.py tests/test_fim_leika_enrich.py tests/test_enrich_metadata_worker.py
uv run pytest            # whole ingest suite: every module above the line changed imports
cd ../..
./ci.sh
```

CLI contract check (the operator-visible surface must not move): `uv run python -m discovery_ingest --help` and `budget show --help` print the same text as on `main`.

## Parallel notes

Siblings running in the same batch: I2 (ingest typing), B3, B4, W3, W4, T1 slices.

- **I2** edits `pvog/`, `govdata/`, `fim/`, `leika/`, `enrich.py`, `extract/llm/{schema,schema_prep,payloads,cloudflare,client}.py` and `worker/enrich_metadata.py` (`_parse_steckbrief_body`). I1 must not touch those files except `worker/enrich_metadata.py`, where I1 owns the machine-client lines (import, `get_catalogue`, `post_entity`, `post_claim`, `complete_task`, `DiscoveryMachineApiError`) and I2 owns `_parse_steckbrief_body`; the hunks are disjoint, so the chief of staff rebases whichever lands second. I1 does not touch `extract/llm/evaluation/command.py`'s typing, only its client lines; I2 must not edit that file.
- **T1 step 2** (docstring slices) edits the same ingest files as docstring-only changes. If a slice for `discovery_ingest/` root or `worker/` is open, rebase after it lands; T1 step 2 starts after T1 step 1 and may overlap this chapter.
- **A3** (before I1) already changed `worker/run.py`, `worker/llm_setup.py`, `browser/client.py`, `pvog/client.py`, `govdata/ckan.py`; start from its merged state.
- **Must not be touched by this chapter:** `apps/api/**`, `.github/**`, `pyproject.toml` (no new dependency here), `cli.py` structure beyond the client lines (I3 and I4 own it), `browser/client.py` and `extract/llm/redaction.py` (scrub helpers stay as they are).
- Unblocks **I3** (operations take the facade) and **I5** (contract test reads the same model modules).
