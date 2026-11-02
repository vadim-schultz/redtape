---
name: "Chapter 9 — Smell sweep"
overview: "One explicit pass of the refactoring skill over every API and web entity this suite touched, recording each smell with evidence and applying behaviour-preserving refactorings one small step at a time."
todos:
  - id: scan-api
    content: "Scan the touched API entities against smells.md and record the report"
    status: pending
  - id: scan-web
    content: "Scan the touched web entities against smells.md and record the report"
    status: pending
  - id: apply
    content: "Apply the chosen refactorings, narrow suite green after each step"
    status: pending
  - id: record
    content: "Write the result table into this chapter"
    status: pending
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

_To be filled by the implementer:_ the report table per entity and the final line in the skill's form:

```text
Refactor gate: smells found -> <smells>, refactorings applied -> <names>.
Narrow suite: <command>, green after each step.
```

## Verification

```bash
./ci.sh
```

## Commits

One commit per refactoring family, `refactor(api): …` / `refactor(web): …`, each green on its own.

## Out of scope

New behaviour; new tests; dependency changes; smells in files this suite did not touch.
