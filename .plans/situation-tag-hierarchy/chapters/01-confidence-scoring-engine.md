---
name: "Chapter 1 — Confidence scoring engine, and persisting it onto published documents"
overview: "Replace TagSupport's accepted boolean and confidence_tier() with one continuous [0, 1] score per code, computed from a direct-source confidence (manual stays a full override, unchanged; PVOG and any future direct source combine via noisy-OR) and a calibrated LLM-evidence curve — then freeze that score onto document_domain/document_life_situation at promotion time, since those link tables carry nothing to sort or style by today."
todos:
  - id: mention-columns
    content: "Add direct_domain_confidence / direct_situation_confidence (nullable float) to DiscoveryCandidateMention"
    status: pending
  - id: score-functions
    content: "Add llm_evidence_score(), noisy_or(), MIN_SUGGESTED_SCORE to tags.py; remove confidence_tier, DEFAULT_MIN_PROCEDURES/SHARE, TagThresholds, axis_thresholds"
    status: pending
  - id: tag-support-shape
    content: "Change TagSupport.accepted: bool to TagSupport.score: float"
    status: pending
  - id: single-candidate-scoring
    content: "Rewrite candidate_axis_support() to score non-manual rows in Python via noisy_or(); keep the manual-override branch (full replace, score=1.0) unchanged"
    status: pending
  - id: bulk-usable-predicate
    content: "Replace _meets()/TagThresholds in the bulk path with a SQL _usable() floor predicate; drop the two axis-specific settings pairs"
    status: pending
  - id: accepted-renames
    content: "Rename accepted_codes/accepted_supports to usable_codes/usable_supports, filtering on score >= MIN_SUGGESTED_SCORE"
    status: pending
  - id: suggestion-payload
    content: "Change SuggestedTags.tag_confidence and NewDocumentPayload.tag_confidence from dict[str, Literal] to dict[str, float]"
    status: pending
  - id: link-table-confidence
    content: "Add confidence: float NOT NULL (migration, backfill 1.0) to document_domain and document_life_situation"
    status: pending
  - id: persist-on-promotion
    content: "Thread tag_confidence through DocumentService.create_from_suggestion/_resolve_tags into DocumentRepository.add/_link_terms"
    status: pending
  - id: tests
    content: "Unit-test the score functions, the rewritten single-candidate path, the bulk predicate, and the promotion-time persistence"
isProject: false
---

# Chapter 1 — Confidence scoring engine, and persisting it onto published documents

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/situation-tag-hierarchy-confidence-scoring-engine` · **Status:** planned

**Depends on:** none · **Decisions:** D1, D6, D7, D8, D9 (`../gaps-and-decisions.md`) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-situation-tag-hierarchy`

## Goal

Every `accepted: bool` in the tagging pipeline becomes a `score: float` in `[0, 1]`. Manual curator overrides keep their existing full-replace behaviour (D4 of `situation-tag-activation` — the one extractor either engine special-cases; unchanged here). Everything else — an LLM-extracted consensus assertion, a PVOG-sourced direct assertion, and later a vote-count term — combines by noisy-OR instead of being filtered by a procedure-count/share threshold. Then, new in this suite (D6): freeze that score onto `document_domain`/`document_life_situation` at the moment a document is created from a suggestion, so it survives for chapter 4's UI to sort and style by — today those link tables are flat membership pairs with nothing to read.

This lands as two commits, mirroring `situation-tag-activation` chapter 1's own precedent of landing a mergeable change and a behavioural change separately within one chapter/deploy.

## Design

### Part A — the scoring engine

**New evidence columns.** `apps/api/app/models/discovery/discovery_candidate_mention.py`: add `direct_domain_confidence: float | None` and `direct_situation_confidence: float | None` (both nullable, default `NULL`). `NULL` means "this mention's assertion is LLM-extracted — score it via the corroboration curve"; a non-`NULL` value means "this mention supplies its own fixed confidence directly" (a clean PVOG leaf, an ambiguous one, or in future a vote-backed estimate), independent of how many other procedures agree. Every existing mention stays `NULL` on both columns — behaviourally a no-op until chapter 3 starts populating `direct_situation_confidence` for PVOG mentions. `TagAxis` (`tags.py`) gains a `confidence_column` property mirroring the existing `column` property, picking the right one of the two per axis.

**Score functions**, `apps/api/app/features/discovery/tags.py`:

