---
name: "T3 — Architecture guards"
overview: "Make the layering rules executable. Web: an ESLint no-restricted-imports rule for cross-feature and shared-to-feature imports (relative paths included) plus a path-resolving extension of architecture.test.ts. API: an AST-walking pytest for schema/ and for services/repositories. Both start with a measured allow-list that other chapters shrink."
todos:
  - id: web-eslint
    content: "ESLint no-restricted-imports: cross-feature (relative) and shared-to-feature, with a baseline override"
    status: pending
  - id: web-test
    content: "architecture.test.ts: resolved cross-feature and shared-to-feature checks, stale-baseline test"
    status: pending
  - id: api-test
    content: "tests/test_architecture.py: schema imports no features or ORM classes; services and repositories import no litestar; allow-lists"
    status: pending
isProject: false
---

# T3 — Architecture guards

**Repo:** `redtape` · **Branch:** `refactor/architecture-guards` · **Status:** planned

**Depends on:** none · **Architecture:** [../00-audit-report.md](../00-audit-report.md) (L5, L8, D13, section 4) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-codebase-audit` · **Release branch:** `main`

**Touches:** `apps/web/eslint.config.js`, `apps/web/src/architecture.test.ts`, one new API test file (`apps/api/tests/test_architecture.py`). **After:** none.

**Findings:** L5, L8, D13 (and the "ESLint has no `no-restricted-imports`" tooling gap in section 1).

## Goal

Layering that today lives in `CLAUDE.md` and in reviewers' heads fails CI instead:

- web: a feature does not reach into another feature's components, containers, services or utils; shared code (`components/`, `services/`, `hooks/`, ...) does not import `features/`;
- API: `schema/` does not import `features/` or ORM classes; services, repositories and models do not import `litestar`.

Rules start with an allow-list of measured, existing violations. The chapters named below delete their entries; chapter G2 verifies the lists are empty or consciously permanent. No application behaviour changes.

## Files

- `apps/web/eslint.config.js` — currently one `tseslint.config(...)` block plus `prettier`; it has no `no-restricted-imports`. Add the generated per-feature blocks, the shared block and a named baseline block (below).
- `apps/web/src/architecture.test.ts` — already guards "components do not import feature services" (`featureServiceImports`, `IMPORT_RE` matching only relative `from "..."`), inline query keys, kebab folders and tables. Extend it; keep the existing exports and tests untouched.
- `apps/web/CLAUDE.md` — states "Features do not import each other's components"; no edit here (docs follow the rule, not the other way round), but the PR notes the widened rule.
- New: `apps/api/tests/test_architecture.py`.
- `apps/web/tsconfig.json` has no `paths` or `baseUrl` (verified), so there are no alias imports: every cross-feature import is a relative path, which is why the ESLint rule is regex-based on the specifier and the test resolves paths.

## The rules

### Web

Features: `auth`, `candidates`, `discovery-admin`, `documents`, `locations`, `suggestions`, `taxonomy`.

| Rule | Statement | Enforced by |
| --- | --- | --- |
| W-A | A non-test file outside `src/features`, `src/app` and `src/test` (that is `components`, `contexts`, `hooks`, `services`, `utils`, `i18n`, `theme`, `worker`) does not import from `features/`. `src/app` is the composition root and `src/test` holds fixtures; both are allowed. | ESLint + test |
| W-B | A non-test file in feature F does not import another feature G, except through G's public surface: `G/types/**` (any G), `auth/contexts/**`, `taxonomy/hooks/**` (reference data). `components/`, `containers/`, `services/`, `utils/`, other hooks and the feature root are not public. | ESLint + test |
| W-C | Existing: components never import any feature `services/*` module. | existing test, unchanged |

Test files (`*.test.ts[x]`) are exempt: 27 of the 64 cross-feature import specifiers in the tree are in test files (almost all `auth/services/fakeAuthGateway` and `authGateway`, deliberate test seams); the other 37 are production code.

### API

| Rule | Statement |
| --- | --- |
| A-1 | No module under `app/schema/` imports `app.features.*`. |
| A-2 | No module under `app/schema/` imports an ORM class from `app.models.*`. Enums and constants are allowed (every `StrEnum` such as `DiscoveryTaskKind` lives in `app/models` and 23 such imports are legitimate); a class is an ORM class when its body assigns `__tablename__`. |
| A-3 | No module in `app/services/`, `app/models/`, no module named `repository.py` or inside a `repository/` package, and no module named `service.py` or `*_service.py` imports `litestar` (directly). |
| A-4 | The same set does not reach `litestar` through its `app.*` imports, except through three named hub modules (allow-list). |

The narrowing of A-2 to ORM classes is deliberate: banning every `app.models` import from `schema/` would put 23 harmless enum and constant imports on the allow-list and bury the seven real violations.

## Measured violations (the allow-lists)

All measured read-only on 2026-11-02 at `main` `0e713cc`: ESLint with a scratch config outside the repo (symlinked `node_modules`), and a stdlib `ast` walk of `apps/api/app`.

### Web: 7 files

| File (non-test) | Imports | Rule | Removed by |
| --- | --- | --- | --- |
| `src/services/api.ts:2` | `../features/auth/contexts/AuthContext` | W-A | W1 (finding L8: `useApi` moves out of shared `services/`) |
| `src/components/layout/menu/ProfileMenuRow.tsx:7` | `../../../features/auth/contexts/AuthContext` | W-A | none assigned |
| `src/components/layout/menu/DocumentsMenuRow.tsx:5` | `../../../features/discovery-admin/components/DiscoveryAdminMenuLinks` | W-A | none assigned |
| `src/features/candidates/components/CandidateDetailView/CandidateScreenshot.tsx:5` | `../../../suggestions/utils/formatRelativeTime` | W-B | W2 (`formatRelativeTime` and `formatRetryAfter` merge into a shared util, D13) |
| `src/features/discovery-admin/components/columns/candidateColumns.tsx:2` | `../../../suggestions/utils/formatRelativeTime` | W-B | W2 |
| `src/features/discovery-admin/components/columns/taskColumns.tsx:3` | `../../../suggestions/utils/formatRelativeTime` (the D13 site the old test misses) | W-B | W2 |
| `src/features/discovery-admin/components/columns/cells/CandidateReadinessCell.tsx:1` | `../../../../candidates/components/CompletenessChips` | W-B | W2 (shared blocks) or W4 |

"None assigned": the audit lists L8 only for `services/api.ts`. The two layout rows are a separate finding of this chapter; the chief of staff either assigns them to W2 (move `DiscoveryAdminMenuLinks` and the auth hook usage behind a shared prop or context) or accepts them as a permanent exception and records it in G2.

Allowed by the public-surface exception today (not in the baseline): `discovery-admin` -> `auth/contexts/AuthContext` (15 non-test files: `RequireDiscoveryAdmin.tsx`, `utils/discoveryAdminGuardOutcome.ts` and 13 hooks, which W1 collapses), `discovery-admin` -> `taxonomy/hooks` (`useTagNames.ts`), `documents` -> `taxonomy/{types,hooks}` (9 files), `documents` and `discovery-admin` -> `candidates/types` (3 files).

### API: allow-lists

**A-1 (1 import)**

| File | Import | Removed by |
| --- | --- | --- |
| `app/schema/discovery/candidates.py:10` | `app.features.suggestions.slugs.pick_title` | B3 (L5; B1 decides where `pick_title` lives) |

**A-2 (7 ORM-class imports in 3 files)**

| File | ORM classes | Removed by |
| --- | --- | --- |
| `app/schema/discovery/read.py:10` | `CatalogueService`, `DiscoveryArtifact`, `DiscoveryCandidateMention`, `DiscoveryDocumentCandidate`, `DiscoveryTask` (used by the `from_row` classmethods) | B3 (L5) |
| `app/schema/discovery/artifacts.py:12` | `DiscoveryArtifact` | B3 (L5) |
| `app/schema/suggestion/read.py:11` | `Suggestion` (`from_row`) | none assigned: L5 names only `schema/discovery`; B2 or B3 should take it, or it stays as a permanent exception recorded by G2 |

**A-3 (direct `litestar` imports): empty.** `app/services`, `app/models` and every repository and service module are clean today; the rule locks that in.

**A-4 (transitive): three hub modules.** Starting from the A-3 set, a breadth-first walk over `app.*` imports reaches `litestar` only through these three modules (the allow-list stops the walk at them):

| Hub | Litestar import | Reached by | Removed by |
| --- | --- | --- | --- |
| `app.shared.list_query.errors` | `ValidationException` (`raise_if_any`) | every discovery and candidates repository through `app.shared.list_query`, and `features/candidates/service.py:16` and `features/discovery/candidate_list_items.py:13`, which call `raise_if_any` and so raise an HTTP exception from below the controller | none assigned (closest: B5, list query params; the fix is a domain error mapped in the controller, as chapter 1 of the previous remediation did for discovery) |
| `app.shared.locale` | `Request` | `features/candidates/service.py:17` (imports `ResolvedLocale` from the module that also defines the request provider) | B1 (`ResolvedLocale` is split from `provide_resolved_locale`) |
| `app.schema.discovery.artifacts` | `UploadFile` | `features/discovery/admin_service.py` and `candidate_admin_service.py` through `app.schema.discovery.read` | B3 |

## TDD loop

### Red

**Web.**

1. `src/architecture.test.ts`: add failing tests (they fail because `crossFeatureImports` and `sharedFeatureImports` do not exist yet, then because the baseline is empty):
   - `flags a relative import of another feature's utils` (`features/candidates/components/X.tsx` importing `../../../suggestions/utils/formatRelativeTime`): 1 hit.
   - `flags a relative import of another feature's components` (`features/discovery-admin/components/columns/cells/X.tsx` -> `../../../../candidates/components/CompletenessChips`).
   - `allows types, auth contexts and taxonomy hooks` (`../../taxonomy/types`, `../../auth/contexts/AuthContext`, `../../taxonomy/hooks/useDomainsQuery`): 0 hits (negative-path guard against over-blocking).
   - `ignores imports inside the same feature and into shared folders` (`../hooks/useX`, `../../../components/data-display/DataTable`): 0 hits.
   - `flags a shared module importing features` (`src/services/x.ts` -> `../features/auth/contexts/AuthContext`) and `allows src/app and src/test` to do so.
   - `cross-feature imports match the baseline exactly`: the offender list equals the baseline list (the real tree against the real file list).
   - `every baseline entry still violates` (fails when a chapter fixed a file but forgot to delete its line: the stale-entry test).
   - `eslint config and test share the public surfaces`: reads `eslint.config.js` and asserts it contains the `PUBLIC_SURFACES` string constant of the test.
2. ESLint: with the new blocks and an empty baseline, `npm run lint` reports the 7 files above (record the output). That is the red.

**API.** `tests/test_architecture.py`, empty allow-lists:

- `test_schema_imports_no_feature_module` fails with the `candidates.py` import.
- `test_schema_imports_no_orm_class` fails with the three files above.
- `test_services_and_repositories_import_no_litestar` passes (zero violations; it is the lock).
- `test_services_and_repositories_reach_no_litestar_except_through_hubs` fails with the three hubs when the hub list is empty.
- Unit tests for the helpers on in-memory source strings (the happy and negative paths of the checker itself, so a broken walker cannot silently pass): `test_import_walker_sees_function_level_and_type_checking_imports`, `test_import_walker_resolves_relative_imports`, `test_orm_class_detection_requires_a_tablename`, `test_a_synthetic_service_importing_litestar_is_flagged`, `test_a_synthetic_schema_importing_an_enum_is_allowed`.

### Green

**Web `eslint.config.js`.** Generate, do not hand-write, one block per feature, so adding a feature adds one array entry:

```js
const FEATURES = ["auth", "candidates", "discovery-admin", "documents", "locations", "suggestions", "taxonomy"];
// Public surface of a feature: types of any feature, the auth context, taxonomy reference-data hooks.
const PUBLIC_SURFACES = "(?:auth/contexts|taxonomy/hooks)(?:/|$)|[a-z-]+/types(?:/|$)";
const crossFeature = (own) => ({
  files: [`src/features/${own}/**/*.{ts,tsx}`],
  ignores: ["**/*.test.{ts,tsx}"],
  rules: { "no-restricted-imports": ["error", { patterns: [{
    regex: `^(?:\\.\\./)+(?!${PUBLIC_SURFACES})(?:${FEATURES.filter((f) => f !== own).join("|")})(?:/|$)`,
    message: "Features talk to each other only through types/, auth/contexts and taxonomy/hooks. Move shared code to src/utils or src/components.",
  }] }] },
});
```

