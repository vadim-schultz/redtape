---
name: "Chapter 1 — Crawler package skeleton"
overview: "apps/crawler exists as its own installable package with ruff, mypy and pytest configured, wired into ci.sh and a new CI workflow, before any crawling logic is written."
todos:
  - id: package
    content: "pyproject.toml, package layout, one placeholder module and test"
    status: pending
  - id: ci
    content: "ci.sh and a crawler-lint-test workflow"
    status: pending
isProject: false
---

# Chapter 1 — Crawler package skeleton

**Repo:** `redtape` (`apps/crawler` new, `ci.sh`, `.github/workflows`) · **Branch:** `feat/crawler-skeleton` · **Status:** planned

**Depends on:** none · **Architecture:** [../00-architecture.md](../00-architecture.md) §3 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

A new package the rest of this suite can build in, with the same tooling discipline as `apps/api`
(`ruff`, `mypy`, `pytest`) enforced from the first commit, not bolted on later.

## Design decisions

**Mirrors `apps/api`'s `pyproject.toml` shape**: `[project]` with a `dev` extra (`ruff`, `mypy`, `pytest`,
`respx` added in chapter 2), `[tool.ruff]` matching the API's line length and rule set
(`E, F, W, I, UP, B, SIM`), `[tool.mypy]` non-strict to start (matches the API's own posture).

**`pytest.ini_options` registers a `needs_playwright` marker** now, even though nothing uses it until
chapter 7, so the marker is never "invented ad hoc" mid-suite; `-m "not needs_playwright"` is the default
local/CI invocation, matching the rollout's per-chapter gate.

**`ci.sh` gains a third section**, `=== Crawler Checks ===`, after the web section, following the same
venv-presence-check pattern already used for the API section (`if [ ! -d ".venv" ] ...`).

**A separate GitHub Actions workflow** `crawler-lint-test.yml`, triggered on `apps/crawler/**` changes only
(mirrors `api-lint-test.yml`'s path trigger), so unrelated API/web PRs do not pay for it.

**One placeholder module** (`crawler/__init__.py` with `__version__`) and one test, so "does the package
import and does pytest discover it" is proven before any real code exists.

## Files

| Path | Change |
| --- | --- |
| `apps/crawler/pyproject.toml` | New |
| `apps/crawler/crawler/__init__.py` | New |
| `apps/crawler/tests/test_package.py` | Tests below |
| `apps/crawler/.gitignore` | `.venv`, `__pycache__`, matching the API's |
| `ci.sh` | New section |
| `.github/workflows/crawler-lint-test.yml` | New |

## Red tests

| Test | Asserts |
| --- | --- |
| `package · crawler module imports and exposes __version__` | Import succeeds, version is a non-empty string |
| `package · the needs_playwright marker is registered, not an unknown-marker warning` | `pytest --strict-markers` passes |

## Green

1. `pyproject.toml`, package files; test 1.
2. Marker registration; test 2.
3. `ci.sh` and the workflow (no test; verified by running the gate).

## Refactor gate

Nothing to refactor at this size; report "no refactor needed — one module, one test".

## Verification

```bash
cd apps/crawler
uv pip install -e ".[dev]"
ruff format --check . && ruff check . && mypy crawler
python -m pytest --strict-markers
cd ../.. && ./ci.sh
```

## Out of scope

Any crawling logic (chapters 2 onward).

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/crawler-skeleton
```

```text
test(crawler): describe the package import and marker registration

feat(crawler): add the apps/crawler package skeleton and its CI
```
