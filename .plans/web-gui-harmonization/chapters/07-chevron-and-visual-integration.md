---
name: "Chapter 7 — Chevron and visual integration"
overview: "Verify the menu-suite chevron fix and apply the harmonized visual language across the completed admin data surfaces."
todos:
  - id: ownership
    content: "Confirm the existing frontend-ui-menu chapter owns and removes the non-functional count chevron."
    status: pending
  - id: smoke
    content: "Run the cross-route visual integration pass in light, dark, and narrow layouts."
    status: pending
  - id: tests
    content: "Add integration regressions without duplicating the menu chapter implementation."
    status: pending
isProject: false
---

# Chapter 7 — Chevron and visual integration

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/web-gui-harmonization-visual-integration` · **Status:** planned  
**Depends on:** [05-coverage-metrics-tables.md](05-coverage-metrics-tables.md), [06-table-interactions.md](06-table-interactions.md), and [frontend-ui-menu chapter 1](../../frontend-ui-menu/chapters/01-remove-list-chevron.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-web-gui-harmonization` · **Release branch:** `main`

## Goal

The completed table and coverage surfaces read as one interface across routes and modes. The
populated document list has no non-functional expansion chevron beside its count. The existing
frontend-ui-menu chapter remains the owner of the source fix; this chapter verifies the integration
and catches regressions caused by table/list-shell work.

## Design decisions

- Do not duplicate the chevron implementation or take ownership of the menu chapter’s source file.
- A legitimate select indicator remains allowed in filter controls; the regression targets the
  document-count row and `aria-expanded`/expand affordances only.
- Visual smoke covers light/dark mode, narrow width, long values, refreshing states, and all admin
  routes in the rollout checklist.
- Fix only defects introduced by this suite or the linked menu chapter; unrelated visual polish gets
  a follow-up plan.

## Files

**Edit**

- integration tests for document list/table shell and relevant route tests
- plan links/status references if the menu chapter changes its completion path
- only the shared visual/table source file proven to cause a regression

**Do not edit**

- `frontend-ui-menu` chapter implementation as a duplicate
- API contracts
- unrelated route or brand behavior

## Red tests

| Test | Asserts |
| --- | --- |
| `populated document count row has no expand control` | Count text and rows render without `aria-expanded`, disclosure role, or non-functional chevron. |
| `admin tables retain the shared shell across routes` | Catalogue, documents, tasks, mentions, and coverage expose the same surface and state language. |
| `legitimate filter select indicators remain available` | Negative: removing the count affordance does not remove a real filter select indicator or its accessible name. |
| `narrow admin tables remain horizontally inspectable` | Negative: narrow layout does not hide table content or remove keyboard access. |

Confirm the relevant existing regression fails before any integration adjustment.

## Green

1. Verify the linked menu chapter’s test and source ownership.
2. Add integration assertions at the document-list and admin-route boundaries.
3. Fix only any source regression revealed by those tests.
4. Perform the manual smoke sequence and record concrete failures for the next chapter if they are
   outside this suite.

## Refactor gate

Audit the complete count-row/list-shell integration and any changed route composition. Ensure no
visual-only boolean prop creates a second list mode, no duplicate chevron detector exists, and route
tests remain focused on route behavior rather than styling implementation details. Report the
outcome and rerun the narrow suite after each extraction.

## Verification

```bash
cd apps/web
npm run test -- src/components/feedback src/features/documents src/features/discovery-admin
npm run lint
npm run format:check
npm run typecheck
npm run build
cd ../..
./ci.sh
```

Manual smoke:

- `/documents`, `/admin/discovery/catalogue`, `/coverage`, `/tasks`, document detail, and pipeline
  detail in light and dark mode;
- approximately 360px viewport with long URLs and excerpts;
- refresh, empty, error, and populated states;
- no count-row chevron; real select indicators still work.

## Out of scope

- New menu design
- New tables or API behavior
- Reworking the RedTape brand

## Git workflow

```bash
git checkout feat/plans-web-gui-harmonization && git pull
git checkout -b feat/web-gui-harmonization-visual-integration
```

Suggested commits:

```text
test(web): guard harmonized admin visual integration
fix(web): preserve list affordances while removing stray chevron
```

Open the chapter PR into `feat/plans-web-gui-harmonization`.

