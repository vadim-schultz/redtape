---
name: "Chapter 1 — Unify the consensus engine, then make it axis-aware"
overview: "Stop having two independent implementations of the same consensus rule, then relax the situation axis's acceptance bar on top of the single merged engine, as two commits in one chapter/one deploy."
todos:
  - id: code-support
    content: "Add code_support() and _manual_support() to candidate_completeness_tags.py, per-code and unfiltered"
    status: pending
  - id: axis-support-entry
    content: "Add candidate_axis_support(session, candidate_id, axis, thresholds) as the single-candidate entry point"
    status: pending
  - id: delete-python-engine
    content: "Delete aggregate_tags, curated_codes, _procedures_by_code, _support, TaggedMention/ProvenancedMention from tags.py; move TagAxis there"
    status: pending
  - id: candidate-tags-signature
    content: "Change candidate_tag_suggestions() to (session, candidate_id), delete _consensus()/_axis_support()"
    status: pending
  - id: update-callers
    content: "Update suggested_tags() and candidate_detail() to the new signature"
    status: pending
  - id: axis-settings
    content: "Add discovery_tag_min_procedures_situation / discovery_tag_min_share_situation to config.py"
    status: pending
  - id: axis-thresholds-fn
    content: "Add axis_thresholds(settings, axis) as the one place either path gets its thresholds from"
    status: pending
  - id: bulk-signature
    content: "Change flags_subquery/completeness_subquery to take settings instead of a pre-built TagThresholds"
    status: pending
  - id: call-sites
    content: "Update cards.py, candidate_completeness_repository.py, candidate_relations.py to pass settings"
    status: pending
  - id: tests
    content: "Regression-prove the merge, then prove the axis-aware acceptance change on top"
    status: pending
isProject: false
---

# Chapter 1 — Unify the consensus engine, then make it axis-aware

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/situation-tag-activation-axis-aware-consensus-thresholds` · **Status:** planned

**Depends on:** none · **Decisions:** D3, D4, D5 (`../gaps-and-decisions.md`) — the merge-before-threshold ordering, PVOG non-special-casing, and the confidence-tier floor constant this chapter's merge must preserve for chapter 2; grows out of `situation-tag-coverage` T-PENDING's working hypothesis (S4) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-situation-tag-activation`

## Goal

Stop having two independent implementations of the same consensus rule. Make the SQL module the single source of truth for both the existing bulk listing/completeness-flag path *and* the single-candidate detail/emit path; then add the axis-aware threshold on top of that one engine. These two changes ship together, in one chapter/one deploy — an intermediate state where only one has landed is exactly the kind of transient divergence this chapter exists to eliminate forever, not just reduce. Within the chapter, they land as **two separate commits**: the merge first, proven behaviour-preserving by its own regression tests, then the threshold change on top, proven to be the *only* observable difference.

## Design

### Part A — merge the engines

Both engines today read the same flat `settings.discovery_tag_min_procedures`/`discovery_tag_min_share`, confirmed by direct read (`../00-architecture.md §3`):

