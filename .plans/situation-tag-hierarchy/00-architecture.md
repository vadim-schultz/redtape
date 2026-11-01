---
name: Situation tag hierarchy — Architecture
overview: "situation-tag-activation shipped axis-aware consensus and a binary confidence tier, then its own post-deploy check found that binary tier failing its precision bar. This suite replaces every accept/reject threshold with one continuous, weighted confidence score, adds a Group tier above the 18 situation codes so browsing never shows more than ~8 choices, and builds out PVOG's deterministic leaf signal as first-class scope."
isProject: false
---

# Situation tag hierarchy — Architecture

**Rollout:** [01-rollout.md](01-rollout.md) · **Decisions:** [gaps-and-decisions.md](gaps-and-decisions.md) · **Chapters:** [chapters/](chapters/) · **Prior suites:** [situation-tag-coverage](../situation-tag-coverage/00-architecture.md) (spike, measurement only) → [situation-tag-activation](../situation-tag-activation/00-architecture.md) (shipped axis-aware consensus, a binary confidence tier, and the PVOG situation signal)

## 1. Why

`situation-tag-activation`'s own post-deploy live run (`situation-tag-activation/gaps-and-decisions.md` D-PENDING, `02-live-runs.md` LR1) found its relaxed `min_procedures_situation=1` threshold at 37.5–62.5% hand-labelled precision — below the pre-agreed 70% rollback trigger — and left the rollback decision open rather than execute it. Separately, that suite's own "Candidate future work" table flagged an unscoped idea: using more of PVOG's 56-leaf citizen vocabulary directly, deterministically, rather than squeezing it into the 18-code taxonomy or growing the taxonomy to match it.

A working session with the user (vadim.schultz, 2026-11-01) worked through both findings together, plus a third, previously undiscussed problem: the taxonomy has no hierarchy at all — just a flat 18-code situation axis — so there's no way to show a manageable number of choices to someone browsing or filtering, short of overwhelming them with either the 18 codes directly or (if the taxonomy ever grew to match PVOG) 56.

Three decisions came out of that session, settled before this suite was scoped (not re-litigated here — see [gaps-and-decisions.md](gaps-and-decisions.md) "Settled"):

- **No threshold rollback.** `discovery_tag_min_procedures_situation` stays at `1`. The binary accept/reject gate it feeds is being removed entirely in this suite, not tuned — there is no cliff left to roll back.
- **Pursue this as its own chapter-based suite**, not a smaller slice, following the `situation-tag-coverage` → `situation-tag-activation` precedent.
- **Build PVOG leaf refinement now**, as committed scope — not conditional on first measuring PVOG's coverage ceiling, because the facet is deterministic-only (zero LLM accuracy risk) and PVOG already covers a sizeable share of the catalogue.

What this suite ships: a single continuous `[0, 1]` confidence score replacing every binary accept/reject decision in the situation (and domain) tagging pipeline; a new `LifeSituationGroup` tier sitting above the 18 situation codes so default browsing never shows more than ~8 choices; and PVOG leaf-level refinement as an optional, deterministic-only secondary facet once a user has already picked a situation. Curator voting stays out of scope — see §5.

## 2. Vocabulary

Carried over from `situation-tag-activation` (chip, axis, consensus, support — see [situation-tag-activation/00-architecture.md §2](../situation-tag-activation/00-architecture.md)), plus what this suite adds or replaces:

