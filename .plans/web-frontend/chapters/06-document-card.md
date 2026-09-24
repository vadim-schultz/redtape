---
name: "Chapter 6 — Document card"
overview: "DocumentCard becomes a Chakra Card compound with surface, shadow, hover lift, and namespace imports."
todos:
  - id: card
    content: "Card.Root/Body/Title/Description with RouterLink wrapper"
    status: pending
  - id: tests
    content: "DocumentCard.test.tsx happy and negative"
    status: pending
isProject: false
---

# Chapter 6 — Document card

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/web-visual-document-card` · **Status:** planned

**Depends on:** [2](02-theme-system.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §6 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Each document in the list is a clickable card: `Card.Root` on `surface.base`, `shadow="card"`, hover
elevation, `Card.Title` with Iceberg-friendly title styling, optional `Card.Description`. Uses
`Card` namespace import — no `CardRoot`.

## Design decisions

**Link wrapper pattern.** `RouterLink` wraps `Card.Root` or uses `asChild` on a Chakra link pattern
that preserves card semantics — pick one; tests assert navigation target
`/documents/${id}`.

**Title typography.** `Card.Title` with `textStyle` matching card title size (may use `sectionHeader`
or a dedicated `fontSize` on title — not bold weight).

**Hover motion.** Basic `_hover` shadow/translate; full motion tokens refined in chapter 10.

## Files

**Edit**

| Path | Change |
| --- | --- |
| `apps/web/src/features/documents/components/documents-list/DocumentCard.tsx` | Card compound |

**Add**

| Path | Contents |
| --- | --- |
| `DocumentCard.test.tsx` | Render with sample `DocumentSummary` |

## Red tests

| Test | Asserts |
| --- | --- |
| `DocumentCard · renders title inside a card` | Card region contains title text |
| `DocumentCard · links to document detail path` | Anchor/link `href` or `to` ends with document id |
| `DocumentCard · omits description when document has none` | No description element when `description` undefined |
| `DocumentCard · rejects flat CardRoot import` | ESLint optional: not required; code review checks namespace usage |

## Green

Refactor component to Card compound; keep props interface stable for parent.

## Refactor gate

Single component — audit for inline hover object size; extract `_hover` constant if object repeats
later in chapter 10.

## Verification

```bash
cd apps/web
npm run test -- src/features/documents/components/documents-list/DocumentCard.test.tsx
cd ../.. && ./ci.sh
```

## Out of scope

List empty/error states (chapter 7). Motion token binding polish (chapter 10).

## Git workflow

```bash
git checkout -b feat/web-visual-document-card
```

```text
feat(web): restyle DocumentCard with Chakra Card compound
```