plus one block for W-A (`files: ["src/{components,contexts,hooks,services,utils,i18n,theme,worker}/**/*.{ts,tsx}"]`, `ignores` tests, regex `^(?:\.\./)+features(?:/|$)`), plus the baseline block placed last (so it wins) and delimited for the test:

```js
// architecture-baseline:start (T3; delete a line when its chapter fixes the file)
{ name: "architecture-baseline", files: [
  "src/services/api.ts",                                  // W1
  "src/components/layout/menu/ProfileMenuRow.tsx",        // unassigned
  "src/components/layout/menu/DocumentsMenuRow.tsx",      // unassigned
  "src/features/candidates/components/CandidateDetailView/CandidateScreenshot.tsx", // W2
  "src/features/discovery-admin/components/columns/candidateColumns.tsx",          // W2
  "src/features/discovery-admin/components/columns/taskColumns.tsx",               // W2
  "src/features/discovery-admin/components/columns/cells/CandidateReadinessCell.tsx", // W2/W4
], rules: { "no-restricted-imports": "off" } },
// architecture-baseline:end
```

The regex was verified read-only against 11 sample specifiers (bans `../../../suggestions/utils/x`, `../../taxonomy/utils/x`, `../../auth/services/authGateway`; allows `../../auth/contexts/x`, `../../candidates/types`, `../hooks/x`, `../../../components/data-display/DataTable`) and against the tree (exactly the 7 files). It is depth-independent because it only looks at the first segment after the `../` run. Known limit: a feature that gains a sub-folder named like another feature (`features/documents/auth/`) would false-positive; none exists, and the resolved-path test below is the precise check.

