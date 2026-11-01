---
name: "Chapter 5 — Live validation"
overview: "Once chapters 1-4 are merged and deployed, hand-label a fresh sample against the shipped confidence scores to check the LLM-evidence curve's calibration, confirm the grouped UI never renders an empty facet, and record the result as this suite's own 02-live-runs.md — the same forcing check situation-tag-activation's own live run was."
todos:
  - id: wait-for-deploy
    content: "Confirm chapters 1-4 merged and deployed before starting"
    status: pending
  - id: sample
    content: "Hand-label a fresh sample of newly-visible low/mid-score tags against production"
    status: pending
  - id: curve-check
    content: "Compare the curve's predicted score to the hand-labelled precision per procedures bucket"
    status: pending
  - id: ui-check
    content: "Manually browse the grouped UI; confirm no empty facets ever render; confirm existing tags resolve to the right group"
    status: pending
  - id: record
    content: "Write 02-live-runs.md; resolve gaps-and-decisions.md P1"
    status: pending
isProject: false
---

# Chapter 5 — Live validation

**Repo:** `redtape` · **Branch:** none (read-only measurement, same as `situation-tag-activation`'s own live run) · **Status:** planned

**Depends on:** Chapters 1–4 merged and deployed · **Decisions:** forces P1 (`../gaps-and-decisions.md`) · **Rollout:** [../01-rollout.md](../01-rollout.md)

## Goal

This suite removed every binary accept/reject gate in favour of a continuous score, calibrated against `situation-tag-activation`'s own 16-sample hand-label (gaps-and-decisions.md P1). That calibration has never been checked against fresh data. This chapter is the forcing check, in the same `02-live-runs.md` live-run style both prior suites in this area used — not a code chapter, no PR, no branch.

## Design

**Sample.** After chapters 1–4 are deployed, pull a fresh sample of `(document, code)` pairs whose confidence score sits in the newly-interesting range this suite created — specifically, codes that would have been excluded under the old binary gate (score below what the historical 2-procedure floor would have required) but now clear `MIN_SUGGESTED_SCORE` and are visible in the UI at a de-emphasized opacity. Hand-label each as correct or not, the same AI-first-pass-flagged-for-human-spot-check discipline `situation-tag-activation`'s own LR1 and `situation-tag-coverage`'s LR3 both used.

**Curve check.** Bucket the sample by its dominant evidence source (LLM-only at 1 procedure, LLM-only at 2+, PVOG clean leaf, PVOG ambiguous leaf) and compare each bucket's actual hand-labelled precision to what `llm_evidence_score()`/the clarity weights in chapter 1 and 3 predicted. A bucket off by more than a small margin is a signal to adjust `LLM_SCORE_BASE`/`LLM_SCORE_STEP`/`LLM_SCORE_CEILING` or the two clarity constants (`0.95`/`0.65`/`0.8`) — editing three or four named constants, not re-deriving a formula, is the entire point of having calibrated against named constants in chapter 1.

**UI check.** Manually browse the deployed grouped UI: confirm no leaf-refinement facet ever renders with zero matching documents; confirm every situation code's existing tags resolve to the right one of the 8 groups; confirm a low-confidence tag is visibly, not just numerically, lighter than a high-confidence one.

**Record.** Write `../02-live-runs.md` (new file, this suite's equivalent of the prior suites' live-run doc) with the sample, the bucketed precision table, and the UI check's findings. Resolve `../gaps-and-decisions.md` P1 — either confirm the calibration holds, or record the adjusted constants and why.

## Verification

Read-only against production; no `./ci.sh` gate (no code changes). If the curve check recommends adjusting a constant, that adjustment is a small follow-up PR against the already-merged chapter 1 code — not a new chapter, since the formula/shape doesn't change, only its three named constants.

## Out of scope

Re-opening any of this suite's settled decisions (D1–D9, `../gaps-and-decisions.md`); building the deferred curation queue (D5) — this chapter measures the automatic pipeline's calibration, not a human-review workflow; growing the taxonomy or revisiting the 8-group split (P2) beyond noting whether it held up, which is a separate future-work item, not this chapter's job to resolve.
