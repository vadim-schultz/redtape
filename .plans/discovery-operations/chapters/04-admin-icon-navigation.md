---
name: "Chapter 4 — Discovery admin icon navigation"
overview: "Replace the three allowlisted discovery text links with accessible existing-library icons while preserving routes, authorization, and ordinary document actions."
todos:
  - id: icon-red
    content: "Add failing allowlisted, hidden, route, and accessibility assertions"
    status: pending
  - id: icon-green
    content: "Render Catalogue, Coverage, and Tasks with existing react-icons"
    status: pending
  - id: icon-refactor
    content: "Audit menu composition, accessibility, and probe coupling"
    status: pending
isProject: false
---

# Chapter 4 — Discovery admin icon navigation

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/discovery-operations-admin-icons` · **Status:** planned

**Depends on:** [02](02-queue-observability.md) · [discovery-admin UI menu chapter](../../discovery-admin-ui/chapters/04-menu-discovery-navigation.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/discovery-operations`

## Goal

Make the three discovery admin destinations compact icon controls, matching the existing Browse and Suggest document actions:

- Catalogue → `FaList`;
- Coverage → `FaTasks`, representing progress bars;
- Tasks → `FaClipboard`, representing an operational task list.

The links remain under Documents, remain visible only after the existing discovery admin probe succeeds, and retain their stable routes:

```text
/admin/discovery/catalogue
/admin/discovery/coverage
/admin/discovery/tasks
```

This chapter intentionally supersedes the earlier discovery-admin decision to keep these three links as readable text labels. The new visual treatment must preserve accessible names and discoverability.

## Design decisions

- Reuse `apps/web/src/features/discovery-admin/components/DiscoveryAdminMenuLinks.tsx`; do not create a second navigation source.
- Add icon metadata to the existing link configuration rather than duplicating three link components.
- Use the already-installed `react-icons/fa` family. Verify the exact exports during implementation; do not add an icon package.
- Use Chakra's existing link/icon-button composition and router links so keyboard focus and navigation remain native.
- Every control has a translated `aria-label` and a `title` or existing tooltip affordance. Visible icon-only presentation must not remove the accessible label.
- Preserve the server probe as the authorization boundary. `403`, unauthenticated, and unavailable outcomes must not render discovery controls.
- Preserve ordinary Browse, Suggest, Home, profile, colour-mode, language, focus, close, and sign-out behavior.
- Do not add a standalone Pipeline link; pipeline still requires a catalogue service ID and is reached from a row.

## Files

**Edit**

- `apps/web/src/features/discovery-admin/components/DiscoveryAdminMenuLinks.tsx`
- focused menu test files under `apps/web/src/components/layout/` and `apps/web/src/features/discovery-admin/`
- locale files only if the existing Catalogue, Coverage, or Tasks accessible labels are missing

No backend route, schema, worker, crawler, evidence, or authentication changes belong in this chapter.

## TDD loops

### Red

1. `allowlisted user sees labelled Catalogue, Coverage, and Tasks icon links` — mock the existing probe as successful and assert accessible link names, stable destinations, and icon rendering.
2. `non-admin and unavailable probe hide discovery icon links` — mock `403`, unauthenticated, and unavailable outcomes and assert the controls are absent while ordinary document actions remain.
3. `icon links preserve keyboard-accessible names` — assert each control is discoverable by role/name and has no text-only route regression.

Run the focused web suite and confirm the new assertions fail before implementation.

### Green

1. Add icon components to the existing immutable discovery link definitions.
2. Render icon-only router links with the translated accessible labels and tooltip/title text.
3. Keep the existing probe view selection and menu composition unchanged.

### Refactor

Audit the containing menu feature, not only the changed lines:

- the menu configuration owns route/icon/label data;
- the component only maps configuration to links;
- authorization remains in the existing probe outcome;
- no duplicate URLs or boolean display-mode parameters exist;
- icon-only controls do not introduce a second focus or tooltip system;
- ordinary Documents actions remain independent of discovery probe failure.

Re-run the focused suite after each extraction and report the refactor outcome.

## Verification

```bash
cd apps/web
npm run test -- src/components/layout/AppMenu.test.tsx src/components/layout/menu src/features/discovery-admin
npm run lint
npm run format:check
npm run typecheck
npm run build
cd ../..
./ci.sh
```

Manual smoke:

- allowlisted user sees three icon controls with tooltips/accessible labels;
- non-admin user sees none of the discovery controls;
- each icon navigates to the existing route;
- menu remains usable when the discovery probe is unavailable.

## Out of scope

New icon dependencies, new admin routes, backend/API changes, crawler work, screenshots, evidence, automatic emit, voting, moderation, and canonical promotion.
