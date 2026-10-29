---
name: "Chapter 1 — Visual foundation and surface shell"
overview: "Make sections, toolbars, and data shells visibly related through semantic borders, shadows, spacing, and text styles without changing product behavior."
todos:
  - id: tokens
    content: "Define or reconcile semantic surface, border, table, shadow, focus, and typography roles."
    status: pending
  - id: shell
    content: "Add the shared section/table shell composition and apply it to one representative admin view."
    status: pending
  - id: tests
    content: "Add paired token and shell regression tests."
    status: pending
isProject: false
---

# Chapter 1 — Visual foundation and surface shell

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/web-gui-harmonization-visual-foundation` · **Status:** done  
**Depends on:** existing `web-frontend` theme chapters · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-web-gui-harmonization` · **Release branch:** `main`

## Goal

Sections, toolbars, and table shells have a modest visual lift: semantic surface background, a
consistent border, a low-contrast named shadow, and shared spacing/typography. The representative
catalogue view demonstrates the pattern without changing its data or route behavior.

## Design decisions

- Reuse the current RedTape semantic tokens and text styles. Add only missing roles required by the
  visual contract.
- Prefer one `SectionCard`/surface-shell composition with an optional title and toolbar slot. Do not
  create a wrapper that only renames `Card.Root`.
- Keep static shells still; only linked document cards use the existing hover lift.
- Do not migrate every screen in this chapter. Later chapters apply the shell to the shared DataTable
  and admin surfaces after its API exists.

## Files

**Add or edit**

- `apps/web/src/theme/semantic-tokens/table.ts`
- `apps/web/src/theme/semantic-tokens/surfaces.ts`
- `apps/web/src/theme/semantic-tokens/borders.ts`
- `apps/web/src/theme/semantic-tokens/shadows.ts`
- `apps/web/src/theme/textStyles.ts`
- `apps/web/src/components/data-display/SectionCard.tsx`
- representative discovery catalogue container/component and its test
- colocated theme and shell tests

**Do not edit**

- API contracts or discovery query behavior
- the existing `AppCard` hover contract
- `frontend-ui-menu` implementation files

## Red tests

| Test | Asserts |
| --- | --- |
| `theme exposes the shared table and section surface roles` | The system resolves the expected semantic background, border, shadow, and table header/row tokens. |
| `SectionCard renders a raised title and toolbar surface` | A title, optional toolbar, and body share the intended semantic surface and accessible structure. |
| `SectionCard does not invent raw visual values` | Negative: the shared shell does not expose a raw colour/shadow value or a hover lift for a static section. |
| `catalogue page keeps its existing rows inside the shell` | Existing catalogue content still renders in the representative shell. |

Confirm both the happy and negative assertions fail before implementation.

## Green

1. Add the smallest missing semantic roles and theme assertions.
2. Implement `SectionCard` with Chakra namespace imports, a title slot, toolbar slot, and body slot.
3. Wrap the representative catalogue surface without moving query logic.
4. Run the narrow theme/shell/catalogue tests after each meaningful change.

## Refactor gate

Audit the complete `SectionCard`, the changed theme modules, and the representative catalogue
container. Check that the shell owns presentation only, no boolean mode is threaded through it, and
the containing units stay within the repository’s size/nesting guidance. Report either the extraction
performed and tests rerun or `no refactor needed` before continuing.

## Verification

```bash
cd apps/web
npm run test -- src/theme src/components/data-display/SectionCard.test.tsx <catalogue-test>
npm run lint
npm run format:check
npm run typecheck
npm run build
cd ../..
./ci.sh
```

## Out of scope

- DataTable implementation
- list-query API changes
- coverage conversion
- public card/table decisions

## Git workflow

```bash
git checkout feat/plans-web-gui-harmonization && git pull
git checkout -b feat/web-gui-harmonization-visual-foundation
```

Suggested commits:

```text
test(web): define shared surface visual contract
feat(web): add raised section shell
```

Open the chapter PR into `feat/plans-web-gui-harmonization`.

