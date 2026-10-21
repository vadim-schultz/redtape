---
name: "Chapter 5 — Integration smoke and docs"
overview: "Verify the browser-to-Worker-to-Render path, document the complete admin route surface, and close the chief-of-staff suite."
todos:
  - id: smoke-red
    content: "Define route, auth, proxy, and data smoke assertions"
    status: pending
  - id: smoke-green
    content: "Run CI and update operator route/configuration documentation"
    status: pending
  - id: smoke-refactor
    content: "Audit suite scope and report final refactor/verification outcome"
    status: pending
isProject: false
---

# Chapter 5 — Integration smoke and docs

**Repo:** `redtape` (`apps/web`, `docs`) · **Branch:** `docs/discovery-admin-ui-smoke` · **Status:** planned

**Depends on:** [03](03-catalogue-data-states.md) and [04](04-menu-discovery-navigation.md) merged · **Architecture:** [../00-architecture.md](../00-architecture.md) §2, §5, §7 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-admin-ui` · **Release branch:** `main`

## Goal

Prove that successful database writes are visible through the complete browser path and make the
operator route/configuration contract match the implemented UI.

The smoke must separate these concerns:

1. Render service health and cold-start readiness;
2. Worker same-origin `/api/*` proxy;
3. bearer-token authentication and admin allowlist;
4. discovery API data and catalogue/task rows;
5. React route and menu rendering.

## Red / green / refactor

### Red

Define the final smoke assertions before running them:

- no-token admin request is `401`;
- authenticated non-admin request is `403`;
- allowlisted admin probe is `200`;
- coverage and catalogue return valid JSON;
- `/admin/discovery/coverage`, `/catalogue`, `/tasks`, and a valid pipeline URL render a visible state;
- an unknown discovery path renders the explicit fallback;
- admin menu links appear only for the allowlisted session;
- Home, Browse, and Suggest retain `/`, `/documents`, and `/suggest`.

For documentation changes, use the existing operations/runbook tests where applicable. No new
production behavior should be added in this chapter.

### Green

1. Run the narrow web suite and `./ci.sh`.
2. Verify `GET /health` returns application JSON before browser checks.
3. From the deployed Worker origin, verify:

   ```text
   /api/v1/discovery/admin/tasks?limit=1&offset=0
   /api/v1/discovery/admin/coverage
   /api/v1/discovery/admin/catalogue?limit=50&offset=0
   ```

4. Sign in with the allowlisted email and manually check the four admin URLs and the menu.
5. Compare task rows and catalogue rows independently so a successful task insert is not mistaken for
   a successful catalogue query.
6. Update:

   - `docs/operations/discovery-layer.md` with the complete web route list and menu behavior;
   - `docs/operations/deployment-checklist.md` with the coverage route and explicit probe/error
     sequence;
   - `docs/operations/discovery-online-production-setup.md` if its production verification list omits
     the coverage page.

### Refactor

Audit the completed suite rather than introducing another abstraction:

- route and menu contracts are documented once;
- operational docs point to real paths;
- no chapter duplicated backend or deployment configuration;
- all changed frontend components have the expected status and accessibility tests;
- all per-chapter refactor outcomes are recorded in the rollout ledger.

For documentation-only edits, report “no refactor needed” after link and runbook tests pass.

## Files

**Edit**

- `docs/operations/discovery-layer.md`
- `docs/operations/deployment-checklist.md`
- `docs/operations/discovery-online-production-setup.md` when route coverage is incomplete
- `.plans/discovery-admin-ui/run-ledger.md`

## Verification

```bash
cd apps/web
npm run test -- src/features/discovery-admin src/components/layout
npm run lint
npm run format:check
npm run typecheck
npm run build
cd ../..
./ci.sh
```

Manual production verification is complete only when the API has left Render cold start and the
Worker-origin requests return API responses rather than an HTML platform loading page.

## Git workflow

```bash
git checkout feat/plans-discovery-admin-ui && git pull
git checkout -b docs/discovery-admin-ui-smoke
```

```text
test(web): cover discovery admin integration smoke
docs: document discovery admin route verification
```

After this chapter, open the release PR from `feat/plans-discovery-admin-ui` to `main`.
