---
name: "T1 — pydocstyle gate"
overview: "Enable ruff D rules (pep257) in apps/api and apps/discovery-ingest. Step 1 adds the config, auto-fixes whitespace and records a per-directory baseline. Step 2 writes the missing docstrings in parallel directory slices and shrinks the baseline. A final gate (G2) empties it."
todos:
  - id: config
    content: "Step 1: select D, convention pep257, tests exempt, per-file-ignores baseline, ruff --fix for D202/D209"
    status: pending
  - id: slices-api
    content: "Step 2: API slices A-S1..A-S6, one agent each, docstrings only"
    status: pending
  - id: slices-ingest
    content: "Step 2: ingest slices I-S1..I-S3, one agent each, docstrings only"
    status: pending
  - id: gate
    content: "Final gate: baseline empty in both apps (closed by G2); ruff check green"
    status: pending
isProject: false
---

# T1 — pydocstyle gate

**Repo:** `redtape` · **Branch:** `refactor/pydocstyle` (step 1); step 2 slices use `refactor/pydocstyle-<slice>` · **Status:** planned

**Depends on:** none (step 1); step 2 after step 1 · **Architecture:** [../00-audit-report.md](../00-audit-report.md) section 1 and 5 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-codebase-audit` · **Release branch:** `main`

**Touches:** step 1: ruff config of `apps/api` and `apps/discovery-ingest`, auto-fixed whitespace/docstring lines. Step 2: one directory slice per agent (docstrings only). **After:** step 2 after step 1.

**Findings:** audit baseline (section 1, "pydocstyle D violations"); decision U4 in [../gaps-and-decisions.md](../gaps-and-decisions.md).

## Goal

`ruff check` enforces docstrings on every public module, class, method, function, package and `__init__` of `apps/api/app`, `apps/api/scripts` and `apps/discovery-ingest/discovery_ingest`. Tests and migrations are exempt. Existing violations are frozen in a per-directory baseline (`per-file-ignores`) that only shrinks; step 2 deletes the entries slice by slice; chapter G2 verifies it is empty.

Docs rules (apply to every docstring written here and in every other chapter):

- Imperative mood, one summary line ("Return the enabled locales", not "Returns" or "This returns").
- State intent: why the symbol exists or what it guarantees (ordering, idempotency, what it raises, what it never writes). Do not restate the signature or the code ("Takes a session and returns a list" is noise).
- No docstring is better than a false one; an inherited or trivially named dunder still gets a one-line intent ("Bind the service to its repository").
- `pep257` only: no section headers, no `Args:`/`Returns:` blocks required. Use a short second paragraph when a precondition or error matters.

## Measured baseline (2026-11-02, `main` at `0e713cc`)

Command, read-only (never `--fix`):

```bash
cd apps/api && .venv/bin/ruff check app scripts --select D --isolated --statistics   # 367 with the default convention
```

`--isolated` ignores the pep257 convention, so it reports 367 (it adds D212 x6). With `convention = "pep257"` the numbers below apply (measured with an equivalent temporary config outside the repo): **API 361, ingest 27**. Step 1's autofix removes D202 and D209 (API 31, ingest 2), leaving **API 330, ingest 25** to document by hand.

| Rule | Meaning | API now | Ingest now |
| --- | --- | --- | --- |
| D102 | public method | 156 | 0 |
| D103 | public function | 67 | 1 |
| D100 | module | 41 | 0 |
| D107 | `__init__` | 26 | 14 |
| D101 | class | 17 | 0 |
| D104 | package | 11 | 0 |
| D202 | blank line after function docstring (autofix) | 27 | 2 |
| D205 | blank line after summary | 9 | 1 |
| D209 | closing quotes on own line (autofix) | 4 | 0 |
| D401 | imperative mood | 2 | 8 |
| D200 / D400 | one-line / trailing period | 1 / 0 | 0 / 1 |
| **Total** | | **361** | **27** |

Not selected on purpose: D203/D211/D212/D213 and the numpy/google section rules (`pep257` convention switches them off).

## Files

- `apps/api/pyproject.toml` — `[tool.ruff.lint] select` (lines 47-55) gets `"D"`; add `[tool.ruff.lint.pydocstyle] convention = "pep257"`; `[tool.ruff.lint.per-file-ignores]` (line 61) gets `"tests/*"` extended with `"D"` and the baseline entries below. `alembic/**` is already out of scope through `extend-exclude = ["alembic/**"]` (line 44): add nothing.
- `apps/discovery-ingest/pyproject.toml` — same three edits (`select` on line 36, `per-file-ignores` on line 39); no migrations directory exists there.
- No source file changes in step 1 except what `ruff check --fix --select D202,D209` rewrites (whitespace only; review the diff before committing).
- Step 2: only the files of the slice. No signature, import or logic changes.

## Step 1 — config, autofix, baseline (one agent, one PR)

### Baseline shape

One `per-file-ignores` line per slice, listing only the codes that slice still violates after the autofix, so a new violation of another code in the same directory fails immediately. Globs are relative to the `pyproject.toml` directory (verified: a `"app/features/discovery/**" = ["D"]` entry removed exactly the 78 discovery violations in a dry run with inline `--config`).

```toml
[tool.ruff.lint.per-file-ignores]
"tests/*" = ["S101", "D"]
"tests/test_discovery_error_responses.py" = ["F811"]
"scripts/*" = ["T201"]
# docstring baseline (T1): delete the line when its slice is done
"app/features/discovery/**" = ["D102", "D103", "D205", "D401"]
"app/features/suggestions/**" = ["D100", "D102", "D103", "D107"]
# ...one line per slice from the table below
```

Ruff merges all matching patterns, and `"scripts/*"` already exists, so the scripts baseline is added as `["T201", "D100", ...]` on that same line rather than a second key.

### TDD loop

There is no behaviour to test; the gate is the linter itself.

**Red.** With only `select += "D"` and `convention = "pep257"` added (no baseline yet), `ruff check .` reports 361 errors in `apps/api` and 27 in `apps/discovery-ingest` (run it, record the numbers, discard the change).

**Green.**

1. Add the config and the `tests/*` exemption. Run `ruff check --fix --select D202,D209 app scripts` (ingest: `discovery_ingest`). Do not pass `--unsafe-fixes`.
2. Re-measure per slice: `ruff check <paths> --statistics` and write each slice's remaining codes into the baseline (table below is the expected result; re-measure because earlier merged chapters change it).
3. `ruff check .` and `ruff format --check .` are green in both apps.
4. Prove the gate bites with a throwaway negative check (do not commit): add `def f(): pass` to `app/features/voting/service.py`; `ruff check` must fail with D103 in a directory that has no baseline entry for it; then revert.
5. Prove tests and migrations are exempt: `ruff check apps/api/tests apps/api/alembic` reports no D code.

**Refactor gate.** There is no code refactor in this step. Judge the config by responsibility: one baseline line per slice, no blanket `"app/**" = ["D"]`, no `# noqa: D` in source, no `--add-noqa`. Rule of three: if the same code list repeats for three slices, still keep one line per slice (each line is deleted independently). New public symbols in this step: none. No new `Any`.

### Baseline per slice

Counts are after the step 1 autofix. "Now" is before it. Re-measure at the start of the chapter.

**`apps/api` (361 now, 330 after autofix)**

| Slice | Paths | Now | After autofix | Remaining codes | Starts |
| --- | --- | --- | --- | --- | --- |
| A-S1 | `app/features/discovery/**` | 78 | 64 | D102 44, D103 15, D205 4, D401 1 | after B3 and B4 merge (batch 2b) |
| A-S2 | `app/features/suggestions/**` | 36 | 36 | D102 25, D107 6, D103 4, D100 1 | after B2 merges (batch 2b) |
| A-S3 | `app/features/{locations,taxonomy,voting,candidates,events}/**` | 78 | 78 | D102 46, D103 12, D107 8, D100 7, D104 3, D401 1, D101 1 | batch 2 |
| A-S4 | `app/features/{documents,auth}/**`, `app/schema/discovery/**` | 89 | 77 | D102 33, D101 10, D103 10, D100 10, D107 9, D205 4, D104 1 | after B3 merges (batch 2b) |
| A-S5 | `app/schema/{auth,candidate,document,location,suggestion,taxonomy,vote}/**`, `app/schema/openplz.py`, `app/models/**`, `app/shared/**`, `app/services/**`, `app/middleware/**`, top-level `app/*.py`, `app/features/__init__.py` | 53 | 51 | D100 20, D103 10, D104 7, D102 6, D101 5, D107 2, D205 1 | batch 2 |
| A-S6 | `scripts/**` | 27 | 24 | D103 16, D100 3, D102 2, D101 1, D107 1, D200 1 | batch 2 |
| **Total** | | **361** | **330** | | |

Per-directory detail of the heaviest files (today): `features/auth` 60 (`service.py` 14, `dependencies.py` 12, `repository.py` 12), `features/discovery` 78 (`machine_controller.py` 14, `dependencies.py` 13), `features/suggestions/handlers.py` 15, `features/documents/repository.py` 16, `models/**` 13 (all D100/D101-level, one per file).

**`apps/discovery-ingest` (27 now, 25 after autofix)**

| Slice | Paths | Now | After autofix | Remaining codes | Starts |
| --- | --- | --- | --- | --- | --- |
| I-S1 | `worker/**` (`fetcher`, `handler_table`, `llm_drain`, `llm_extract`, `outcome`, `pacing`, `render_enqueue`, `robots`, `run`) | 9 | 9 | D401 5, D107 4 | batch 2 |
| I-S2 | `browser/**`, top-level `discovery_ingest/*.py` except `api_client.py`, `extract/*.py` except `extract/llm/` | 6 | 4 | D107 3, D401 1 | batch 2 |
| I-S3 | `api_client.py`, `extract/llm/**`, `pvog/**`, `govdata/**`, `fim/**`, `leika/**`, `harvest/**` | 12 | 12 | D107 7, D401 2, D205 1, D400 1, D103 1 | after I1 and I2 merge (batch 2b) |
| **Total** | | **27** | **25** | | |

`browser/` and `harvest/` are already clean today.

## Step 2 — docstring slices (parallel, one agent per slice)

Each slice agent: branch `refactor/pydocstyle-<slice>` from the loop branch, one PR per slice.

### Scheduling rule (resolves overlap with batch 2)

Several batch-2 chapters rewrite the same files. A docstring pass over a directory that another chapter is rewriting produces merge conflicts and stale docstrings, so:

- Slices marked "batch 2" run in parallel with B2, B3, B4, I1, I2, W3, W4: no batch-2 chapter touches their paths.
- Slices marked "batch 2b" start after the named chapters merge into the loop branch. By then those chapters have already written the docstrings of the files they rewrote and removed their baseline entries (standard rule 5), so the slice only fills the remainder.
- The chief of staff may instead run one closing sweep per 2b slice; the content is identical.

### Per-slice TDD loop

**Red.** Delete the slice's baseline line(s) from `pyproject.toml`. `ruff check <slice paths>` fails with exactly the counts in the table (record them; this is the red).

**Green.** Write the docstrings until `ruff check <slice paths>` and the full `ruff check .` pass. Rules:

1. Read the symbol before documenting it; state intent, not the signature. If the intent is unclear, read the callers and the tests.
2. Docstring-only diff: no renames, no reordering, no formatting churn beyond what `ruff format` demands. A reviewer should be able to confirm "only strings and blank lines changed" with `git diff -U0 | grep '^[+-]' | grep -v '"""'`.
3. A docstring on `__init__` says what it binds or validates ("Bind the repository and the clock"), not "Initialize".
4. Package `__init__.py` gets a one-line statement of the package's responsibility.
5. If a symbol turns out to be dead or misnamed, record it in the PR text. Do not fix it here.

**Refactor gate.** Judge by responsibility, not line count. While reading a file you may find a class you cannot describe without "and"; report it (it belongs to a B or I chapter), do not split it here. Rule of three, one nesting level, parameter counts: observe and report, do not change. Every new docstring follows the rules in Goal. No new `Any`, no signature changes.

**Negative path.** After the slice, `ruff check .` must still fail if a new undocumented public function is added to the slice directory (repeat the throwaway check from step 1). The PR records the narrow command and before/after numbers.

## Final gate

When the last slice and the last batch-2 chapters are merged:

- `[tool.ruff.lint.per-file-ignores]` has no D baseline lines in either app (only `tests/*` keeps `D`).
- `ruff check .` is green in both apps.
- Chapter G2 re-runs `ruff check --select D --statistics` and fails the release gate if anything is left.

## Verification

```bash
cd apps/api
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
uv run pytest tests/test_vote_service.py tests/test_discovery_emit.py -q   # smoke: a docstring-only slice must not change any result
cd ../discovery-ingest
uv run ruff format --check . && uv run ruff check . && uv run mypy discovery_ingest
cd ../..
./ci.sh
```

Docstring-only slices need no new tests and no test may change. Run the full `uv run pytest` once per slice PR (the API suite needs Postgres; run it in the background).

## Git workflow

```bash
git checkout feat/plans-codebase-audit && git pull
git checkout -b refactor/pydocstyle
```

```text
build(api,ingest): enable pydocstyle D rules with a per-directory baseline
style(api,ingest): drop blank lines after docstrings (ruff --fix D202, D209)
```

Slice PRs: `docs(<slice>): document public symbols and drop the D baseline for <paths>`. Open every PR into `feat/plans-codebase-audit`, not `main`.

## Parallel notes

Step 1 (batch 1) runs beside T2, T3, A1, A2, A3, A4, B1, B6, W1, W2. It edits only the two `pyproject.toml` ruff sections and whitespace that `--fix` rewrites in docstrings; T2 edits the same two files, so T1 step 1 and T2 must not both change `[tool.ruff.lint]` in the same hunk: merge T1 first and rebase T2 (or edit `per-file-ignores` and `select` in separate commits). The `--fix` whitespace pass touches files that A1-A4, B1 and B6 rewrite; run it as the last commit and, if it conflicts, re-run `--fix` after the rebase instead of resolving by hand. Step 2 slices run beside each other (disjoint paths) and beside the batch-2 chapters according to the scheduling rule. Do not touch `apps/web`, `tests/`, `alembic/`, lock files or `ci.sh`.
