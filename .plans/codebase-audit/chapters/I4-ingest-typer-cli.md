---
name: "Chapter I4 — Ingest Typer CLI"
overview: "Replace the argparse CLI of discovery-ingest (cli.py plus eight register_* modules) with a hierarchical Typer app modelled on rsb-test-storage-client, behind a contract test suite written first against argparse and kept green after the migration."
todos:
  - id: contract-first
    content: "Pin the 20 commands (flags, defaults, exit codes, stdout formats, help snapshots, workflow invocations) against the argparse CLI"
    status: pending
  - id: typer-app
    content: "Add typer>=0.12; build cli/ package with one commands.py per group, a lazy ctx.obj and one error handler"
    status: pending
  - id: remove-argparse
    content: "Delete cli.py, the *_cli.py/register_* modules and cli_errors.py; keep main(argv) -> int and python -m discovery_ingest"
    status: pending
  - id: breaking-notes
    content: "Document what cannot be preserved exactly in the PR and the README"
    status: pending
isProject: false
---

# Chapter I4 — Ingest Typer CLI

**Repo:** `redtape` · **Branch:** `refactor/ingest-typer-cli` · **Status:** planned

**Depends on:** I3 · **Architecture:** [../00-audit-report.md](../00-audit-report.md) D5, C4 (CLI part) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-codebase-audit` · **Release branch:** `main`

**Touches:** new `ingest/cli/`, removal of `ingest/cli.py` and `*_cli.py` modules, `ingest/pyproject.toml` (rollout table). The test migration listed under "Tests to migrate" also touches `ingest/tests`.

**Findings:** D5, C4 (CLI part: API refusals that exit 1 without a message).

**This is the contract chapter.** Settled decisions: U1 (follow `rsb-test-storage-client`), D5 (accept Typer, pin `typer>=0.12`, keep `python -m discovery_ingest` as the supported entry point). The CLI is called by `.github/workflows/discovery-*.yml`, `.github/workflows/platform-maintenance.yml` and by 8 files under `docs/operations/`, one under `docs/discovery/` and the README. Command names, flags, defaults, exit codes and machine-read stdout formats do not change.

## Goal

`cli.py` (540 lines, `_build_parser` 139 lines, hand-synced `_COMMANDS` table) and the eight `register_*` modules are replaced by a `discovery_ingest/cli/` package: one Typer sub-app per command group, each command a thin wrapper that reads options, calls a method on the client facade (I1) or a function in `operations/` (I3), and renders the typed result. Nothing in `cli/` contains flow logic; nothing outside `cli/` prints.

Reference implementation in `/home/schult_v/projects/rsb-test-storage-client/src/rsb_test_storage_client/`:

| Pattern | File |
| --- | --- |
| root app, `add_typer` per group, root callback builds `ctx.obj` | `cli/main.py` (`app = typer.Typer(...)`; `app.add_typer(campaigns_app, name="campaigns")`; `set_base_url` callback sets `ctx.obj = {"base_url": ..., "api_client": APIClient(...)}`) |
| group package exports one sub-app | `cli/campaigns/__init__.py` (`from .commands import campaigns_app`) |
| group callback prints help when no subcommand; commands are thin wrappers that call `ctx.obj["api_client"].campaigns.<method>` and render | `cli/campaigns/commands.py` (`campaigns_callback`, `list_campaigns`, `get_campaign`) |
| facade the commands call | `client/api_client.py`, `client/campaigns_api.py` (built in I1) |

Deliberate differences from the reference: (1) the facade in `ctx.obj` is **lazy**, because `browser probe`, `llm probe`, `fim probe` and every `--help` must work without `DISCOVERY_API_URL` and `DISCOVERY_API_KEY` (the probe workflows pass neither); (2) a group without a subcommand prints help and exits **2**, not 0, to keep today's exit code; (3) machine-read output (TSV, JSON, key=value lines) is written with `typer.echo`, never with `rich`.

## Part 1. Today's commands (from the real parser definitions)

Verified by walking `_build_parser()` (`cli.py:402-540` plus `register_*`) and reading each handler. Group order in the parser: `govdata, pvog, fim, leika, worker, candidates, budget, browser, llm, artifacts, capture`. There are no positional arguments and no short options except argparse's `-h`/`--help`. `_COMMANDS` (`cli.py:378-399`) maps 20 `(group, command)` pairs.

`UUID`, `int`, `float` are parsed by argparse (`type=`); "custom" means a `type=` function that raises `ArgumentTypeError`. Exit code 1 is also what an uncaught exception gives (Python traceback), for example a missing `DISCOVERY_API_URL` (`pydantic.ValidationError` from `load_ingest_settings()`); only `llm eval` catches it and exits 2.

| Group command | Flags: type, default, required | stdout | Exit codes |
| --- | --- | --- | --- |
| `govdata run` | `--input` str, required; `--jurisdiction-id` UUID, required | nothing | 0 ok; 1 `no mappable GovData rows` (stderr) or API refusal (silent today, C4) |
| `govdata fetch` | `--jurisdiction-id` UUID, required; `--max-pages` int, 150; `--page-size` int, 100; `--max-records` int, none | nothing | 0; 1 `govdata fetch failed: {err}`, API refusal (prints the error), or `no mappable GovData rows` |
| `pvog run` | `--jurisdiction-id` UUID, required; `--max-pages` int, none | nothing | 0; 1 PVOG error (printed bare), `no mappable PVOG rows`, API refusal (silent) |
| `pvog vocabulary` | none | personalMatters leaf codes, one per line | 0; 1 PVOG error (bare message) |
| `fim enrich` | `--catalogue-service-id` UUID, required; `--catalogue-export` str, required; `--input` str, required | nothing | 0; 1 row not found / no steckbrief key / `fim fetch failed: ...` / API refusal (silent) |
| `fim probe` | `--keys` custom (comma separated 14-digit keys), required; `--base-url` str, `https://fimportal.de` | one line per key (`{key} status=200 keys=a,b,...`) plus `gate: N/M returned 200 with leistungsschluessel (passed\|failed)` | 0 gate passed; 1 gate failed |
| `leika enrich` | same three flags as `fim enrich` | nothing | 0; 1 row not found / `catalogue row missing redaktion_id and leistung_id` / `leika fetch failed: ...` / API refusal (silent) |
| `worker drain` | `--max-tasks` int, none (resolves to 5 when `llm_extract` is drained, else 50); `--max-batches` int, 1; `--time-budget-seconds` float, none; `--browser-budget-seconds` float, 570.0; `--neuron-budget` float, none; `--kinds` custom (comma separated task kinds), `fetch_url,enrich_metadata,harvest_payload,extract_page` | **exactly one line**: the `DrainReport` as JSON (`json.dumps(report.model_dump(mode="json"))`) | 0 `succeeded`; 1 `succeeded=false` or API refusal (`drain failed: {err}` on stderr); 2 invalid bounds (`invalid drain bounds: ...`); `BrowserSetupError`/`LlmSetupError` print their message and exit with their code (2 missing settings, 1 storage/ledger/taxonomy not ready) |
| `candidates emit` | exactly one of `--id` UUID (repeatable) or `--all-staged` flag (mutually exclusive, one required); `--min-mentions` int, 0; `--limit` int, 10; `--dry-run` flag | the preview or emit report, one line per candidate | 0; 1 `emit failed: {err}`; 2 `invalid selection: ...` |
| `candidates page` | `--candidate-id` UUID, required; `--out` Path, none | one line per procedure: `{catalogue_service_id} {source_url} {host} has_screenshot=true\|false`; `--out` writes `<id>.txt` files | 0; 1 no procedures, a missing snapshot, or API refusal (`candidates page command failed: {err}`) |
| `candidates curate` | `--file` str, required; `--dry-run` flag; `--check-pages` / `--no-check-pages` boolean-optional, default on | per candidate `{title} tags=.. edges=..`, then `mentions_created=.. mentions_updated=.. edges_created=.. edges_updated=.. edges_skipped=.. unknown_codes=.. dry_run=true\|false` | 0; 1 a post was refused; 2 `curation refused: ...` (file or validation problems, stderr); 1 API refusal (`candidates curate command failed: ...`) |
| `budget show` | `--resource` RESOURCE, repeatable; `--require-remaining RESOURCE=N` custom, repeatable; `--strict` flag | one line: `{"items": [...]}` JSON | 0 ok, or ledger unreachable without `--strict`; **3** a required resource is short or exhausted (`budget short or exhausted: ...` on stderr); **4** ledger unreachable with `--strict`; 1 API refusal (`budget command failed: ...`) |
| `budget report-minutes` | `--minutes` custom positive int, required | nothing | 0 (also when the ledger is unreachable; stderr says so); 1 API refusal |
| `browser probe` | `--url` repeatable; `--error-url` repeatable; `--variant` repeatable, choices `ua-echo, content, content-lean, snapshot-md, screenshot-jpeg, screenshot-png, snapshot-shot`; `--max-browser-seconds` float, 240.0 | probe table lines | 0; 1 Cloudflare refused; 2 `missing environment: ...` |
| `llm eval` | `--model` str, required; `--prompt-version` str, `ext-5` (current `PROMPT_VERSION`); `--limit` int, none; `--out` str, none; `--neuron-budget` float, 4000.0; `--gold-dir` str, `<repo>/apps/discovery-ingest/tests/fixtures/gold`; `--cache-dir` str, `.llm-eval-cache` | results table (secrets scrubbed); `--out` writes JSON | 0; 1 run stopped early; 2 bad setup or missing environment |
| `llm requeue` | `--host` str, none; `--limit` custom 1-200, 50; `--dry-run` flag | one line: `key={input_key} pages=N queued=N already_queued=N failed=N` plus ` dry_run=true` | 0; 1 any enqueue failed or API refusal; 2 `LLM_MODEL` unset |
| `llm probe` | `--model` repeatable, default `[LLM_MODEL]`; `--fixture` str, required; `--max-neurons` float, 900.0 | probe table lines | 0; 1 Cloudflare refused; 2 missing settings, fixture or model |
| `artifacts list` | `--host` str, required; `--limit` custom positive int, 20; `--kind` choices `html_snapshot, screenshot`, `html_snapshot` | **TSV, four tab-separated columns** per artifact: `{id}\t{kind}\t{byte_size}\t{source_url}` (the fixture-capture workflow reads them with `IFS=$'\t' read -r id _kind _size _url`) | 0; 1 API refusal (`artifacts command failed: ...`) |
| `artifacts download` | `--id` UUID, required; `--out` Path, required | `wrote {out} ({n} bytes)` | 0; 1 API refusal |
| `capture requeue` | `--host` str, none; `--limit` custom 1-200, 50; `--dry-run` flag; `--service-id` UUID, repeatable, at most 20 (the 21st is refused before any call) | one line: `pages=N queued=N already_queued=N failed=N` plus ` dry_run=true` | 0; 1 any enqueue failed or API refusal (`capture requeue command failed: ...`) |

