---
name: "Chapter I3 — Ingest operations layer"
overview: "Move catalogue ingest, FIM/LeiKa enrich, drain wiring and model-client construction out of cli.py into a printing-free operations package with typed results; add PageBudget, DrainDeps and LeafHints; read bot and FIM settings from settings instead of the environment."
todos:
  - id: characterize
    content: "Pin stdout, stderr and exit codes of govdata, pvog, fim, leika and worker drain commands through main()"
    status: pending
  - id: settings
    content: "BotSettings, shared Cloudflare account base, DEFAULT_FIM_PORTAL_URL; remove os.environ and the hard-coded FIM URLs"
    status: pending
  - id: operations
    content: "operations/{catalogue,enrich,drain,models}.py and page_budget.py with typed results"
    status: pending
  - id: parameter-objects
    content: "DrainDeps replaces the 11-parameter drain signature; LeafHints and PvogDrafter replace the 9-parameter _draft"
    status: pending
  - id: fixture-vs-live
    content: "Split fixture and live steckbrief and stammtext sources into separate classes"
    status: pending
isProject: false
---

# Chapter I3 — Ingest operations layer

**Repo:** `redtape` · **Branch:** `refactor/ingest-operations-layer` · **Status:** planned

**Depends on:** I1, I2 · **Architecture:** [../00-audit-report.md](../00-audit-report.md) D6, D8 (PageBudget), D9, L12, L13 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-codebase-audit` · **Release branch:** `main`

**Touches:** new `ingest/operations/`, `ingest/worker/`, `ingest/harvest/`, `ingest/config.py` (rollout table). Also, as listed under Files: `cli.py` (handlers become thin), `fim/client.py`, `leika/client.py`, `pvog/client.py` and `govdata/ckan.py` (PageBudget), `extract/llm/evaluation/command.py` (model client).

**Findings:** D6, D8 (page and record caps), D9, L12, L13 (drain, PVOG hints).

## Goal

`cli.py` stops being the place where flows live. Each flow becomes a function or small class in `discovery_ingest/operations/` that takes typed inputs, returns a typed result and **never prints or calls `sys.exit`**; the argparse handlers in `cli.py` (replaced by Typer in I4) only parse, call and render. A new enrich source touches one class, not three code paths. No change to operator-visible stdout, stderr text or exit codes (the ingest CLI is a public interface, see I4).

The same layering as the reference repo `/home/schult_v/projects/rsb-test-storage-client/src/rsb_test_storage_client/`: `client/` (I1) is the transport and resources; `operations/` is the new middle layer (the reference has no equivalent because its commands call the client directly); `cli/` (I4) renders.

## Verified current state

| Smell | Evidence |
| --- | --- |
| D6 three copies of the enrich flow | `cli._fim_enrich` (`cli.py:173-204`), `cli._leika_enrich` (`cli.py:303-333`), `worker/enrich_metadata.handle_enrich_metadata` (`worker/enrich_metadata.py:21-61`). Each does: build entity request, `post_entity`, loop `post_claim`. Parallel function pairs in `enrich.py`: `fim_steckbrief_entity_request`/`leika_stammtext_entity_request`, `fim_steckbrief_claim_requests`/`leika_stammtext_claim_requests`, `fim_id_from_catalogue`/`leika_segments_from_catalogue`. |
| D6 flow also forks on catalogue ingest | `_govdata_run` (all rows, one post), `_govdata_fetch_pages` (post per CKAN page, `posted_any`), `_pvog_run` (walk every page, then post once). Messages: `"no mappable GovData rows"`, `"no mappable PVOG rows"`, `"skip row: {err}"` (printed inside the mapping loops `cli.py:336-375`). |
| D8 page and record caps | `pvog/client.py:55,63,118` (`_budget_allows_fetch(max_pages, pages_fetched)`, counting the bootstrap page too) and `govdata/ckan.py:36-65` (`max_pages`, `max_records`, trim, `len(records) < page_size`). |
| D9 environment bypass | `cli.py:208` `os.environ.get("BOT_CONTACT_URL", DEFAULT_BOT_CONTACT_URL)` in `fim probe`; `browser/probe_cli.py:24,50` use `DEFAULT_BOT_CONTACT_URL` and ignore `BOT_CONTACT_URL` altogether. Workflow `discovery-fim-probe.yml` sets no `DISCOVERY_*` variable, so `fim probe` cannot use `IngestSettings` (it requires `DISCOVERY_API_URL` and `DISCOVERY_API_KEY`). |
| D9 FIM base URL, 5 literals | `config.py:76` (the setting), `worker/enrich_metadata.py:18`, `fim/client.py:26`, `leika/client.py:24`, `cli.py:471` (`fim probe --base-url` default). |
| D9 duplicate setting | `cloudflare_account_id` declared in `BrowserSettings` (`config.py:27`) and `LlmSettings` (`llm_settings.py:25`); `IngestSettings(BrowserSettings, LlmSettings)` inherits both. |
| L12 | `fim/client.py` `fetch_steckbrief` and `leika/client.py` `fetch_stammtext` branch on `if self._fixture is not None` between a local fixture and a live `httpx.Client` GET. |
| L13 | `worker/drain.run_worker_drain` has 11 parameters (`client, fetcher, policy, clock, budget, browser, after_snapshot, extractors, llm, after_extract, llm_enqueue`); `worker/run.run_recorded_drain` 7; `harvest/pvog._draft` 9 and `_module_drafts` 7, both carrying the same five hint values (`situation_codes`, `situation_confidence`, `domain_codes`, `domain_confidence`, `leaf_code`) computed by five functions that each re-read `_leaf_code(raw_payload)`. |
| Model client built twice | `worker/llm_setup.prepare_llm` (lines 80-82) and `extract/llm/evaluation/command._runtime` (lines 56-58) both call `CloudflareAiClient(settings, model=..., http=httpx.Client(trust_env=True), throttle=Throttle(MIN_INTERVAL_SECONDS))`; `MIN_INTERVAL_SECONDS = 1.0` exists in `worker/llm_setup.py:22`, `extract/llm/probe_cli.py:22`, `extract/llm/evaluation/command.py:36` and as `DEFAULT_MIN_INTERVAL_SECONDS` in `cloudflare.py:20`. |

## Target design

### Package layout

```text
discovery_ingest/
  page_budget.py             PageBudget (shared by crawl clients; not under operations/, which crawl clients must not import)
  operations/
    __init__.py
    results.py               IngestResult, EnrichResult
    catalogue.py             CatalogueSource protocol, GovDataFileSource, GovDataCkanSource, PvogSource, ingest()
    enrich.py                Enricher protocol, FimEnricher, LeikaEnricher, post_enrichment(), run_enrich(), EnrichError family
    drain.py                 DrainOptions, run_drain()
    models.py                build_model_client()
  worker/drain_deps.py       DrainDeps (parameter object; lives with the drain it configures)