```python
MIN_SUGGESTED_SCORE = 0.05
"""Below this, a code isn't offered at all — noise suppression, not a precision claim (D9)."""

LLM_SCORE_BASE = 0.5
LLM_SCORE_STEP = 0.35
LLM_SCORE_CEILING = 0.95

def llm_evidence_score(procedures: int, share: float) -> float:
    """Saturating curve for LLM-only corroboration, anchored to situation-tag-activation's LR1 sample:
    one procedure lands near its measured 37.5-62.5% midpoint, two or more approach the historical
    "high" ceiling. Not yet validated beyond that sample — see gaps-and-decisions.md P1."""
    if procedures <= 0:
        return 0.0
    return min(LLM_SCORE_CEILING, LLM_SCORE_BASE + LLM_SCORE_STEP * (procedures - 1)) * share

def noisy_or(scores: Iterable[float]) -> float:
    """Combine independent evidence: 1 - product(1 - s). A 0.0 term (no evidence) is the identity —
    safe to always pass the LLM score even when there were zero LLM-extracted mentions for a code."""
    remaining = 1.0
    for score in scores:
        remaining *= 1 - score
    return 1 - remaining
```

Delete `confidence_tier()`, `DEFAULT_MIN_PROCEDURES`, `DEFAULT_MIN_SHARE`, `TagThresholds`, `axis_thresholds()` — nothing downstream reads a tier or a threshold once this chapter lands (D1: the rollback decision is moot, not acted on, because there is no threshold left). Delete `discovery_tag_min_procedures`, `discovery_tag_min_share`, `discovery_tag_min_procedures_situation`, `discovery_tag_min_share_situation` from `apps/api/app/config.py` (D8: no per-axis constant survives — both axes now run the same curve).

**`TagSupport`** loses `accepted: bool`, gains `score: float`: `TagSupport(code: str, procedures: int, share: float, score: float)`. `procedures`/`share` keep their existing meaning for display (total distinct procedures/share across *every* source asserting the code, direct or LLM) — `score` is the only field anything now branches on.

**Single-candidate path**, `apps/api/app/features/discovery/repository/candidate_completeness_tags.py::candidate_axis_support()`. The manual branch is unchanged — if any mention asserts the axis with `extractor == MANUAL_EXTRACTOR`, its codes replace everything else, each returned as `TagSupport(code, procedures, 1.0, score=1.0)`, exactly as today's `TagSupport(code, procedures, 1.0, True)`. Only the non-manual path changes: instead of querying the pre-aggregated `code_support()` subquery, fetch the raw per-mention rows for the candidate (`candidate_id, catalogue_service_id, code, confidence`, via `axis.confidence_column`) and score them in Python — this is a handful of rows for one candidate, cheap, and keeps the formula in one readable place instead of a SQL expression:

```python
def _score_rows(rows: Sequence[Row], total_tagged: int) -> list[TagSupport]:
    supports = []
    for code, code_rows in _group_by_code(rows):
        llm_rows = [r for r in code_rows if r.confidence is None]
        direct = [r.confidence for r in code_rows if r.confidence is not None]
        llm_procedures = _distinct_procedures(llm_rows)
        llm_share = llm_procedures / total_tagged if total_tagged else 0.0
        llm_score = llm_evidence_score(llm_procedures, llm_share)
        procedures = _distinct_procedures(code_rows)
        share = procedures / total_tagged if total_tagged else 0.0
        supports.append(TagSupport(code, procedures, share, noisy_or([llm_score, *direct])))
    return supports
```

**Bulk completeness-flag path**, same module, `axis_acceptance()`/`flags_subquery()`/`completeness_subquery()`. Still SQL, still manual-replaces-consensus unchanged (`_manual_branch()` untouched). The non-manual branch's `_consensus()` currently filters `code_support()` by `_meets(thresholds)`; replace that filter with a SQL-expressible `_usable()` predicate standing in for "would this code's score clear `MIN_SUGGESTED_SCORE`" without computing the exact float: a code is usable if it has *any* row with `confidence IS NOT NULL` (any direct source, including a future vote-backed one, is always above the floor — the smallest clarity weight chapter 3 introduces, 0.65, is nowhere near 0.05), **or** its LLM-only procedures/share clears `llm_evidence_score(...) >= MIN_SUGGESTED_SCORE`. This bulk path only ever needs a boolean "is this code worth listing" for the completeness flag and the three remaining `TagThresholds.from_settings()` call sites (`cards.py`, `candidate_completeness_repository.py`, `candidate_relations.py`) — update all three to call nothing (the bulk query no longer takes a thresholds argument at all).

**Downstream renames**, `apps/api/app/features/discovery/candidate_tags.py`: `accepted_codes()`/`accepted_supports()` become `usable_codes()`/`usable_supports()`, filtering on `support.score >= MIN_SUGGESTED_SCORE` instead of `support.accepted`.

**Suggestion payload**, `apps/api/app/features/discovery/candidate_emit_payload.py::SuggestedTags` and `apps/api/app/schema/suggestion/payload.py::NewDocumentPayload`: `tag_confidence` changes from `dict[str, Literal["high", "low"]]` to `dict[str, float]`, built from `usable_supports()`'s `.score` instead of `confidence_tier()`. `NewDocumentPayload`'s existing key-membership validator (every `tag_confidence` key must be in `domain_codes`/`situation_codes`) is unchanged in shape, just typed against floats now.