- **Python** (single-candidate detail/emit path): `apps/api/app/features/discovery/tags.py` (`aggregate_tags`, `TagSupport`, `curated_codes`/`MANUAL_EXTRACTOR`) → `apps/api/app/features/discovery/candidate_tags.py` (`_consensus()`, `_axis_support()` — no axis parameter, same thresholds for both axes). This path returns the *full* per-code breakdown (including codes that didn't clear the bar), because `candidate_admin_service.py::candidate_detail()` needs every code's support for the admin `TagSupportChip` display, not just the accepted ones.
- **SQL** (bulk listing/completeness-flag path): `apps/api/app/features/discovery/repository/candidate_completeness_tags.py` (`TagAxis` enum lives here; `TagThresholds.from_settings()`, flat) → `.../candidate_completeness_flags.py::flags_subquery()` (one `TagThresholds` object reused for both `TagAxis.DOMAIN` and `TagAxis.SITUATION`). This path only returns the final *accepted*-codes array per candidate, aggregated — no per-code detail survives it.

**Why this is genuinely mergeable, not just two things that happen to agree:** both engines already build on the identical raw ingredients — `_support()` (procedures per code) and `_tagged()` (total tagged procedures) in the SQL module compute exactly what `tags.py`'s pure-Python `_procedures_by_code`/`_support` re-derive from an in-memory loop. `candidate.mentions` (the thing the Python path iterates) is consumed in exactly one place (`candidate_emit_payload.py:20`), and `candidate_tag_suggestions()` has exactly two callers (`candidate_emit_payload.py::suggested_tags()` and `candidate_admin_service.py::candidate_detail()`) — both already have `candidate_id` and a DB session on hand, so neither is structurally tied to the ORM-loaded mention list.

Changes:

- `apps/api/app/features/discovery/repository/candidate_completeness_tags.py`: add `code_support(exploded: CTE, thresholds: TagThresholds) -> Select` — one row per `(candidate_id, code)` (not filtered or grouped), built from the exact same `_support()`/`_tagged()`/`_meets()` pieces `_consensus()` already uses: `(candidate_id, code, procedures, share, accepted)`. Refactor `_consensus()` to filter `code_support()` by `accepted` and aggregate codes, instead of re-deriving share/accepted inline — same outward SQL behavior, one fewer place the formula is written.
- Add `_manual_support(exploded: CTE) -> Select` — the per-code mirror of the existing `_manual_branch()` (which already aggregates manual mentions into one codes-array per candidate for the bulk path): return `(candidate_id, code, procedures)` per manually-asserted code, restricted to `extractor == MANUAL_EXTRACTOR`, un-aggregated.
- Add `candidate_axis_support(session: Session, candidate_id: UUID, axis: TagAxis, thresholds: TagThresholds) -> list[TagSupport]` — the new single-candidate entry point and the direct replacement for `tags.py`'s `aggregate_tags`/`curated_codes()` combination: query `_manual_support()` filtered to `candidate_id`; if any rows, map to `TagSupport(code, procedures, 1.0, True)` for each and return (manual replaces consensus entirely — same semantics `curated_codes()` has today); otherwise query `code_support()` filtered to `candidate_id` and map rows straight to `TagSupport` (accepted already computed by `_meets()`).
- `apps/api/app/features/discovery/tags.py`: delete `aggregate_tags`, `curated_codes`, `_procedures_by_code`, `_support`, `TaggedMention`/`ProvenancedMention` (confirm nothing else still imports these before deleting). Keep `TagSupport`, `MANUAL_EXTRACTOR`, `DEFAULT_MIN_PROCEDURES`/`DEFAULT_MIN_SHARE` (chapter 2 needs the historical-floor constant, per D5). Move `TagAxis` here from the repository module — it's a shared vocabulary type both layers reference, not something that belongs buried in one repository file; the repository imports it back.
- `apps/api/app/features/discovery/candidate_tags.py`: `candidate_tag_suggestions()` changes signature from `(mentions: Iterable[DiscoveryCandidateMention])` to `(session: Session, candidate_id: UUID)`; its body becomes two calls to `candidate_axis_support()` (domain, situation), each with its own axis thresholds. Delete `_consensus()`/`_axis_support()` — now redundant.
- Update both callers: `candidate_emit_payload.py::suggested_tags()` takes `(session, candidate)` and passes `candidate.id` instead of `candidate.mentions`. `candidate_admin_service.py::candidate_detail()` passes `(self._session, candidate_id)` instead of `(row.mention for row in rows)` — it still separately calls `list_candidate_mentions()` for the mentions display list, untouched; only the tag-support computation's input changes.

### Part B — then make it axis-aware

- `apps/api/app/config.py`: add `discovery_tag_min_procedures_situation: int = Field(default=1, ge=1, ...)` and `discovery_tag_min_share_situation: float = Field(default=0.5, gt=0, le=1, ...)`. Existing `discovery_tag_min_procedures`/`discovery_tag_min_share` keep their current field names/defaults as the domain-axis values (no settings-name migration for existing deployments/env vars).
- `apps/api/app/features/discovery/tags.py`: add `axis_thresholds(settings: Settings, axis: TagAxis) -> TagThresholds` — the single place both the single-candidate path (`candidate_axis_support()`'s caller) and the bulk path (`flags_subquery()`/`completeness_subquery()`) get their thresholds from.
- `apps/api/app/features/discovery/repository/candidate_completeness_flags.py::flags_subquery` and `.../candidate_completeness.py::completeness_subquery`: signature changes from a pre-built `TagThresholds` to `settings: Settings`, building each axis's thresholds internally via `axis_thresholds()`.
- Update the three call sites of `TagThresholds.from_settings(settings)` (`apps/api/app/features/candidates/repository/cards.py`, `.../discovery/repository/candidate_completeness_repository.py`, `.../discovery/repository/candidate_relations.py`) to pass `settings` instead.

## Tests

**Regression proof the merge alone changes nothing observable**, before the threshold change is added:

- `code_support()`/`_manual_support()` SQL fixture tests (`test_candidate_completeness_tags.py`-style) covering the same cases `tags.py`'s old `aggregate_tags`/`curated_codes` tests covered.
- A `candidate_axis_support()` integration test (real DB, fixture mentions) proving it returns the same `TagSupport` values the deleted Python `aggregate_tags()` used to, for an identical fixture — the single most important test in this chapter, since it's the one place a real behavior change could slip in disguised as a refactor.
- A cross-path agreement test proving bulk `axis_acceptance()` and single-candidate `candidate_axis_support()` agree on the same fixture for the same axis (trivially true once they share the same SQL building blocks, but worth pinning explicitly so a future change that breaks it is caught immediately).

**Then, layered on top, proving the axis-aware acceptance change is the only observable difference:**

- A test proving a single-procedure situation mention is now accepted while an identical single-procedure domain mention is not (the actual regression this chapter exists to create).
- Re-run and update `test_discovery_tags.py`/`test_candidate_completeness_tags.py`/`test_discovery_candidate_emit.py` for the new call signatures, confirming domain-axis behaviour is provably unchanged (same 2/50% result on existing fixtures) while situation-axis fixtures now accept single-procedure cases.

## Verification

```bash
cd apps/api && ./ci.sh
pytest tests/test_discovery_tags.py tests/test_candidate_completeness_tags.py tests/test_discovery_candidate_emit.py -v
```

Commit the merge (Part A) and prove it green on its own before adding the threshold change (Part B) on top — two commits, not one, even though both ship in this same chapter/PR.

## Refactor gate

`grep -rn "aggregate_tags\|curated_codes\|TaggedMention\|ProvenancedMention\|_procedures_by_code" apps/api` should return nothing once Part A lands — confirm no caller outside this chapter's own files was missed before deleting. `grep -rn "TagThresholds.from_settings" apps/api` should return nothing once Part B lands — confirm all three call sites were updated, not just the ones already known.

## Commits

- `refactor(api): unify the Python and SQL consensus engines behind candidate_axis_support`
- `feat(api): add axis-aware consensus thresholds, relaxing the situation axis to one procedure`

## Out of scope

Touching domain's threshold (no data supports it — see `../00-architecture.md §5`); anything about PVOG or confidence tiers (chapters 3 and 2 respectively); any backfill or recompute step (D1 — confidence is computed live, nothing to backfill); any new review UI (invariant 3, `../01-rollout.md`).