Top level behaviours to preserve:

| Situation | Today |
| --- | --- |
| `python -m discovery_ingest` with no command, or a group alone (`... worker`) | prints the **top-level** help to stdout, exit **2** (`cli.py:69-71`) |
| `-h` / `--help` at any level | usage to stdout, exit 0 |
| unknown command, unknown flag, missing required flag, invalid value | usage plus `error: ...` on stderr, exit 2 |
| entry point | `python -m discovery_ingest` (`__main__.py`: `raise SystemExit(main())`); there is no `[project.scripts]` |
| help of `candidates curate` | carries the multi-line `REVERSAL` epilog (SQL that undoes a curation) printed verbatim (`RawDescriptionHelpFormatter`) |

### Who relies on what

| Consumer | Contract it relies on |
| --- | --- |
| `discovery-extract.yml:78`, `discovery-drain.yml:77`, `discovery-render.yml:91`, `discovery-screenshot.yml:87`, `discovery-llm.yml:99` | `budget show --resource R [--resource R] --require-remaining R=N [...] \|\| code=$?`; exit **3** skips the job, other non-zero fails it |
| `discovery-extract.yml:101`, `discovery-drain.yml:100`, `discovery-render.yml:115`, `discovery-screenshot.yml:111`, `discovery-llm.yml:116` | `worker drain` flags `--max-tasks --max-batches --time-budget-seconds --kinds --browser-budget-seconds --neuron-budget`; stdout teed to `drain-report.json` and read with `jq`/Python (one JSON object, nothing else on stdout) |
| `discovery-*.yml` `report-minutes` steps | `budget report-minutes --minutes N` |
| `discovery-browser-probe.yml:75`, `discovery-llm-probe.yml:65`, `discovery-fim-probe.yml:47` | probes tee'd to a file, `PIPESTATUS[0]` read; they run without `DISCOVERY_API_URL` and `DISCOVERY_API_KEY` |
| `discovery-fixture-capture.yml:63-66` | `artifacts list` TSV (4 columns) and `artifacts download --id --out` with `< /dev/null` |
| `platform-maintenance.yml:98-112` | `govdata fetch --jurisdiction-id --max-pages --page-size`; `pvog run --jurisdiction-id --max-pages` |
| `docs/operations/{candidate-view,discovery-online,discovery-layer,extraction-operator-checklist,crawlers-operator-checklist,scheduled-jobs,gha-budget,crawlers-post-deploy-human-steps}.md`, `docs/discovery/government-data-sources.md`, `apps/discovery-ingest/README.md` | the examples: `govdata run`, `pvog run`, `fim enrich`, `leika enrich`, `fim probe`, `candidates emit/page/curate`, `capture requeue`, `llm requeue/probe/eval`, `artifacts list/download`, `browser probe`, `worker drain`, `budget show` |
| existing tests | `tests/test_{discovery_llm,llm_probe,browser,drain}_workflow*.py` parse the workflow files and (`test_discovery_llm_workflow.py:11,125`) call `_build_parser()` and `_drain_policy`; 23 test modules import from `discovery_ingest.cli` (22 call `main(argv)`; three use the private `_build_parser`/`_drain_policy`) |

