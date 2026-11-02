---
name: Situation tag hierarchy — Live runs
overview: "The chief-of-staff-executed post-deploy run chapter 5 calls for: a fresh hand-labelled sample against production, a curve-calibration check, and a structural check of the deployed group/leaf-facet/confidence contract."
isProject: false
---

# Situation tag hierarchy — Live runs

**Rollout:** [01-rollout.md](01-rollout.md) · **Decisions:** [gaps-and-decisions.md](gaps-and-decisions.md) (P1) · **Architecture:** [00-architecture.md](00-architecture.md) · **Chapter:** [chapters/05-live-validation.md](chapters/05-live-validation.md)

**Who ran this:** the chief of staff, against production, 2026-11-02, immediately after the release PR (#312, `feat/plans-situation-tag-hierarchy` → `main`) merged — mirroring `situation-tag-activation/02-live-runs.md`'s LR1 precedent. **AI first-pass hand-labelling, not a human domain expert's** — same caveat as both prior suites' live runs; treat the verdict below as provisional pending human spot-check, especially the calls marked "debatable."

## LR1 — Post-deploy sample, curve check, and structural UI/API check

### Population

Queried production directly (read-only, via a scoped probe credential):

- **Catalogue is still MVP-sized**: 4 published documents (seed/demo data), 9 `document_life_situation` rows, 6 `document_domain` rows — **all backfilled to `confidence=1.0`** (D7); zero rows have been computed by the new continuous engine, because **zero documents have been promoted since chapters 1–4 deployed**. There is nothing newly-scored on the *published* side to sample yet.
- **`discovery_candidate_mention`**: 5,914 total mentions. Of those, **19 candidates carry 22 `(candidate, code)` situation-axis pairs** — this is the entire current population, same shape as `situation-tag-activation`'s own LR1 (16 pairs). It is substantially the *same* underlying candidates LR1 already hand-labelled on 2026-10-28 (e.g. the "Transferkurzarbeitergeld" document family, the ZVR/Vorsorgevollmacht family, "Identitätsbestätigung", the "Nebenwirkungen" reporting forms), now simply re-scored by the new continuous engine instead of the old binary gate, plus 3 new manually-tagged pairs (rehabilitation/`Teilhabe` benefit documents) not present in LR1's sample.
- **Zero PVOG leaf codes anywhere in production** (`pvog_leaf_code`, `direct_situation_confidence`, `direct_domain_confidence` all `NULL` on every one of the 5,914 mentions). Chapter 3's leaf-refinement and domain-hint recovery have **never been exercised** — no PVOG harvest cycle has run since chapter 3 shipped. This is the same "scheduling gap" LR1's own A2 found (harvesting is additive, not retroactive), now extended: not just the PVOG-corroboration case, but the entire PVOG-sourced scoring path (clarity weights, domain hints) is unmeasured in production, zero rows.

### Curve check — procedures=1, LLM-only bucket (22 of 22 sampled pairs, 100% of the current population)

All 22 pairs are single-procedure, LLM-or-manual-extracted, no direct-confidence source: `llm_evidence_score(1, 1.0) = 0.5`. Judged against the same standard LR1 used — does the code describe the actual personal life-event plausibly motivating this specific procedure, not just thematic/agency proximity:

| Group (by underlying procedure) | Pairs | Code | Verdict |
| --- | --- | --- | --- |
| "Transferkurzarbeitergeld" document family (7 document candidates, same layoff/short-time-allowance procedure) | 7 | `job-loss` | **Correct** (×7) — same procedure LR1 already judged correct, one more document candidate now attached |
| ZVR / Vorsorgevollmacht registration family (`Eintragungsunterlagen`, `Zusatzformular PZ`, `Antragsformular P`) | 3 | `moving-house` | **Wrong** (×3) — no connection to moving, same call as LR1 |
| "Identitätsbestätigung" (generic ID-confirmation mention, 3 codes attached) | 3 | `moving-house`, `birth-of-child`, `death-of-relative` | **Wrong** (×2, `moving-house`/`birth-of-child`); **wrong, debatable** (×1, `death-of-relative` — same debatable call LR1 made) |
| "Nebenwirkungen" adverse-effect reporting forms | 2 | `illness-care` | **Wrong, debatable** (×2) — safety-reporting duty, not a personal illness/care situation, same call as LR1 |
| Rehabilitation/`Teilhabe` benefit documents (new since LR1) | 2 | `illness-care` | **Correct** (×2) — `Antrag auf Leistungen zur Teilhabe` and `Nachweis über den Grad der Behinderung (GdB)` are squarely disability/illness-benefit applications |
| Rehabilitation/`Teilhabe` benefit documents (new since LR1) | 1 | `illness-care` | **Wrong, debatable** (×1) — `Bescheide eines anderen Rehabilitations- oder Sozialversicherungs-Trägers` names a broad cross-agency set (Jobcenter, Krankenkasse, Rentenversicherung, Eingliederungshilfe, Jugendhilfe); plausible but not squarely health-specific on its own |
| "Ferienbeschäftigung" (foreign-student vacation-work) family | 2 | `new-job` | **Correct, debatable** (×2) — vacation employment is itself a new-job-shaped procedure for the student; the employer-side `Vollmacht des Betriebes` shares the same procedure |
| "Ferienbeschäftigung" family | 1 | `immigration` | **Wrong, debatable** (×1) — the document itself only confirms employment status, not an immigration procedure |
| FDZ research-data-provision family | 1 | `new-job` | **Wrong** (×1) — same "no connection" call LR1 made on this family's other document |

**Unambiguous correct: 9/22. Unambiguous wrong: 6/22. Debatable: 7/22.**

- **Strict reading** (debatable → wrong): **9/22 = 40.9%**
- **Generous reading** (debatable → correct): **16/22 = 72.7%**

This brackets, and sits a little above, LR1's own 37.5–62.5% range — driven by the 2 new, unambiguously-correct `Teilhabe`/disability pairs. **No calibration adjustment recommended.** `LLM_SCORE_BASE=0.5` was deliberately anchored at this bucket's measured midpoint, not at a "high confidence" value — chapter 4 renders this score at the gradient's middle (`opacity ≈ 0.75`), not as an accepted/high badge. A real precision range of ~41–73% for a tag explicitly rendered as "medium, not confirmed" is consistent with the design intent; there is no accept/reject line left for this range to fail.

**procedures≥2 bucket, PVOG-clean bucket, PVOG-ambiguous bucket: 0 pairs in production.** All three remain unmeasured — same gap LR1's A2 left open for PVOG, now also true of the procedures≥2 LLM case and the domain-hint table, because the candidate population hasn't grown and no PVOG harvest has run since deploy.

### Structural UI/API check (read-only against the live production API)

No browser session was available in this run, so the actual rendered gradient/chip-interaction could not be eyeballed. In its place, the data contract the frontend reads from was checked directly against the deployed API:

- `GET /api/v1/life-situation-groups` — live, returns exactly the 8 groups from `00-architecture.md` §4.
- `GET /api/v1/life-situations` — live, all 18 situations returned, every one carrying a `group_code` that matches one of the 8 groups, exactly the partition in §4 (spot-checked in full, not sampled).
- `GET /api/v1/documents/?situation=<code>` — live; `available_leaf_codes` is `[]` on every query tried (`job-loss`, `moving-house`, no filter) — expected, since zero PVOG leaf data exists in production yet. Chapter 4's "never render an empty facet" contract is correctly, if trivially, satisfied today.
- `GET /api/v1/documents/{id}` — live; the one inspected document's `domains`/`life_situations` both carry `confidence: 1.0` (backfilled, D7), confirming the schema chapter 4's `TagBadge` reads from round-trips correctly end to end.

**Not checked, and flagged as a remaining gap**: the actual browser-rendered opacity gradient and the group-chip expand/collapse interaction. The data contract is confirmed correct; whether it reads as *visually* distinct in the real UI needs a human (or a future run with browser access) to look at the deployed frontend directly.

### Verdict and resolution of P1

**`gaps-and-decisions.md` P1 — partially resolved.** The procedures=1 LLM-only bucket's calibration (`LLM_SCORE_BASE=0.5`) is reasonably consistent with this fresh 22-pair sample and is not adjusted. The procedures≥2 bucket, both PVOG clarity weights (0.95/0.65), and the domain-hint table's 0.8 weight remain **entirely unvalidated in production** — there is no data of those shapes yet. P1 does not close; re-run this section's three unmeasured buckets once either (a) the candidate population grows past single-procedure LLM-only pairs, or (b) a PVOG harvest cycle runs under chapter 3's shipped code and populates `pvog_leaf_code`/`direct_situation_confidence` on fresh mentions.

**No rollback or constant change recommended.** Unlike `situation-tag-activation`'s LR1, there is no accept/reject line left to trip — this run confirms the engine, the group taxonomy, and the leaf-facet/confidence data contract are all live and behaving as designed; it does not (and structurally cannot yet) validate the PVOG-sourced or multi-procedure parts of the curve.

---

**Status:** Sample, curve check, and structural API check complete and recorded above. The browser-level visual check (opacity gradient, group-chip interaction) and the procedures≥2/PVOG buckets of the curve check remain open — re-run once a PVOG harvest cycle has processed fresh candidates and/or a human has looked at the deployed frontend directly.
