---
name: "T2 — Any gate"
overview: "Keep Any out of annotations for good: ruff ANN401 plus a typing.Any import ban (TID251) with per-file baselines in apps/api and apps/discovery-ingest, and mypy disallow_any_explicit for discovery_ingest. Each baseline entry is removed by the chapter that types that file."
todos:
  - id: measure
    content: "Re-measure ANN401, TID251 and mypy explicit-any counts per file"
    status: pending
  - id: ruff-gate
    content: "Enable ANN401 and the typing.Any ban with per-file baselines; exempt tests"
    status: pending
  - id: mypy-gate
    content: "Enable disallow_any_explicit for discovery_ingest with the pydantic plugin and a per-module baseline"
    status: pending
isProject: false
---

# T2 — Any gate

**Repo:** `redtape` · **Branch:** `refactor/any-gate` · **Status:** planned

**Depends on:** none (the gate lands first; the baseline entries are removed by later chapters) · **Architecture:** [../00-audit-report.md](../00-audit-report.md) section 5 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-codebase-audit` · **Release branch:** `main`

**Touches:** ruff and mypy config only. **After:** none.

**Findings:** T4, T5, T6 (the gate for the typing design in section 5); decision U3.

## Goal

After this chapter nobody can add a new `Any` to `apps/api/app`, `apps/api/scripts` or `apps/discovery-ingest/discovery_ingest` without CI failing. Existing uses are frozen in a per-file baseline. Every typing chapter deletes the baseline entries of the files it fixes, so the count only goes down; chapter G2 verifies the baselines are empty.

## What `ANN401` does and does not cover (measured)

`ANN401` flags `Any` only as the annotation of a parameter or a return. It does not flag `dict[str, Any]`, `list[Any]` or `Callable[[Any], T]`, which are the dominant forms in the audit (67 `Any` in ingest, 21 in API by grep). Measured on 2026-11-02 with `ruff check <paths> --select ANN401 --isolated --statistics` (read-only):

| Scope | `ANN401` | `typing.Any` import (TID251 below) | grep `\bAny\b` (words) |
| --- | --- | --- | --- |
| `apps/api` `app` + `scripts` | 10 | 5 files | 24 |
| `apps/api/tests` | 2 | 2 files | n/a |
| `apps/discovery-ingest/discovery_ingest` | 3 | 14 files | 67 |
| `apps/discovery-ingest/tests` | 35 | 36 files | n/a |

So `ANN401` alone would freeze only 13 of the roughly 90 production uses and would let `dict[str, Any]` back in. The chapter therefore adds a second rule that bans the name itself.

## Design

1. **`ANN401`** (requested): `Any` in a signature.
2. **`TID251` (flake8-tidy-imports banned-api)** on `typing.Any` and `typing_extensions.Any`: any import or attribute use of `Any` is an error, which catches every nested form. Ruff reports it once per file (at the import), so the baseline is a short list of files, not of lines. Verified read-only: it reports exactly the files in the tables below.
3. **mypy `disallow_any_explicit`** for `discovery_ingest` only (requested). It needs the pydantic plugin, see "mypy" below.
4. Tests are exempt from all three (`"tests/*" = [..., "ANN401", "TID251"]`); alembic stays excluded by `extend-exclude`.

Message for the ban (shown in the CI log, so it teaches the fix): `Use a Pydantic model, a TypedDict or pydantic.JsonValue instead of Any (see .plans/codebase-audit/00-audit-report.md section 5).`

## Files

- `apps/api/pyproject.toml` — `[tool.ruff.lint] select` (lines 47-55) gets `"ANN401"`, `"TID251"`; new `[tool.ruff.lint.flake8-tidy-imports.banned-api]` with `"typing.Any"` and `"typing_extensions.Any"`; `[tool.ruff.lint.per-file-ignores]` (line 61) gets `ANN401`/`TID251` for tests and the baseline lines below. mypy section unchanged.
- `apps/discovery-ingest/pyproject.toml` — same ruff edits (`select` line 36, `per-file-ignores` line 39); `[tool.mypy]` (line 42) gets `plugins = ["pydantic.mypy"]` and `disallow_any_explicit = true`, plus per-module overrides for the baseline.
- No source file changes. If the pydantic plugin makes `discovery_ingest/config.py:92` report an unused `type: ignore` (it does with pydantic 2.14.1, the version in `apps/discovery-ingest/uv.lock`), remove that one comment; it is the only source edit allowed.

## Baselines (measured)

### `apps/api` — 5 files (ANN401 10, all inside these files)

| File | ANN401 | Sites | Removed by |
| --- | --- | --- | --- |
| `app/features/suggestions/handlers.py` | 3 | `KindHandler.validate/normalized_url/conflicts` `payload: Any` (lines 49, 51, 53) | B2 (typing design: `KindHandler[PayloadT]`) |
| `app/services/openplz_client.py` | 5 | `_parse_json`, `get_json`, three `payload` parameters (lines 92-131) | B6 |
| `scripts/import_openplz_locations.py` | 2 | `**kwargs: Any` (lines 143, 151) | B6 (touches `api/scripts/`) |
| `app/routes.py` | 0 (nested) | `list[dict[str, Any]]`, `dict[str, Any]` (lines 19, 41) | B1 (`/locales` and `/translations` move to a typed `locales` feature, `routes.py` keeps only `/health`) |
| `app/features/auth/jwt.py` | 0 (nested) | `_build_claims(payload: dict[str, Any])` (line 45) | B3 (touches `features/auth`; `JwtClaims` model) |

mypy `disallow_any_explicit` is **not** enabled for `apps/api`: with pydantic 2.13.4 (the version in `apps/api/uv.lock`) it reports 133 errors, almost all on plain `class X(BaseModel)` lines (verified on a three-line probe), even with `pydantic.mypy` loaded. Revisit when the API lock moves to pydantic 2.14 (where the same probe passes); then add the same flag with an empty baseline.

### `apps/discovery-ingest` — 14 files (ANN401 3, mypy explicit-any 53)

| File | mypy | ANN401 | Removed by |
| --- | --- | --- | --- |
| `pvog/client.py` | 14 | 0 | I2 (`PvogFacade`/`PvogPage`/`PvogRecord`) |
| `govdata/client.py` | 8 | 0 | I2 (`GovDataRow`) |
| `enrich.py` | 7 | 0 | I2 (`Steckbrief`, `Stammtext`) |
| `govdata/ckan.py` | 6 | 0 | I2 (`CkanPackage`, `CkanResource`, `CkanResponse`) |
| `extract/llm/schema_prep.py` | 3 | 3 (lines 16, 26) | I2 (`JsonObject`/`JsonValue`) |
| `extract/llm/schema.py` | 2 | 0 | I2 |
| `extract/llm/payloads.py` | 2 | 0 | I2 (`Body`) |
| `extract/llm/cloudflare.py` | 2 | 0 | I2 (`ChatMessage`) |
| `extract/llm/client.py` | 1 | 0 | I2 |
| `fim/client.py` | 2 | 0 | I2 (`Steckbrief`) |
| `leika/client.py` | 2 | 0 | I2 (`Stammtext`) |
| `worker/enrich_metadata.py` | 1 | 0 | I2 per the typing table (`_parse_steckbrief_body`), but `worker/` is in I3's touches and not I2's: the chief of staff decides; default I3, which also merges the third FIM flow (D6) |
| `cli.py` | 2 | 0 | I4 (file is deleted) |
| `capture_requeue.py` | 0 | 0 | I4 (`values: str \| Sequence[Any] \| None`, line 31; disappears with the Typer CLI) |

Mypy errors by class line (`class X(BaseModel)`) disappear with the plugin; the 53 above are real signature/variable uses. `emit_models.py`, `schemas.py`, `mentions.py`, `edges.py`, `budget_models.py`, `artifacts.py`, `curation.py` appear in the plugin-less run only because of that false positive and need no baseline.

## TDD loop

The gate is the linter and the type checker. There is no application behaviour to pin; the "tests" are CI invocations and three throwaway negative checks.

### Red

1. Re-measure: `ruff check <paths> --select ANN401,TID251 --isolated --statistics` (read-only; never `--fix`) and `mypy discovery_ingest --disallow-any-explicit` with the plugin on a scratch config outside the repo. Record the numbers in the PR; they replace the tables above if they changed.
2. Enable the rules with **no** baseline. `ruff check .` fails with the counts above in both apps; `mypy discovery_ingest` fails with 54 errors (53 `explicit-any`, 1 unused ignore). This is the red.

### Green

1. Add the baseline: one `per-file-ignores` line per file, listing only the codes it violates (`["ANN401", "TID251"]` or `["TID251"]`), each with a trailing comment naming the removing chapter (`# T2 baseline, removed by B6`).
2. Ingest mypy: top-level `disallow_any_explicit = true`; one `[[tool.mypy.overrides]]` per removing chapter (I2, I3, I4) listing its modules with `disallow_any_explicit = false`. Group by chapter so each chapter deletes exactly one override block.
3. `ruff format --check .`, `ruff check .`, `mypy` (API: `mypy app scripts`; ingest: `mypy discovery_ingest`) are green in both apps.
4. Negative checks (throwaway, not committed):
   - add `def f(x: Any) -> None: ...` with `from typing import Any` to `app/features/voting/service.py`: `ruff check` fails with ANN401 and TID251;
   - add `x: dict[str, Any] = {}` to a file without a baseline entry: only TID251 fires (this is the case ANN401 alone would miss);
   - add the same to `apps/discovery-ingest/discovery_ingest/budget.py`: `ruff check` and `mypy` both fail.