## Part 2. Target `cli/` package

```text
discovery_ingest/
  __main__.py              raise SystemExit(main())          (unchanged)
  cli/
    __init__.py            exports app and main(argv=None) -> int
    main.py                root Typer app, add_typer per group, root callback
    context.py             CliContext: lazy settings, lazy DiscoveryIngestClient, closed on exit
    errors.py              the one error handler and the exit-code constants
    options.py             shared option objects and click parsers (jurisdiction id, kinds, requirement, keys)
    govdata/{__init__,commands}.py       run, fetch
    pvog/{__init__,commands}.py          run, vocabulary
    fim/{__init__,commands}.py           enrich, probe
    leika/{__init__,commands}.py         enrich
    worker/{__init__,commands}.py        drain
    candidates/{__init__,commands}.py    emit, page, curate
    budget/{__init__,commands}.py        show, report-minutes
    browser/{__init__,commands}.py       probe
    llm/{__init__,commands}.py           eval, requeue, probe
    artifacts/{__init__,commands}.py     list, download
    capture/{__init__,commands}.py       requeue
```

Group package shape is the reference's: `__init__.py` re-exports `<group>_app`; `commands.py` defines `<group>_app = typer.Typer(name=..., help=..., add_completion=False)`, a callback with `invoke_without_command=True` that prints help and raises `typer.Exit(2)` when no subcommand is given, and the commands. `main.py` registers them in today's order with `app.add_typer(govdata_app, name="govdata")` and so on.

