---
name: "Chapter 11 — Snapshot drain"
overview: "Make the translate drain handle snapshot tasks in batches of five: fetch each page through the machine API, run the pure pipeline, translate its blocks under the document share of the character ledger, validate, and complete. A page whose cleaned text is unchanged costs zero characters. The snapshot schedule is off until the operator enables it."
id: AZ11
depends_on:
  - AZ03
  - AZ08
  - AZ10
touches:
  - apps/discovery-ingest/discovery_ingest/worker/snapshot_fetch.py
  - apps/discovery-ingest/discovery_ingest/worker/snapshot_translate.py
  - apps/discovery-ingest/discovery_ingest/worker/snapshot_settle.py
  - apps/discovery-ingest/discovery_ingest/worker/snapshot_batch.py
  - apps/discovery-ingest/discovery_ingest/client/snapshot_api.py
  - apps/discovery-ingest/discovery_ingest/operations/snapshot_drain.py
  - apps/discovery-ingest/discovery_ingest/cli/translate/
  - apps/discovery-ingest/discovery_ingest/schemas.py
  - .github/workflows/discovery-translate.yml
  - apps/discovery-ingest/tests/
execution: chapter-implementer
---

# Chapter 11 — Snapshot drain

**Repo:** `redtape` (`apps/discovery-ingest`, `.github/workflows`) · **Depends on:** [Chapter 03](03-character-meter-and-floor.md), [Chapter 08](08-snapshot-machine-api.md), [Chapter 10](10-snapshot-pipeline.md) · **Decisions:** [D2](../gaps-and-decisions.md#d2--azure-ai-translator-f0-first-a-19-million-character-monthly-cap), [D6](../gaps-and-decisions.md#d6--snapshot-translations-are-blocks-of-text-not-markup) · **Open seam:** [O7](../gaps-and-decisions.md) · **Rules:** [../../../CLAUDE.md](../../../CLAUDE.md) (package registries) · **Status:** planned

## Goal

Translate snapshot tasks end to end, through the existing drain shape. Documents spend only the document share of the monthly ledger. A stale page, a pruned page and a page whose text has not changed each have a defined outcome, and none of them loses an attempt unfairly.

## Scope

- In: the `translate drain --unit snapshot` mode, the snapshot worker modules, the document-share meter, the workflow step behind its own repo variable, the report.
- Out: the public read (12), the web (13), enqueue and backfill (09).

## Design

1. **CLI.** `translate drain --unit card|snapshot`, default `card`, so the existing behaviour is unchanged. `translate summary` counts snapshot tasks for `--unit snapshot`.
2. **Claim and fetch.** Claim up to 5 tasks. For each, fetch the page through `GET /artifacts/{artifact_id}/content` with the same `X-API-Key`. A 404 means the snapshot was pruned: the task is released with reason `snapshot_gone`, without consuming an attempt, so the next claim gets the newest snapshot.
3. **Zero-character path.** Run the pipeline. If the cleaned hash equals `stored_source_hash`, post `unchanged` with that hash. No reservation is made, and no call is sent.
4. **Skip path.** If the pipeline says skip, post `skipped` with the reason.
5. **Translate.** For `translated`, the non-empty blocks become `TranslationUnit`s (`title` is the block text, `description` is empty). They are sent to the Azure engine for each target locale. The adapter chunks the requests (chapter 02).
6. **Document share.** The meter is `FlooredMeter(CharacterMeter(guard), Floor(azure_translator_chars, (1 − share) × cap))`. `AZURE_DOCUMENT_BUDGET_SHARE` defaults to 0.6, is read in the worker's environment, and is documented in chapter 16. A reservation that would breach the floor is denied, and the batch is released.
7. **Validate and settle.** Validation follows chapter 10. A failing block is posted with `untranslated: true` and its German text. A structural mismatch fails the task permanently with its reason in `last_error`.
8. **Complete.** Post the translated payload through `POST /snapshots/complete`. Answers `stored`, `unchanged` and `stale` are tallied. `stale` is not an error: the server requeues the task.
9. **Stops.** A denial or a `403001` raises the existing `StopDrain`, releases the batch without consuming attempts, and ends the drain as succeeded with its stop reason.
10. **Workflow.** A snapshot step in `discovery-translate.yml`, gated by the repo variable `SNAPSHOT_TRANSLATE_SCHEDULE`, default off. It shares the `discovery-pipeline` concurrency group, runs after the card step, and has its own character precheck.

## Files

| Path | Change |
| --- | --- |
| `worker/snapshot_fetch.py` (new) | fetch and the pruned-snapshot release |
| `worker/snapshot_translate.py` (new) | pipeline call, unit building, engine call |
| `worker/snapshot_settle.py` (new) | validation, untranslated blocks, complete |
| `worker/snapshot_batch.py` (new) | one batch of claimed tasks |
| `client/snapshot_api.py` (new) | machine client for snapshot routes |
| `operations/snapshot_drain.py` (new) | wiring, meter, stop handling |
| `cli/translate/` | `--unit` option; summary per unit |
| `schemas.py` | snapshot report fields |
| `.github/workflows/discovery-translate.yml` | snapshot step behind `SNAPSHOT_TRANSLATE_SCHEDULE` |
| `tests/test_snapshot_drain*.py` (new) | drain tests |

## Red tests

**Happy path**
- `Drain · an unchanged page completes with zero characters reserved and no engine call`
- `Drain · a changed page translates each block into the target locale and completes with blocks`
- `Drain · the characters settled equal the billed figure`
- `Drain · a skipped page completes with its skip reason`
- `Summary · --unit snapshot counts snapshot tasks only`
- `Workflow · the snapshot step is skipped unless SNAPSHOT_TRANSLATE_SCHEDULE is enabled`

**Negative path**
- `Drain · a reservation that would breach the document floor is denied; tasks are released and attempt_count is unchanged`
- `Drain · a 404 for a pruned snapshot releases the task with snapshot_gone and no attempt used`
- `Drain · one block failing validation is posted as untranslated and the page still completes`
- `Drain · a structural mismatch fails the task with its reason in last_error`
- `Drain · an unreadable ledger sends no fetch and no engine call`
- `Drain · a 403001 calls exhaust once and stops the drain`
- `Drain · the API key never appears in logs or the report`

## Green

The smallest change for each red test, starting with the unchanged path, because it is the one that spends nothing.

## Refactor gate

- `snapshot_batch.py` loops over tasks and delegates each task to one function. Outcomes are dispatched through a table keyed by outcome, not a chain of conditions.
- Each module stays under about 100 lines. Functions are about 5 lines, at most 3 parameters.
- The snapshot drain reuses `drain_until_stop`, the lease settle helpers and `MeteredTranslator`. It does not copy them.
- No boolean flags: the unit is a string literal.

## Verification

```bash
cd apps/discovery-ingest
.venv/bin/python -m pytest -q tests/test_snapshot_drain*.py tests/test_translate_drain.py tests/test_translate_workflow.py tests/test_translate_cli.py tests/test_api_contract.py
.venv/bin/ruff format --check . && .venv/bin/ruff check . && .venv/bin/mypy discovery_ingest
cd ../.. && ./ci.sh
```

No live call in CI. The first live snapshot drain is an operator step below.

## Out of scope

The public read (12), the web (13), changing the card schedule, a document-specific glossary gate (O7), chunking a page above 30,000 characters.

## Operator steps after merge

1. Run the snapshot drain manually once, with `--limit 5`, and inspect the report and the coverage page.
2. Set repo variable `SNAPSHOT_TRANSLATE_SCHEDULE=enabled` only after that inspection.

## Git workflow

```bash
git checkout feat/plans-azure-translation && git pull
git checkout -b feat/azure-11-snapshot-drain
# test(ingest): ... (red), feat(ingest): ... (green), refactor(ingest): ... (gate), feat(ops): workflow step
git push -u origin HEAD
# PR into feat/plans-azure-translation
```