| Term | Meaning |
| --- | --- |
| **Confidence score** | A single float in `[0, 1]` per `(candidate-or-document, code)`, replacing both `TagSupport.accepted` and `confidence_tier()`. Nothing downstream asks "accepted or not" — only "what's the score." |
| **Mapping-clarity weight** | The score a PVOG leaf's direct assertion contributes, set by whether that leaf maps to the situation taxonomy cleanly (one leaf → one code) or ambiguously (one leaf → several codes, per the existing `lr3-personal-matters-mapping.md` "clean"/"ambiguous" split) |
| **LLM evidence curve** | A saturating function of `(procedures, share)` giving the score an LLM-extracted consensus assertion contributes — calibrated against `situation-tag-activation`'s own LR1 hand-label sample, not a round number |
| **Noisy-OR combination** | `1 - Π(1 - sᵢ)` over every evidence source asserting the same code — the rule that lets independent corroboration (e.g. PVOG and the LLM both proposing a code) push the combined score higher than either source alone, without a source ever being discarded once another has an opinion |
| **Inclusion floor** | A small, non-statistical cutoff (`MIN_SUGGESTED_SCORE`) below which a code isn't even offered in a suggestion payload — a display/noise knob, not a precision claim, the only thing resembling a "threshold" left anywhere in this design |
| **Persisted tag confidence** | The confidence score frozen onto a *published* document's tag at promotion time — new, since `document_domain`/`document_life_situation` today are flat membership links with nothing to sort or style by |
| **Group** | A new tier above the 18 situation codes (~8 groups), purely presentational — no situation code's meaning, mentions, or consensus data changes |
| **Leaf refinement** | An optional, deterministic-only facet under a situation, populated only for PVOG-sourced documents/mentions, carrying the raw PVOG leaf code |

## 3. Where the binary gate lives today, and what has to change

Confirmed by direct read of the current (post-`situation-tag-activation`) code:

- `apps/api/app/features/discovery/tags.py`: `TagSupport(code, procedures, share, accepted)`, `confidence_tier()` keyed off `DEFAULT_MIN_PROCEDURES=2`, `axis_thresholds()` reading `discovery_tag_min_procedures[_situation]`/`min_share[_situation]` from `Settings`.
- `apps/api/app/features/discovery/repository/candidate_completeness_tags.py`: `_meets()` computes the `accepted` boolean from `TagThresholds`; `code_support()`/`candidate_axis_support()` return `TagSupport` rows (accepted or not) for the single-candidate path; `axis_acceptance()` filters to `accepted` for the bulk path.
- `apps/api/app/features/discovery/candidate_emit_payload.py::SuggestedTags`: `tag_confidence: dict[str, Literal["high", "low"]]`, built by `confidence_tier()` over `accepted_supports()`.
- `apps/api/app/schema/suggestion/payload.py::NewDocumentPayload.tag_confidence: dict[str, Literal["high", "low"]] | None`.
- **Not previously accounted for in the design session:** `apps/api/app/models/taxonomy.py`'s `document_domain`/`document_life_situation` link tables are flat `(document_id, {domain,life_situation}_id)` pairs — no score, no confidence, nothing. `DocumentRepository.add()`/`_link_terms()` and `DocumentService.create_from_suggestion()`/`_resolve_tags()` just resolve codes to ids and insert membership rows. **A continuous score computed pre-promotion is invisible on every already-published document** unless it is persisted at promotion time — the rendering/sorting half of this suite's own goal (§ in the rollout) cannot work against live documents without this. This is new scope discovered during this suite's own design, not in the original session's framing — recorded as a settled addition in [gaps-and-decisions.md](gaps-and-decisions.md).

All of the above collapses into one replacement: every `accepted: bool` becomes a `score: float`, computed once per evidence source and combined by noisy-OR, then — new — frozen onto the link-table row at the moment a document is created from a suggestion, so it survives for the UI to sort and style by.

## 4. Grouping the 18 situation codes

Confirmed against `apps/api/scripts/seed_data/taxonomy.py`'s 18 `SITUATIONS` entries — a pure partition, every code assigned to exactly one group:

| Group | Situation codes |
| --- | --- |
| `family-relationships` | `marriage`, `separation-divorce`, `birth-of-child`, `death-of-relative` |
| `home-housing` | `moving-house`, `renting-home`, `buying-property` |
| `work-career` | `new-job`, `job-loss`, `going-self-employed` |
| `education` | `studying`, `starting-school` |
| `vehicles-travel` | `buying-vehicle`, `getting-licence` |
| `residence-migration` | `immigration`, `naturalisation` |
| `health-care` | `illness-care` |
| `retirement` | `retirement` |