### Thin-wrapper rules

1. A command function does exactly: take options, get the client or settings from `ctx.obj`, call one operation or resource method, render the result, `raise typer.Exit(code)` for a non-zero code. Setup of `argparse`-style parsing (`_task_kinds_arg`, `_requirement_arg`, `_steckbrief_keys_arg`, `limit_arg`, `_positive_int`) moves to click parser functions in `options.py` raising `typer.BadParameter` (exit 2, same as argparse).
2. No flow logic, no `httpx`, no direct `print` of anything but the rendered result: rendering is `typer.echo(...)` for machine output (stdout) and `typer.echo(..., err=True)` for diagnostics.
3. Rendering helpers shared by three or more commands live in `cli/options.py` or `cli/render.py` (rule of three): the `key=value` counts line (`llm requeue`, `capture requeue`), the JSON-line (`worker drain`, `budget show`), the TSV line (`artifacts list`). Do not create them earlier.
4. The operations the old `*_cli.py` modules still hold (artifact paging and `_line`, `_short_resources`, `Counts`/`enqueue_all`, `EvalCommand`, `run_probe` glue, `curation_command` stages) move to `operations/` or stay in their existing non-CLI modules (`candidate_emit.py`, `curation_*.py`, `latest_snapshots.py`) as functions that **return** data or lines; they lose their `argparse.Namespace` parameters (take explicit arguments or a small options model).
5. Help text: every `help=` string of today's `add_argument` calls is copied verbatim into the Typer option `help=`. The long `--kinds` and `--neuron-budget` help strings are also checked by `test_llm_eval_command.py:144-148` and stay character for character.

### Shared error handler (C4)

`cli/errors.py` replaces `cli_errors.failing_with_api_error`. One decorator `@handles_errors(label)` (or one callback on the root app) maps exceptions to a message on stderr and an exit code, in one place:

