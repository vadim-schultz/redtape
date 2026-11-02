---
name: "A3 — Ingest run lifecycle"
overview: "A drain run is always closed, whatever stops it; crawl clients raise their own typed error for transport, status and JSON failures; every httpx.Client the drain creates is closed."
todos:
  - id: pin
    content: "Pin the current run, PVOG and CKAN behaviour; red tests for unclosed runs, raw httpx/ValueError escapes and leaked clients"
    status: pending
  - id: run
    content: "recorded_run context manager closes the run on any exception, including KeyboardInterrupt"
    status: pending
  - id: crawl
    content: "One _get_json per crawl client wrapping httpx.HTTPError and ValueError in the client error"
    status: pending
  - id: close
    content: "ExitStack owns the LLM http client and the browser client; browser client gains close()"
    status: pending
isProject: false
---

# A3 — Ingest run lifecycle

**Repo:** `redtape` · **Branch:** `fix/ingest-run-lifecycle` · **Status:** planned

**Depends on:** none (batch 1) · **Architecture:** [../00-audit-report.md](../00-audit-report.md) (C3, C5, C4 crawl-client part) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-codebase-audit` · **Release branch:** `main`

**Touches:** `ingest/worker/{run,llm_setup}.py`, `ingest/pvog/client.py`, `ingest/govdata/ckan.py`, `ingest/browser/client.py`. **After:** none.

**Findings:** C3, C5, C4 (crawl-client part; the CLI printing part is I4).

## Goal

1. **C3.** `worker drain` opens a run (`POST /machine/runs`) and always finishes it. Today `run_recorded_drain` finishes the run as failed only for `DiscoveryMachineApiError` (`worker/run.py:73-75`); a handler bug, `httpx.HTTPError`, `pydantic.ValidationError` or Ctrl-C leaves the run `running` forever.
2. **C4 (crawl clients).** `PvogClient` and `GovDataCkanClient` raise only their own error type (`PvogClientError`, `GovDataCkanError`) for transport failures, HTTP statuses and invalid JSON. Today a `httpx.ConnectError` or `ValueError` escapes (`pvog/client.py:100-115`, `govdata/ckan.py:82-95`) and the CLI's `except PvogClientError` / `except GovDataCkanError` (`cli.py:109`, `156`, `357`) never sees it, so the operator gets a traceback.
3. **C5.** Every `httpx.Client` the drain creates is closed: the LLM client built in `worker/llm_setup.py:81`, the Cloudflare browser client (`browser/client.py:46`), and the one in the `llm eval` runtime (`extract/llm/evaluation/command.py:57`).

Behaviour that does not change: command names, flags and exit codes of `python -m discovery_ingest` (the exit code for a connection failure is 1 before and after: before as an uncaught exception, after as a printed message). The CLI's own `except DiscoveryMachineApiError: return 1` branches that print nothing (`cli.py:88`, `168`, `202`, `331`; the audit cites 68, 132, 182, 293, which are stale) are deliberately **not** touched here: the Typer rewrite (I4) replaces them with one central error handler. Retries and backoff are an open seam (see gaps-and-decisions): this chapter wraps errors only.

## Files (verified)

| File | Lines | Change |
| --- | --- | --- |
| `apps/discovery-ingest/discovery_ingest/worker/run.py` | `run_recorded_drain` 47-77 | new `recorded_run` context manager; `run_recorded_drain` uses it |
| `apps/discovery-ingest/discovery_ingest/pvog/client.py` | `PvogClientError` 23, `_fetch_page` 100-115 | `_fetch_page` becomes the single `_get_json` wrapper (see below) |
| `apps/discovery-ingest/discovery_ingest/govdata/ckan.py` | `GovDataCkanError` 16, `_fetch_json` 82-89, `_get` 91-95 | one `_get_json` wraps transport, status and JSON failures |
| `apps/discovery-ingest/discovery_ingest/worker/llm_setup.py` | `prepare_llm` 74-83 (client at 81) | takes an `ExitStack` that owns the `httpx.Client` |
| `apps/discovery-ingest/discovery_ingest/browser/client.py` | `__init__` 32-48 (client at 46) | add `close()`, `__enter__`, `__exit__`; close only a client this class created |
| `apps/discovery-ingest/discovery_ingest/cli.py` | `_drain_and_print` 265-281 (the only edit) | one `with ExitStack()` around `prepare_*` and `run_recorded_drain` |
| `apps/discovery-ingest/discovery_ingest/extract/llm/evaluation/command.py` | `_runtime` 53-59, `llm_eval` 138 | `_runtime` receives the `ExitStack` |
| `apps/discovery-ingest/tests/test_llm_eval_command.py` | line 44 | the seam `lambda _settings, _model: runtime` gains a third parameter |

Two files are outside the table's Touches: `cli.py` (call site only; no other batch-1 chapter edits it, I4 rewrites it later after I3) and `extract/llm/evaluation/command.py` (I2 touches `extract/llm` in batch 2, after A3 merges). Report both in the PR. `worker/browser_setup.py` is unchanged: `prepare_browser` already returns the client, the caller enters it into the stack.

Other `httpx.Client(...)` sites are already scoped correctly and stay as they are: `api_client.py` (15 `with` blocks), `worker/fetcher.py:117`, `health.py:42`, `fim/client.py:41`, `leika/client.py:38`, `extract/llm/probe_cli.py:59`, `browser/probe_cli.py:53`. Their consolidation is I1.

## Design

### `recorded_run`

```python
@contextmanager
def recorded_run(client: DiscoveryMachineClient) -> Iterator[RecordedRun]:
    """Open a run and guarantee that it is finished, as failed when the body leaves without finishing it."""