**Web `architecture.test.ts`.** Add, in the existing style (pure exported helpers, then `describe` blocks):

- `crossFeatureImports(file, source): string[]` resolves each relative specifier with `path.resolve(path.dirname(file), spec)`, derives `(ownFeature, targetFeature, layer)` from `path.relative(FEATURES, ...)`, and returns the specifiers where `targetFeature !== ownFeature` and the layer is not public (`types` for any target, `contexts` for `auth`, `hooks` for `taxonomy`).
- `sharedFeatureImports(file, source)` for W-A on files outside `features/`, `app/` and `test/`.
- `IMPORT_RE` also learns `import("...")` and `export ... from`; the current expression already matches `export { x } from "./y"` and plain `import x from`, but not dynamic `import(` or bare `import "./x"` (side-effect imports): extend it, and add one test per new form.
- `baselineFiles()` parses the quoted paths between the `architecture-baseline:start/end` markers of `eslint.config.js` (read with `readFileSync`; no import of the config, so vitest does not load ESLint plugins). The exact-match test compares offenders (relative to `apps/web`, sorted) with that list.

**API `tests/test_architecture.py`.** Pure stdlib (`ast`, `pathlib`); no database fixture, no import of `app` (the ORM check is static: collect, by AST over `app/models/**`, the names of classes whose body assigns `__tablename__`, then flag `from app.models... import <name>` in `schema/`). Helpers: `module_imports(path) -> list[tuple[int, str]]` (walks the whole tree, so function-level and `if TYPE_CHECKING` imports count; resolves relative imports), `LOW_LAYER` (the A-3 set), `import_graph()` for A-4. Allow-lists are module-level constants `SCHEMA_FEATURE_ALLOW`, `SCHEMA_ORM_ALLOW`, `LITESTAR_HUBS`, each entry with a trailing `# removed by <chapter>` comment. Failure messages print `path:line module` so the fix is obvious. A second test per rule fails if an allow-list entry no longer violates (shrink-only ratchet).

