---
name: "Chapter 4 — Menu discovery navigation"
overview: "Expose allowlisted discovery pages in the Documents menu, add a full-width Home action, and replace Browse/Suggest text with accessible existing-library icons."
todos:
  - id: menu-red
    content: "Add menu happy/negative navigation and icon tests"
    status: pending
  - id: menu-green
    content: "Implement admin links, Home button, and document icons"
    status: pending
  - id: menu-refactor
    content: "Audit menu rows, probe coupling, and accessibility boundaries"
    status: pending
isProject: false
---

# Chapter 4 — Menu discovery navigation

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/discovery-admin-ui-menu-navigation` · **Status:** planned

**Depends on:** [02](02-admin-guard-feedback.md) merged · **Architecture:** [../00-architecture.md](../00-architecture.md) §3, §5–6 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-admin-ui` · **Release branch:** `main`

## Goal

Extend the existing top-level `AppMenu` without creating a second navigation system:

- Under Documents, allowlisted users see links to Catalogue, Coverage, and Tasks.
- Anonymous and non-allowlisted users do not see discovery links.
- A Home button appears at the top of the menu and links to `/`.
- Browse Documents and Suggest remain in the Documents row, but their visible controls become
  magnifying-glass and upward-arrow icons.

The existing server guard still protects direct navigation. Menu visibility is a UX filter, not an
authorization mechanism.

## Design decisions

Reuse the current architecture:

- `AppMenuPanel` remains the panel composition root.
- `DocumentsMenuRow` remains the Documents group.
- `KeyValueRow` remains the label/value layout.
- `useDiscoveryAdminProbe` and its React Query key are reused, so opening the menu does not create a
  second access contract.
- `DiscoveryAdminMenuLinks` belongs under
  `apps/web/src/features/discovery-admin/components/` because the feature owns the probe and route
  vocabulary. `DocumentsMenuRow` composes it as a shell navigation slot.
- `HomeMenuButton` belongs under `apps/web/src/components/layout/menu/` and is placed before the
  `KeyValueRow` children. It is full width and therefore spans the complete panel, including both
  visual label/value columns.

Use the installed `react-icons` package, keeping the existing Font Awesome import family where
possible:

- Browse Documents: `FaSearch`, icon-only link with `aria-label={t("nav.browse_documents")}`;
- Suggest: `FaArrowUp`, icon-only link with `aria-label={t("nav.suggest")}`;
- Home: `FaHome` alongside the translated Home label.

Do not remove accessible labels when replacing visible text. Do not add an icon dependency.

## Files

**Add**

- `apps/web/src/features/discovery-admin/components/DiscoveryAdminMenuLinks.tsx`
- `apps/web/src/components/layout/menu/HomeMenuButton.tsx`
- Focused menu tests where existing `AppMenu.test.tsx` becomes too broad

**Edit**

- `apps/web/src/components/layout/AppMenuPanel.tsx`
- `apps/web/src/components/layout/menu/DocumentsMenuRow.tsx`
- `apps/web/src/components/layout/AppMenu.test.tsx`
- `apps/web/src/components/layout/AppLayout.test.tsx` or `FloatingControls.test.tsx` if navigation is
  asserted there
- Locale fallback files only if Home/discovery labels are missing

## TDD loops

### Red

1. `AppMenu · allowlisted user sees Catalogue, Coverage, and Tasks under Documents` — happy path;
   mock the existing admin probe as `200` and assert links point to the three stable routes.
2. `AppMenu · non-admin and anonymous users do not see discovery links` — negative/access path; mock
   `403` or unauthenticated status and assert the links are absent.
3. `DocumentsMenuRow · uses labelled search and upward-arrow links` — happy path; assert Browse and
   Suggest retain their routes and accessible names while their visible text is replaced by icons.
4. `AppMenu · Home button is first and navigates to /` — happy path; assert the full-width Home action
   appears before the key-value rows and uses the root route.
5. `AppMenu · probe failure does not remove ordinary document navigation` — negative/resilience path;
   assert Browse and Suggest still render when discovery access cannot be established.

Run the focused menu suite and confirm the new assertions fail before implementation.

### Green

1. Add `HomeMenuButton` above the existing rows in `AppMenuPanel`.
2. Change `DocumentsMenuRow` to a compact accessible icon-link group using Chakra `IconButton` or
   `Link` composition and existing `react-icons`.
3. Add `DiscoveryAdminMenuLinks` that renders only when authenticated and the shared admin probe has
   succeeded; render it beneath the ordinary document links.
4. Preserve profile, colour-mode, language, focus, close, sign-out, and locale behavior.

### Refactor

Audit `AppMenuPanel`, `DocumentsMenuRow`, `DiscoveryAdminMenuLinks`, and `HomeMenuButton`:

- menu composition only routes to named row components;
- access decision logic stays with the discovery feature component;
- icons do not duplicate accessible labels or navigation URLs;
- the shared probe is not wrapped in a second API client or boolean mode switch;
- the menu does not acquire nested conditional layout branches beyond one level.

Rerun the focused menu suite after every extraction and report the refactor outcome.

## Verification

```bash
cd apps/web
npm run test -- src/components/layout/AppMenu.test.tsx src/components/layout/menu src/features/discovery-admin
cd ../..
./ci.sh
```

## Git workflow

```bash
git checkout feat/plans-discovery-admin-ui && git pull
git checkout -b feat/discovery-admin-ui-menu-navigation
```

```text
test(web): cover discovery navigation menu states
feat(web): add discovery links and document icons to app menu
```

Open the chapter PR into `feat/plans-discovery-admin-ui`, not `main`.