| Exception | Message on stderr | Exit |
| --- | --- | --- |
| `DiscoveryMachineApiError` | `{label} command failed: {err}` (the `str(err)` is already bounded and key-scrubbed by I1) | 1 |
| `BrowserSetupError`, `LlmSetupError` | the message | `err.exit_code` |
| `GovDataCkanError` | `govdata fetch failed: {err}` | 1 |
| `PvogClientError` | `{err}` | 1 |
| `EnrichError` family (I3) | the message | 1 |
| `NothingToIngest` (I3) | `no mappable {name} rows` | 1 |
| `ValueError` from `DrainPolicy`/`EmitSelection` validation | `invalid drain bounds: ...` / `invalid selection: ...` | 2 |

The four paths that return 1 with **no message** today (`govdata run`, `pvog run`, `fim enrich`, `leika enrich` on `DiscoveryMachineApiError`) now print `{label} command failed: {err}`; stdout and exit codes are unchanged, stderr gains one line. This is the only intended output change and is listed in the breaking-change notes. `label` values stay as today: `budget`, `artifacts`, `candidates page`, `candidates curate`, `llm requeue`, `capture requeue`, plus `emit`, `drain` for the two messages `cli.py` prints itself (`emit failed:`, `drain failed:`); the new labels are `govdata`, `pvog`, `fim`, `leika` (the same prefix style).

### `ctx.obj`

```python
@dataclass
class CliContext:
    def settings(self) -> IngestSettings: ...                      # load_ingest_settings(), cached
    @cached_property
    def client(self) -> DiscoveryIngestClient: ...                 # DiscoveryIngestClient.from_settings(self.settings()); closed via ctx.call_on_close
```

The root callback creates `ctx.obj = CliContext()` (no network, no settings read) and returns; `--help` and the probes never touch the facade. `fim probe` and `browser probe` use `load_bot_settings()` (I3). This keeps the reference's shape (`ctx.obj` holds what commands need) while honouring the "no API settings for probes" contract. Missing `DISCOVERY_API_*` for a command that needs them still fails with the same `pydantic.ValidationError` message as today (exit 1), or, new, a one-line `missing environment: DISCOVERY_API_URL, DISCOVERY_API_KEY` exit 2 as `llm eval` already does. Decide in the PR; if changed, list it in the notes. Default recommendation: keep exit 1 and the traceback-free one-line message.

### `main(argv)` and the entry point

`cli/__init__.py` exposes `main(argv: list[str] | None = None) -> int`: it calls the click command with `standalone_mode=False`, `prog_name="discovery_ingest"`, and converts `click.ClickException` to `e.show()` plus its exit code, `click.exceptions.Exit` to its code and `click.Abort` to 1. It **returns** the code and never raises `SystemExit`; `__main__.py` stays `raise SystemExit(main())`. Typer app settings: `add_completion=False` (no `--install-completion`/`--show-completion`), `pretty_exceptions_enable=False` (tracebacks stay plain), `context_settings={"help_option_names": ["-h", "--help"]}`, `no_args_is_help=False` (the callback decides, to exit 2).

## Part 3. Contract test plan (written BEFORE the migration)

Commit 1 and 2 of the implementation add the tests below against the argparse CLI and merge them (a separate PR into the loop branch is fine and recommended: it makes the contract reviewable without the migration noise). Everything stays green when the Typer CLI replaces argparse; the only edits at that point are the adapter swap and the explicitly listed test migrations.

| File | Content |
| --- | --- |
| `tests/cli_contract.py` | the table of Part 1 as data: `CommandSpec(group, name, options)` with `OptionSpec(flags, kind, required, default, choices, repeatable)` for all 20 commands |
| `tests/cli_adapters.py` | `describe(root) -> list[CommandSpec]`. Commit 1 holds only the argparse adapter (walks `_build_parser()` `_SubParsersAction` and `_actions`); the Typer migration adds the click adapter (walks `typer.main.get_command(app)`) and deletes the argparse one |
| `tests/golden/help/*.txt` | the `--help` text of the root, each group and each of the 20 commands, captured from argparse with `COLUMNS=100` |
| `tests/test_cli_contract.py` | the tests below |
| `tests/cli_invocations.py` | every real invocation from the workflows and docs, as argv lists with placeholders substituted (UUIDs, numbers, paths), with the source file and line in a comment |
| `tests/test_cli_invocations.py` | parse-only check of those argv lists, and a regex scan of the workflow files |
| `tests/test_cli_process.py` | a few `subprocess.run([sys.executable, "-m", "discovery_ingest", ...])` checks of the real process exit codes and streams |

Tests (names are the contract):