### Refactor

**Refactor gate.** Smells to look for while writing: the three duplicated ways of finding a feature from a path (extract one `featureOf(resolved)` used by the old and the new helpers; the old `isFeatureService` already has the logic), and the regex in ESLint versus the layer set in the test (kept in sync by the shared-constant test, not by a third copy). Judge by responsibility, not size: the helpers are one function per rule, each describable without "and"; do not merge W-A and W-B into one function with a mode flag. Rule of three: three rule helpers share `featureOf` and `walk`; no further abstraction. Every new exported helper has a TSDoc one-liner as the file already does; every new Python function in the test has a docstring (imperative mood, states intent). No `any`, no `as` cast, no `eslint-disable`, no new `Any`; ESLint baseline entries use the config block, never inline disables.

## Verification

```bash
cd apps/web
NODE_OPTIONS=--max-old-space-size=8192 npm run lint && npm run format:check && npm run typecheck
NODE_OPTIONS=--no-experimental-webstorage npx vitest run src/architecture.test.ts
cd ../api
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
uv run pytest tests/test_architecture.py -q
cd ../..
./ci.sh
```

Acceptance checks, run once and recorded in the PR: (1) temporarily add `import { x } from "../../../suggestions/utils/formatRelativeTime";` to a new file `src/features/documents/utils/tmp.ts`: both `npm run lint` and the vitest test fail, then delete the file; (2) temporarily add `from litestar import Request` to `app/features/voting/service.py`: `test_services_and_repositories_import_no_litestar` fails, then revert; (3) remove one baseline line: lint and the exact-match test fail.

