---
name: "Chapter E20 — Quote-grounded rate"
overview: "Split the eval's grounded rate into the share of model items whose quote is on the page (the threshold, 0.95) and the share the pipeline kept (informational), so guard drops for data fields, generic names and repeats stop counting as grounding failures; both numbers are always printed."
todos:
  - id: reasons
    content: "One table assigns every drop reason to grounding or guard, with a test that no reason is unassigned"
    status: pending
  - id: metrics
    content: "Summary, report and JSON carry the quote-grounded rate and the kept rate"
    status: pending
  - id: replay
    content: "Replay the recorded ext-4 answers and record old versus new numbers"
    status: pending
isProject: false
---

# Chapter E20 — Quote-grounded rate

**Repo:** `redtape` (`apps/discovery-ingest`, docs) · **Branch:** `feat/extraction-grounded-rate` · **Status:** planned

**Depends on:** [E5](05-eval-harness-and-model-choice.md) (eval metrics), [E16](16-documents-not-data-fields.md) and [E18](18-non-documents-and-tag-restraint.md) (guard drops), [E19](19-neuron-overshoot.md) (order only) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/extraction`

**Order:** executes after [E19](19-neuron-overshoot.md), before the live runs in [../02-live-runs.md](../02-live-runs.md), so the `ext-5` eval prints the corrected rows. Owner direction 2026-10-30: get as close as possible to the X16 targets, and keep the aim in view (documents as nodes, edges, and domain and life-situation tags for the dependency graph).

## Goal

`grounded_rate` ([metrics.py](../../../apps/discovery-ingest/discovery_ingest/extract/llm/evaluation/metrics.py), [summary.py](../../../apps/discovery-ingest/discovery_ingest/extract/llm/evaluation/summary.py)) is kept items over raw items, so every item that a **guard** removes counts as "ungrounded". On the `ext-4` eval Qwen has no `quote` drop, yet reads 0.87 and, after the E18 guards, 0.64, because `data_field`, `generic_name` and `duplicate` drops are counted. The threshold (0.95) was written for the question "is what the model quotes on the page?", which is the E3 invariant 8 ("grounding is not optional"). A guard drop answers a different question ("is this a document?") that precision and recall already measure.

Report both, always:

| Row | Question | Threshold |
| --- | --- | --- |
| quote-grounded rate | Of the items the model returned, how many quote text that is on the page? | 0.95 (unchanged) |
| kept rate | Of the items the model returned, how many did the pipeline keep? | none (informational) |

This corrects what the metric measures. It does not move the threshold and does not hide a guard drop: the kept rate is printed next to it, and the per-reason drop report stays.

## Contract

1. **One reason table.** `metrics.py` (or a small `drop_reasons.py` beside it) holds a table that assigns each drop reason to a class. `grounding`: `quote`, `dependency_quote`. `guard`: `noise`, `data_field`, `generic_name`, `duplicate`, `dependency_duplicate`, `dependency_endpoint` (a consequence of a missing or rejected document, not a quote failure), and any count cap. The implementer lists the reasons from the call sites of `Tally.lose` and `Tally.drop` in `extract/llm/ground*.py` and finds none left out.
2. **Unlisted reasons fail loudly.** A test iterates every reason the grounding code can produce (collected from a replay of all recorded answers and from a grep-style list in the test) and fails when one is in neither class; an unlisted reason at run time raises in the scorer instead of silently counting as grounded.
3. **Scores and summary.** `Scores` keeps `raw_items` and `kept_items` and gains `quote_failed_items` (count of dropped items in the `grounding` class). `Summary` has `grounded_rate` = `1 - quote_failed / raw` (1.0 with no items, as today) and `kept_rate` = `kept / raw` (the old figure).
4. **Report.** `report.py` prints `| quote-grounded rate | value | target 0.95 |` and `| kept rate | value | |`; `report_json.py` writes `grounded_rate` (now quote-based) and `kept_rate`. The JSON gets no silent change of meaning: the report header line names the metric version (`grounded_rate=quote`), and the ledger notes the change on the day it ships.
5. **Cache replay is free.** Cache keys do not change (**no `PROMPT_VERSION` or `CLEAN_VERSION` bump, no gold label edit**), so a re-run with the cache directory of earlier runs costs 0 neurons and re-scores with the new rule. The chapter's verification replays what exists (the recorded answers in `tests/` and, if present, the operator's eval cache).
6. **Docs.** The starting-threshold sentence in [gaps-and-decisions.md](../gaps-and-decisions.md) (X16) and the eval section of `apps/discovery-ingest/README.md` use the two names; docs tests stay green.

## TDD loops

### Loop A — Reason table

**Red** (`tests/test_llm_eval_metrics.py`, `tests/test_ground_recorded_answers.py`)

1. `quote and dependency_quote are grounding reasons; data_field, generic_name, duplicate, noise, dependency_duplicate and dependency_endpoint are guard reasons`.
2. `every drop reason that grounding produces on the recorded answers is assigned` (negative: a made-up reason is rejected by the scorer).

**Green:** the table and the lookup. **Refactor:** a table, not branching; `metrics.py` stays near its current size.

### Loop B — Rates

**Red** (`tests/test_llm_eval_metrics.py`, `tests/test_llm_eval_gold_set.py`)

1. `a page with only guard drops has a quote-grounded rate of 1.0 and a kept rate below 1.0`.
2. `a page with quote drops lowers both rates`.
3. `no items at all is a full rate for both`.
4. `on the recorded ext-4 Qwen answers the quote-grounded rate is 1.0 and the kept rate equals the old grounded figure` (the old figure is reproduced exactly; use the replay that E18 already built).
5. `on the recorded ext-4 70B answers the quote drops (13) lower the quote-grounded rate and it stays below the 0.95 target`.

**Green:** `Scores`, `summarise`, `grounded_rate` signature (`raw_items`, `quote_failed_items`) and a `kept_rate` function. **Refactor:** the old `grounded_rate(raw, kept)` call sites are renamed so no caller still means "kept".

### Loop C — Report and JSON

**Red** (`tests/test_llm_eval_command.py` or the report tests)

1. `the table prints the quote-grounded rate with its 0.95 target and the kept rate without a target`.
2. `the JSON report has grounded_rate and kept_rate and names the metric version`.
3. `a run that stopped early still prints both rows`.

**Green:** `report.py`, `report_json.py`. **Refactor:** none expected.

## Verification

```bash
cd apps/discovery-ingest && ruff format --check . && ruff check . && mypy discovery_ingest && python -m pytest -q
cd apps/api && python -m pytest tests/test_extraction_docs.py tests/test_extraction_docs_structure.py -q
```

No live call. Record old versus new numbers for Qwen and the 70B in the PR body (the chief copies them into the ledger).

## Out of scope

Segment-wise grounding (the E13 fallback), new name or code guards (a possible E21, written from live-drain evidence, see [gaps-and-decisions.md](../gaps-and-decisions.md)), any prompt, cleaner or schema change, editing gold labels, moving a threshold.