- `test_the_command_set_is_exactly_the_twenty_documented_commands`, `test_every_command_matches_its_contract_row[<group> <command>]` (flags, kind, required, default, choices, repeatable).
- `test_defaults_match_the_contract` (including `--prompt-version ext-5`, `--browser-budget-seconds 570.0`, `--max-pages 150`, `--limit 10` for emit, 50 for requeues, 20 for artifacts) and `test_kinds_default_is_the_worker_default_kinds`.
- Negative: `test_missing_required_flag_exits_2[<command>]` (one case per required flag), `test_unknown_flag_exits_2`, `test_unknown_command_exits_2`, `test_invalid_values_exit_2[...]` (`--jurisdiction-id nope`, `--kinds nope`, `--require-remaining actions_minutes`, `--require-remaining x=1`, `--minutes 0`, `--limit 0` and `--limit 201` for the requeues, `--keys 123`, a 21st `--service-id`, `--variant nope`, `--kind nope`), `test_emit_needs_exactly_one_of_id_or_all_staged` (neither, and both: exit 2).
- Help: `test_no_command_prints_help_and_exits_2` for the root and each of the 11 groups; `test_help_exits_0_for_every_command`; `test_help_matches_the_golden_file` (exact, argparse only, removed with the argparse adapter) and its successor `test_help_keeps_every_flag_and_help_sentence` (whitespace-normalised: every flag token, every `help=` sentence and the curate epilog appear in the new help).
- Exit-code and format tests through `main([...])` with the existing MockTransport fakes (most exist; Step 0 audits all 20 commands against the list and adds the missing ones): `budget show` 0/3/4 and `--strict`, `budget report-minutes` with an unreachable ledger exits 0, `worker drain` 0/1/2 plus `BrowserSetupError`/`LlmSetupError` codes, `candidates emit` 2 for an invalid selection, `candidates curate` 2 when refused, `llm requeue` 2 without `LLM_MODEL`, `fim probe` 1 when the gate fails, `pvog vocabulary` newline-joined codes, `artifacts list` prints four tab-separated columns (`test_artifacts_list_is_four_tab_separated_columns`), `worker drain` prints exactly one JSON line and nothing else on stdout (`test_drain_stdout_is_one_json_object`), `candidates page` line format, `llm requeue`/`capture requeue` line format.
- Workflow compatibility: `test_workflow_invocations_parse[<file>:<line>]` runs each argv in `cli_invocations.py` through the parse-only adapter; `test_every_flag_used_in_workflows_is_in_the_contract` extracts `python -m discovery_ingest <group> <command>` and the `--flags` that follow (including the `args=( ... )` arrays and `args+=(...)` lines) from `.github/workflows/discovery-*.yml` and `platform-maintenance.yml` and asserts each is in the contract; `test_budget_show_exit_3_is_the_skip_signal` pins the number the workflows test for.
- Process level (subprocess): `python -m discovery_ingest --help` exits 0; `... worker drain --max-tasks x` exits 2 with `error` on stderr and nothing on stdout; `... budget show` without `DISCOVERY_API_URL` exits non-zero with nothing on stdout; `... fim probe --keys 1` exits 2. These pin the real streams and codes independent of `main()`.

Existing tests that must be migrated in the Typer commit, not before:

| Test | Change |
| --- | --- |
| `test_cli_worker.py:10,118`, `test_cli_worker_llm.py:10,65`, `test_discovery_llm_workflow.py:11,125` | replace `_build_parser`/`_drain_policy` with the click adapter's parse-only call and `DrainOptions(...).policy()` (I3) |
| the 13 `pytest.raises(SystemExit)` sites: `test_llm_requeue.py:157`, `test_artifacts_cli.py:117,169`, `test_llm_eval_command.py:143`, `test_cli_worker_llm.py:163`, `test_candidates_cli.py:157`, `test_cli_budget.py:133,158`, `test_capture_requeue.py:177,192`, `test_fim_probe.py:129`, `test_worker_drain.py:270,433` | `main()` now returns the usage-error code 2 (or 0 for `--help`) instead of raising; assert on the returned code. The process exit code seen by the operator is identical (covered by `test_cli_process.py`). |
| `monkeypatch.setattr("discovery_ingest.api_client.httpx.Client", ...)` helpers | already moved to `discovery_ingest.client.http_client.httpx.Client` in I1 |

## Part 4. Dependency and entry point

