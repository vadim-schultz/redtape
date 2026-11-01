---
name: Situation tag coverage — Gaps and decisions
overview: "Settled decisions, open seams and recorded risks for closing the gap between domain and life-situation tag coverage on documents."
isProject: false
---

# Situation tag coverage — Gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md) · **Live runs:** [02-live-runs.md](02-live-runs.md) · **Parent decisions:** [extraction](../extraction/gaps-and-decisions.md) (X8, X12, X16), [crawlers](../crawlers/gaps-and-decisions.md) (census F4, chapter 22 step S12b)

## Settled

| # | Decision |
| --- | --- |
| T1 | **Closed — a free static mapping from the stored PVOG/GovData payload is rejected.** Crawlers census F4 ran against the production catalogue (520 PVOG rows, 893 GovData rows) and found the stored `raw_payload` carries no Lebenslage or category keys, only bare LeiKa identifiers. `.plans/crawlers/run-ledger.md` line 43; recorded as an open seam in `.plans/extraction/gaps-and-decisions.md` |
| T2 | **Taxonomy growth is out of scope.** The 18 situation codes aren't missing; assignment of existing codes to documents is the problem. No pipeline exists anywhere in this repo to discover new taxonomy codes from documents, and this suite does not build one |
| T3 | **The eval harness currently pools domain and situation Jaccard into one number.** `apps/discovery-ingest/discovery_ingest/extract/llm/evaluation/scoring.py`'s `gold_codes()` and `score_page()` concatenate `(*gold.domain_codes, *gold.situation_codes)` before scoring `tag_agreement`, so domain accuracy masks situation accuracy in every reported number. Chapter 1 splits it |

## Pending decisions

### T-PENDING — Which fix(es) for situation-axis coverage ship. Status: open, forcing spike: [02-live-runs.md](02-live-runs.md)

**Working hypothesis (chief of staff bet, not yet confirmed by live numbers).** Ship **S4** (make situation-axis acceptance axis-aware — trust a single confidently-grounded page assertion for situation codes instead of requiring 2-procedure corroboration, e.g. `min_procedures=1` for that axis, or an equivalent "grounded single page" rule) **plus S3** (the PVOG `personalMatters` capture) wherever S3's hand-mapping spike comes back clean, backstopped by the existing curator-override mechanism (`tags.py`'s `curated_codes`, already built — just needs prioritising via the existing `has_situation` completeness flag, `apps/api/app/features/discovery/repository/candidate_completeness_flags.py`'s `FLAG_NAMES`).

Reasoning: the 2-procedure consensus rule is structurally the wrong bar for an axis whose defining property is one-procedure-per-situation (`00-architecture.md` §1). Relaxing it for situations only, backed by the page-level grounding that already exists (every situation code the model emits must come from a page the extraction pipeline already grounds against quoted text), should recover coverage without inventing new infrastructure. S3 adds an independent, deterministic second signal on PVOG rows specifically, where available. **S5** (direct per-document classification) is predicted to underperform — most documents are generic bureaucratic forms ("Antrag auf …") with no situation signal in isolation, the signal lives in the surrounding procedure narrative — but it is cheap enough against the 47 gold documents to confirm rather than assume, so it stays in the suite as a check, not because it is expected to win.

A separate "graph/traversal" reframe (life situation as purely a procedure attribute, not a document attribute) is not treated as a sixth option: if S4 ships, that is functionally what you get, without a schema change.

Fill in after the live runs ([02-live-runs.md](02-live-runs.md) LR2 through LR5):

| Option | Coverage | Precision signal | Verdict |
| --- | --- | --- | --- |
| S3 (PVOG personalMatters) | _pending LR3_ | _pending LR3_ | _pending_ |
| S4 (axis-aware consensus) | _pending LR4_ | _pending LR4_ | _pending_ |
| S5 (per-document classification) | _pending LR5_ | _pending LR5_ | _pending_ |

**What would change this recommendation:**

- If S3's hand-mapping spike (LR3) comes back mostly ambiguous or many-to-many against the 18 codes, rather than cleanly mappable.
- If S4's precision check (LR4, the ~20-30 hand-labelled candidates) shows clearly wrong situations slipping past the single-page rule often enough that a human reviewer's trust in the chip erodes.
- If S5 (LR5) actually shows strong document-level signal on the 47 gold documents, which would argue for spending more on direct classification than the hypothesis currently expects.

## Open seams

| Seam | Placeholder | Forcing condition |
| --- | --- | --- |
| PVOG dedupe keeps only the first Lebenslage per row (`iter_records`'s `seen_lb_ids` dedupe keeps a row only the first time its `lb_id` is seen across the outer walk) | Capture as-is in chapter 3, one plausible situation per row | Fix the dedupe only if T-PENDING ships S3 and multi-situation coverage turns out to matter |
| Re-scoring existing candidates after a threshold change | None yet | A threshold change (S4) ships to production and existing staged candidates need their support recomputed |
| Taxonomy growth itself | Out of scope per T2 | S3 or S4 spikes reveal documents with genuinely no fitting code among the 18 |

## Risks

| Risk | Mitigation |
| --- | --- |
| Hand-labelling a small sample for precision-checking is noisy | Everything stays human-reviewed before emit, same as today; the sample informs the decision, it does not gate production on its own |
| PVOG vocabulary may map many-to-many or ambiguously to the 18 situation codes | Record the ambiguous share as its own number, don't force a 1:1 mapping |
| Relaxing consensus could surface more wrong situation tags to reviewers | Nothing is auto-emitted, per extraction X7/X8 precedent; a human still gates every promotion |
