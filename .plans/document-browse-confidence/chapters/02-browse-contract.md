---
name: "Chapter 2 — Browse contract"
overview: "Make the public candidate list filter by presence of any selected code regardless of score, accept several codes per axis, add a confidence sort key and default order, and return the filter-aware card confidence computed by the same SQL expression the sort uses."
todos:
  - id: codes-filter
    content: "CSV codes_filter parser (1-20 codes of 1-64 chars) for filter[domain] and filter[situation]"
    status: pending
  - id: presence-filter
    content: "PublicCandidateFilter matches by EXISTS over the score model: OR within an axis, AND across axes"
    status: pending
  - id: confidence-sort
    content: "PublicSortKey.CONFIDENCE, new default order, card confidence from the same expression"
    status: pending
  - id: unknown-codes
    content: "422 per unknown code in CandidateReadService"
    status: pending
  - id: tests
    content: "Filter, sort, card-confidence and 422 tests; update public API characterisation"
    status: pending
isProject: false
---

# Chapter 2 — Browse contract

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/document-browse-confidence-browse-contract` · **Status:** planned
**Depends on:** Chapter 1 ([01-candidate-tag-scores.md](01-candidate-tag-scores.md)) · **Architecture:** [../00-architecture.md](../00-architecture.md) §3 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-document-browse-confidence` · **Release branch:** `main`

## Goal

`GET /api/v1/candidates` becomes the document list: selecting domain and life-situation chips returns **all** documents carrying any selected code, whatever its confidence; the list can be sorted by confidence; every card carries the confidence the circle will show.

## Design

All paths under `apps/api/app/`.

### Parsing — `features/candidates/list_query.py`

- Replace `_code_filter` with `codes_filter(raw) -> FilterValue`: split on `,`, strip, reject empty items, each item 1–64 characters, at most 20 items, de-duplicate and return the normalised CSV string (`FilterValue` is `str | int`, so the filter stays a string). A violation raises `ValueError` with a client-facing message (the shared parser turns it into a 422 for that parameter).
- `PUBLIC_CANDIDATE_SPEC.sort_keys` follows `PublicSortKey`, so adding the enum member adds the key.
- `public_filter_from` splits the CSV into `domains: tuple[str, ...]` and `situations: tuple[str, ...]`.

### Filter and order — `features/candidates/repository/public_filter.py`

- `PublicCandidateFilter.domain/situation: str | None` become `domains/situations: tuple[str, ...] = ()`.
- `conditions()`: for each non-empty axis, `EXISTS (SELECT 1 FROM tag_scores WHERE candidate_id = … AND axis = … AND code = ANY(:codes))` (any score). Drop the `_accepted(...)` predicates on `accepted_*_codes` for these two filters. `complete` and `q` conditions are unchanged.
- `PublicSortKey.CONFIDENCE = "confidence"`. Define `confidence_expression(tag_scores, filter) -> ColumnElement[float]`: a scalar subquery `coalesce(max(score), 0.0)` over the candidate's score rows restricted to the selected codes (per axis) when any are selected, else over all rows.
- `ordering()`: the default (no `sort_by`) is `confidence desc, completeness desc, mention_count desc, *tie_break()`. `sort_by=confidence` honours `sort_order`, with the same tie-break.
- `repository/cards.py::CardRow` gains `confidence: float`; `list_card_rows` selects the same `confidence_expression` it orders by, so the displayed number and the sort key are one expression (invariant 3). `get_card_row` (detail) computes it with an empty selection.

### Schema and service

- `schema/candidate/read.py::CandidateCard.confidence: float`; `card_builder.card_for` copies it from the row.
- `features/candidates/service.py::_reject_unknown_codes` checks every code of both axes against `known_domain_codes`/`known_situation_codes` and reports one `InvalidParam` per unknown code (`filter[domain]`, `filter[situation]`).

## Tests

Happy path (`tests/test_candidates_public_api.py` and a new `tests/test_candidates_browse.py` using `candidates_public_world.py`):
- A chip filter returns candidates whose only matching code scores below the old 0.05 floor and ones that score 0.9.
- `filter[domain]=a,b` returns the union; `filter[domain]=a&filter[situation]=x` returns the intersection of axes.
- `sort_by=confidence&sort_order=asc|desc` orders by the card confidence; with no `sort_by`, the order is confidence desc.
- `card.confidence` equals the max score over the selected codes, and the max over all tags when none is selected.
- `filter[complete]=yes|no` still behaves as before.

Negative path:
- 21 codes → 422 naming `filter[domain]`; an empty item (`a,,b`) → 422; a 65-character code → 422.
- An unknown code → 422 naming that code; two unknown codes → two errors.
- `sort_order` without `sort_by` → 422 (existing behaviour, pinned).
- A selected code that no candidate has → empty page, `total == 0`, not an error.

Update `tests/test_controller_params_characterization.py` or the public-API characterisation where it pins the old single-code, floor-gated behaviour.

## Verification

```bash
cd apps/api && uv run pytest tests/test_candidates_browse.py tests/test_candidates_public_api.py tests/test_list_query.py
./ci.sh
```

## Data-design gate

Applies (changes the read query of a list endpoint). Record: EXISTS predicates per axis use the score relation once per filter (not per row of the page); the confidence subquery is evaluated once per returned row; no new index; materialisation deferred (seam S3). Findings table as in chapter 1.

## Refactor gate

Scan `public_filter.py` (Data Clumps: `domains`, `situations` travel together into both `conditions()` and `confidence_expression()` — introduce one `Selection` value if the scan agrees), `list_query.py` and `repository/cards.py`. Respect the 5-line function limit.

## Commits

- `feat(api): filter candidates by presence of any selected code, several codes per axis, regardless of score`
- `feat(api): sort candidates by confidence and return the filter-aware card confidence`

## Out of scope

Any web change; a `group` filter in the API (D9); the completeness read model; removing the `complete` filter.
