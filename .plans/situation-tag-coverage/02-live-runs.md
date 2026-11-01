---
name: Situation tag coverage — Live runs
overview: "The five chief-of-staff-executed runs against real data and APIs that settle the pending decision on situation-axis coverage, run only after all five chapters are built."
isProject: false
---

# Situation tag coverage — Live runs

**Rollout:** [01-rollout.md](01-rollout.md) · **Decisions:** [gaps-and-decisions.md](gaps-and-decisions.md) (T-PENDING) · **Architecture:** [00-architecture.md](00-architecture.md)

**Who runs this:** the chief of staff, against real data and real APIs, only after chapters 1 through 5 are built and merged. This mirrors `.plans/extraction/02-live-runs.md`'s L0 to L5 shape: a numbered sequence of live gates, each recorded back into the decisions file, with no run spending anything on its own initiative beyond what is scoped below.

## LR1 — Baseline: split tag agreement on the gold set

After chapter 1 lands, run `python -m discovery_ingest llm eval` against the 20-page gold set. Record the new domain-only and situation-only tag agreement numbers as the baseline row in `gaps-and-decisions.md`'s T-PENDING table — this is the "before" figure every later option is measured against.

**Done 2026-11-01.** Ran `llm eval --model @cf/qwen/qwen3-30b-a3b-fp8` against the full 20-page gold set (1,177 neurons; 3 pages failed with `invalid_output`, unrelated to tagging). Result: **domain_tag_agreement = 0.65**, **situation_tag_agreement = 0.85** — both clear the 0.60 floor, and situation scores *higher* than domain at this page-level extraction stage. This is an important, somewhat counter-intuitive baseline: it means the model's own per-page situation-code extraction is not the weak link. The gap the suite exists to close (0 of 58 candidates getting a situation tag in production) must therefore live downstream of extraction — in the cross-procedure consensus step, not in what the model sees on one page. LR2 and LR4 below confirm this directly.

## LR2 — The structural consensus ceiling

Run chapter 2's report against production `discovery_candidate_mention` data. Record what share of candidates are referenced by at least 2 distinct procedures — the structural ceiling the current 2-procedure consensus rule imposes, independent of model accuracy. This is the number that confirms or disproves the root-cause claim in `00-architecture.md` §1.

**Done 2026-11-01.** Ran `python -m scripts.consensus_ceiling_report` directly against production (read-only query, `DATABASE_URL` supplied by the owner for this run only, never persisted). Result: **4,627 total candidates; 648 (14.0%) at or above the 2-procedure floor; 3,979 (86.0%) at exactly one procedure; 0 (0.0%) at zero.** This confirms the root-cause claim decisively: 86% of all candidates are structurally incapable of ever clearing the current consensus floor on *any* axis — not a model-accuracy problem, a structural one. The 14% ceiling also contextualises LR4 below: even among the minority of candidates with 2+ procedures to agree, zero of them land an accepted situation code under baseline, meaning that even when two procedures exist, they essentially never independently assert the *same* situation.

## LR3 — PVOG personalMatters vocabulary mapping

Run chapter 3's vocabulary enumeration against the live PVOG v7 bootstrap endpoint. A human then hand-maps the returned `personalMatters` leaf codes against the 18 situation codes. Record the percentage cleanly mapped, ambiguous, and unmapped. Feed the result into T-PENDING's S3 row.

**Done 2026-11-01.** Ran against the live, public v7 bootstrap endpoint (no credentials needed — read-only GET). Full mapping and tallies: [lr3-personal-matters-mapping.md](lr3-personal-matters-mapping.md). Headline: of 118 leaf codes (56 citizen-facing, 62 business-facing), **15.3% clean, 11.9% ambiguous, 72.9% unmapped** against the 18 `life_situation` codes — driven mostly by the business/citizen split (all 62 business leaves are out of scope by design) plus domain-shaped citizen buckets (taxes, IDs, legal process) that don't correspond to any triggering life event. 12 of the 18 situation codes get at least one clean PVOG leaf; `moving-house`, `job-loss`, `new-job`, `going-self-employed`, `starting-school` and `renting-home` get none (bundled ambiguously or absent). **Caveat:** this hand-mapping was done by the chief of staff as a first pass, not by a human domain expert as this section originally specified — flagged for a human spot-check, especially the 14 ambiguous rows, before being treated as settled.

