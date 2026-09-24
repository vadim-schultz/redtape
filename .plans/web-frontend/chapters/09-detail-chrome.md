---
name: "Chapter 9 — Detail chrome"
overview: "Breadcrumb compound for jurisdiction path, sectionHeader for requirements blocks, Card/Link for requirements, EmptyState when none."
todos:
  - id: breadcrumb
    content: "DocumentBreadcrumb uses Breadcrumb.Root"
    status: pending
  - id: sections
    content: "DocumentDetailQueryStatus section headings sectionHeader"
    status: pending
  - id: requirements
    content: "RequirementItem styled with tokens; empty uses EmptyState"
    status: pending
  - id: tests
    content: "Breadcrumb, RequirementItem, query status tests"
    status: pending
isProject: false
---

# Chapter 9 — Detail chrome

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/web-visual-detail-chrome` · **Status:** planned

**Depends on:** [5](05-page-titles.md), [6](06-document-card.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §2 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Detail page secondary chrome uses Chakra compounds: jurisdiction path as `Breadcrumb`, requirement
section titles as Iceberg `sectionHeader`, requirement rows as token-styled links or compact
`Card.Root`, empty requirements as `EmptyState`. Back button keeps behavior; style with `Button`
ghost variant.

## Design decisions

**Breadcrumb over joined Text.** One `Breadcrumb.Item` per [JurisdictionPathNode](../../apps/web/src/features/documents/types/index.ts); separator via `Breadcrumb.Separator`.

**RequirementItem stays a component.** Restyle internals with `Text`/`Link`/`Card` — do not invent
`RequirementRow` duplicate of Card.

**DocumentDetailQueryStatus owns section headings.** Apply `sectionHeader` to requirements and
official source titles; loading/error branches keep Skeleton/Alert patterns consistent with chapter 7
where applicable.

## Files

**Edit**

| Path | Change |
| --- | --- |
| `apps/web/src/features/documents/components/document-detail/DocumentBreadcrumb.tsx` | Breadcrumb compound |
| `apps/web/src/features/documents/components/document-detail/requirements/RequirementItem.tsx` | Tokens + link color |
| `apps/web/src/features/documents/components/document-detail/requirements/RequirementsList.tsx` | List spacing |
| `apps/web/src/features/documents/components/document-detail/requirements/RequirementsEmpty.tsx` | EmptyState or delegate to EmptyState |
| `apps/web/src/features/documents/components/document-detail/DocumentDetailQueryStatus.tsx` | Section headers, status styling |
| `apps/web/src/features/documents/components/document-detail/DocumentBackButton.tsx` | Ghost Button tokens |

**Add**

| Path | Contents |
| --- | --- |
| `DocumentBreadcrumb.test.tsx` | |
| `RequirementItem.test.tsx` | |
| `DocumentDetailQueryStatus.test.tsx` | Empty requirements + breadcrumb absent |

## Red tests

| Test | Asserts |
| --- | --- |
| `DocumentBreadcrumb · renders one item per jurisdiction node` | N nodes → N breadcrumb items |
| `DocumentBreadcrumb · renders nothing when nodes empty` | Empty array → null/empty container |
| `RequirementItem · links to required document path` | Router link to `/documents/{id}` |
| `DocumentDetailQueryStatus · empty requirements shows empty state` | No items → EmptyState visible |
| `DocumentDetailQueryStatus · loading shows skeleton not breadcrumb content` | Loading branch |

## Green

Migrate components; ensure `DocumentHeader` from chapter 5 still composes correctly.

## Refactor gate

Audit `DocumentDetailQueryStatus` — likely multiple branches (loading, error, success with/without
requirements). If >2 arms for same decision, extract status renderer helper per refactor-step rule.

## Verification

```bash
cd apps/web
npm run test -- src/features/documents/components/document-detail/
cd ../.. && ./ci.sh
```

## Out of scope

New document fields. Tree visualization.

## Git workflow

```bash
git checkout -b feat/web-visual-detail-chrome
```

```text
feat(web): use Breadcrumb, sectionHeader, and EmptyState on document detail
```
