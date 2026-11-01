---
name: Situation tag activation — Gaps and decisions
overview: "Settled decisions, open seams and recorded risks for shipping axis-aware situation tagging, a confidence tier and the PVOG corroboration signal."
isProject: false
---

# Situation tag activation — Gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md) · **Live runs:** [02-live-runs.md](02-live-runs.md) · **Parent decisions:** [situation-tag-coverage](../situation-tag-coverage/gaps-and-decisions.md) (T1–T3, T-PENDING)

## Settled

| # | Decision |
| --- | --- |
| D1 | **No backfill chapter is needed — closes the parent suite's open seam "re-scoring existing candidates after a threshold change."** Confidence (`TagSupport.procedures`/`.share`) is computed live on every read, never stored: no model/migration carries it, `accepted_codes()` collapses `TagSupport` to a bare `str`, and `SuggestedTags`/`new_document_payload()` carry only bare code lists into `NewDocumentPayload` (`extra="forbid"`). A threshold change takes effect on the very next read of any existing candidate, with zero migration and no recompute step. |
| D2 | **Scope is situation-axis only; domain's threshold is untouched.** The parent suite's LR2 shows the asymmetry is axis-specific, not just a shared count-floor problem: even within the 14% of candidates with 2+ procedures, situation never corroborates while domain does. No data in the parent suite's live runs supports relaxing domain's rule, and relaxing an axis nobody measured a problem on would be an unforced, unverified behaviour change. |
| D3 | **The two consensus engines merge in chapter 1, before the axis-aware threshold lands, as two separate commits in the same chapter/deploy — not two chapters.** Splitting the merge and the threshold change across chapters would reopen exactly the transient-divergence risk the merge exists to close (one engine axis-aware, the other still flat, for the span between two deploys). Keeping them in one chapter, as two commits, gets the regression-proof (merge first, prove behaviour-preserving) without ever shipping a half-merged state to production. |
| D4 | **The PVOG mention gets no special-casing in consensus.** It sits on its own real, distinct `catalogue_service_id`, so when a candidate is also mentioned by a different, LLM-extracted procedure asserting the same situation, the two together can satisfy even the unrelaxed 2-procedure bar — genuine independent corroboration, not just "one more vote under an already-loosened floor." It flows through the merged engine completely unmodified, the same way `MANUAL_EXTRACTOR` is the only extractor value either engine singles out today. |
| D5 | **The confidence tier is keyed off the constant historical floor (`DEFAULT_MIN_PROCEDURES=2`), not the now-axis-aware settings.** This is what makes `"high"` mean something stable across future threshold tuning: "would have passed even under the strict historical floor," regardless of which relaxed rule is active for either axis at the time. |

## Pending decisions

### D-PENDING — Whether the shipped relaxed threshold and PVOG signal hold up on hand-labelled precision. Status: open, forcing spike: [02-live-runs.md](02-live-runs.md)

Mirrors the parent suite's T-PENDING shape, now against the real shipped change instead of an offline variant. This suite's working bet (chief of staff, not yet confirmed by live numbers): both A1 (axis-aware threshold) and A2 (PVOG signal) are worth shipping now, backstopped by the existing curator-override mechanism — but neither's actual precision on real, newly-qualified candidates has been checked by a human yet. The parent suite's LR4 found the *coverage* story (0 → 19 of 4,627 candidates under `min_procedures=1`) but explicitly never ran the precision half.

Fill in after the post-deploy live run ([02-live-runs.md](02-live-runs.md)):

| Mechanism | Coverage (parent suite) | Precision signal | Verdict |
| --- | --- | --- | --- |
| A1 (axis-aware threshold alone) | baseline 0 of 4,627; `min_procedures=1` recovers 19 (`situation-tag-coverage` LR4) | not yet run | _pending post-deploy live run_ |
| A2 (PVOG corroboration) | vocabulary maps cleanly to 12 of 18 situation codes, 15.3% of 118 leaves (`situation-tag-coverage` LR3) | not yet run; also gated on chapter 3's own Step 0 human mapping sign-off | _pending post-deploy live run and Step 0 sign-off_ |

**Remaining before this can flip to settled:** (1) chapters 1–3 shipped and deployed; (2) chapter 3's Step 0 human spot-check of the LR3 mapping recorded in the parent suite's `gaps-and-decisions.md`; (3) the post-deploy hand-labelling run itself (~20–30 candidates via the admin UI), split by which mechanism newly qualified each one.

**Cross-reference — supersedes the parent suite's T-PENDING resolution path.** `situation-tag-coverage/gaps-and-decisions.md`'s T-PENDING entry is annotated: "A1/A2 (this suite's axis-aware threshold and PVOG signal, equivalent to parent S4/S3) now shipping via `situation-tag-activation`; see that suite's D-PENDING for the resolution," following the `discovery-operations` D7 → `discovery-throughput` D5 cross-suite-supersession precedent. T-PENDING itself stays open in the parent suite until this suite's D-PENDING settles.

## Open seams

| Seam | Placeholder | Forcing condition |
| --- | --- | --- |
| PVOG dedupe keeps only the first Lebenslage per row (`iter_records`'s `seen_lb_ids`) | Carried as-is from the parent suite; one plausible situation per row | Fix only if multi-situation PVOG coverage turns out to matter after this suite ships |
| PVOG/LLM overlap is unmeasured | Chapter 3's one-off read-only production count (how often a PVOG-catalogued procedure and an LLM-extracted procedure co-mention the same candidate) | If the count comes back near zero, A2's corroboration story (D4) delivers far less than hoped — revisit before leaning on it further |
| Whether the voting pipeline has ever promoted anything in production | Unknown — frontend has zero consumers of the voting API today | The chief of staff confirms this as part of the post-deploy live run (`02-live-runs.md`), since it affects how much safety net "nothing reaches the catalogue without crossing the vote threshold" actually provides right now |

## Risks

| Risk | Mitigation |
| --- | --- |
| The engine merge (chapter 1) hides a real behaviour change inside what looks like a refactor | The chapter's own regression-proof test — `candidate_axis_support()` returning the same `TagSupport` values the deleted Python `aggregate_tags()` used to, on an identical fixture — plus the merge landing as its own commit before the threshold change, specifically so a regression can be bisected to one or the other |
| Relaxing situation consensus could surface more wrong situation tags to reviewers | Nothing is auto-emitted, same as today; the confidence tier (chapter 2) flags which codes only cleared the relaxed bar, and the post-deploy live run is the forcing check before this is called settled |
| Hand-labelling a small post-deploy sample is noisy | Split explicitly by mechanism (A1 vs A2) so either knob can be rolled back independently from its own sample, rather than one blended verdict forcing an all-or-nothing rollback |
| PVOG vocabulary mapping was an AI first pass, not yet human-confirmed | Chapter 3's Step 0 blocking prerequisite — implementation does not start until a human sign-off is recorded in the parent suite's `gaps-and-decisions.md` |
