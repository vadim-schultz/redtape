---
name: "Chapter 1 — Candidate tag scores"
overview: "Compute the per-(candidate, axis, code) tag score for the whole candidate pool in one SQL relation that mirrors the Python scorer, with no inclusion floor, and expose each tag's confidence on the candidate card."
todos:
  - id: score-model
    content: "candidate_tag_scores(candidate_id, axis, code, score) SQL relation beside candidate_completeness_tags.py"
    status: pending
  - id: parity
    content: "Parity test: SQL score equals candidate_axis_support score for every world-fixture candidate"
    status: pending
  - id: tag-confidence
    content: "CandidateTag.confidence; card_for builds tags from the score model, most confident first"
    status: pending
  - id: tests
    content: "Happy and negative tests; data-design gate note on query cost"
    status: pending
isProject: false
---

# Chapter 1 — Candidate tag scores

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/document-browse-confidence-tag-scores` · **Status:** planned
**Depends on:** none · **Architecture:** [../00-architecture.md](../00-architecture.md) §3 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-document-browse-confidence` · **Release branch:** `main`

## Goal

The bulk (list) path knows only whether a code is *usable* (`code_support()` in `candidate_completeness_tags.py` returns a boolean against the 0.05 floor), while the exact score exists only in the single-candidate Python path (`candidate_axis_support` → `_score_rows`). To filter by presence, sort by confidence and show a number per tag, the whole pool needs the exact score in SQL. After this chapter every candidate card lists all of its tags with their confidence, and nothing yet changes about filtering or ordering (chapter 2).

## Design

### Score model

In `apps/api/app/features/discovery/repository/` (a new module `candidate_tag_scores.py`, keeping `candidate_completeness_tags.py` under the size rules), add `tag_scores_subquery() -> Subquery` returning rows `(candidate_id, axis, code, score)` for both axes. It is the SQL mirror of `_score_rows`/`candidate_axis_support`:

- **Manual override.** If a candidate has any mention with `extractor == MANUAL_EXTRACTOR` on an axis, that axis' rows are exactly the manually asserted codes, each at score `1.0`; no other code of that axis appears (same as `candidate_axis_support`'s early return).
- **Otherwise**, per `(candidate, code)`: `llm_procedures` = distinct `catalogue_service_id` over mentions with no direct confidence; `share = llm_procedures / tagged` where `tagged` is the distinct procedures that tag anything on the axis (reuse `_exploded`, `_tagged`, `_support_rows`, `_llm_score_sql`); `llm_score = least(CEILING, BASE + STEP * (llm_procedures - 1)) * share`; the direct confidences of the mentions that carry one are combined with `llm_score` by noisy-OR.
- **SQL noisy-OR.** `1 - exp(sum(ln(1 - least(c, 1 - 1e-9))))` over `[llm_score, *direct]`. A `0.0` term contributes `ln(1) = 0`. The clamp keeps `ln` finite when a source reports `1.0`; the parity test pins the tolerance (`1e-6`).
- **No floor.** Rows are emitted for every code with at least one mention; `usable_codes`/`usable_supports` and `MIN_SUGGESTED_SCORE` stay untouched for the (dormant) emit path.
- Reuse the constants from `app/features/discovery/tags.py`; add no constant.

`code_support()` and `axis_acceptance()` (used by the completeness read model and its flags) are **not** changed (seam S2).

### Card

- `apps/api/app/schema/candidate/read.py::CandidateTag` gains `confidence: float`.
- `apps/api/app/features/candidates/card_builder.py::card_for` builds `domains`/`situations` from the score model instead of `done.accepted_*_codes`, sorted by confidence desc then code. `CardContext` gains the scores for the page (`Mapping[UUID, ...]`), loaded in one query by a new repository method in `apps/api/app/features/candidates/repository/` (next to `completeness_for`).
- `CandidateCard.confidence` is **not** added here (chapter 2 adds it with the filter-aware definition).

## Tests

Happy path:
- `tests/test_candidate_tag_scores.py` parity test: for every candidate of the existing worlds (`tests/completeness_world.py`, `tests/candidates_public_world.py`; extend them where a case is missing) the SQL score equals the `candidate_axis_support` score within `1e-6`, for: LLM-only one procedure, LLM-only two procedures, a PVOG direct confidence alone, LLM plus PVOG (noisy-OR), a manual override (other codes absent), and a code below the old 0.05 floor (present in SQL).
- A candidate card lists every tag with its confidence, most confident first.

Negative path:
- A candidate without mentions has no rows; a manual override hides the consensus codes of its axis only (the other axis keeps its consensus).
- A direct confidence of exactly `1.0` yields score `1.0`, not `NaN` or an error.

## Verification

```bash
cd apps/api && uv run pytest tests/test_candidate_tag_scores.py tests/test_candidates_public_api.py tests/test_candidate_completeness.py
./ci.sh
```

## Data-design gate

Applies (a new read model computed on every list request). Record in the chapter result: the query plan note for the score relation over the current mention count, that it adds no write path, no index and no migration, and that materialising it is the documented answer if chapter 11 finds it slow (seam S3). Findings as `apply | observed | accepted-risk`.

## Refactor gate

Scan `candidate_completeness_tags.py` and the new module against `smells.md`. Expected: Duplicated Code between the Python scorer and the SQL scorer is **inherent** (two languages, one rule) and held together by the parity test and the shared constants — record it as `observed`, not a defect. Check `_exploded`/`_support_rows` reuse instead of copies, and the 5-line / 100-line limits from `code-structure.md`.

## Commits

- `feat(api): compute per-code tag scores for every candidate in SQL, parity-tested against the Python scorer`
- `feat(api): list every scored tag with its confidence on the candidate card`

## Out of scope

Filtering, sorting, `CandidateCard.confidence` (chapter 2); the completeness flags; the emit payload; any web change.
