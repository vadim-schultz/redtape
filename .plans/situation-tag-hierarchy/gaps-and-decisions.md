---
name: Situation tag hierarchy — Gaps and decisions
overview: "Settled decisions, open seams and recorded risks for replacing every accept/reject tag threshold with a continuous confidence score, grouping the situation taxonomy, and extending PVOG leaf refinement."
isProject: false
---

# Situation tag hierarchy — Gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md) · **Prior suite decisions:** [situation-tag-activation](../situation-tag-activation/gaps-and-decisions.md) (D-PENDING — superseded, see D1 below)

## Settled

| # | Decision |
| --- | --- |
| D1 | **`situation-tag-activation`'s D-PENDING rollback recommendation is not executed.** `discovery_tag_min_procedures_situation` stays at `1` (vadim.schultz, 2026-11-01). It becomes moot once chapter 1 removes the binary accept/reject gate it fed — there is no threshold left to roll back once acceptance is a continuous score. This closes that suite's D-PENDING row for A1 without acting on its own recommendation, superseding it rather than following it. |
| D2 | **Full chapter-based suite, not a smaller first slice** (vadim.schultz, 2026-11-01) — grouping, scoring and leaf refinement ship together as one suite, following the `situation-tag-coverage` → `situation-tag-activation` precedent, rather than shipping grouping alone first. |
| D3 | **The 8-group split in `00-architecture.md` §4 is confirmed as the starting taxonomy** (vadim.schultz, 2026-11-01) — not re-opened for this suite; a future suite can revisit it once real browsing data exists, since groups (unlike the 18 situation codes) are new and still cheap to adjust. |
| D4 | **PVOG leaf refinement ships now, as committed scope** (vadim.schultz, 2026-11-01) — not deferred pending a coverage-ceiling measurement, because the facet is deterministic-only (zero LLM accuracy risk) and PVOG already covers a sizeable share of the catalogue. |
| D5 | **Curator voting stays out of scope** (vadim.schultz, 2026-11-01). The scoring design (chapter 1) includes a vote-count term so voting can slot in later without rework, but no queue, review workflow, or UI for feeding votes is built in this suite — that is a social-layer product decision, not a classification-pipeline one. |
| D6 | **Persisting confidence onto published documents is in scope, discovered during this suite's own design, not in the originating conversation.** `document_domain`/`document_life_situation` are flat membership links with no score column — a continuous score computed pre-promotion is invisible on every already-published document unless frozen onto the link row at promotion time. Without this, chapter 4's "sort/style by confidence" has nothing to read for anything already in the catalogue. Added as chapter 1's Part B, mirroring `situation-tag-activation` chapter 1's own precedent of landing a mergeable change and a behavioural change as two commits in one chapter. |
| D7 | **Existing published tag rows backfill to confidence `1.0`, not a recomputed value.** Unlike `situation-tag-activation`'s D1 (no backfill needed, because confidence was never persisted), this suite does persist confidence — so every row written before chapter 1 ships needs *some* value. There is no mention-level data left to recompute a real score from for an already-promoted document, and a document's tags were, by construction, reviewed under whatever gate was active when it was promoted; treating them as fully confident is the honest default, not an attempt to retroactively score them. |
| D8 | **The noisy-OR combination and the per-source score functions are applied identically to both axes** (domain and situation) — chapter 1 does not special-case the situation axis the way `situation-tag-activation` did (that suite's axis-aware thresholds, D2 there, are superseded by D1 above: there is no axis-specific threshold left to differ). Domain's LLM-evidence curve uses the same shape as situation's; no data suggests domain needs a different one, and inventing one unmeasured would be an unforced change. |
| D9 | **A code with no deterministic source and zero procedures of LLM support is never offered at all** — the inclusion floor (`MIN_SUGGESTED_SCORE`) exists purely to avoid proposing a code backed by nothing, and is tuned for noise suppression, not validated against a precision bar. |
| D10 | **Chapter 3 depends on chapter 1 — corrected from the originating design session's assumption that all three build chapters (1, 2, 3) could run in parallel.** Both chapters touch `document_life_situation` (chapter 1 adds `confidence`, chapter 3 adds `pvog_leaf_code`), and chapter 3 populates the `direct_situation_confidence`/`direct_domain_confidence` mention columns chapter 1 defines. Caught while writing chapter 3's own design, not in the original conversation — `01-rollout.md`'s dependency graph and execution order were updated to match; chapter 2 is unaffected and still runs independently. |

## Pending decisions

### P1 — Where exactly to anchor the LLM evidence curve and the Wilson-estimator prior. Status: open, forcing spike: chapter 5 ([chapters/05-live-validation.md](chapters/05-live-validation.md))

Chapter 1's LLM evidence curve (`llm_score(procedures, share)`) is calibrated against `situation-tag-activation`'s own LR1 sample — `procedures=1` anchored near the 37.5–62.5% midpoint it measured, `procedures>=2` anchored near the historical "high" meaning — but that sample was 16 candidates, AI-labelled, not a human domain expert's. The curve's exact constants (chapter 1's `§Design`) are a reasonable first calibration, not a validated one. Chapter 5's live validation is the forcing check: hand-label a fresh post-deploy sample and compare the curve's predicted scores against it, tightening the constants if they're off by more than a small margin. The Wilson-lower-bound prior for the (currently unused, D5) vote term has no production data to anchor it at all yet — left as a documented placeholder in chapter 1's design until voting is actually fed by a later suite.

### P3 — Human sign-off on chapter 3's new domain-hint table. Status: open, blocking chapter 3's domain-hint half only

Chapter 3 ([chapters/03-pvog-leaf-refinement.md](chapters/03-pvog-leaf-refinement.md)) introduces `PERSONAL_MATTER_TO_DOMAIN` — 14 PVOG citizen leaves mapped to 6 existing domains (`taxes-finance`, `identity-civil-status`, `law-justice`, `social-benefits`, `education`, `family-children`), a first pass done in this suite's own design, never reviewed by anyone. Unlike the situation-axis mapping-clarity weights (which only annotate leaves `situation-tag-coverage`'s T4 sign-off already reviewed), this table itself needs the same kind of spot-check T4 got before it ships — chapter 3's own Step 0. The situation-axis work (clarity weights, leaf-refinement facet) is not blocked by this.

### P2 — Whether the eight groups need adjustment once real browsing/filter data exists. Status: open, not blocking this suite

D3 confirms the starting split; this row exists only to flag that it is not expected to be the last word. Revisit only if a later suite finds evidence (e.g. one group absorbing a disproportionate share of traffic, or a situation code that reads oddly under its assigned group) — not scoped here.

## Open seams

| Seam | Placeholder | Forcing condition |
| --- | --- | --- |
| The vote-count term in chapter 1's noisy-OR combination has no real input yet | Contributes nothing (identity element) until a later suite wires `apps/api/app/features/voting/` to actually cast votes against a code — see D5 | A future suite building that queue |
| Domain-hint recovery (chapter 3) only covers 14 of the 24 unmapped citizen leaves | The remaining 10 (civic engagement, hobbies, travel, environment) have no clean analogue among the 13 existing domains and stay unmapped, same as today | A future domain-taxonomy change, if one is ever proposed — not forced by anything in this suite |
| Sorting a document list by confidence when more than one situation filter is selected (chapter 4) uses `max(confidence)` across the selected situations' link rows, not a combined score | A pragmatic first choice, not measured against any alternative (e.g. average, or per-situation separate rankings) | Revisit only if real usage shows `max` produces a confusing order once multi-select filtering sees real traffic |

## Candidate future work (not scoped — a new suite, if pursued)

| Idea | Rationale | Open questions before scoping |
| --- | --- | --- |
| Feed the vote-count term for real: build the review queue `situation-tag-activation`'s own "Deferred: curation queue" (and this suite's D5) both left out | The scoring design already has a slot for it; the dormant voting pathway (`apps/api/app/features/voting/`, 0 rows ever) is the natural backstop once low-confidence tags are actually visible to users via chapter 4 | Needs a product decision on who reviews what and how a vote surfaces to a curator — out of scope for a classification-pipeline suite |
| Revisit the 8-group split with real usage data (P2) | Groups are new, cheap to adjust now, expensive once documents/UI depend on them for a long time | Needs real browsing/filter telemetry, which does not exist until chapter 4 ships |

## Risks

| Risk | Mitigation |
| --- | --- |
| Replacing a binary gate with a continuous score could make *every* candidate's code look plausible if the UI doesn't actually render the gradient distinctly | Chapter 4's design renders confidence as a visible gradient (opacity/weight), not a flat badge — reviewed against real pages in chapter 5, the same way `situation-tag-activation`'s own live run checked its binary tier |
| Backfilling existing tag rows to `1.0` (D7) overstates confidence for rows that were, in fact, accepted only under the now-removed relaxed threshold | Acceptable and explicit: those rows already went through whatever review/consensus gate was active at promotion time; this suite does not re-litigate past promotions, only how confidence is computed and shown going forward |
| The LLM evidence curve's constants (P1) are a first calibration against a 16-sample AI-labelled set, the same caveat `situation-tag-activation`'s own LR1 carried | Chapter 5 is the explicit forcing check before this is called settled, following the same measure-first house convention |
| Sorting by `max(confidence)` across multiple selected situations (open seam above) could look wrong in an edge case nobody has tested yet | Flagged explicitly rather than silently shipped as if validated; revisit only if usage shows it's actually confusing |
