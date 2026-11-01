---
name: "Chapter 1 — Split tag agreement by axis"
overview: "Stop pooling domain and situation codes into one Jaccard tag_agreement number; report the two axes separately everywhere the eval harness surfaces metrics."
todos:
  - id: results
    content: "Give Scores two code pairs (domain, situation) instead of one pooled pair"
    status: pending
  - id: scoring
    content: "Stop concatenating domain_codes and situation_codes in scoring.py"
    status: pending
  - id: summary
    content: "Split Summary.tag_agreement into domain_tag_agreement and situation_tag_agreement"
    status: pending
  - id: targets
    content: "Split MIN_TAG_AGREEMENT into a per-axis constant pair"
    status: pending
  - id: report
    content: "Print and emit both axis numbers in the table and the JSON report"
    status: pending
  - id: tests
    content: "Add the summarise split test and update the command-level assertions"
    status: pending
isProject: false
---

# Chapter 1 — Split tag agreement by axis

**Repo:** `redtape` (`apps/discovery-ingest`) · **Branch:** `feat/situation-tag-coverage-split-tag-agreement-by-axis` · **Status:** planned

**Depends on:** none · **Decisions:** T3 (`.plans/situation-tag-coverage/gaps-and-decisions.md`) — the suite's own record that the harness pools domain and situation Jaccard into one number; grows out of X8 (`.plans/extraction/gaps-and-decisions.md`), the axis-blind consensus rule this suite is measuring · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-situation-tag-coverage`

## Goal

Stop pooling `domain_codes` and `situation_codes` into one Jaccard `tag_agreement` number. Report two numbers — `domain_tag_agreement` and `situation_tag_agreement` — everywhere the eval harness surfaces metrics (the printed table, the JSON report, the `Summary` object), so the situation axis's accuracy is visible on its own instead of being averaged away by the much higher domain-axis number. This is purely a measurement change: no extraction, grounding or consensus behaviour changes.

## Design

The pooling happens at exactly two call sites in `apps/discovery-ingest/discovery_ingest/extract/llm/evaluation/scoring.py`, both of which already have the two axes apart before they concatenate them — `GoldPage` already carries separate `domain_codes`/`situation_codes` tuples (`evaluation/gold.py`), and `Grounded` already carries separate `domain_codes`/`situation_codes` tuples (`ground_state.py:38-39`, both `tuple[str, ...]`). The fix is to stop joining them and thread both tuples through as two pairs instead of one.

**`evaluation/results.py`** — `Scores` (lines 24-36). Replace the one pooled pair with two axis pairs, following the same shape the dataclass already uses for `documents`/`edges` (two separate `Counts`, not one pooled count):

```python
predicted_codes: tuple[str, ...] = ()
gold_codes: tuple[str, ...] = ()
```
becomes
```python
predicted_domain_codes: tuple[str, ...] = ()
predicted_situation_codes: tuple[str, ...] = ()
gold_domain_codes: tuple[str, ...] = ()
gold_situation_codes: tuple[str, ...] = ()
```

