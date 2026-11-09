---
id: C11
depends_on:
  - C4
touches:
  - apps/web/src/features/candidates/components/CandidateDetailView/CandidateSources.tsx
  - apps/web/src/features/documents/utils/filterParams.ts
  - apps/web/src/features/taxonomy/utils/categoryNames.ts
  - apps/discovery-ingest/discovery_ingest/client/candidates_api.py
execution: chapter-implementer
todos:
  - ch11-api-web-spec
---

# Chapter 11 — API and web spec cleanup (L5, L6, L7)

**Suite:** [README](README.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md) · **Ledger:** [../run-ledger.md](../run-ledger.md)
**Decisions:** O5 in [../gaps-and-decisions.md](../gaps-and-decisions.md)

**Batch:** B3 · **Execution:** chapter-implementer · **Status:** planned

## Goal

Three small fixes from the review:

- **L6:** the URL category filter (`filterParams.ts`) and the category name lookup (`categoryNames.ts`) each walk the category tree. Share one traversal. `filterParams.ts` also carries a duplicate `flattenCategoryCodes`.
- **L7:** the `candidates_api.py` docstring is wrong. Fix it.
- **L5:** `SourceCard` is not extracted. Record the decision. Keep the source card inline unless a second card variant appears.

## Boundaries

- `depends_on`: C4.
- `touches`: the four files listed. `CandidateSources.tsx` is touched only to confirm the inline source card. `candidates_api.py` changes are limited to the docstring.
- Do not change the URL contract or the category codes.

## Red

- **Happy path:** the URL filter and the category name lookup share one traversal. A single test drives both from the same tree fixture and gets consistent results.
- **Negative path:** unknown codes in the URL are still dropped. A URL with an unknown category code produces the same filter as a URL without it.

Confirm the happy test fails because the traversal is duplicated (for example, a test that asserts the shared export exists).

## Green

- Export one traversal from `taxonomy/utils/categoryNames.ts`. `filterParams.ts` imports it.
- Remove the duplicate `flattenCategoryCodes` in `filterParams.ts`.
- Fix the `candidates_api.py` docstring to match the function's behaviour.

## Refactor

- `SourceCard` stays inline in `CandidateSources.tsx` unless a second card variant appears. Record that decision in [../gaps-and-decisions.md](../gaps-and-decisions.md) under the L5 row.
- Refactor audit: `filterParams.ts` and `categoryNames.ts`, the containing modules of the shared traversal.
- No new behaviour.

## Gate

- Web: in `apps/web`, `npm run test -- src/features/documents src/features/taxonomy`, then lint, format check, typecheck, and build.
- Ingest: in `apps/discovery-ingest`, `uv run ruff format --check .`, `uv run ruff check .`, and `uv run mypy discovery_ingest`. The docstring change must not change any test.
- Then `./ci.sh`.
- Record results in [the ledger](../run-ledger.md).
- Corporate build block: [corporate-build-env.md](../../../.cursor/skills/chief-of-staff/corporate-build-env.md).

## Notes

- Chip size is `sm` in code. Do not change it here. C12 corrects the docs.
- O5 default: list cards use a linked title and independent chip links, with no nested anchors. C12 confirms this against the shipped markup.
