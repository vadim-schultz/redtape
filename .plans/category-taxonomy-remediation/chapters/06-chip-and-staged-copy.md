---
id: C6
depends_on:
  - C0
touches:
  - apps/web/src/components/data-display/CategoryChip.tsx
  - apps/web/src/components/data-display/CategoryChip.test.tsx
  - apps/web/src/i18n/fallback/en.json
  - apps/web/src/i18n/fallback/de.json
  - apps/api/scripts/seed_data/translations/en.json
  - apps/api/scripts/seed_data/translations/de.json
  - apps/web/src/i18n/fallback/fallback.test.ts
execution: chapter-implementer
todos:
  - ch06-chip-and-staged-copy
---

# Chapter 6 — Chip opacity and staged copy (M4, L4)

**Suite:** [README](README.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md) · **Ledger:** [../run-ledger.md](../run-ledger.md)
**Decisions:** invariants 7 and 8 in [../00-architecture.md](../00-architecture.md)

**Batch:** B1 · **Execution:** chapter-implementer · **Status:** planned

## Goal

Two public-surface fixes:

1. Category chips encode confidence in opacity (`style={{opacity: 0.5 + 0.5 * confidence}}`). That is an internal score shown as a visual signal. Remove it.
2. The empty-state copy for the ingress, egress, and flow sections says "staged". That is the staging wording the earlier suite removed from public presentation (D10). Remove it in both locales and in both bundles.

## Boundaries

- `depends_on`: C0.
- `touches`: `CategoryChip.tsx` and its test, the web fallback `en.json` and `de.json`, the API seed translation `en.json` and `de.json`, and `fallback.test.ts`.
- Do not change the chip size. The size is `sm` in code. C12 corrects the docs.
- Do not change the progress circle.

## Red

- **Happy path:** chips render no `opacity` style at confidence 0.1 and at confidence 0.9.
- **Negative path:** the keys `ingress_empty`, `egress_empty`, and `flow_empty` contain no staged wording in either bundle (web fallback and API seed translations). Both locales keep the same key set. The known strings include "No documents staged" and "No dependencies staged for this document" (`apps/api/scripts/seed_data/translations/en.json`, around lines 96 to 111).

Confirm the happy test fails on the existing opacity style. Confirm the negative test fails on the existing copy.

## Green

- Remove the opacity style from `CategoryChip.tsx`.
- Change the empty-state copy in both bundles, in both locales, so the key sets stay equal.

## Refactor

- Remove `opacityFor`. It has no caller after the style is removed.
- Refactor audit: the whole of `CategoryChip.tsx`, since removing the style may leave an unused prop or helper.
- No new behaviour.

## Gate

- Web: in `apps/web`, `npm run test -- src/components/data-display/CategoryChip.test.tsx src/i18n/fallback/fallback.test.ts`, then lint, format check, typecheck, and build.
- Backend: the API seed translation change is covered by the existing translation tests. Run `uv run pytest` for the translation tests in `apps/api`.
- Then `./ci.sh`.
- Record results in [the ledger](../run-ledger.md).
- Corporate build block: [corporate-build-env.md](../../../.cursor/skills/chief-of-staff/corporate-build-env.md).

## Notes

- Confidence stays in the data and in the tests. Only the visual encoding is removed (M4).
- A parity test between the two bundles protects against one locale drifting (L4).
