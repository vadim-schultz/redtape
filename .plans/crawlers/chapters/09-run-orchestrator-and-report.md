---
name: "Chapter 9 — Run orchestrator and report"
overview: "python -m crawler.run wires fetching, extraction, submission and evidence together across all enabled sources, producing a JSON report and an exit code that reflects real failures, with a --dry-run mode that never writes."
todos:
  - id: run-source
    content: "run_source(source) processing one source end to end"
    status: pending
  - id: report
    content: "RunReport and the CLI entry point"
    status: pending
isProject: false
---

# Chapter 9 — Run orchestrator and report

**Repo:** `redtape` (`apps/crawler`) · **Branch:** `feat/crawler-orchestrator` · **Status:** planned

**Depends on:** [6](06-first-extractor.md), [8](08-evidence-submission.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §7 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

One command runs the whole pipeline over every enabled source and reports exactly what happened: how many
candidates were found, created, duplicate, failed, and with or without evidence — this is what the GitHub
Actions job (chapter 10) actually invokes.

## Design decisions

**`run_source(source, fetcher, extractor, suggestion_client, evidence_client, screenshot, *, dry_run) ->
SourceReport`**: fetch the source's `start_url`, extract candidates, and for each one — submit (skip
entirely in `dry_run`), on `Created` capture a screenshot and upload it, on `Duplicate` or `Error` record
the outcome without capturing a screenshot (no point capturing evidence for something that was not created
or that failed validation). Each step's failure is caught **per candidate**: one bad candidate does not stop
the rest of the source, and one failed source does not stop the rest of the run (a `try`/`except` boundary
around each candidate and around each source, each logged into the report — this is the one place in the
suite where broad exception handling is deliberate and documented, not a smell, because a scheduled batch
job's job is to make maximum forward progress and report, not to crash on the first surprise).

**`RunReport`**: `{sources: [{source_id, fetched: bool, candidates_found, created, duplicates, errors,
evidence_attached, evidence_failed}], started_at, finished_at}`, serialized to JSON on stdout and optionally
written to a file (`--report-path`).

**Exit code**: 0 if every source fetched successfully (regardless of individual candidate duplicates —
those are expected, D7); non-zero if any source failed to fetch or extract entirely, so the workflow can
fail loudly on infrastructure problems while staying quiet on ordinary duplicate noise.

**CLI** (`argparse`, matching `import_openplz_locations.py`'s style): `--source <id>` (repeatable, default
all enabled), `--dry-run` (fetch and extract, never call the submission or evidence clients — useful for
verifying an extractor against the live page, as chapter 6's manual check uses), `--report-path`.

## Files

| Path | Change |
| --- | --- |
| `apps/crawler/crawler/orchestrator.py` | `run_source`, `RunReport` |
| `apps/crawler/crawler/run.py` | CLI entry point |
| `apps/crawler/tests/test_orchestrator.py`, `test_run_cli.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `run_source · a fully successful source creates suggestions and attaches evidence for each` | Report counts |
| `run_source · a duplicate candidate is counted, not treated as an error` | `duplicates` incremented, `errors` not |
| `run_source · a candidate whose submission errors does not stop the rest of the source` | Later candidates still processed |
| `run_source · a failed screenshot capture is recorded as evidence_failed, the suggestion still exists` | Partial success |
| `run_source · dry_run never calls the submission or evidence clients` | Fakes record zero calls |
| `run_source · a source whose fetch fails is recorded, not raised` | Report shows `fetched: false` |
| `RunReport · serializes to valid JSON` | Round trip |
| `CLI · --source filters to the named sources` | Only those run |
| `CLI · exits non-zero when any source failed to fetch` | Exit code |
| `CLI · exits zero when all sources fetched, even with duplicates and per-candidate errors` | Exit code |

## Green

1. `run_source` happy path with fakes for every collaborator; test 1.
2. Duplicate and per-candidate error handling; tests 2–4.
3. Fetch failure and dry-run; tests 5–6.
4. Report serialization; test 7.
5. CLI wiring and exit codes; tests 8–10.

## Refactor gate

`run_source` composes named steps (`_fetch`, `_extract`, `_process_candidate`); `_process_candidate` is the
one place with the deliberate broad `except`, commented as such. If the orchestrator exceeds ~100 LOC,
extract a `CandidateProcessor`. Report the outcome.

## Verification

```bash
cd apps/crawler
python -m pytest tests/test_orchestrator.py tests/test_run_cli.py -m "not needs_playwright"
cd ../.. && ./ci.sh
python -m crawler.run --dry-run --report-path /tmp/report.json && cat /tmp/report.json
```

## Out of scope

Scheduling the run (chapter 10).

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/crawler-orchestrator
```

```text
test(crawler): describe the run report and its per-candidate failure isolation

feat(crawler): add the run orchestrator and CLI
```