5. Positive check: `ruff check apps/api/tests apps/discovery-ingest/tests` reports no ANN401 or TID251.

### Refactor

**Refactor gate.** No production code changes in this chapter. Judge the config by responsibility: the baseline is per file with an owner comment, not a directory wildcard and not `# noqa`; the ban is in the tool that sees every form (TID251), the signature rule stays for its clearer message (ANN401). Rule of three: three baseline files owned by one chapter share one mypy override block, not three. No `type: ignore`, no `cast`, no new `Any`; the single allowed source edit is the removal of an unused `type: ignore` (`config.py:92`). Docstring rule: none to write (no new Python symbol).

## Which chapter removes which entry

| Chapter | Removes (ruff `per-file-ignores` and mypy override entries) |
| --- | --- |
| B1 | `app/routes.py` (the `Any` handlers move into the typed `locales` feature; the new files are born clean) |
| B2 | `app/features/suggestions/handlers.py` |
| B3 | `app/features/auth/jwt.py` |
| B6 | `app/services/openplz_client.py`, `scripts/import_openplz_locations.py` |
| I2 | `pvog/client.py`, `govdata/client.py`, `govdata/ckan.py`, `fim/client.py`, `leika/client.py`, `enrich.py`, `extract/llm/{schema,schema_prep,payloads,cloudflare,client}.py` |
| I3 (default) | `worker/enrich_metadata.py` |
| I4 | `cli.py`, `capture_requeue.py` |
| G2 | verifies both baselines and the mypy override list are empty; deletes the now-empty sections and the T2 comments |

