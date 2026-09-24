---
name: "Chapter 1 — Test harness and not-found"
overview: "Vitest + jsdom wired into apps/web and ci.sh, renderWithProviders helper, and an explicit not-found route so unknown paths never show a blank main."
todos:
  - id: vitest
    content: "Add vitest, @testing-library/react, jest-dom; configure in vite.config.ts"
    status: pending
  - id: render-helper
    content: "src/test/setup.ts and renderWithProviders.tsx matching AppBootstrap stack"
    status: pending
  - id: not-found
    content: "NotFoundView and Route path=* replacement for redirect-only behavior"
    status: pending
  - id: ci
    content: "npm test script and ci.sh web section"
    status: pending
isProject: false
---

# Chapter 1 — Test harness and not-found

**Repo:** `redtape` (`apps/web`) · **Branch:** `feat/web-visual-test-harness` · **Status:** planned

**Depends on:** — · **Architecture:** [../00-architecture.md](../00-architecture.md) §7 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

`apps/web` has a real unit/component test runner and `./ci.sh` executes it. A minimal smoke test proves
the shell renders `RedTape`. Unknown URLs render a dedicated not-found view instead of silently
redirecting to `/documents`, so later chapters can assert routing without fighting a catch-all
redirect.

## Design decisions

**Vitest inside `vite.config.ts`.** Same config as test-storage/rehearsal: one alias table for build
and test. Alternative: separate `vitest.config.ts` — rejected due to alias drift risk.

**Not-found replaces `Navigate to="/documents"` for `*`.** Today [App.tsx](../../apps/web/src/app/App.tsx)
redirects unknown paths to the list. That hides routing bugs and makes a negative test meaningless.
Alternative: keep redirect and test redirect — rejected per [gaps-and-decisions.md](../gaps-and-decisions.md) seam note and chapter goal.

**renderWithProviders wraps the production provider stack.** Uses `MemoryRouter` with configurable
`initialEntries` so list/detail/not-found tests do not need a live backend.

## Files

**Add**

| Path | Contents |
| --- | --- |
| `apps/web/src/test/setup.ts` | `@testing-library/jest-dom`, cleanup after each test |
| `apps/web/src/test/renderWithProviders.tsx` | QueryClient, Chakra (defaultSystem until ch.2), LocaleProvider stub or real, MemoryRouter |
| `apps/web/src/views/NotFoundView.tsx` | Accessible message; uses Chakra `Heading` + `Text` |
| `apps/web/src/app/App.test.tsx` | Shell and not-found tests |
| `apps/web/vitest.config` block | In `vite.config.ts`: `environment: 'jsdom'`, `setupFiles` |

**Edit**

| Path | Change |
| --- | --- |
| `apps/web/package.json` | `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`; script `"test": "vitest run"` |
| `apps/web/vite.config.ts` | `test` block |
| `apps/web/src/app/App.tsx` | `path="*"` → `<NotFoundView />` |
| `ci.sh` | After typecheck, run `npm test` in `apps/web` |

**Do not edit** — theme tokens (chapter 2), feature API hooks.

## Red tests

| Test | Asserts |
| --- | --- |
| `app · renders RedTape in the layout header` | `/documents` shows wordmark text `RedTape` inside header/main tree |
| `app · renders not-found for an unregistered path` | `/nope` shows not-found copy, not document list heading |
| `app · not-found exposes a landmark main region` | `main` or `role="main"` contains the not-found message |
| `renderWithProviders · mounts children inside the router` | A probe route renders at the requested path |
| `renderWithProviders · rejects rendering without a router entry` | Initial entry `/missing` reaches NotFound when registered |

## Green

1. Install devDependencies; add `test` script.
2. `setup.ts` + `renderWithProviders.tsx` — mirror `AppBootstrap` providers except use
   `MemoryRouter` instead of `BrowserRouter` in tests.
3. `NotFoundView` with localized-ready plain strings (i18n strand may replace later).
4. Change catch-all route; update test expecting redirect if any existed.
5. Wire `ci.sh`.

## Refactor gate

- **`AppBootstrap` vs test helper duplication.** If provider wiring is copy-pasted, extract
  `AppProviders` taking `{ children, router: 'browser' | 'memory' }` only when duplication exceeds
  two copies — not preemptively in chapter 1 unless the audit finds >~15 duplicated lines.
- **`App.tsx` route map.** If a third route variant appears, consider a tiny `routes.tsx` export for
  tests — trigger is three+ special cases, not two.

Report outcome; re-run `npm run test -- src/app/App.test.tsx` after each extraction.

## Verification

```bash
cd apps/web
npm install
npm run test -- src/app/App.test.tsx
npm run lint && npm run format:check && npm run typecheck && npm run build
cd ../.. && ./ci.sh
```

## Out of scope

Custom Chakra theme (chapter 2). Color mode toggle (chapter 3). Shell visual polish (chapter 4).
MSW and API mocking — add when component tests need fetch (chapter 7+).

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/web-visual-test-harness
```

```text
test(web): add vitest, testing-library, and renderWithProviders

feat(web): show NotFoundView for unknown routes

ci: run apps/web vitest in ci.sh
```