## Git workflow

```bash
git checkout feat/plans-codebase-audit && git pull
git checkout -b refactor/architecture-guards
```

```text
test(web): resolve cross-feature and shared-to-feature imports in architecture.test.ts
build(web): restrict cross-feature imports in eslint with a measured baseline
test(api): add ast-based layering guards for schema, services and repositories
```

Open the chapter PR into `feat/plans-codebase-audit`, not `main`.

## Parallel notes

Runs in batch 1 beside T1 step 1, T2, A1, A2, A3, A4, B1, B6, W1, W2. It edits only `apps/web/eslint.config.js`, `apps/web/src/architecture.test.ts` and the new `apps/api/tests/test_architecture.py`. W1 and W2 edit web source but must not edit those two files (they delete their own baseline lines in their PRs after T3 merges, otherwise in the follow-up commit the chief of staff schedules). A1, A2, A3, A4, B1, B6 touch API source only and do not intersect the new test. If W2 or B1 merges first and removes a baseline file, drop that entry before merging T3 (the stale-entry test will tell). Do not touch `apps/web/CLAUDE.md`, `package.json`, lock files, any source under `app/` or `src/`, or `ci.sh`. Later chapters that delete entries: W1, W2, W4 (web) and B1, B2, B3 (API); G2 closes both lists.