Rule for those chapters: the PR that fixes a file also deletes its baseline line in the same commit; CI then proves the file is clean.

## Verification

```bash
cd apps/api
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
uv run pytest tests/test_import_openplz_locations.py tests/test_import_openplz_incremental.py -q   # smoke only: no source changed
cd ../discovery-ingest
uv run ruff format --check . && uv run ruff check . && uv run mypy discovery_ingest
uv run pytest -q
cd ../..
./ci.sh
```

Run the full `uv run pytest` once as well (needs Postgres; background). CI installs ingest with `pip install -e ".[dev]"` (unpinned, latest pydantic); local runs use `uv.lock` (2.14.1). Run the mypy check once against the CI resolution (fresh venv) to confirm the plugin behaves the same; if CI resolves an older pydantic, raise the floor in `[project] dependencies` (`pydantic>=2.14`) in this PR.

## Git workflow

```bash
git checkout feat/plans-codebase-audit && git pull
git checkout -b refactor/any-gate
```

```text
build(api,ingest): ban typing.Any and enable ANN401 with a per-file baseline
build(ingest): enable mypy disallow_any_explicit with the pydantic plugin and a module baseline
```

Open the chapter PR into `feat/plans-codebase-audit`, not `main`.

## Parallel notes

Runs in batch 1 beside T1 step 1, T3, A1, A2, A3, A4, B1, B6, W1, W2. Shares `apps/api/pyproject.toml` and `apps/discovery-ingest/pyproject.toml` with T1 step 1: both edit `[tool.ruff.lint] select` and `per-file-ignores`. Merge order: T1 step 1, then T2 (rebase onto it; resolve by keeping both lists). Do not touch any file under `app/`, `scripts/` or `discovery_ingest/` except the one `type: ignore` removal; do not touch `tests/`, `apps/web` or lock files (a pydantic floor change in `pyproject.toml` that needs a lock refresh is raised with the chief of staff, not done here). B1, B2, B3, B6, I2, I3, I4 are the consumers of the baseline; they run later or beside this chapter and rebase onto it.