```

Operations import `client/` (I1) and the typed models (I2); they do not import `argparse`, `typer`, `rich` or `sys`. A test enforces it (below).

### Settings (D9)

- `config.py`: `DEFAULT_FIM_PORTAL_URL = "https://fimportal.de"` used as the default of `fim_portal_base_url` and imported by `fim/client.py`, `leika/client.py`, `worker/enrich_metadata.py` and the `fim probe` flag default (the `--help` text keeps the same string).
- `BotSettings(BaseSettings)`: `bot_contact_url` (`BOT_CONTACT_URL`) and `user_agent`; `load_bot_settings()`. `IngestSettings` inherits it. `fim probe` and `browser probe` use `load_bot_settings()` (needs no secret). Consequence to state in the PR: `browser probe` now honours `BOT_CONTACT_URL`; no workflow sets it, the README documents it (`README.md:116`).
- `CloudflareAccountSettings(BaseSettings)` holds `cloudflare_account_id` once; `BrowserSettings` and `LlmSettings` extend it, so `IngestSettings` has one declaration. `credentials()`/`ai_credentials()` and `missing_*` keep their messages.
- `os.environ` is no longer read outside `config.py`/`llm_settings.py` (a test greps for it).
- `FEDERAL_ARS` default of `govdata_open_pvog_ars` (`config.py:68`) imports `catalogue_scope.FEDERAL_ARS` created in I2.

### PageBudget (D8)

```python
@dataclass(slots=True)
class PageBudget:
    max_pages: int | None
    max_records: int | None = None
    @property
    def exhausted(self) -> bool: ...                 # pages or records used up
    def spend_page(self) -> None: ...                # count one fetch
    def admit(self, records: Sequence[T]) -> list[T]: ...  # trim to the remaining record cap, count what is kept