## LR4 — Axis-aware consensus: coverage versus precision

Run chapter 4's offline tool against exported mention data with 2 to 3 threshold variants: today's 2-procedure/50 percent baseline, `min_procedures=1`, and any grounded-page variant chapter 4 ends up scoping. Hand-label about 20 to 30 candidates via the admin UI as a precision check. Record a coverage-versus-precision table per variant, and feed it into T-PENDING's S4 row.

**Coverage half done 2026-11-01; precision half not done.** Read all 5,914 production `discovery_candidate_mention` rows (read-only, same `DATABASE_URL` as LR2) and ran `situation_coverage_by_variant` over all 4,627 candidates:

| Variant | Accepted candidates | Newly covered vs. baseline |
| --- | --- | --- |
| baseline (2 procedures, 50% share) | 0 | — |
| relaxed (1 procedure, 50% share) | 19 | 19 |

Relaxing to one procedure takes situation-axis coverage from 0 to 19 candidates (of 4,627) — a real but modest absolute gain, consistent with LR2's finding that only 648 candidates even have 2+ procedures, and that even that minority produces zero situation agreement today. The **grounded-page variant was not built** (chapter 4 deliberately deferred it pending a mention-schema extension, per its own doc) and the **hand-labelled precision check (~20-30 candidates via the admin UI) was not run** — that step calls for a human reviewer judging real documents against the taxonomy, which is outside what the chief of staff can do unsupervised. **This half of T-PENDING's S4 row stays open** until a human runs that precision check.

## LR5 — Document-level classification eval

Run chapter 5's document-level eval against the 47 gold documents, where document text is available. Record situation-axis tag agreement and compare it to LR1's page-level baseline. Feed the result into T-PENDING's S5 row.

**Done 2026-11-01.** Ran `EvalRunner.run_documents` (no CLI wiring exists yet, per chapter 5's own scope — invoked via a one-off driver script) against the 5 gold documents chapter 5 hand-authored `document_text` for (not 6 — chapter 5's own report over-counted by one; the gold fixtures hold exactly 5, across 4 pages: `aa-probebeschaeftigung`, `aa-transferkurzarbeitergeld` ×2, `bzkj-antrag-indizierung`, `vorsorgeregister-registrierung`). 188.5 neurons spent. Also ran the page-level baseline restricted to those same 4 pages, for a like-for-like comparison:

| Run | situation_tag_agreement |
| --- | --- |
| Document-level (5 cases) | **0.40** |
| Page-level, same 4 pages | **0.75** |

Document-level classification scores well below the matching page-level baseline: 3 of 5 cases grounded zero situation codes from the document's own isolated text (the model had nothing in the text itself to tie to a situation), 1 was a correct trivial empty match, and only 1 (a form literally named "Antrag Transferkurzarbeitergeld" — a form whose own title names the situation) scored a true positive. This **confirms the working hypothesis**: most documents are generic forms with no isolable situation signal; the signal lives in the surrounding procedure narrative, not the document text alone.

---

Record every outcome back in `gaps-and-decisions.md`'s T-PENDING table and flip its status from open to settled once all five are in.

**Status after this run (2026-11-01):** LR1, LR2, LR3 and LR5 are complete. LR4 is complete for its coverage half; its precision half (hand-labelling ~20-30 candidates via the admin UI) still needs a human reviewer, as does a spot-check of LR3's AI-drafted PVOG mapping. T-PENDING is **not** flipped to settled — see its table and the two flagged open items.
