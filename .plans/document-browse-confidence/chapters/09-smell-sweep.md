---
name: "Chapter 9 — Smell sweep"
overview: "One explicit pass of the refactoring skill over every API and web entity this suite touched, recording each smell with evidence and applying behaviour-preserving refactorings one small step at a time."
todos:
  - id: scan-api
    content: "Scan the touched API entities against smells.md and record the report"
    status: completed
  - id: scan-web
    content: "Scan the touched web entities against smells.md and record the report"
    status: completed
  - id: apply
    content: "Apply the chosen refactorings, narrow suite green after each step"
    status: completed
  - id: record
    content: "Write the result table into this chapter"
    status: completed
isProject: false
---

# Chapter 9 — Smell sweep

**Repo:** `redtape` (`apps/api`, `apps/web`) · **Branch:** `feat/document-browse-confidence-smell-sweep` · **Status:** planned
**Depends on:** Chapters 1–8 · **Method:** `~/.claude/skills/chief-of-staff/references/refactoring/refactoring.md` (phases 1 and 2), `smells.md`, `refactorings.md` · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-document-browse-confidence` · **Release branch:** `main`

## Goal

Every chapter already runs the refactor gate on its own diff. This chapter is the second, whole-suite look the user asked for: the entities as they stand after all eight chapters, scanned together, because duplication and clumping often only show up across chapters.

## Method

For each entity below: read the whole containing entity, check it against `smells.md`, record evidence, choose one refactoring per smell, then apply one small step at a time with the narrow suite after each (revert on red). Do not add behaviour, do not add tests, do not change existing tests. Keep types strict (no `Any`/`any`), docstrings on new public Python functions, TSDoc on new exported `src/core` symbols. Smells outside the entities, or needing behaviour change, are recorded as `observed` and not touched.

Report format (per the skill):

```text
Containing entity: <path and symbol>
Scope: <method | class | module | component>

