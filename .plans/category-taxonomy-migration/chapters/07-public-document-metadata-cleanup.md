---
name: "Chapter 7 — Remove public staging and completeness metadata"
overview: "Remove the staged/unreviewed notice and completeness section from the document experience while retaining only the progress-circle confidence signal and any private ranking inputs still required."
id: C7
depends_on:
  - C5
  - C6
touches:
  - apps/web/src/features/candidates/
  - apps/web/src/features/documents/components/ConfidenceCircleView/
  - apps/web/src/components/data-display/CompletenessChips/
  - apps/web/src/i18n/fallback/
  - apps/api/app/schema/candidate/
  - apps/api/app/features/candidates/
  - apps/api/app/features/discovery/
  - apps/api/tests/
  - apps/web/src/test/
execution: chapter-implementer
todos:
  - id: remove-banner
    content: "Remove the staged/unreviewed banner from all document states and its user-facing translation keys."
    status: pending
  - id: remove-checklist
    content: "Remove the completeness section and public-only completeness fields while preserving required internal ranking inputs."
    status: pending
  - id: retain-progress
    content: "Verify the confidence/progress circle remains the only indirect confidence signal."
    status: pending
  - id: tests
    content: "Add negative UI/contract tests for hidden staging/completeness and regression tests for confidence display and ranking."
    status: pending
---

# Chapter 7 — Remove public staging and completeness metadata

**Repo:** `redtape` (`apps/api`, `apps/web`)
**Depends on:** [Chapter 5](05-frontend-category-browsing.md), [Chapter 6](06-admin-and-suggestion-contract-cutover.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Decisions:** [../gaps-and-decisions.md](../gaps-and-decisions.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

## Goal

Remove technical discovery state from the user-facing document experience:

- no “Staged and unreviewed” banner;
- no completeness heading, count, or checklist;
- no public DTO fields whose only purpose is rendering those disclosures;
- the confidence/progress circle remains as the indirect signal.

This is a presentation and contract cleanup, not permission to remove internal score calculations that still rank candidates or support operations.

## Design decisions

- Delete the banner from the shared `CandidateDetailView` shell so it cannot reappear in loading, error, or loaded states.
- Remove `CandidateChecklist` and its `CompletenessChips` dependency from the document detail composition. Delete the shared component only after reference scans prove no other feature uses it.
- Audit `CandidateCard.status`, `completeness`, `complete`, and `flags` independently. Remove them from public responses only when no public consumer needs them; retain private query projections for ranking/operations where required.
- Keep `confidence` and the existing progress-circle component (`ConfidenceCircleView`) intact and visible wherever the document list currently presents it. Do not replace confidence with a renamed completeness field.
- Remove only translation keys that no longer have consumers, and maintain API/web translation parity.
- Admin/operator surfaces may retain technical status in their explicitly internal context; this chapter removes public document disclosures, not useful moderation diagnostics.

## Files

| Path | Change |
| --- | --- |
| `apps/web/src/features/candidates/components/CandidatesBanner/CandidatesBanner.tsx` | Delete the public staged/unreviewed banner component after reference scan. |
| `apps/web/src/features/candidates/components/CandidateDetailView/CandidateDetailView.tsx` | Remove the banner from every query state. |
| `apps/web/src/features/candidates/components/CandidateDetailView/CandidateDetailContent.tsx` | Remove checklist composition while preserving header, relationships, flow, and evidence. |
| `apps/web/src/features/candidates/components/CandidateDetailView/CandidateChecklist.tsx` | Delete or isolate from public detail after all callers are removed. |
| `apps/web/src/components/data-display/CompletenessChips/` | Delete only if no internal/admin caller remains; otherwise keep it outside the public document view. |
| `apps/web/src/features/candidates/types/index.ts` and `types/detail.ts` | Remove public-only completeness/status fields or split internal and public read types. |
| `apps/web/src/features/documents/components/ConfidenceCircleView/` | Preserve the progress-circle contract and add a regression test if it lacks one for the current list path. |
| `apps/api/app/schema/candidate/read.py` | Remove public completeness fields that have no remaining consumer, or document why an internal API still needs them. |
| `apps/api/app/features/candidates/card_builder.py` | Keep ranking inputs separate from public card mapping. |
| `apps/api/app/features/candidates/repository.py` | Preserve private completeness/ranking query data only where required. |
| `apps/api/tests/test_candidates_public_api.py` | Assert the public response no longer exposes removed presentation fields. |
| `apps/web/src/features/candidates/containers/CandidateDetailPage.test.tsx` | Replace banner/checklist assertions with absence and confidence regressions. |
| `apps/web/src/features/candidates/components/CandidateChecklist.test.tsx` | Delete or move to an internal-only test according to reference scan. |
| `apps/web/src/i18n/fallback/{de,en}.json` | Remove staged/banner/checklist keys with no consumers. |
| `apps/api/scripts/seed_data/translations/{de,en}.json` | Keep translation parity after key removal. |

## Red tests

### Happy path

- `candidate detail · renders title, categories, relationships, and confidence` asserts useful content remains after cleanup.
- `document card · still renders the progress circle from confidence` asserts the indirect signal is intact.
- `candidate list · internal ranking remains deterministic` asserts removing public fields does not change ordering.

### Negative path

- `candidate detail · does not render Staged and unreviewed` asserts the banner is absent in loaded, loading, and error states.
- `candidate detail · does not render completeness section or count` asserts no checklist heading, “n of 5” text, or completeness chips remain.
- `candidate API · omits presentation-only completeness fields` asserts the public contract contains no removed fields when no consumer requires them.
- `translation parity · removed banner/checklist keys have no dangling consumers` asserts no stale key lookup remains.

## Green

1. Add absence tests before removing the banner and checklist.
2. Remove public composition and fields, preserving internal ranking projections.
3. Remove dead translations/components only after a repository-wide reference scan.
4. Add/retain the progress-circle regression test.

## Refactor gate

Audit the complete public candidate/detail presentation:

- no public component imports `CandidatesBanner`, `CandidateChecklist`, or completeness chips;
- private ranking data is not threaded into public components;
- confidence/progress has one source and one visual component;
- no `status`/`complete` boolean changes public rendering;
- the query-state shell remains a simple loading/error/not-found/content dispatcher;
- no dead translation keys or DTO fields remain without a documented internal consumer.

Report the refactor outcome and rerun the narrow suite after every extraction or deletion.

## Verification

```bash
cd apps/web
npm test -- src/features/candidates src/features/documents/components/ConfidenceCircleView src/i18n
npm run lint && npm run format:check && npm run typecheck && npm run build

cd ../api
uv run pytest tests/test_candidates_public_api.py tests/test_candidate_completeness.py
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
cd ../..
./ci.sh
```

Record public response shape, absent copy, and progress-circle evidence in [../run-ledger.md](../run-ledger.md).

## Out of scope

Accordion restructuring, source-card design, deleting internal completeness calculations, deleting all status fields from admin APIs, taxonomy schema changes, embeddings, and entity identification.

## Git workflow

```bash
git checkout feat/plans-category-taxonomy-migration && git pull
git checkout -b feat/public-document-metadata-cleanup
```

```text
test(web): describe removal of public staging and completeness details
refactor(web): hide technical document metadata from the public view
```
