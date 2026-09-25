---
name: "Chapter 9 — Detail chrome"
overview: "Breadcrumb compound for jurisdiction path, sectionHeader for requirements blocks, Card/Link for requirements, EmptyState when none."
todos:
  - id: breadcrumb
    content: "DocumentBreadcrumb uses Breadcrumb.Root"
    status: done
  - id: sections
    content: "DocumentDetailQueryStatus section headings sectionHeader"
    status: done
  - id: requirements
    content: "RequirementItem styled with tokens; empty uses EmptyState"
    status: done
  - id: tests
    content: "Breadcrumb, RequirementItem, query status tests"
    status: done
isProject: false
---

# Chapter 9 — Detail chrome

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/web-visual-detail-chrome` · **Status:** done

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

**Implementation note:** the loading/error/empty/success arms in `DocumentDetailQueryStatus` tripped
the refactor gate (4 arms for "what to render for this query state"), so it was split into a
`renderQueryStatus` dispatcher plus `LoadingSkeleton`/`ErrorAlert`/`DocumentDetailContent` handlers,
mirroring `DocumentsListQueryStatus` from chapter 7. `DocumentDetailView` additionally wraps the whole
`DocumentDetailQueryStatus` output in a `Card.Root` (outside the scope of the original files table) so
document details read as a single enclosed surface, per explicit follow-up direction; the back button
stays outside the card as page-level chrome.

## Files

**Edit**

| Path | Change |
| --- | --- |
| `apps/web/src/features/documents/components/document-detail/DocumentBreadcrumb.tsx` | Breadcrumb compound |
| `apps/web/src/features/documents/components/document-detail/requirements/RequirementItem.tsx` | Tokens + link color |
| `apps/web/src/features/documents/components/document-detail/requirements/RequirementsEmpty.tsx` | EmptyState or delegate to EmptyState |
| `apps/web/src/features/documents/components/document-detail/DocumentDetailQueryStatus.tsx` | Section headers, status styling, dispatcher extraction |
| `apps/web/src/features/documents/components/document-detail/DocumentBackButton.tsx` | Ghost Button tokens |
| `apps/web/src/features/documents/components/document-detail/DocumentDetailView.tsx` | Encloses detail content in `Card.Root` (not in original files table; added per explicit follow-up direction) |

`RequirementsList.tsx` needed no change — its existing spacing already matched the target look, so it
was left untouched rather than edited for its own sake.

**Add**

| Path | Contents |
| --- | --- |
| `DocumentBreadcrumb.test.tsx` | |
| `RequirementItem.test.tsx` | |
| `RequirementsEmpty.test.tsx` | |
| `DocumentDetailQueryStatus.test.tsx` | Empty requirements + breadcrumb absent |
| `DocumentBackButton.test.tsx` | |
| `DocumentDetailView.test.tsx` | Card encloses details; back button stays outside |

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