```

- `PvogClient.iter_records`: one budget; `spend_page()` per HTTP fetch including the bootstrap page, `exhausted` replaces both `_budget_allows_fetch` tests (I2 inlined them; this removes the inline copies).
- `GovDataCkanClient.iter_record_pages`: `while not budget.exhausted:` fetch, `kept = budget.admit(records)`, stop on empty `kept` or a short page. `max_pages < 1` yields nothing, as today.
- Tests first: `max_pages` of 0, 1, 2, `None`; `max_records` trimming mid-page; short page stops; the bootstrap page counts in PVOG.

### Catalogue ingest

```python
class CatalogueSource(Protocol):
    name: str                                         # "GovData" or "PVOG", used in messages
    def batches(self) -> Iterator[SourceBatch]: ...   # SourceBatch(items: list[CatalogueBatchItem], skipped: list[str])

def ingest(source: CatalogueSource, client: DiscoveryIngestClient) -> IngestResult: ...
```

- `GovDataFileSource(path, jurisdiction_id)` yields one batch (as `govdata run`), `GovDataCkanSource(ckan, jurisdiction_id, options)` yields one per feed page (as `govdata fetch`), `PvogSource(pvog, jurisdiction_id, max_pages)` walks every page and yields **one** batch (as `pvog run` today: a late-page failure posts nothing). That granularity is a source decision and is pinned by a test.
- `ingest` posts each non-empty batch with `client.catalogue.upsert_batches` and returns `IngestResult(source, rows_posted, rows_skipped, skipped: list[str])`.
- Failures are exceptions, not prints: `NothingToIngest(source_name)` (message `no mappable {name} rows`), and the existing `GovDataCkanError`, `PvogClientError`, `DiscoveryMachineApiError` propagate. The command layer prints `skip row: {message}` for each `skipped` entry (stderr order changes from "while mapping" to "before the exit message"; text is identical) and maps exceptions to exit 1 with today's text (`govdata fetch failed: {err}`, bare `{err}` for PVOG, `no mappable ...`). The two API-error paths that return 1 silently today (`cli.py:88,168,202,331`, finding C4) print through the shared handler in I4; this chapter keeps them as they are.

### Enrich (D6, L12)

```python
class Enricher(Protocol[DocT]):
    name: str                                         # "fim" or "leika"
    def lookup(self, catalogue: CatalogueExportItem) -> Lookup: ...   # raises MissingLookupKey(message)
    def fetch(self, lookup: Lookup) -> DocT: ...                      # raises EnrichFetchError
    def entity_request(self, catalogue, document: DocT) -> EntityUpsertRequest: ...
    def claim_requests(self, catalogue, document: DocT, entity_id: UUID) -> list[ClaimAppendRequest]: ...

