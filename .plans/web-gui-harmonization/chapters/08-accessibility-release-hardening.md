---
name: "Chapter 8 — Accessibility and release hardening"
overview: "Close the suite with accessibility, responsive, documentation, architecture, and release checks for the unified GUI."
todos:
  - id: accessibility
    content: "Verify table semantics, keyboard interaction, names, focus, and long-content handling."
    status: pending
  - id: docs
    content: "Update API/component documentation, route smoke notes, and plan status references."
    status: pending
  - id: release
    content: "Run full CI and record the refactor and manual smoke outcomes."
    status: pending
isProject: false
---

# Chapter 8 — Accessibility and release hardening

**Repo:** `redtape` (`apps/web`, documentation) · **Branch:** `feat/web-gui-harmonization-release-hardening` · **Status:** planned  
**Depends on:** [07-chevron-and-visual-integration.md](07-chevron-and-visual-integration.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-web-gui-harmonization` · **Release branch:** `main`

## Goal

The harmonized GUI is ready for release: table semantics and controls are keyboard accessible,
long values remain inspectable, empty/error states are explicit, architecture constraints are
documented, and the full local gate plus manual smoke results are recorded before the release PR.

## Design decisions

- Accessibility tests verify user-observable semantics, not Chakra implementation details.
- Long content uses a consistent wrap/truncate policy. A tooltip is used only where it gives access
  to the complete value and does not replace the visible label.
- Architecture tests are extended only for rules introduced by this suite, such as shared table
  imports or feature/service direction.
- Documentation records the stable list contract and component responsibilities; it does not copy
  implementation details that belong in source types.
- No release is marked ready with a green narrow suite but a failing root gate or an unreported
  refactor outcome.

## Files

**Edit**

- shared DataTable and pagination tests for accessibility and responsive behavior
- discovery admin tests for labels, roles, focus, and long cells
- `apps/web/src/architecture.test.ts` only if a new layer rule is required
- API/component documentation selected by the implementation
- `.plans/README.md`, suite status, and [run-ledger.md](../run-ledger.md)

**Add**

- focused accessibility regression tests where no existing colocated test is appropriate
- operator/admin smoke documentation if the repository’s existing docs location requires it

**Do not edit**

- unrelated accessibility issues outside the harmonized surfaces
- product copy unrelated to table/coverage interactions
- auth, ingestion, or deployment behavior

## Red tests

| Test | Asserts |
| --- | --- |
| `DataTable exposes headers, row cells, and named sort/filter controls` | Table semantics and control names are available to assistive technology. |
| `pagination exposes the current page and keyboard navigation` | Current/next/previous semantics are observable without pointer interaction. |
| `long table values remain inspectable at narrow width` | Full or deliberately wrapped values remain available without layout collapse. |
| `unnamed or non-semantic table controls fail the accessibility contract` | Negative: missing accessible names, invalid roles, or hidden data are rejected. |
| `full admin state matrix has no silent blank result` | Negative: loading, empty, error, and refreshing states render explicit feedback. |

Confirm the paired accessibility failures before implementation or documentation changes.

## Green

1. Add focused semantic/accessibility tests to the shared DataTable.
2. Fix labels, focus, row/link behavior, and long-cell presentation.
3. Add the smallest required architecture rule and documentation.
4. Run the full CI gate and manual smoke; fix only in-scope failures.
5. Update the ledger with chapter outcomes and prepare the release checklist.

## Refactor gate

Audit the complete DataTable accessibility surface, state-view module, and any changed documentation
helpers. Check that accessibility behavior is not hidden behind boolean mode switches, repeated
label construction is centralized, and table rendering remains separate from query transformation.
Rerun the narrow accessibility suite after each extraction and record an explicit outcome.

## Verification

```bash
cd apps/web
npm run test -- src/components/data-display src/features/discovery-admin
npm run lint
npm run format:check
npm run typecheck
npm run build
cd ../..
./ci.sh
```

Manual smoke:

- keyboard-only traversal through table sort/filter controls, row links, and pagination;
- light/dark mode and narrow viewport;
- long URLs, excerpts, IDs, empty groups, API errors, and background refetch;
- accessible names and visible focus for every interactive control;
- no non-functional document-count chevron.

## Out of scope

- New feature work discovered during smoke
- Visual changes unrelated to harmonized data surfaces
- Remote deployment or production verification

## Git workflow

```bash
git checkout feat/plans-web-gui-harmonization && git pull
git checkout -b feat/web-gui-harmonization-release-hardening
```

Suggested commits:

```text
test(web): cover harmonized table accessibility
docs(web): document list contract and release smoke checks
```

Open the chapter PR into `feat/plans-web-gui-harmonization`. After merge, open the single release PR
from the loop branch to `main`.

