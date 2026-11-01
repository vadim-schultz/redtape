---
name: Situation tag activation — Live runs
overview: "The one chief-of-staff-executed post-deploy run that completes the parent suite's unrun LR4 precision half, against the real shipped change rather than an offline variant."
isProject: false
---

# Situation tag activation — Live runs

**Rollout:** [01-rollout.md](01-rollout.md) · **Decisions:** [gaps-and-decisions.md](gaps-and-decisions.md) (D-PENDING) · **Architecture:** [00-architecture.md](00-architecture.md)

**Who runs this:** the chief of staff, against real data and real APIs, only after chapters 1 through 3 are built, merged and deployed to production — and only after chapter 3's own Step 0 human sign-off on the PVOG mapping is recorded. This mirrors `situation-tag-coverage/02-live-runs.md`'s numbered-gate shape, but holds exactly one run instead of five, because this suite ships the fix rather than measuring options.

## LR1 — Post-deploy precision check, split by mechanism

**Not yet run — chapters 1–3 have not shipped.**

Once chapters 1–3 are deployed together (cheap to roll back: chapter 1's engine merge is a code-structure change with no schema/migration, the axis threshold is a plain setting, and chapter 3's mention source is purely additive), hand-label roughly 20–30 of the newly-accepted situation-tagged candidates via the admin UI. **Split the sample by which mechanism newly qualified each candidate** — relaxed threshold alone (chapter 1's A1) vs. PVOG corroboration (chapter 3's A2) — so either knob can be independently rolled back from its own sample if its precision looks bad, rather than one blended verdict forcing an all-or-nothing call.

This finally completes `situation-tag-coverage` LR4's unrun precision half (that suite's coverage half found 0 → 19 of 4,627 candidates under `min_procedures=1` but never checked whether those situations were *correct*), now against the real shipped change instead of an offline variant.

**What to record:**

- The sample size and split (how many candidates attributed to A1 only, A2 only, or both).
- Per-mechanism precision: of the candidates attributed to that mechanism, how many of the hand-labelled situation codes were judged correct.
- An explicit, pre-agreed rollback trigger per mechanism (e.g. "if A1's sample precision falls below X%, revert `discovery_tag_min_procedures_situation` to 2 without waiting for a full re-run"), decided *before* labelling starts, not fitted to the numbers afterward.
- As a side check, not a blocker: confirm whether the existing voting pipeline (`apps/api/app/features/voting/`) has ever actually promoted a suggestion via real votes in production, or has sat entirely unexercised — the frontend has zero consumers of the voting API today. This matters for how much safety net "nothing reaches the catalogue without crossing the vote threshold" actually provides right now, independent of this suite's own changes.

**Where the result goes:** record the outcome and the rollback-trigger decision in [gaps-and-decisions.md](gaps-and-decisions.md)'s D-PENDING table, and flip D-PENDING from open to settled once both mechanisms have a verdict. Then annotate `situation-tag-coverage/gaps-and-decisions.md`'s T-PENDING entry as resolved, closing the loop the parent suite left open.

---

**Status:** not started. This section will be updated in place, the same way `situation-tag-coverage/02-live-runs.md` records each run's outcome directly beneath its own heading, once chapters 1–3 are merged and deployed.
