---
name: "Chapter 3 — KeyValueRow"
overview: "Port eggs KeyValueRow (1fr 3fr grid) into apps/web; no menu wiring yet."
todos:
  - id: component
    content: "KeyValueRow.tsx under components/ui"
    status: pending
  - id: tests
    content: "Grid ratio and alignment tests"
    status: pending
isProject: false
---

# Chapter 3 — KeyValueRow

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/frontend-ui-menu-key-value-row` · **Status:** planned

**Depends on:** [2](02-single-floating-control.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §3 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-frontend-ui-menu` · **Release branch:** `main`

---

## Goal

Add a shared `KeyValueRow` layout primitive matching eggs for the menu panel in chapter 4.

## Design decisions

**Source.** Copy shape from `eggs/src/components/ui/KeyValueRow.tsx`: `SimpleGrid`, `templateColumns="1fr 3fr"`,
`data-testid="key-value-row"`, `alignItems="center"`, muted label `Text`.

**Tests.** Use `renderWithProviders` per redtape convention.

**Scope.** No imports from menu in this chapter.

## Files

**Add** — `apps/web/src/components/ui/KeyValueRow.tsx`, `KeyValueRow.test.tsx`.

## Red tests

| Test | Asserts |
| --- | --- |
| `KeyValueRow · uses a 1fr / 3fr column template` | `gridTemplateColumns` |
| `KeyValueRow · vertically centres label and value` | `alignItems: center` |
| `KeyValueRow · renders the label text` | Label and children visible |

## Green

Port component and tests from eggs (adapt imports).

## Refactor gate

N/A if clean port; report “no refactor needed” if so.

## Verification

```bash
cd apps/web
npm run test -- src/components/ui/KeyValueRow.test.tsx
cd ../.. && ./ci.sh
```

## Git workflow

```bash
git checkout feat/plans-frontend-ui-menu && git pull
git checkout -b feat/frontend-ui-menu-key-value-row
```

```text
test(web): KeyValueRow 1fr 3fr layout

feat(web): add KeyValueRow panel primitive
```

Open PR **into `feat/plans-frontend-ui-menu`**.
