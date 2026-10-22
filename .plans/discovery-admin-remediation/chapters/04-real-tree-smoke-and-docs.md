---
name: "Chapter 4 — Real-tree smoke and docs"
overview: "Table-driven tests for every guard outcome and the menu-to-page path through App, plus corrected operator troubleshooting docs."
todos:
  - id: smoke-red
    content: "Real-tree tests: menu click reaches coverage; anonymous, 403, 503 outcomes"
    status: pending
  - id: smoke-green
    content: "Production fixes only if a test exposes a defect; share fixtures"
    status: pending
  - id: smoke-docs
    content: "Troubleshooting entry and corrected smoke sequence in discovery-layer.md"
    status: pending
isProject: false
---

# Chapter 4 — Real-tree smoke and docs

**Repo:** `redtape` (`apps/web` + docs) · **Branch:** `docs/discovery-admin-remediation-smoke` · **Status:** planned

**Depends on:** [02](02-route-nesting-fix.md) and [03](03-admin-probe-resilience-and-menu-feedback.md) merged · **Architecture:** [../00-architecture.md](../00-architecture.md) §4 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-admin-remediation` · **Release branch:** `main`

## Goal

Lock in the fixes with tests that go through the same route tree as production, and replace the unverified "smoke" claims in the docs with a sequence that can actually be run.

## Files

**Add or edit**

- `apps/web/src/app/routes.discoveryAdmin.test.tsx` — extend with the table-driven cases below
- `apps/web/src/test/discoveryAdminFixtures.ts` (new, only if the fetch stub and session fixture are duplicated across test files)
- [`docs/operations/discovery-layer.md`](../../../docs/operations/discovery-layer.md) — troubleshooting entry and corrected smoke sequence
- [`.plans/discovery-admin-ui/run-ledger.md`](../../discovery-admin-ui/run-ledger.md) — note only if the orchestrator agrees; otherwise hand the note to the chief of staff (the implementer does not edit ledgers)

## TDD loop

### Red

Table-driven, one parameterised case per outcome (no branching inside the test body):

1. `app · menu Coverage link opens the coverage page` — happy path. Open the menu with probe 200, click Coverage, assert the chip.
2. `app · anonymous visitor at /admin/discovery/catalogue lands on login` — negative path.
3. `app · probe 403 shows the forbidden view` — negative path.
4. `app · probe 503 shows the disabled message with retry` — negative path.

Some cases may already be green after chapters 2–3. Keep them as regression tests and **say so** in the PR (characterization tests). Any case that fails exposes a real defect: fix it minimally in this chapter.

### Green

No production change is expected. Extract shared fixtures only if they are duplicated.

### Refactor

Audit the test file and fixtures against the checklist: table-driven cases, no duplicated stubs, one concern per helper. Report the outcome.

## Docs content

`docs/operations/discovery-layer.md` additions, in the repo's STE-style prose:

- **Blank admin page or missing menu links** entry: probe status table (200/401/403/503/5xx → cause → fix), the console warning `No routes matched location`, and the `curl` status check from chapter 1.
- Corrected smoke sequence: unit tests are not a live smoke; list the worker-origin `curl` check, the sign-in check, and the three page checks.
- Keep the route table from the previous suite.

## Verification

```bash
cd apps/web
npm run test -- src/app/routes.discoveryAdmin.test.tsx src/components/layout/AppMenu.test.tsx
npm run lint && npm run format:check && npm run typecheck && npm run build
cd ../..
./ci.sh
```

Then run the **Manual smoke after chapter 4** list in [../01-rollout.md](../01-rollout.md) against the deployed site and report each item.

## Git workflow

```bash
git checkout feat/plans-discovery-admin-remediation && git pull
git checkout -b docs/discovery-admin-remediation-smoke
```

```text
test(web): cover discovery admin routes and menu through the app tree
docs(discovery): document admin route and probe troubleshooting
```

Open the chapter PR into `feat/plans-discovery-admin-remediation`, not `main`.
