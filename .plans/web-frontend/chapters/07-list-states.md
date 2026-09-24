---
name: "Chapter 7 — List states"
overview: "DocumentsListQueryStatus uses Skeleton, EmptyState, and Alert for loading, empty, and error; success shows cards and count."
todos:
  - id: states
    content: "Branch isLoading/isError/empty/success with Chakra components"
    status: done
  - id: tests
    content: "DocumentsListQueryStatus.test.tsx all branches"
    status: done
isProject: false
---

# Chapter 7 — List states

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/web-visual-list-states` · **Status:** done

**Depends on:** [5](05-page-titles.md), [6](06-document-card.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §6.2 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

The documents list communicates four states with native Chakra UI: loading (`Skeleton`), error
(`Alert` + status.error tokens), empty success (`EmptyState`), and populated list (count + one
`DocumentCard` per row). No custom status panel component.

**Implementation note:** the four state arms (loading/error/empty/success) exceeded the rule-of-three
threshold, so the branches were extracted into small per-state components (`LoadingSkeleton`,
`ErrorAlert`, `EmptyDocumentsState`, `PopulatedDocumentsList`) behind a `renderListContent` dispatcher,
all colocated in `DocumentsListQueryStatus.tsx` since none are reused elsewhere. Empty-state copy
("No documents found") wasn't specified in the plan and was chosen as a placeholder pending i18n.

## Design decisions

**Keep error copy as-is for now.** `"Server error"` stays hardcoded until i18n strand; only styling
changes.

**Empty vs undefined.** Treat `documents?.length === 0` after successful load as empty — not loading.

**MSW optional.** Unit tests pass props directly without fetch.

## Files

**Edit**

| Path | Change |
| --- | --- |
| `apps/web/src/features/documents/components/documents-list/DocumentsListQueryStatus.tsx` | State branches |

**Add**

| Path | Contents |
| --- | --- |
| `DocumentsListQueryStatus.test.tsx` | Four branch tests |

## Red tests

| Test | Asserts |
| --- | --- |
| `DocumentsListQueryStatus · loading renders skeleton not cards` | `isLoading` true → skeleton, zero cards |
| `DocumentsListQueryStatus · error renders alert and zero cards` | `isError` true → Alert, zero cards |
| `DocumentsListQueryStatus · empty list renders empty state` | `documents=[]`, not loading/error → EmptyState |
| `DocumentsListQueryStatus · populated list renders count and cards` | Two documents → two cards + count text |

## Green

Implement branches in order: loading, error, empty, success. Import `EmptyState`, `Alert` namespaces.

## Refactor gate

If the component exceeds three state arms in one function, extract `renderListContent(state)` helpers
or small subcomponents — rule of three applies to **decision** paths (loading / error / empty /
success = four → extract dispatch helper that returns JSX per state).

Report outcome; re-run full test file after extraction.

## Verification

```bash
cd apps/web
npm run test -- src/features/documents/components/documents-list/DocumentsListQueryStatus.test.tsx
cd ../.. && ./ci.sh
```

## Out of scope

Fetching logic in container/page. i18n for error strings.

## Git workflow

```bash
git checkout -b feat/web-visual-list-states
```

```text
feat(web): use Skeleton, EmptyState, and Alert for document list states
```