### Part B — persist the score onto the published document

**Schema.** New Alembic migration adding `confidence: Mapped[float]` (`NOT NULL`, `server_default="1.0"`) to both `document_domain` and `document_life_situation` (`apps/api/app/models/taxonomy.py::_link_table()` — the helper both tables share, so one change covers both). The `server_default` backfills every existing row to `1.0` (D7: there is no mention-level data left to recompute a real score for an already-promoted document; treating existing rows as fully confident is the honest default, not a retroactive scoring attempt).

**Threading the score through promotion.** `apps/api/app/features/documents/service.py::DocumentService.create_from_suggestion()`/`_resolve_tags()`: currently resolves `payload.domain_codes`/`situation_codes` to ids via `taxonomy.resolve_domain_ids/resolve_situation_ids`. Extend this to also build `{id: confidence}` dicts from `payload.tag_confidence`, defaulting any code missing from that dict to `1.0` (a `NewDocumentPayload` authored without `tag_confidence` at all — e.g. a hand-written admin creation — is treated as fully confident, the same default the migration backfill uses). `apps/api/app/features/documents/repository.py::DocumentRepository.add()`/`_link_terms()`: change the `ids: Sequence[UUID]` parameter to `scores: dict[UUID, float]`, writing `confidence` alongside `document_id`/`{term}_id` in the same insert.

**Read side.** `apps/api/app/schema/document/read.py`: add `TaggedTermRead(TermRead)` with `confidence: float`; `DocumentDetail.domains`/`life_situations` change from `list[TermRead]` to `list[TaggedTermRead]`. `apps/api/app/features/documents/document_read.py::DocumentReadMapper` reads the link row's `confidence` column alongside the term when building these lists. The plain `/domains`/`/life-situations` vocabulary endpoints (`TaxonomyController`) are untouched — they list the taxonomy itself, not a document's tags, and never had a confidence to carry.

## Tests

- `llm_evidence_score()`: monotonic in `procedures`, scales with `share`, saturates at `LLM_SCORE_CEILING`, zero at `procedures=0`.
- `noisy_or()`: empty input → `0.0`; a single `1.0` input → `1.0`; two independent `0.5`s combine to `0.75`.
- `candidate_axis_support()`: manual-override branch unchanged (regression-prove against the existing fixture, swapping `True`/`share=1.0` assertions for `score=1.0`); a non-manual fixture with one LLM mention and one direct-confidence mention on the same code scores higher than either alone; a fixture with only a single, low-share LLM mention scores below `MIN_SUGGESTED_SCORE`.
- The bulk `_usable()` predicate agrees with the single-candidate path's `score >= MIN_SUGGESTED_SCORE` on the same fixture (cross-path agreement test, same shape as `situation-tag-activation` chapter 1's own).
- `DocumentRepository.add()`/`_link_terms()`: writes the given confidence per term id; a code missing from `scores` is rejected by the caller contract, not silently defaulted inside the repository (the default-to-`1.0` behaviour lives in `_resolve_tags()`, one layer up, so the repository itself stays a pure write).
- Migration test: backfilled existing rows read back as `1.0`.

## Verification

```bash
cd apps/api && ./ci.sh
pytest tests/test_discovery_tags.py tests/test_candidate_completeness_tags.py tests/test_discovery_candidate_emit.py tests/test_document_service.py tests/test_document_repository.py -v
```

Commit Part A and prove it green before adding Part B on top — two commits, one chapter/PR, same discipline as the precedent chapter.

## Refactor gate

`grep -rn "confidence_tier\|DEFAULT_MIN_PROCEDURES\|DEFAULT_MIN_SHARE\|TagThresholds\|axis_thresholds\|\.accepted\b" apps/api/app/features/discovery` should return nothing once Part A lands. `grep -rn "discovery_tag_min" apps/api` should return nothing anywhere once the four settings fields are deleted.

## Commits

- `refactor(api): replace the accept/reject tag gate with a combined, continuous confidence score`
- `feat(api): persist tag confidence onto document_domain/document_life_situation at promotion`

## Out of scope

Populating `direct_situation_confidence`/`direct_domain_confidence` for PVOG mentions (chapter 3 — this chapter only adds the columns and the scoring logic that reads them); the groups taxonomy (chapter 2); any UI rendering of the persisted confidence (chapter 4); wiring a real vote-count term into the noisy-OR combination (D5 — out of scope for this suite entirely; the combination function already accepts an arbitrary list of scores, so a future term slots in without reshaping this chapter's work).
