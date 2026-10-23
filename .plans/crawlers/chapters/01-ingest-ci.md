---
name: "Chapter 1 — Ingest CI"
overview: "Give apps/discovery-ingest its own GitHub Actions workflow so worker changes are checked on every pull request."
todos:
  - id: workflow
    content: "Add discovery-ingest-ci.yml (ruff format, ruff check, mypy, pytest) with a path filter"
    status: pending
  - id: ci-sh
    content: "Make ci.sh run the whole ingest test directory instead of a named file list"
    status: pending
  - id: red-proof
    content: "Prove the job goes red on a deliberate failure, then green again"
    status: pending
isProject: false
---

# Chapter 1 — Ingest CI

**Repo:** `redtape` (`.github/workflows`, `ci.sh`) · **Branch:** `feat/crawlers-ingest-ci` · **Status:** planned

**Depends on:** none · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/crawlers`

## Goal

Today no GitHub workflow covers `apps/discovery-ingest`. The discovery-operations ledger records that its chapter 3 PR ran only the Cloudflare check, and `./ci.sh` runs a hand-maintained list of ten test files that omits `test_batch_dedup.py` and `test_fim_leika_enrich.py`. Every later worker chapter depends on trustworthy remote checks, so this comes first.

## Contract

`.github/workflows/discovery-ingest-ci.yml`, modelled on [api-lint-test.yml](../../../.github/workflows/api-lint-test.yml):

- Triggers: `push` to `main`/`develop` and `pull_request`, both filtered to `apps/discovery-ingest/**` and the workflow file itself.
- `defaults.run.working-directory: apps/discovery-ingest`.
- One job on `ubuntu-latest`: checkout, `actions/setup-python` 3.12 with pip cache keyed on `apps/discovery-ingest/pyproject.toml`, `pip install -e ".[dev]"`, then `ruff format --check .`, `ruff check .`, `mypy discovery_ingest`, `python -m pytest` (the whole `tests/` directory, no file list).
- No secrets and no network beyond PyPI: the existing tests use fixtures and `httpx` mock transports.

`ci.sh`'s "Discovery ingest checks" step runs `uv run pytest` over the whole directory so local and remote agree. If an unlisted test fails today, fix it or mark it with a documented reason in this chapter's ledger entry; do not shrink the directory run.

## TDD loops

CI configuration has no unit-test harness, so the paired proof is behavioural.

### Loop A — Green on a clean branch

**Red:** open the chapter PR with only the workflow added and confirm the job runs (it is the first run, so "red" means the workflow did not exist before).

**Green:** `gh pr checks --watch` shows `Discovery ingest CI` passing, including the previously unlisted tests.

**Refactor:** audit the workflow for duplicated install steps and cache settings; keep one job unless runtime exceeds five minutes.

### Loop B — Red on a deliberate failure

**Red:** push a throwaway commit that breaks formatting in one ingest file and a second that fails an assertion; confirm `ruff format --check` and `pytest` each turn the job red.

**Green:** revert both commits; confirm the job is green again. Record the run IDs in the ledger.

**Refactor:** none expected; this loop proves the gate has teeth.

## Verification

```bash
gh pr checks --watch
gh run list --workflow=discovery-ingest-ci.yml --limit 5
gh run view <run-id> --log-failed   # for the deliberate-failure runs
```

Also confirm that a PR touching only `apps/web/**` does not trigger the workflow (path filter negative).

## Out of scope

Coverage thresholds, dependency caching beyond pip, browser tests (none exist; chapters 15 and 19 render through Cloudflare's hosted browser), changing any worker behaviour.
