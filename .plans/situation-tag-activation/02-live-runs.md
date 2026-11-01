---
name: Situation tag activation — Live runs
overview: "The one chief-of-staff-executed post-deploy run that completes the parent suite's unrun LR4 precision half, against the real shipped change rather than an offline variant."
isProject: false
---

# Situation tag activation — Live runs

**Rollout:** [01-rollout.md](01-rollout.md) · **Decisions:** [gaps-and-decisions.md](gaps-and-decisions.md) (D-PENDING) · **Architecture:** [00-architecture.md](00-architecture.md)

**Who runs this:** the chief of staff, against real data and real APIs, only after chapters 1 through 3 are built, merged and deployed to production — and only after chapter 3's own Step 0 human sign-off on the PVOG mapping is recorded. This mirrors `situation-tag-coverage/02-live-runs.md`'s numbered-gate shape, but holds exactly one run instead of five, because this suite ships the fix rather than measuring options.

## LR1 — Post-deploy precision check, split by mechanism

**Run 2026-11-01, chief of staff, against production** (all three chapters merged and deployed to `main`; chapter 3's Step 0 sign-off recorded as T4). **AI first-pass hand-labelling, not a human domain expert's — same caveat as the parent suite's LR3 mapping; treat the verdict below as provisional pending human spot-check**, especially the calls marked "debatable."

**Pre-agreed rollback trigger**, decided before any labelling (`gaps-and-decisions.md`, committed 2026-11-01 prior to this run): **70% per-mechanism sample precision**, below which that mechanism reverts immediately.

### Sample and split

Queried production directly (`discovery_candidate_mention`, situation axis) for `(candidate, code)` pairs accepted under the new `min_procedures=1` rule that would **not** have been accepted under the old `min_procedures=2` floor (i.e. `procedures = 1`), excluding candidates with a manual override (which bypass consensus in both regimes) — this is the exact "newly accepted" population, not a down-sample of a larger one:

- **16 total newly-accepted `(candidate, code)` pairs** — this is the entire population currently in production, smaller than the ~20–30 target because that's genuinely all there is right now, not a sampling choice.
- **A1 (relaxed threshold alone, non-PVOG): 16 of 16.**
- **A2 (PVOG corroboration): 0.** All 5,808 `pvog-payload` mentions in production were created 2026-10-28, before chapter 3 shipped; harvesting is additive and doesn't retroactively populate `situation_codes` on existing rows. A2 has no production candidates to sample until the PVOG crawl/harvest next runs post-chapter-3. **Not a mapping failure — a scheduling gap.** Revisit after the next PVOG harvest cycle.

### A1 hand-labelling (16 of 16, full population)

Judged against: does the situation code describe the actual personal life-event plausibly motivating this specific procedure (not just thematic/agency proximity)?

| # | Candidate | Code | Procedure | Verdict |
| --- | --- | --- | --- | --- |
| 1–2, 4, 8, 13–14 | 6 candidates | `job-loss` | "Transferkurzarbeitergeld beantragen" (transfer short-time allowance for employees moving into a Transfergesellschaft during layoffs) | **Correct** (×6) — squarely a job-loss procedure |
| 3, 12, 15 | 3 candidates | `moving-house` | "Vorsorgevollmacht und Betreuungsverfügung im Zentralen Vorsorgeregister registrieren lassen" (power-of-attorney/care-directive registration) | **Wrong** (×3) — no connection to moving |
| 5–7 | 1 candidate (`4c33cd88`), 3 codes | `birth-of-child`, `death-of-relative`, `moving-house` | "Zugang zu den Stasi-Unterlagen ... zur eigenen Person, vermissten oder verstorbenen Angehörigen" (Stasi-records access for self/missing/deceased relative); all 3 codes attached to the same generic "Identitätsbestätigung" (ID-confirmation) document mention, none grounded in that excerpt's actual text | **Wrong** (×3) — `death-of-relative` is debatable (procedure title does mention deceased relatives as one of three applicant categories) but the quoted excerpt itself grounds none of the three |
| 9, 16 | 2 candidates | `illness-care` | "Verdacht auf Nebenwirkungen ... melden" (reporting suspected adverse drug/vaccine effects) | **Wrong, debatable** (×2) — health-domain-adjacent, but this is a safety-reporting duty, not a personal illness/care-benefit situation; could reasonably be scored correct under a looser standard |
| 10 | 1 candidate | `new-job` | "Daten für die Wissenschaft bereitstellen" (research data provision) | **Wrong** (×1) — no connection |
| 11 | 1 candidate | `job-loss` | "Erstattung der Beiträge zur Sozialversicherung ... zum Saison-Kurzarbeitergeld" (reimbursement of social security contributions, seasonal short-time allowance) | **Wrong, debatable** (×1) — reads as an employer-side reimbursement claim, not a personal citizen job-loss situation; same job-loss family as #1 if read as citizen-facing |

**Precision: 6 of 16 = 37.5%** under the strict reading above (debatable calls scored wrong). Even scoring every debatable call as correct — the most generous reading — gives **10 of 16 = 62.5%**. **Both readings fall below the 70% rollback trigger.**

Methodological caveat: the 6 "correct" pairs are all one procedure (6 different document candidates attached to "Transferkurzarbeitergeld beantragen"); counting distinct *procedures* rather than `(candidate, code)` pairs, only 1 of 6 (or 2 of 6, generously) distinct procedures are correctly tagged — an even weaker signal than the pair-level number suggests.

### Side check — voting pipeline

Queried production directly: `suggestion` table has 2 rows, both `status='pending'`; `suggestion_vote` has **0 rows ever**. **Confirmed: the voting pipeline has never promoted anything in production** — it has sat entirely unexercised, consistent with the frontend having zero consumers of the voting API. The "nothing reaches the catalogue without crossing the vote threshold" safety net provides no actual protection today, independent of this suite's changes, because nothing has ever been voted on.

### Verdict

- **A1: rollback trigger hit.** 37.5–62.5% sample precision, below the pre-agreed 70% bar under every reading. **Recommend executing the pre-agreed rollback** (`discovery_tag_min_procedures_situation` back to `2`) — see `gaps-and-decisions.md` D-PENDING for the chief of staff's recommendation and open question back to the user before acting, given several of the 16 calls are genuinely debatable AI-judgment, not a human domain expert's.
- **A2: not measurable yet.** Zero production candidates since chapter 3 shipped; revisit after the next PVOG harvest run.

**Where the result goes:** recorded in [gaps-and-decisions.md](gaps-and-decisions.md)'s D-PENDING table. D-PENDING does **not** flip to settled yet — A1 has a verdict (fails) but A2 doesn't have one yet, and the rollback itself hasn't been executed pending the user's decision.

---

**Status:** A1 run and verdict recorded above (rollback triggered, pending user decision). A2 blocked on the next PVOG harvest cycle — re-run this section's A2 half once PVOG mentions with `situation_codes` exist in production.
