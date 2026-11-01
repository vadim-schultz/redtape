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
| T4 | **Human sign-off (2026-11-01, vadim.schultz) on LR3's PVOG mapping — widen S3 to include the 14 ambiguous leaves, not just the 12 clean ones.** Reviewed [lr3-personal-matters-mapping.md](lr3-personal-matters-mapping.md) directly; decision: keep S3 within the 18-code situation taxonomy (no new codes, exact-string corroboration with LLM-extracted assertions stays intact) but stop excluding a leaf just because it's ambiguous — emit *all* plausible codes for a bundled leaf instead of dropping it (e.g. `1040300` "Jobsuche und Arbeitslosigkeit" → `["job-loss", "new-job"]`, not excluded). This raises mapped coverage from 12 to 17 of the 18 situation codes — only `going-self-employed` stays unmapped, since it has no citizen-branch PVOG leaf at all (confirmed in LR3's own tally). Detail and the full widened table: [lr3-personal-matters-mapping.md](lr3-personal-matters-mapping.md)'s sign-off section. This is the Step 0 prerequisite `situation-tag-activation` chapter 3 was blocked on — now satisfied |

## Pending decisions

### T-PENDING — Which fix(es) for situation-axis coverage ship. Status: open, forcing spike: [02-live-runs.md](02-live-runs.md)

**S4/S3 now shipping via `situation-tag-activation`; see that suite's [D-PENDING](../situation-tag-activation/gaps-and-decisions.md) for the resolution.** Following the `discovery-operations` D7 → `discovery-throughput` D5 cross-suite-supersession precedent, this entry stays open here until that suite's post-deploy precision check settles it.

**Working hypothesis (chief of staff bet, not yet confirmed by live numbers).** Ship **S4** (make situation-axis acceptance axis-aware — trust a single confidently-grounded page assertion for situation codes instead of requiring 2-procedure corroboration, e.g. `min_procedures=1` for that axis, or an equivalent "grounded single page" rule) **plus S3** (the PVOG `personalMatters` capture) wherever S3's hand-mapping spike comes back clean, backstopped by the existing curator-override mechanism (`tags.py`'s `curated_codes`, already built — just needs prioritising via the existing `has_situation` completeness flag, `apps/api/app/features/discovery/repository/candidate_completeness_flags.py`'s `FLAG_NAMES`).

Reasoning: the 2-procedure consensus rule is structurally the wrong bar for an axis whose defining property is one-procedure-per-situation (`00-architecture.md` §1). Relaxing it for situations only, backed by the page-level grounding that already exists (every situation code the model emits must come from a page the extraction pipeline already grounds against quoted text), should recover coverage without inventing new infrastructure. S3 adds an independent, deterministic second signal on PVOG rows specifically, where available. **S5** (direct per-document classification) is predicted to underperform — most documents are generic bureaucratic forms ("Antrag auf …") with no situation signal in isolation, the signal lives in the surrounding procedure narrative — but it is cheap enough against the 47 gold documents to confirm rather than assume, so it stays in the suite as a check, not because it is expected to win.

A separate "graph/traversal" reframe (life situation as purely a procedure attribute, not a document attribute) is not treated as a sixth option: if S4 ships, that is functionally what you get, without a schema change.

Fill in after the live runs ([02-live-runs.md](02-live-runs.md) LR2 through LR5):

| Option | Coverage | Precision signal | Verdict |
| --- | --- | --- | --- |
| S3 (PVOG personalMatters) | 15.3% of 118 leaves clean + 11.9% ambiguous now in scope per T4's human sign-off (widened); 17/18 situation codes covered, multi-code for bundled leaves ([LR3 detail](lr3-personal-matters-mapping.md)) | n/a — vocabulary mapping only, no precision check run yet | _widened mapping human-confirmed (T4); precision still pending the post-deploy live run_ |
| S4 (axis-aware consensus) | baseline 0 of 4,627 candidates accepted; `min_procedures=1` recovers 19 (coverage ceiling itself is 648 candidates with 2+ procedures per LR2) ([02-live-runs.md](02-live-runs.md) LR4) | **not run** — the ~20-30 hand-labelled precision check needs a human reviewer in the admin UI | _coverage confirmed, precision unchecked — cannot settle yet_ |
| S5 (per-document classification) | situation_tag_agreement 0.40 (5 document cases) vs. 0.75 on the same 4 pages at page level ([02-live-runs.md](02-live-runs.md) LR5) | n/a — underperforms the baseline directly, as predicted | **confirmed underperforms; do not pursue** |

**Where this leaves the working hypothesis, after LR1–LR5 (2026-11-01):**

- **LR1** (page-level baseline) shows the model's own extraction is *not* the weak link — situation_tag_agreement (0.85) actually beats domain (0.65) at the page level.
- **LR2** (structural ceiling) confirms the root cause decisively: 86% of all 4,627 candidates have exactly one procedure and can never clear *any* axis's consensus floor, no matter what the model says.
- **LR4** confirms S4's coverage story directionally (0 → 19 under `min_procedures=1`) but the gain is small in absolute terms against 4,627 candidates, and **the precision half is unrun** — nobody has checked whether those 19 (or the broader relaxed set) are *correct* situations, only that they'd newly pass the count bar. S4 cannot be called settled until that human check happens.
- **LR3** gives S3 a weaker signal than hoped: only 15.3% of the PVOG vocabulary maps cleanly, and two situation pairs (`job-loss`/`new-job`, `moving-house`/`renting-home`) are bundled under one ambiguous PVOG leaf each, so S3 alone can't disambiguate them. This was also an AI first-pass mapping, not yet human-reviewed.
- **LR5 settles S5**: confirmed to underperform as predicted (0.40 vs. 0.75) — drop it from further consideration.

**What would change this recommendation:**

- ~~If S3's hand-mapping spike (LR3) comes back mostly ambiguous or many-to-many against the 18 codes, rather than cleanly mappable.~~ **Partially triggered** — 11.9% ambiguous, 72.9% unmapped. S3 is weaker than hoped but not worthless (12/18 codes get a clean leaf); treat as a secondary signal, not primary.
- If S4's precision check (LR4, the ~20-30 hand-labelled candidates — still not run) shows clearly wrong situations slipping past the single-page rule often enough that a human reviewer's trust in the chip erodes.
- ~~If S5 (LR5) actually shows strong document-level signal on the 47 gold documents~~ — **did not happen**; S5 is ruled out.

**Remaining before this can flip to settled:** ~~(1) a human spot-check of the LR3 mapping, especially its 14 ambiguous rows~~ — **done, T4**; (2) the LR4 precision check — hand-label ~20-30 candidates against the `min_procedures=1` variant via the admin UI.

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