def post_enrichment(enricher, catalogue, document, client) -> EnrichResult: ...   # the one entity + claims post sequence
def run_enrich(enricher, catalogue, client) -> EnrichResult: ...                  # lookup, fetch, post_enrichment
```

- `FimEnricher(source: SteckbriefSource, fim_base_url)` wraps `fim_id_from_catalogue`, `fim_steckbrief_*`; `LeikaEnricher(source: StammtextSource, fim_base_url)` wraps `leika_segments_from_catalogue`, `leika_stammtext_*` (functions stay in `enrich.py` as the pure mapping; I2 already typed them).
- Fixture versus live (L12): `SteckbriefSource` and `StammtextSource` protocols; `FixtureSteckbriefSource(steckbrief)` and `HttpSteckbriefSource(base_url, http_client)` replace `FimSteckbriefClient`'s `if self._fixture is not None`; same for LeiKa. `from_json_file` moves to the fixture classes. The live source uses the shared `httpx` conventions of the crawl clients (`trust_env=True`, timeout 60 as today).
- The three callers: `fim enrich` and `leika enrich` call `run_enrich`; `handle_enrich_metadata` (task flow) keeps its own acquisition (`PoliteUrlFetcher`, `Steckbrief.from_body`) and calls `post_enrichment`, with `fim_base_url` taken from `DrainDeps` instead of `_DEFAULT_FIM_BASE`. Its settle mapping (`fail_permanently`, `fail_from_outcome`) is unchanged.
- Errors keep their messages as exceptions: `CatalogueRowNotFound` (`catalogue service id not found in export`), `MissingLookupKey` (`catalogue row has no steckbrief key (fim_id, leistungsschluessel, leika_key or leikakeys)` and `catalogue row missing redaktion_id and leistung_id`), `EnrichFetchError` (`fim fetch failed: ...`, `leika fetch failed: ...`).

### Drain wiring (L13)

- `DrainDeps(client, fetcher, browser=None, llm=None, after_extract=no_after_extract, llm_enqueue=None, after_snapshot=None, extractors=EXTRACTORS, budget=None, clock=time.monotonic, fim_base_url=DEFAULT_FIM_PORTAL_URL)` frozen dataclass in `worker/drain_deps.py`.
- `run_worker_drain(deps, policy)` and `run_recorded_drain(deps, policy)` (2 parameters each, was 11 and 7); `handler_table` takes the deps. `_open_spend`, `_close_tally` keep their roles.
- `operations/drain.py`: `DrainOptions(kinds, max_tasks, max_batches, time_budget_seconds, browser_budget_seconds, neuron_budget)` with `.policy() -> DrainPolicy` (moves `_drain_policy` and `LLM_BATCH_SIZE = 5` out of `cli.py`); `run_drain(options, settings, client) -> DrainReport` is `_drain_and_print` without the `print`. `BrowserSetupError` and `LlmSetupError` still propagate with their `exit_code`.
- `operations/models.py`: `build_model_client(settings, model) -> CloudflareAiClient`, the single place that wires `httpx.Client`, `Throttle` and the credentials; `prepare_llm` and `evaluation/command._runtime` call it. One `MIN_INTERVAL_SECONDS` (the `cloudflare.py` default constant is reused). Client closing follows the mechanism chosen in A3 (do not invent a second one).

### PVOG hints (L13)

`LeafHints(situation_codes, situation_confidence, domain_codes, domain_confidence, leaf_code)` frozen dataclass with `LeafHints.from_payload(raw_payload)` reading `_personal_matter_code` once and consulting the four mapping tables. A small `PvogDrafter(locale, hints)` class replaces the nine-parameter `_draft` and seven-parameter `_module_drafts`: `module_drafts(module)` and a private `_draft(module, selector, item)`. `harvest_pvog_payload(raw_payload)` builds one drafter. Output (`MentionDraft` list, order, values) is identical; `tests/test_pvog_harvest.py` is the characterisation.

## Files

Create: `discovery_ingest/page_budget.py`, `operations/{__init__,results,catalogue,enrich,drain,models}.py`, `worker/drain_deps.py`.

Edit: `config.py` (`BotSettings`, `CloudflareAccountSettings`, `DEFAULT_FIM_PORTAL_URL`), `llm_settings.py` (extend the shared base), `cli.py` (handlers call operations; imports of `os` removed), `enrich.py` (no behaviour change; callers move), `fim/client.py`, `leika/client.py`, `pvog/client.py`, `govdata/ckan.py`, `worker/{drain,run,handler_table,llm_setup,enrich_metadata,batch}.py`, `harvest/pvog.py`, `browser/probe_cli.py`, `extract/llm/evaluation/command.py` (`_runtime` only).

Tests to update: call sites of `run_worker_drain` and `run_recorded_drain` (`test_enrich_metadata_worker.py` x4, `test_llm_extract_stops.py` x5, `test_render_worker.py` x2, `test_worker_drain.py` x2, `test_extract_wiring.py`, `test_extract_worker.py`, `test_fetch_enqueue.py`, `test_llm_wiring.py`, `test_robots.py`); a helper `deps_for(client, fetcher, **overrides)` in `tests/` keeps the edits mechanical. `prepare_llm`/`_runtime` users: `llm_worker_fakes.py`, `test_llm_eval_command.py`. `FimSteckbriefClient` and `LeikaStammtextClient` users: `test_fim_leika_enrich.py`.

## TDD loop

### Red

1. **Characterise the commands through `main()` first (green).** Extend `test_govdata_cli.py`, `test_govdata_fetch.py`, `test_pvog_cli.py`, `test_fim_leika_enrich.py`, `test_worker_drain.py` so each pins stdout, stderr and the exit code for: success, no mappable rows, a mapping skip (`skip row: ...`), an API refusal (exit 1, nothing printed today), a source failure (`govdata fetch failed: ...`, bare PVOG message), fim/leika fixture mismatch, fim/leika missing key, drain with and without browser/llm settings (exit 2 for `BrowserSetupError`/`LlmSetupError`), drain report JSON. Name pattern: `test_pvog_run_posts_nothing_when_a_late_page_fails`, `test_govdata_fetch_posts_each_page_as_it_arrives`, `test_fim_probe_user_agent_comes_from_bot_settings`.
2. **New unit tests for the new objects (fail: modules do not exist).**
   - `test_ingest_returns_counts_and_skips_for_each_source` (happy, three sources), `test_ingest_raises_nothing_to_ingest_when_every_row_is_skipped`, `test_ingest_propagates_machine_api_error`.
   - `test_run_enrich_posts_entity_then_claims_for_fim_and_leika` (happy, same assertions for both enrichers through the one function), `test_run_enrich_raises_missing_lookup_key_with_the_existing_message`, `test_run_enrich_raises_enrich_fetch_error_on_fixture_mismatch`, `test_post_enrichment_stops_at_the_first_api_error_after_the_entity`.
   - `test_page_budget_*` (see above), `test_page_budget_admit_trims_to_remaining_records`, `test_page_budget_zero_pages_is_exhausted`.
   - `test_drain_options_policy_uses_llm_batch_size_when_llm_extract_is_drained`, `test_drain_options_invalid_bounds_raise_value_error` (negative: `max_tasks=0`, `neuron_budget` missing for `llm_extract`).
   - `test_run_drain_returns_the_report_and_prints_nothing` (`capsys` empty).
   - `test_leaf_hints_from_payload_matches_the_old_five_functions` (parametrised over mapped, ambiguous, bundled and unmapped leaf codes plus no code).
   - `test_build_model_client_wires_throttle_and_credentials`, `test_build_model_client_without_credentials_raises_value_error`.
   - `test_settings_declare_cloudflare_account_id_once` (`IngestSettings.model_fields` alias check) and `test_no_module_outside_config_reads_os_environ` (greps the package).
   - `test_operations_import_no_cli_or_output_library` (imports each `operations` module, asserts `argparse`, `typer`, `rich` are not in its direct imports, and `capsys` stays empty for every operation test).
3. Run the narrow suite: new tests fail on import, characterisation tests pass.

### Green

1. `page_budget.py`, then switch the two crawl clients (existing PVOG and CKAN tests stay green).
2. Settings changes; `fim probe` and `browser probe` on `BotSettings`.
3. `FimSteckbriefClient`/`LeikaStammtextClient` split into source classes; `Enricher`, `post_enrichment`, `run_enrich`; point `cli._fim_enrich`, `cli._leika_enrich` and the worker handler at them.
4. `catalogue.py` sources and `ingest`; point `_govdata_run`, `_govdata_fetch`, `_pvog_run` at them. The handlers shrink to parse, call, print.
5. `DrainDeps`, `run_worker_drain(deps, policy)`, `DrainOptions`, `run_drain`, `build_model_client`; update test call sites.
6. `LeafHints` and `PvogDrafter`.

### Refactor

Judge by responsibility, not line count: after the move `cli.py` should contain parsing, one call and rendering per handler, and nothing it imports should be a private name (`_map_govdata_record`, `_post_catalogue_batches` are gone after I1 and I2). Check for: the rule of three on result-printing code (three handlers print `skip row:`; the helper belongs in the command layer, I4), one nesting level in the loops that moved, `ingest` free of `isinstance` on source type, parameter lists of at most three (objects otherwise), no new `Any`, no one-line wrappers left (`_pvog_vocabulary` is a candidate: if it only calls the client and joins, leave it for I4's command). Docstrings: every new public class and function gets an imperative docstring (pydocstyle `D`, `pep257`), and the files rewritten here drop their `D`/`ANN401` baseline entries. Report `Refactor gate: smells found -> ..., refactorings applied -> ...` with before and after: lines of `cli.py` (540 today), longest parameter list in `worker/` (11 to 2), `os.environ` reads outside config (1 to 0), FIM URL literals (5 to 1), `MIN_INTERVAL_SECONDS` definitions (4 to 1).

## Verification

```bash
cd apps/discovery-ingest
uv run ruff format --check . && uv run ruff check . && uv run mypy discovery_ingest
uv run pytest tests/test_operations_catalogue.py tests/test_operations_enrich.py tests/test_operations_drain.py \
  tests/test_page_budget.py tests/test_ingest_settings.py tests/test_pvog_harvest.py tests/test_pvog_client.py \
  tests/test_govdata_ckan.py tests/test_govdata_cli.py tests/test_govdata_fetch.py tests/test_pvog_cli.py \
  tests/test_fim_leika_enrich.py tests/test_enrich_metadata_worker.py tests/test_worker_drain.py \
  tests/test_worker_run.py tests/test_llm_wiring.py tests/test_llm_eval_command.py
uv run pytest
cd ../..
./ci.sh
```

Contract spot check: `python -m discovery_ingest worker drain --help` and `govdata fetch --help` print the same text as on `main` (the full golden-help suite is created in I4 and must already pass here).

## Parallel notes

Batch 3 siblings: I5 (read-only against the API schema; edits ingest tests only) and B5/B7 (API). I3 runs after I1 and I2 are merged, so it starts from their client facade and typed models.

- **I5** adds contract tests under `tests/` and reads `schemas.py`, `artifacts.py`, `mentions.py`, `edges.py`, `emit_models.py`, `budget_models.py`, `candidate_sources.py`. I3 must not edit those model modules; if a model needs a field for the operations layer, add it in a new module.
- **I4** starts after I3: it replaces argparse in `cli.py`, removes the `*_cli.py` modules and moves rendering into `cli/`. I3 leaves `register_*_parser` functions untouched and keeps `cli._COMMANDS` working so the CLI stays runnable between chapters.
- **T1 step 2** docstring slices touching `worker/`, `harvest/`, `fim/` must have landed or be rebased over.
- **Must not be touched:** `apps/api/**`, `client/` (I1), the typed models of I2 beyond using them, `.github/**`, `pyproject.toml`, the command names, flags and exit codes.
