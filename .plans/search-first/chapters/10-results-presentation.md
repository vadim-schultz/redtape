---
name: "Chapter 10 — Results presentation"
overview: "Show confidence and similarity as two rings from one shared component, surface the degraded keyword mode, and make result counts plural-aware."
id: C10
depends_on:
  - C8
  - C9
touches:
  - apps/web/src/components/data-display/
  - apps/web/src/features/documents/
  - apps/web/src/features/candidates/types/
  - apps/web/src/i18n/fallback/
  - apps/web/src/test/contract/
execution: chapter-implementer
todos:
  - id: score-ring
    content: "Extract a shared ScoreRing and keep ConfidenceCircle behaviour unchanged."
    status: pending
  - id: similarity-ring
    content: "Add SimilarityCircle and show both rings on each card with captions."
    status: pending
  - id: mapping
    content: "Map similarity and search_mode through the API types and document mapper."
    status: pending
  - id: degraded-mode
    content: "Omit the similarity ring and show a subtle hint in keyword mode."
    status: pending
  - id: plurals-copy
    content: "Add plural-aware result count and the new copy for en and de."
    status: pending
  - id: tests
    content: "Add ring, mapper, card, mode and contract tests."
    status: pending
---

# Chapter 10 — Results presentation

**Repo:** `redtape` (`apps/web`)
**Depends on:** [Chapter 8](08-hybrid-query-path.md), [Chapter 9](09-centred-search-and-sort-removal.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

## Goal

Let users see two different things on each result: how much evidence supports it (confidence) and how well it matches their query (similarity), using the visual language they already know.

## Design decisions

- **One ring component.** `features/documents/components/ConfidenceCircleView/ConfidenceCircle.tsx` is a Chakra `ProgressCircle` with traffic-light bands from `features/documents/utils/confidenceBand.ts` (low below 0.4, high from 0.7) and an aria label from `documents.confidence_aria`. Extract the ring into a shared `ScoreRing` (`components/data-display/ScoreRing.tsx`, props `value`, `label`, `palette`; at most 3 props). `ConfidenceCircle` becomes a thin wrapper with exactly today's output (the existing `ConfidenceCircle.test.tsx` and its use at `DocumentCard.tsx` stay green and unchanged), and `SimilarityCircle` is a second thin wrapper with `documents.similarity_aria` ("Similarity {percent}%, {band}"). The band words reuse `documents.confidence_low|mid|high` unless a neutral `band_*` rename is cleaner; either way both locales' files and the parity test stay consistent.
- **Two rings on a card**, each with a short visible caption or tooltip so users can tell them apart. The caption wording must stay correct whatever the confidence ring is eventually renamed (open seam O8: it is labelled "Confidence" but the product owner describes it as effectively completeness; renaming is a separate follow-up).
- **Scale.** The API sends `similarity` already rescaled to 0..1 relative to the cut-off (chapter 8). The same 0.4/0.7 bands are used for now; thresholds are re-checked against the golden set in chapter 18 (O7).
- **Degraded mode.** In `search_mode: "keyword"`, and for cards whose `similarity` is `null`, no similarity ring is rendered (not a 0% ring). A subtle, non-blocking hint explains that semantic matching is unavailable, shown once above the list, not per card. In `browse` mode only the confidence ring shows.
- **Types and mapping.** `features/candidates/types/index.ts`: `CandidateCard.similarity?: number | null`, list `search_mode`. `features/documents/services/documentMapper.ts` maps to `DocumentSummary.similarity` and the list's mode; `useDocumentsListQuery` passes the mode through. The contract test (`src/test/contract/`) and `openapi.schemas.json` already carry the new fields from chapter 8.
- **Counts.** A plural-aware result count (`documents.result_count` family with `_one/_other` in `en` and `de`; other locales get their forms in chapter 11) using the chapter 7 `t(key, { count })`.
- Card composition keeps D8 of the taxonomy suite: no nested interactive elements.
- Respect `apps/web/CLAUDE.md` size and layering limits.

## Files

| Path | Change |
| --- | --- |
| `apps/web/src/components/data-display/ScoreRing.tsx` (+ test) | Shared ring. |
| `apps/web/src/features/documents/components/ConfidenceCircleView/ConfidenceCircle.tsx` | Wrap `ScoreRing`; no behaviour change. |
| `apps/web/src/features/documents/components/SimilarityCircleView/` | `SimilarityCircle.tsx`, `index.ts`, test. |
| `apps/web/src/features/documents/components/DocumentsListView/DocumentCard.tsx` | Show both rings with captions. |
| `apps/web/src/features/documents/components/DocumentsListView/` | Search-mode hint and plural result count. |
| `apps/web/src/features/candidates/types/index.ts` | `similarity`, `search_mode`. |
| `apps/web/src/features/documents/services/documentMapper.ts`, `types/index.ts`, `hooks/useDocumentsListQuery.ts` | Mapping and pass-through. |
| `apps/web/src/i18n/fallback/en.json`, `de.json` | `similarity_aria`, captions, hint, `result_count_*`. |
| `apps/web/src/features/documents/**/*.test.tsx` | Tests. |

## Red tests

### Happy path

- `ScoreRing · renders value, palette and label` and `ConfidenceCircle` output is unchanged (existing test).
- `SimilarityCircle · uses the band colours and the similarity aria label`.
- `DocumentCard · shows confidence and similarity rings with captions in hybrid mode`.
- `mapper · maps similarity and search_mode` and a missing field defaults to `null` and `browse`.
- `result count · picks the plural form` for 1 and many in `en` and `de`.

### Negative path

- `DocumentCard · keyword mode shows no similarity ring and one hint above the list`.
- `DocumentCard · similarity null never renders a 0% ring`.
- `SimilarityCircle · clamps values outside 0..1 and non-finite values` (same rule as `confidenceBand`).
- `contract · an API response without the new fields still parses` (older API during rollout).
- `a11y · both rings have distinct accessible names`.

## Green

1. Extract `ScoreRing` with the old tests as the safety net.
2. Add `SimilarityCircle`, types, mapper and card layout.
3. Add the hint and plural count; check German and Russian lengths at phone width.

## Refactor gate

- No duplicated ring markup between the two wrappers.
- Band logic lives in one utility; `confidenceBand.ts` is reused or generalised, not copied.
- `DocumentCard` stays under about 100 lines and 3 props; extract a `CardScores` unit if needed.
- Architecture test passes; no feature-to-feature component imports.

## Verification

```bash
cd apps/web
npm test -- src/components/data-display src/features/documents src/test/contract
npm run lint && npm run format:check && npm run typecheck && npm run build
cd ../.. && ./ci.sh
```

Record screenshots (hybrid with two rings, keyword mode, `de` and `ru`, desktop and mobile) in [../run-ledger.md](../run-ledger.md).

## Out of scope

Relabelling the confidence ring, tuning thresholds (chapter 18), new locales (chapter 11), the translation pop-over (chapter 17), any API change beyond consuming chapter 8's and chapter 12's fields.

## Git workflow

```bash
git checkout feat/plans-search-first && git pull
git checkout -b feat/search-results-rings
```

```text
refactor(web): extract ScoreRing from ConfidenceCircle
test(web): describe similarity ring, keyword mode and result count
feat(web): show confidence and similarity rings on result cards
```