This is the smaller, more consistent-with-existing-style change: `Scores` already models "two independent things, scored separately" for documents and edges; doing the same for the two code axes is the pattern already in the file, not a new one. The alternative — keeping one `predicted_codes`/`gold_codes` pair and having `gold_codes()` return two separate tuples that `tag_agreement` zips post hoc — would require either a second parallel pair anyway or reconstructing per-axis membership from a pooled tuple (lossy, since a code string alone doesn't say which axis it came from). Four flat fields is simpler than inventing a `CodesByAxis` wrapper type for two call sites.

**`evaluation/scoring.py`**:
- Delete `gold_codes()` (lines 14-16) — both call sites can read `gold.domain_codes`/`gold.situation_codes` directly now that nothing needs them concatenated.
- `nothing_found()` (lines 23-26): replace `Scores(documents, edges, gold_codes=gold_codes(gold))` with `Scores(documents, edges, gold_domain_codes=gold.domain_codes, gold_situation_codes=gold.situation_codes)`.
- `score_page()` (lines 46-56): replace
  ```python
  predicted_codes=(*grounded.domain_codes, *grounded.situation_codes),
  gold_codes=gold_codes(gold),
  ```
  with
  ```python
  predicted_domain_codes=grounded.domain_codes,
  predicted_situation_codes=grounded.situation_codes,
  gold_domain_codes=gold.domain_codes,
  gold_situation_codes=gold.situation_codes,
  ```

**`evaluation/metrics.py`** — `tag_agreement()` (lines 81-83) is unchanged. It is already a generic pooled-Jaccard function over `Sequence[tuple[Collection[str], Collection[str]]]`; it has no idea it was ever fed pooled codes, so it is reused twice (once per axis) rather than duplicated.

**`evaluation/summary.py`** — `Summary` (lines 19-36): replace `tag_agreement: float` (line 29) with `domain_tag_agreement: float` and `situation_tag_agreement: float`. `summarise()` (line 67): replace the single call with two:
```python
domain_tag_agreement=tag_agreement(
    [(page.scores.predicted_domain_codes, page.scores.gold_domain_codes) for page in pages]
),
situation_tag_agreement=tag_agreement(
    [(page.scores.predicted_situation_codes, page.scores.gold_situation_codes) for page in pages]
),
```

**`evaluation/targets.py`** — `MIN_TAG_AGREEMENT = 0.60` (line 8) becomes two constants:
```python
MIN_DOMAIN_TAG_AGREEMENT = 0.60
MIN_SITUATION_TAG_AGREEMENT = 0.60
```
Call made here: split the threshold rather than keep one blended `MIN_TAG_AGREEMENT` alongside the two component numbers. A blended threshold has nothing left to apply to once `Scores` no longer carries a pooled code pair — computing one anyway would mean re-concatenating the two axes right back together just to gate on them, which is the exact masking this chapter exists to remove. Both constants start at the same 0.60 X14 placeholder as before; this chapter does not change what either axis's floor should be — that is exactly what the suite's live runs (`02-live-runs.md`) and the pending decision (T-PENDING) are for, once the situation-axis number is visible on its own to make the case.

**`evaluation/report.py`** — `_metric_rows()` (lines 39-51): replace the one `tag agreement` row (line 46) with two:
```python
yield f"| domain tag agreement | {_verdict(summary.domain_tag_agreement, MIN_DOMAIN_TAG_AGREEMENT)} |"
yield f"| situation tag agreement | {_verdict(summary.situation_tag_agreement, MIN_SITUATION_TAG_AGREEMENT)} |"
```
and update the `targets` import (line 16) accordingly.

**`evaluation/report_json.py`** — `_summary()` (line 31): replace `"tag_agreement": summary.tag_agreement,` with `"domain_tag_agreement": summary.domain_tag_agreement, "situation_tag_agreement": summary.situation_tag_agreement,`. `_page()` (lines 66-67): replace `"predicted_codes": list(scores.predicted_codes), "gold_codes": list(scores.gold_codes),` with the four per-axis list fields (`predicted_domain_codes`, `predicted_situation_codes`, `gold_domain_codes`, `gold_situation_codes`).

Out of code scope but worth a follow-up touch: `apps/discovery-ingest/README.md` lines 21 and 202 describe "tag agreement" as one metric in prose; update the wording there in the same PR since it is a one-line doc fix, not a design decision.

## Tests

**`apps/discovery-ingest/tests/test_llm_eval_metrics.py`** (already imports `Scores`, `PageResult`, `Usage`, `summarise` and has the `_result()` helper at line 71):

- `test_summarise_reports_domain_and_situation_tag_agreement_as_two_separate_numbers` — build two `PageResult`s via a small local helper that extends `_result()`'s pattern with the four new `Scores` code fields: one page where `predicted_domain_codes == gold_domain_codes == ("housing",)` (domain agrees) and `predicted_situation_codes == ()` while `gold_situation_codes == ("birth-of-child",)` (situation disagrees, mirroring the real production split — domain tagged, situation not, per `00-architecture.md` §1). Assert `summary.domain_tag_agreement == 1.0` and `summary.situation_tag_agreement == 0.0`. Red today: `Scores(...)` has no `predicted_domain_codes`/`gold_situation_codes` keywords yet (`TypeError: unexpected keyword argument`), and `Summary` has no `domain_tag_agreement` attribute. Green: after the field split above.

**`apps/discovery-ingest/tests/test_llm_eval_command.py`**:

- `test_eval_runs_every_gold_page_through_clean_client_and_grounding_and_prints_a_table` (existing, lines 58-80): update the printed-label assertion at line 74 — replace `"tag agreement"` with `"domain tag agreement"` and `"situation tag agreement"` in the tuple of expected labels — and update line 78 from `summary["tag_agreement"] == 1.0` to `summary["domain_tag_agreement"] == 1.0 and summary["situation_tag_agreement"] == 1.0`. The gold fixture this test uses (`eval_fakes.py`'s `LABELS`/`ANSWERS`) has every page's `situation_codes` empty on both sides, so both axis numbers stay `1.0` here — this test proves the plumbing end to end, not axis divergence (that is what the new `test_llm_eval_metrics.py` test is for). Red today: the JSON summary has no `domain_tag_agreement`/`situation_tag_agreement` keys and the table has no such rows. Green: after the report/report_json split above.

Checked and left unchanged: `test_ground_recorded_answers.py` (calls `score_page` but asserts only on grounding/kept counts, never on `predicted_codes`/`gold_codes`) and `test_llm_eval_gold_set.py`/`test_llm_eval_gold.py` (test `load_gold`/`unknown_codes`/`cleaner_recall`, not `Scores` or `Summary`) — none assume the pooled single-pair shape, so none need fixture changes.

Red: the new metrics test and the updated command-level assertions both fail against the unsplit code (missing fields/keys). Green: the design above makes every one pass with the same gold fixtures already committed.

## Verification

```bash
cd apps/discovery-ingest && ./ci.sh
pytest tests/test_llm_eval_metrics.py tests/test_llm_eval_command.py -v
```

No live gate needed for this chapter alone — it is a pure reporting/plumbing change over the existing committed gold set. The situation-axis number this chapter makes visible is what chapters 4 and 5 and the suite's live runs then act on.

## Refactor gate

Check that no other reader of `Scores.predicted_codes`/`Scores.gold_codes` or `Summary.tag_agreement`/`MIN_TAG_AGREEMENT` was missed — `grep -rn "predicted_codes\|\.gold_codes\|tag_agreement\|MIN_TAG_AGREEMENT" apps/discovery-ingest` should return nothing outside the files this chapter touches (plus the two README lines) once done.

## Commits

- `refactor(discovery-ingest): split pooled tag_agreement into domain_tag_agreement and situation_tag_agreement`

## Out of scope

Changing either axis's threshold value (stays 0.60/0.60 pending the live runs' numbers); any change to extraction, grounding or the consensus rule itself; the gold fixtures' actual code content (no new gold page is added here — that is chapters 4 and 5's job once this split exists for them to build on).