```

`RecordedRun` holds `run_id` and `finish(body)`; `finish` marks the run as attempted before it calls `client.finish_run`, so the cleanup path never sends a second finish for the same run. On exit:

- body finished the run: nothing more to do;
- body raised (`BaseException`, so `KeyboardInterrupt` and `SystemExit` too): send `_failed(detail)` (`stop_reason="error"`, detail capped by the existing `_MAX_ERROR_DETAIL`), swallow a failure of that cleanup call (`DiscoveryMachineApiError`, `httpx.HTTPError`, logged at warning), and re-raise the original exception;
- body returned without finishing (a programming error): send `_failed("the drain returned without finishing the run")`.

Detail text: `str(err)` for `DiscoveryMachineApiError` (unchanged, so the existing assertion `"500" in error_detail` holds), `f"{type(err).__name__}: {err}"` for everything else, `"interrupted"` for `KeyboardInterrupt`.

```python
with recorded_run(client) as run:
    report = run_worker_drain(client, fetcher, policy, browser=browser, llm=llm, after_extract=after_extract, llm_enqueue=llm_enqueue)
    run.finish(_finish_request(report))
return report.model_copy(update={"run_id": run.run_id})
```

`start_run` failing still raises before any run exists and sends no finish (existing test).

### `_get_json` for the crawl clients

One private method per client (two copies, below the rule of three; the shared transport is I1/I2 when FIM and Leika join):

- PVOG (`_fetch_page` keeps its name and callers at lines 57 and 72, 97): GET through the injected client or a scoped `httpx.Client(trust_env=True, timeout=60.0)`; `httpx.HTTPStatusError` -> `PvogClientError("PVOG Suchdienst HTTP <status>")` (message unchanged); any other `httpx.HTTPError` -> `PvogClientError("PVOG Suchdienst request failed: <ExcName>: <msg>")`; `ValueError` from `.json()` -> `PvogClientError("PVOG Suchdienst returned invalid JSON")`; a non-object payload -> `PvogClientError("expected JSON object from PVOG Suchdienst")` (today a bare `ValueError`, line 114).
- CKAN: the same three wraps inside `_get_json` (timeout 120 s, `GovDataCkanError`), merging today's `_fetch_json` and `_get`; the existing messages `GovData HTTP <status> for <url>` and `expected JSON object from <url>` are kept.
- Both chain the cause (`raise ... from err`). The URL in a message is already a public endpoint; nothing secret is in the query. Do not add the response body.

### Closing clients

- `CloudflareBrowserClient`: `self._owns_http = http is None`; `close()` closes the client only when owned; `__enter__` returns `self`; `__exit__` calls `close()`.
- `prepare_llm(settings, client, stack: ExitStack)`: `http = stack.enter_context(httpx.Client(trust_env=True))`. Three parameters, no new one.
- `_drain_and_print`: `with ExitStack() as stack:`, `browser = stack.enter_context(prepare_browser(...)) if policy.drains_browser_kinds else None`, `llm = prepare_llm(settings, client, stack) if policy.drains_llm_kinds else None`. The stack closes on every path, including `LlmSetupError` raised after the browser opened.
- `llm eval`: `llm_eval` wraps its body in `with ExitStack() as stack:` and `_runtime(settings, model, stack)` enters the `httpx.Client` there.

## TDD loop

All tests are in `apps/discovery-ingest/tests`; use `httpx.MockTransport` and the `monkeypatch` patterns already in `tests/test_worker_run.py` (`_patch_transport`, `run_stub.run_response`) and `tests/test_pvog_client.py` / `tests/test_govdata_ckan.py`.

### Characterise first (green now)

- `test_worker_run_records_start_and_succeeded_finish_with_counts`, `..._reports_batch_limit_when_the_batch_is_full`, `..._marks_run_failed_when_claim_api_errors`, `..._does_not_drain_when_run_cannot_start` (`test_worker_run.py:48,71,100,119`).
- `test_pvog_client_iterates_personal_matter_codes_with_dedupe`, `..._stops_at_max_pages_budget`, `..._paginates_until_service_descriptions_last` (`test_pvog_client.py:93,109,124`); `test_ckan_client_requests_scoped_leistungen_page`, `test_ckan_client_raises_when_package_has_no_leistungen_resource` (`test_govdata_ckan.py:39,72`).
- Browser client behaviour (`test_browser_client.py`, whole file) passes an injected `http=`; it must still pass and prove the injected client is not closed by the wrapper.

### Red (written first)

**Run lifecycle** (`tests/test_worker_run.py`; monkeypatch `discovery_ingest.worker.run.run_worker_drain`, call `run_recorded_drain` with a real `DiscoveryMachineClient(API_BASE, "k")` over the mock transport, capture finishes):

1. Parametrised `test_the_run_is_finished_as_failed_when_the_drain_raises` over `ValueError("handler bug")`, `httpx.ConnectError("boom")`, a real `pydantic.ValidationError`, and `KeyboardInterrupt()`: exactly one finish with `status == "failed"`, `stop_reason == "error"`, `error_detail` containing the exception type name (`"interrupted"` for Ctrl-C), and the original exception re-raised (`pytest.raises`). Fails today (zero finishes).
2. `test_the_original_error_wins_when_closing_the_run_also_fails` — finish endpoint answers 503: the caller still sees the original `ValueError`, and the finish endpoint was called once (never twice).
3. `test_a_drain_that_returns_without_finishing_leaves_a_failed_run` — unit test of `recorded_run` with an empty body: one failed finish.
4. `test_an_api_error_keeps_its_message_in_the_failed_run` — `"500" in error_detail` (unchanged behaviour, now through the new path).
5. Happy path stays `test_worker_run_records_start_and_succeeded_finish_with_counts` (one finish, `succeeded`).

**Crawl clients**

6. `test_pvog_client_raises_its_own_error_on_a_connection_failure` (`MockTransport` handler raises `httpx.ConnectError`) -> `PvogClientError`, `__cause__` is the `ConnectError`.
7. `test_pvog_client_raises_its_own_error_on_invalid_json` (body `not json`) and `..._on_a_non_object_payload` (body `[]`) -> `PvogClientError`, not `ValueError`.
8. `test_pvog_client_keeps_the_http_status_message` (404 -> message `PVOG Suchdienst HTTP 404`): negative path that proves the old message survives.
9. `test_ckan_client_raises_its_own_error_on_a_connection_failure`, `..._on_invalid_json`, `..._on_a_non_object_payload`, and `test_ckan_client_keeps_the_http_status_message` (`GovData HTTP 500 for <url>`).
10. CLI-level, one test per client, through `main(...)`: `test_govdata_fetch_prints_the_error_and_exits_1_on_a_connection_failure` and `test_pvog_vocabulary_prints_the_error_and_exits_1_on_a_connection_failure` assert `exit_code == 1`, the message on stderr (`capsys`), and no traceback. They pin the unchanged exit code.

**Resources**

11. `test_the_browser_client_closes_only_a_client_it_created` — constructed without `http=`: after `close()` its client `is_closed`; constructed with `http=injected`: after `close()` the injected client is still open.
12. `test_the_browser_client_is_a_context_manager` (closes on exit, including on an exception).
13. `test_a_drain_closes_the_llm_http_client_on_success_and_on_failure` — in `tests/test_cli_worker_llm.py`, replace `discovery_ingest.worker.llm_setup.httpx.Client` with a subclass that records instances; run the existing `DRAIN` happy path and the existing rejected-token failure path; assert every recorded instance `is_closed` afterwards. Fails today.
14. `test_a_drain_closes_the_browser_client_when_llm_setup_refuses` — browser kinds plus an LLM kind with missing settings: `LlmSetupError` exit code is unchanged and the browser client created before it is closed.
15. `test_llm_eval_closes_its_http_client` — `tests/test_llm_eval_command.py`, using the updated seam.

Run the narrow suite and confirm 1, 2, 3, 6, 7, 9 (three of the four), 11-15 fail for the stated reasons while 4, 5, 8, 10 and the characterisation set pass.

### Green

1. `recorded_run` and `run_recorded_drain` as designed.
2. `_get_json` in PVOG and CKAN; keep every existing message.
3. `close`/context manager on `CloudflareBrowserClient`; `prepare_llm` with the stack; the `_drain_and_print` and `llm_eval` call sites; fix the `_runtime` seam in the one test that patches it.
4. Re-run the narrow suite until green, then the whole ingest suite.

### Refactor

**Refactor gate.** Smells to look for: the same `try/except httpx...` block twice (PVOG and CKAN; two copies is below the rule of three: keep both private, record in the PR that FIM and Leika (I1/I2) make four), a context manager that also formats the failure text (keep `_failed` where it is; the manager only decides *when* to finish). Judge by responsibility, not size: `recorded_run` = "a run is always closed", `run_recorded_drain` = "drain between open and close", neither "and". Do not extract a method just to shorten `_fetch_page`. One nesting level; `run_recorded_drain` keeps its seven parameters (L13 owns the object that replaces them in I3); `prepare_llm` stays at three. New public symbols (`recorded_run`, `RecordedRun`, `close`, `__enter__`, `__exit__`) have docstrings in imperative mood stating intent; the rewritten files (`run.py`, `llm_setup.py`, `pvog/client.py`, `govdata/ckan.py`, `browser/client.py`) get their missing docstrings (T1 baseline for `worker/**` is removed by its slice, not here). No new `Any`: the PVOG and CKAN payloads stay `dict[str, Any]` (baseline entries owned by I2), no `cast`, no `# type: ignore`.

## Verification

```bash
cd apps/discovery-ingest
uv run ruff format --check . && uv run ruff check . && uv run mypy discovery_ingest
uv run pytest tests/test_worker_run.py tests/test_pvog_client.py tests/test_pvog_cli.py tests/test_govdata_ckan.py tests/test_govdata_cli.py tests/test_browser_client.py tests/test_cli_worker_llm.py tests/test_llm_eval_command.py tests/test_worker_drain.py
uv run pytest -q
cd ../..
./ci.sh
```

The workflows `.github/workflows/discovery-*.yml` must keep passing unchanged: run `python -m discovery_ingest worker drain --help` and `python -m discovery_ingest pvog --help` before and after and diff the output (flags and exit codes are identical). Report `Refactor gate: smells found -> ..., refactorings applied -> ...` and the narrow-suite before/after counts in the PR.

## Git workflow

```bash
git checkout feat/plans-codebase-audit && git pull
git checkout -b fix/ingest-run-lifecycle
```

```text
test(ingest): pin run lifecycle and crawl client errors, red for unclosed runs and leaked clients
fix(ingest): close the run on any drain failure and wrap crawl client errors
fix(ingest): close the llm and browser http clients through an ExitStack
```

Open the chapter PR into `feat/plans-codebase-audit`, not `main`.

## Parallel notes

Runs in batch 1 beside T1 step 1, T2, T3, A1, A2, A4, B1, B6, W1, W2; none of them touch `apps/discovery-ingest` except the T1/T2 config files. Files this chapter must not touch: everything in `apps/api` and `apps/web`, `api_client.py` (I1), `fim/`, `leika/`, `enrich.py`, `extract/llm/*` other than `evaluation/command.py` (I2), `worker/` files other than `run.py` and `llm_setup.py` (I3 later), `cli.py` outside `_drain_and_print` (I4), `pyproject.toml` (T1, T2; this chapter adds no dependency). I1, I2 (batch 2) and I3 (batch 3) rebase onto this chapter: `run_recorded_drain` and `prepare_llm` keep their names, so their imports do not move.