| smell | evidence | chosen refactoring | action |
```

## Entities to scan

| Side | Entity | Likely smells to check |
| --- | --- | --- |
| api | `features/discovery/repository/candidate_tag_scores.py`, `candidate_completeness_tags.py` | Duplicated Code (SQL vs Python scorer: expected `observed`, held by the parity test), Long Function, Mysterious Name |
| api | `features/candidates/repository/public_filter.py`, `cards.py` | Data Clumps (`domains`, `situations` travelling together), Long Parameter List, Repeated Switches over sort keys |
| api | `features/candidates/list_query.py`, `service.py`, `card_builder.py` | Primitive Obsession (CSV string for a code list), Feature Envy, Long Function |
| api | `scripts/seed_jurisdictions.py`, `seed_taxonomy.py`, migration | Dead Code, Mysterious Name |
| web | `features/documents/hooks/useDocumentFilters.ts`, `useDocumentListState.ts`, `utils/groupSelection.ts`, `utils/situationCodes.ts` | Mutable Data, Long Function, Duplicated Code (URL param toggling), Primitive Obsession (axis strings) |
| web | `components/DocumentFiltersView/FilterChip.tsx`, `FilterGroup.tsx`, `SituationFilterView/`, `DocumentFilters.tsx` | Primitive Obsession (`tone`), Long Parameter List, Duplicated Code between domain and situation rows |
| web | `components/DocumentsListView/*`, `ConfidenceCircleView/`, `DocumentCard.tsx`, `utils/confidenceBand.ts` | Long Function, Speculative Generality, Magic numbers |
| web | shared search box, `features/discovery-admin/components/ListSearch.tsx` | Duplicated Code (a leftover third copy is fixed here if chapter 3 left it) |
| web | `components/layout/AppMenu.tsx`, `menu/*`, `ui/MenuIconLink.tsx` | Message Chains, Middle Man, Lazy Element |
| web | `features/candidates/*` after chapter 7, `features/suggestions/*` after chapter 6 | Dead Code, Lazy Element (orphaned helpers) |

## Result

Containing entity: `apps/api/app/features/discovery/repository/candidate_completeness_tags.py`, `candidate_tag_scores.py` · Scope: module

| smell | evidence | chosen refactoring | action |
| --- | --- | --- | --- |
| Large module / Divergent Change | 209 lines: SQL blocks, bulk acceptance, the single-candidate Python scorer and the PVOG leaf lookup | Move Function to `candidate_axis_support.py` and `candidate_leaf_codes.py` | applied |
| Duplicated Code | `_candidate_rows` repeated the unnest + confidence select of `exploded_codes` | reuse `exploded_codes` (`_mention_rows`) | applied |
| Long Function | `_score_rows` loop body scored one code in 8 lines | Extract Function `_score_code` | applied |
| Mysterious Name / hidden dependency | `candidate_completeness_flags` imported `TagAxis` through `candidate_completeness_tags`; `tagged_procedures` had no docstring | import from `app.features.discovery.tags`; docstring | applied |
| Duplicated Code | SQL scorer vs Python scorer | none, held by the parity test | observed |
| Duplicated Code | `code_support` and `_consensus_scores` repeat the 3-line support-join | none, two call sites | observed |
| Large module | `candidate_completeness_tags.py` still 133 lines after the split | further split of the acceptance blocks | observed |

Containing entity: `candidate_sort.ordered_by`, `candidate_completeness.completeness_order`, `candidates/repository/public_order._directed` · Scope: function

| smell | evidence | chosen refactoring | action |
| --- | --- | --- | --- |
| Duplicated Code | `desc if DESC else asc` written three times | Extract Function `candidate_sort.directed` | applied |
| Duplicated Code | same expression in `task_sort.py`, `catalogue_filter.py` | reuse `directed` | observed (files this suite did not touch) |

Containing entity: `candidates/repository/public_filter.py`, `cards.py`, `list_query.py`, `service.py`, `card_builder.py` · Scope: module

| smell | evidence | chosen refactoring | action |
| --- | --- | --- | --- |
| Data Clumps | `domains`/`situations` travel together | already one `PublicCandidateFilter.selected` projection and a `Selected` alias | none |
| Primitive Obsession | CSV string for a code list | the shared list-query parser only carries `FilterValue` scalars; `_codes` splits once | observed (shared framework) |
| Long Function / Feature Envy / Repeated Switches | none: all functions under ~8 lines, one rank table | none | none |

Containing entity: `scripts/seed_jurisdictions.py`, `seed_taxonomy.py`, migration `20261102_remove_seeded_documents` · Scope: module

| smell | evidence | chosen refactoring | action |
| --- | --- | --- | --- |
| Magic number | `seed_taxonomy.main` printed 13 / 8 / 18 literals | derive from `len(DOMAINS)` etc. | applied |
| Dead Code | none found | none | none |

Containing entity: `features/documents/hooks/useDocumentFilters.ts`, `useDocumentListState.ts`, `utils/*` · Scope: module

| smell | evidence | chosen refactoring | action |
| --- | --- | --- | --- |
| Large module / mixed concerns | `useDocumentFilters.ts` 109 lines: hook plus seven URL helpers | Move Function to `utils/filterParams.ts` | applied |
| Layering | `utils/hasSelectedChips.ts` imports a type from the hook | narrow the parameter type | observed (a type-only import, no cycle) |

Containing entity: `DocumentFiltersView/*`, `SituationFilterView/`, `DocumentsListView/*`, `ConfidenceCircleView/`, `DocumentCard.tsx`, `utils/confidenceBand.ts` · Scope: component

| smell | evidence | chosen refactoring | action |
| --- | --- | --- | --- |
| Primitive Obsession (`tone`) | `ChipTone` is a three-member union consumed in one function | none | none |
| Duplicated Code between domain and group/situation rows | two `HStack` maps over `FilterChip`, two call sites | none (rule of three not met) | none |
| Magic numbers | thresholds, palette and card count are named constants | none | none |

Containing entity: `ListSearchBox.tsx` and its three callers in `discovery-admin` · Scope: component

| smell | evidence | chosen refactoring | action |
| --- | --- | --- | --- |
| Duplicated Code | no third copy of the search box remains (`ListSearch.tsx` deleted in chapter 3) | none | none |

Containing entity: `components/layout/AppMenu.tsx`, `menu/*`, `ui/MenuIconLink.tsx` · Scope: component

| smell | evidence | chosen refactoring | action |
| --- | --- | --- | --- |
| Message Chains / Middle Man / Lazy Element | one delegated `closesMenu`, panel rows each own their behaviour | none | none |

Containing entity: `features/candidates/*`, `features/suggestions/*` · Scope: feature

| smell | evidence | chosen refactoring | action |
| --- | --- | --- | --- |
| Dead Code | an export scan of the touched web features found no orphaned symbol | none | none |
| Dead Code | i18n key `candidates.not_found_title` is unused in code | delete it in 4 files | observed (`fallback.test.ts` requires it in `CANDIDATE_KEYS`; removing it needs a test change) |

```text
Refactor gate: smells found -> Large module / Divergent Change, Duplicated Code (x2), Long Function, Mysterious Name (hidden re-export), Magic number, mixed concerns in a hook; refactorings applied -> Move Function (x2), Extract Function (x2), reuse of exploded_codes, Replace Magic Literal.
Narrow suite: `pytest` of the candidate scoring, completeness, browse, public, admin, emit and seed tests; `npx vitest run src/features/documents`; ruff, mypy, tsc and eslint, green after each step.
```

## Verification

```bash
./ci.sh
```

## Commits

One commit per refactoring family, `refactor(api): …` / `refactor(web): …`, each green on its own.

## Out of scope

New behaviour; new tests; dependency changes; smells in files this suite did not touch.