Confirmed by the user as the starting taxonomy (settled, see §1). `LifeSituationGroup` is a new, independent table (own `TaxonomyTermMixin` shape) with `LifeSituation.group_id` as a required FK — every situation belongs to exactly one group, no situation is grouped twice, and no existing `LifeSituation` row, mention, or consensus computation is touched.

## 5. PVOG leaf refinement: extending what `situation-tag-activation` chapter 3 already shipped

`apps/discovery-ingest/discovery_ingest/pvog/situation_mapping.py::PERSONAL_MATTER_TO_SITUATION` already maps 32 of PVOG's 56 citizen-branch leaves (18 clean + 14 ambiguous, per `situation-tag-coverage/lr3-personal-matters-mapping.md`'s human sign-off) onto 17 of the 18 situation codes, threaded through `map_pvog_record()`'s `_personal_matter_code` stash and read back by `harvest_pvog_payload()`'s `_situation_codes()`. This suite extends that existing, shipped mechanism three ways, confirmed against the full 56-leaf table in `lr3-personal-matters-mapping.md`:

1. **Mapping-clarity weights.** Pair each of the 32 entries with the clean/ambiguous distinction the sign-off table already records, instead of treating all 32 as equally certain (§3's scoring design needs this).
2. **Domain-axis recovery from the 24 unmapped citizen leaves.** Several are domain-shaped rather than situation-shaped — taxes (`1060100`, `1060200`, `1060300`, `1060800`), identity documents (`1070100`, `1070200`), legal/consumer process (`1150100`–`1150400`), disaster/victim aid (`1160100`, `1160200`), continuing education (`1040100`), and childcare (`1020200`) — and can emit a `domain_codes` hint today they emit nothing at all. The remaining unmapped leaves (civic engagement, hobbies, travel, environment) have no clean domain analogue among the 13 existing domains and stay unmapped.
3. **Leaf refinement facet.** Thread the raw PVOG leaf code (already discovered, already stashed as `_personal_matter_code`) one step further than today — onto the mention, and from there onto the document at promotion — so the UI can offer it as an optional, non-empty-only "more specific" facet under a situation, independent of (and with no bearing on) the 18-code taxonomy itself. `going-self-employed` has no citizen-branch PVOG leaf at all and gets no refinement option, same as today.

## 6. Recommendation

Ship in dependency order: the scoring engine and its persistence onto published documents (chapter 1, two commits — mirroring the `situation-tag-activation` chapter 1 precedent of landing a mergeable engine change and a behavioural change as separate commits in one chapter); the groups taxonomy (chapter 2, no dependency on chapter 1 and free to run in parallel with it); PVOG leaf refinement and domain-hint recovery (chapter 3, a real dependency on chapter 1 — both touch `document_life_situation`, and chapter 3 populates the mention columns chapter 1 defines, caught while designing chapter 3 itself — see [gaps-and-decisions.md](gaps-and-decisions.md) D10); the UI (chapter 4, depends on all three); then one post-deploy live validation (chapter 5), in the same `02-live-runs.md`-style this area's prior suites both used.

## Out of scope

Any curation/voting UI or workflow (the social layer in `apps/api/app/features/voting/` stays unwired; this suite's scoring design leaves room for a vote-count term to slot in later — see [gaps-and-decisions.md](gaps-and-decisions.md) — but builds no queue or review surface); growing the 18-code situation taxonomy to match PVOG's 56 (the group tier and the leaf-refinement facet both exist specifically so this never has to happen); touching the domain axis's own consensus behaviour beyond reusing the same scoring engine (no data suggests changing what domain tags get promoted, only how confidence in them is computed and shown); re-opening the rollback decision (settled — see §1).