- `apps/discovery-ingest/pyproject.toml`: add `"typer>=0.12"` to `[project].dependencies` (decision D5). It brings `click` and, through `typer`, `rich` (and `shellingham`). `uv.lock` is regenerated in the implementation PR. No `[project.scripts]` is added: `python -m discovery_ingest` stays the only supported entry point (D5). `[tool.mypy]` needs no override (typer ships types).
- Every workflow runs `pip install -e .`; the install gains typer, click, rich, pygments, markdown-it-py, shellingham. State the added install time in the PR; no workflow file changes.
- Rendering: keep rich out of every machine-read output. Help may be rich-formatted by Typer when rich is present; decide in Step 0 whether to set `rich_markup_mode=None` and `TYPER_USE_RICH=0` semantics for plain help, then pin the choice in the golden check (the check is whitespace-normalised and box-insensitive).

## Part 5. What cannot be preserved exactly (breaking-change notes for the operator)

Include this section, verbatim in substance, in the PR description and as a short "CLI notes" block in `apps/discovery-ingest/README.md`.

| # | Difference | Impact |
| --- | --- | --- |
| 1 | `--help` layout and the `usage:` line change (argparse `usage: discovery_ingest worker drain [-h] ...` becomes click/Typer `Usage: ...` with option panels). Option wording, defaults and the curate epilog text are kept. | Only people reading help. Scripts must not parse help. |
| 2 | Error text for invalid input changes (`error: argument --jurisdiction-id: invalid UUID value: 'x'` becomes `Invalid value for '--jurisdiction-id': 'x' is not a valid UUID.`), and the mutually exclusive error of `candidates emit`. Exit code stays 2, stream stays stderr. | Anything grepping stderr for argparse phrases. None found in workflows or docs. |
| 3 | argparse accepts **abbreviated long options** (`--max-t` for `--max-tasks`); click does not (exit 2, `No such option`). | None found in the workflows or docs; scripts using abbreviations must spell the flag out. |
| 4 | Group without a subcommand (`... worker`) printed the top-level help; it now prints that group's help. Exit code stays 2. | Cosmetic. |
| 5 | Option values that look like options: argparse rejects `--out -x`; click takes `-x` as the value. Validators (`--minutes`, `--limit`, `--max-tasks`) still reject the same values with exit 2. | None expected. |
| 6 | Tracebacks and warnings: Typer's rich tracebacks are disabled (`pretty_exceptions_enable=False`) so uncaught errors still print a plain Python traceback and exit 1; click may print `Aborted!` for Ctrl-C (exit 1, as before: argparse showed a `KeyboardInterrupt` traceback). | Cosmetic. |
| 7 | New stderr line for API refusals in `govdata run`, `pvog run`, `fim enrich`, `leika enrich` (`{label} command failed: ...`, finding C4). Exit code and stdout unchanged. | Additive. |
| 8 | `main(argv)` returns the code for usage errors and `--help` instead of raising `SystemExit`. | In-process callers only (tests); the process exit code is unchanged. |
| 9 | `--install-completion` / `--show-completion` are not exposed (`add_completion=False`). | None. |

If Part 1 shows a flag the new CLI cannot express with the same name, kind and default, the chapter stops and reports it instead of changing the contract.

## Files

Create: everything under `discovery_ingest/cli/` listed above; `operations/` additions needed by the moved logic (`artifacts.py`, `budget.py`, `requeue.py`, `eval.py`, `curation.py` if the existing helper modules are not reused as they are); the test files of Part 3.

Delete (all verified to exist): `discovery_ingest/cli.py`, `cli_errors.py`, `artifacts_cli.py`, `budget_cli.py`, `candidates_cli.py`, `capture_requeue.py`, `llm_requeue.py`, `requeue_common.py` (its `Counts`, `enqueue_counted` move to `operations/requeue.py`), `curation_command.py`, `browser/probe_cli.py`, `extract/llm/probe_cli.py`, `extract/llm/evaluation/arguments.py`, `extract/llm/evaluation/command.py` (its `EvalCommand`/`EvalRuntime` logic moves to `operations/eval.py`; `register_eval_parser` is dropped).

Edit: `apps/discovery-ingest/pyproject.toml`, `uv.lock`, `__main__.py` (unchanged text), `README.md` (CLI notes), tests as listed.

## TDD loop

### Red

