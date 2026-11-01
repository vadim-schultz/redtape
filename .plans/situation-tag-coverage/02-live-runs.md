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

## LR2 — The structural consensus ceiling

Run chapter 2's report against production `discovery_candidate_mention` data. Record what share of candidates are referenced by at least 2 distinct procedures — the structural ceiling the current 2-procedure consensus rule imposes, independent of model accuracy. This is the number that confirms or disproves the root-cause claim in `00-architecture.md` §1.

## LR3 — PVOG personalMatters vocabulary mapping

Run chapter 3's vocabulary enumeration against the live PVOG v7 bootstrap endpoint. A human then hand-maps the returned `personalMatters` leaf codes against the 18 situation codes. Record the percentage cleanly mapped, ambiguous, and unmapped. Feed the result into T-PENDING's S3 row.

## LR4 — Axis-aware consensus: coverage versus precision

Run chapter 4's offline tool against exported mention data with 2 to 3 threshold variants: today's 2-procedure/50 percent baseline, `min_procedures=1`, and any grounded-page variant chapter 4 ends up scoping. Hand-label about 20 to 30 candidates via the admin UI as a precision check. Record a coverage-versus-precision table per variant, and feed it into T-PENDING's S4 row.

## LR5 — Document-level classification eval

Run chapter 5's document-level eval against the 47 gold documents, where document text is available. Record situation-axis tag agreement and compare it to LR1's page-level baseline. Feed the result into T-PENDING's S5 row.

---

Record every outcome back in `gaps-and-decisions.md`'s T-PENDING table and flip its status from open to settled once all five are in.