1. **Contract on argparse (green).** Add Part 3's files and goldens; every test passes against the current CLI. Capture the goldens with `COLUMNS=100`.
2. **Red for the new surface.** Switch the adapter import to the click adapter and add `tests/test_cli_typer_shape.py`: `test_root_app_registers_the_eleven_groups_in_order`, `test_group_without_subcommand_exits_2_and_prints_group_help[<group>]`, `test_ctx_obj_is_lazy_and_probes_need_no_api_settings` (negative: `fim probe`, `browser probe`, `llm probe` run with `DISCOVERY_API_URL` and `DISCOVERY_API_KEY` unset), `test_api_refusal_prints_label_and_exits_1[govdata run|pvog run|fim enrich|leika enrich]`, `test_main_returns_the_code_and_never_raises_systemexit`, `test_completion_options_are_not_exposed`, `test_cli_package_imports_no_argparse` (grep). They fail because `discovery_ingest.cli` is still a module.

### Green

1. Add the dependency; build `cli/context.py`, `errors.py`, `options.py` and the `main.py` skeleton.
2. Migrate one group at a time, simplest first (`pvog`, `govdata`, `fim`, `leika`, `artifacts`, `budget`, `capture`, `candidates`, `browser`, `llm`, `worker`), keeping the old argparse CLI runnable until the last group moves (a temporary dispatcher in `main` may route migrated groups to Typer); the contract suite is green after every group.
3. Delete `cli.py`, the `*_cli.py` modules and the argparse adapter; migrate the tests of Part 3's table; swap the golden check for the normalised one.
4. Update README and add the CLI notes.

### Refactor

Judge by responsibility, not line count: every `commands.py` command should read as parse, call, render. Look for: flow logic that slipped into a command (move to `operations/`), a renderer written twice (rule of three: only then a shared helper), nested `try` blocks that the shared handler should own, a `ctx.obj` access pattern repeated in every command (a single `get_client(ctx)` accessor is justified at three uses), and options duplicated across `capture requeue` and `llm requeue` (`--host --limit --dry-run`; one shared option set in `options.py`). No new `Any`; the `capture_requeue.py:31` `Sequence[Any]` action disappears with the argparse action. Every new public symbol has an imperative docstring (pydocstyle `D`, `pep257`); the Typer command docstrings double as `--help` text, so write them for the operator and keep them in sync with the golden. Report `Refactor gate: smells found -> ..., refactorings applied -> ...` with before and after: lines of the largest CLI module (540 to the largest `commands.py`), count of modules importing `argparse` (13 to 0), count of `Any` in `cli*` (3 + 2 to 0), `ruff --select D,ANN401` of the new package (0).

## Verification

```bash
cd apps/discovery-ingest
uv run ruff format --check . && uv run ruff check . && uv run mypy discovery_ingest
uv run pytest tests/test_cli_contract.py tests/test_cli_invocations.py tests/test_cli_process.py tests/test_cli_typer_shape.py \
  tests/test_cli_budget.py tests/test_artifacts_cli.py tests/test_cli_worker.py tests/test_cli_worker_llm.py \
  tests/test_govdata_cli.py tests/test_pvog_cli.py tests/test_fim_leika_enrich.py tests/test_fim_probe.py \
  tests/test_candidates_cli.py tests/test_candidates_curate.py tests/test_capture_requeue.py tests/test_llm_requeue.py \
  tests/test_llm_probe.py tests/test_llm_eval_command.py tests/test_browser_probe.py tests/test_worker_drain.py \
  tests/test_discovery_llm_workflow.py tests/test_drain_workflow_budget.py tests/test_browser_workflows.py tests/test_llm_probe_workflow.py
uv run pytest
python -m discovery_ingest --help; python -m discovery_ingest budget show --help
cd ../..
./ci.sh
```

Release-gate check (from the rollout): the workflows `.github/workflows/discovery-*.yml` run unchanged against the new CLI. The workflow contract tests above are the offline proof; a manual `workflow_dispatch` of `discovery-fim-probe.yml` and `discovery-drain.yml` on the loop branch is the live one.

## Parallel notes

Batch 4 runs I4, then G1, then G2, one at a time; I4 has no concurrent sibling. It starts after I3 (and therefore I1, I2) is merged.

- **G1** (test gaps) waits for I4: it adds tests for `cli._build_parser` (listed in the audit as untested) that this chapter replaces with the contract suite; G1 must not recreate them.
- **G2** closes lint baselines after I4 removed the `cli*` entries.
- **Must not be touched:** `.github/**` (the workflows are the contract, not an edit target), `docs/operations/**` (only the README gets the CLI notes), `apps/api/**`, the command names, flags, defaults and exit codes of Part 1, `client/` (I1) and `operations/` semantics from I3 beyond moving the leftover `*_cli.py` logic.
