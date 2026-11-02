---
name: "G2 — Close baselines"
overview: "Final gate: prove the docstring, Any and architecture baselines are empty, delete the four mypy ignore_errors modules by fixing their typing, correct the stale STATUS.md line, record the final measure_code_rules numbers in the ledger, and hand the chief of staff the release PR steps."
todos:
  - id: verify-baselines
    content: "Confirm the T1, T2 and T3 baselines are empty (or recorded as permanent) with the commands below"
    status: pending
  - id: mypy-overrides
    content: "Remove the four-module ignore_errors override from apps/api/pyproject.toml and fix the typing it hid"
    status: pending
  - id: status-doc
    content: "Fix the stale line in docs/planning/STATUS.md"
    status: pending
  - id: ledger
    content: "Record the final informational measure_code_rules numbers in the run ledger"
    status: pending
  - id: release-steps
    content: "Hand over the release PR checklist; do not open the release PR"
    status: pending
isProject: false
---

# G2 — Close baselines

**Repo:** `redtape` · **Branch:** `chore/close-baselines` · **Status:** planned

**Depends on:** T1, T2, T3, G1 (and every earlier chapter) · **Architecture:** [../00-audit-report.md](../00-audit-report.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-codebase-audit` · **Release branch:** `main`

**Touches:** lint/mypy config, `docs/planning/STATUS.md`, ledger.
**After:** T1, T2, T3, G1.

**Findings:** audit tooling gaps (section 1), "Stale `docs/planning/STATUS.md`", open size observations (informational).

## Goal

After G2 nothing in the tooling is lenient by exception. The release gate in [../01-rollout.md](../01-rollout.md) can then be ticked from evidence. G2 changes configuration, three small typing fixes (only if earlier chapters have not already made them), one documentation line, and the ledger; it adds no behaviour.

## Facts measured today (`main` at `0e713cc`; G2 re-measures on the loop branch)

| Item | Today | Source |
| --- | --- | --- |
| mypy override with `ignore_errors = true` for four modules | 9 errors in 4 files when the override is removed: `app.services.openplz_client` 1, `app.middleware.locale` 2, `app.features.locations.repository` 1, `app.features.documents.service` 5. Measured read-only with `mypy app --no-incremental --cache-dir <scratch> --config-file <copy without the override>`. | `apps/api/pyproject.toml:85-92` |
| mypy override for `scripts.*` | Hides about 23 more errors: `import_openplz_locations.py` 9, `fix_saxony_jurisdiction_leak.py` 6, `cleanup_openplz_data.py` 6, `object_store_probe.py` 1, `consensus_ceiling_report.py` 1. | `apps/api/pyproject.toml:81-83` |
| `measure_code_rules.py` | `app`: classes over 100 lines 7, methods over 5 lines 444, parameters over 3: 38. `scripts`: 1, 72, 10. `discovery_ingest`: 2, 409, 47. Informational only (decision U2). | `uv run python scripts/measure_code_rules.py <root>` from `apps/api` |
| `ANN401` in ingest | 3 sites (`ruff check discovery_ingest --select ANN401 --isolated`). | |
| Stale `docs/planning/STATUS.md` line | Line 59 lists three "stale/dead files": (1) `apps/web/src/contexts/LocaleContext.tsx.draft` no longer exists (`ls apps/web/src/contexts` shows only `LocaleContext.tsx` and its test); (2) `apps/mobile/lib/providers/locale_provider.dart.draft` still exists, line stays true; (3) `apps/web/src/features/locations/components/LocationPicker.tsx` has moved to `.../LocationPickerView/LocationPicker.tsx` and is still imported only by its own folder (`index.ts` and the test). | `docs/planning/STATUS.md:59` |

The four-module list in the audit task is one module off today's reality: `app.services.openplz_client` is moved by **B6** to `app.features.locations.openplz.client` (B6, `Files`), so its override entry matches nothing after B6, and the 1 error above disappears with the rewrite. Remove the dead entry regardless.

## Files

| File | Change |
| --- | --- |
| `apps/api/pyproject.toml` | Delete the `[[tool.mypy.overrides]]` block listing the four modules (lines 85-92 today). Delete any leftover `# T1 baseline` or `# T2 baseline` `per-file-ignores` lines and empty sections (ruff `D`, `ANN401`, `TID251`). Keep `tests/*` exemptions, the migrations `extend-exclude`, and the `litestar.*`/`sqlalchemy.*` import overrides. Leave `scripts.*` unless it is clean (see decision below). |
| `apps/discovery-ingest/pyproject.toml` | Delete the per-chapter `disallow_any_explicit = false` override blocks T2 created for I2, I3, I4 (they should already be gone), and any `D`/`ANN401`/`TID251` baseline lines. |
| `apps/web/eslint.config.js`, `apps/web/src/architecture.test.ts` | Remove T3's named baseline block and the baseline list if empty. Otherwise keep only entries recorded below as permanent. |
| `apps/api/app/middleware/locale.py`, `apps/api/app/features/locations/repository.py`, `apps/api/app/features/documents/service.py` | Typing fixes, only if B1 and B3 have not made them (see below). |
| `docs/planning/STATUS.md` | Replace the stale sentence (below). |
| `.plans/codebase-audit/run-ledger.md` | Add an "After" table next to the baseline table. Per-chapter rows stay the chief of staff's. |

## The typing each override hides

Re-run the measurement first (Red). B1 edits `app.middleware.locale` and `app.features.locations`, B3 edits `app.features.documents.service`, B6 replaces the OpenPLZ client, and each chapter was told to fix what mypy shows there but to leave the config edit to G2. If their PRs fixed the typing, G2 only deletes the override.

| Module | Error today | Fix (verified to type-check on a scratch copy) |
| --- | --- | --- |
| `app.services.openplz_client` | `openplz_client.py:83` `no-any-return` | None. B6 rewrites and moves it; delete the stale override entry. |
| `app.middleware.locale` | `locale.py:17` unused `type: ignore` (the `# type: ignore[no-untyped-def]`); `:20` `var-annotated` for `request` | Annotate `async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None` with `from litestar.types import Receive, Scope, Send`, drop the ignore comment, and write `request: Request[object, object, State] = Request(scope, receive)` with `from litestar.datastructures import State`. No `Any`, no cast. Checked: `mypy` reports no issues for this body. |
| `app.features.locations.repository` | `repository.py:34` `arg-type` on `Jurisdiction.administrative_roles.any(administrative_role)` (mypy resolves `.any` as the relationship comparator) | `stmt.where(literal(administrative_role) == any_(Jurisdiction.administrative_roles))` with `from sqlalchemy import any_, literal`. Checked: mypy is clean and the compiled PostgreSQL is identical (`%(param)s = ANY (jurisdiction.administrative_roles)`), so behaviour does not change. `tests/test_locations_repository.py` is the safety net. |
| `app.features.documents.service` | `service.py:73-77`: five `arg-type` errors from splatting a `dict[str, list[UUID] \| UUID \| None]` (`scope`) into `count`, `list_page` and `_leaf_codes_in_scope` | Replace the dict by three local names (`jurisdiction_id`, `domain_ids`, `situation_ids`) passed explicitly, or by a three-field frozen dataclass if B3 introduces one. If B3 already rewrote this method, nothing to do. |

`scripts.*` override: decide at the start with the measured count. If it is zero after B6 (B6 rewrites `import_openplz_locations.py` and `cleanup_openplz_data.py`), delete it. If not, keep it and record in the ledger as a deliberate exception with the module list, because `fix_saxony_jurisdiction_leak.py` is a one-shot repair that B6 removes from `start.sh` only after operator confirmation and the other two files are not in any chapter's scope.

## STATUS.md replacement

Replace the last bullet under "Known documentation/code drift (fixed in this pass)" (line 59) with:

> - Stale/dead files not yet cleaned up (left alone for now — hygiene, not documentation): `apps/mobile/lib/providers/locale_provider.dart.draft`, and `apps/web/src/features/locations/components/LocationPickerView/LocationPicker.tsx`, which nothing outside its own folder imports. (`apps/web/src/contexts/LocaleContext.tsx.draft` was removed.)

Re-verify before editing: `ls apps/web/src/contexts`, `ls apps/mobile/lib/providers`, and `grep -rn "LocationPicker" apps/web/src --include=*.tsx --include=*.ts` outside `LocationPickerView/`. If the picker has since gained an importer, drop that clause. Do not touch the rest of the file.

## TDD loop

### Red

1. Baselines are empty (the assertions the release gate needs). Each command must print nothing or zero:
   - `cd apps/api && uv run ruff check . --select D,ANN401,TID251 --statistics`; same in `apps/discovery-ingest`;
   - `grep -n "T1 baseline\|T2 baseline\|removed by" apps/api/pyproject.toml apps/discovery-ingest/pyproject.toml`;
   - `grep -n "ignore_errors" apps/api/pyproject.toml` lists only `scripts.*` (or nothing);
   - `cd apps/discovery-ingest && uv run mypy discovery_ingest` with `disallow_any_explicit = true` and no override block;
   - web: `grep -n "baseline" apps/web/eslint.config.js apps/web/src/architecture.test.ts` shows no entries, or only the permanent ones listed below.
2. Remove the four-module mypy override. `uv run mypy app scripts` now reports the errors in the table (9 today, fewer after B1, B3, B6). This is the red; record the count in the PR.
3. Prove the gate bites (throwaway, never committed): add `x: int = "a"` to each of `app/middleware/locale.py`, `app/features/locations/repository.py`, `app/features/documents/service.py`; `mypy` must fail for each; revert. Repeat the T1 and T2 negative checks (`def f(): pass` in a file without a baseline; `from typing import Any` use) once, to confirm the gates still bite on the loop branch.

### Green

Apply the fixes in the table above, one commit per module, then the STATUS.md edit and the ledger table. `uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts` pass in `apps/api`; the same triad with `mypy discovery_ingest` in `apps/discovery-ingest`; `npm run lint && npm test` in `apps/web`.

### Refactor

Judge by responsibility; there is no code to restructure. Check that no fix introduced `Any`, `cast` or `type: ignore`, that the middleware body is unchanged apart from annotations, that no unused import remained after the `scripts.*` decision, and that the permanent exceptions (if any) are listed with the reason and an owner in the ledger. Report `Refactor gate: smells found -> …, refactorings applied -> …` with the number of override entries before and after (4 modules plus `scripts.*` to 0 or 1) and the mypy error counts.

## Final informational numbers for the ledger

Run and paste (informational, decision U2; they are not a gate):

```bash
cd /home/schult_v/projects/redtape/apps/api
for root in app scripts ../discovery-ingest/discovery_ingest; do
  echo "$root: $(uv run python scripts/measure_code_rules.py "$root" | tail -1)"
done
uv run ruff check . --select D,ANN401,TID251 --statistics | tail -1
cd ../discovery-ingest && uv run ruff check . --select D,ANN401,TID251 --statistics | tail -1
cd ../web && find src -name '*.ts' -o -name '*.tsx' | xargs wc -l | tail -1
```

Add to the ledger, beside the 2026-11-02 baseline table, an "After" table with the same rows (classes over 100 lines, methods over 5 lines, parameters over 3, `D` violations, `Any` annotations) and the web non-test LOC for reference. Call out the open size observations from the audit (`DocumentRepository`, `DocumentService`, `SuggestionService`, `OpenPLZClient`, `Settings`, `DiscoveryMachineController`, `DiscoveryMachineService`, `EvalRunner`) as informational with their new sizes, with no action.

## Permanent exceptions (fill in if any remain)

| Where | Reason | Owner |
| --- | --- | --- |
| T3 web baseline rows `components/layout/menu/ProfileMenuRow.tsx:7` and `DocumentsMenuRow.tsx:5` (shared layout importing features), if no chapter took them | Layout composes feature menus by design | chief of staff decides: move behind props, or keep and record |
| T3 API baseline rows without an owner (for example `app/schema/suggestion/read.py:11`) | See T3 | chief of staff |
| `scripts.*` mypy override | See decision above | chief of staff |

## Release PR steps (for the chief of staff; G2 does not open it)

1. All chapter rows in [../run-ledger.md](../run-ledger.md) have branch and PR, red to green evidence, refactor outcome and CI status; B7 is either merged or recorded as "not approved".
2. On `feat/plans-codebase-audit`: `git pull`, then `./ci.sh` green locally (API checks with Postgres, migrations round trip, web lint/format/typecheck/test/build, discovery skills, ingest).
3. Remote CI is green on the loop branch for `api-lint-test.yml`, `web-ci.yml` and `discovery-ingest-ci.yml`.
4. Workflows run unchanged against the new CLI: `.github/workflows/discovery-*.yml` must not have been edited by any chapter (`git diff main...feat/plans-codebase-audit --stat -- .github` is empty); G1's CLI contract test passes. If the operator wants a live check, dispatch only probe workflows on the loop branch (`discovery-fim-probe` writes nothing; `discovery-llm-probe` spends a few neurons); `discovery-drain` and the other queue-writing workflows spend budget and need the operator's go.
5. If W2's optional enum-label commit or any seed JSON change landed, note in the PR that the API must re-run the i18n seed on deploy (`python -m scripts.seed_i18n`, already in `scripts/start.sh`); if B7 landed, note the migration and run the migration round trip.
6. Open the release PR: `gh pr create --base main --head feat/plans-codebase-audit --title "Codebase audit remediation" --body-file <body>`. Body: summary per wave (A, B, I, W, T, G), the ledger table, before and after numbers, the two stated API changes (A1, A2), the CLI-contract statement, permanent exceptions, and the attribution line `🤖 Generated with [Claude Code](https://claude.com/claude-code)` at the end.
7. After remote CI re-confirms on the release PR, merge with a merge commit (the repository's history uses merge commits), delete merged chapter branches, and mark the ledger "Release PR" cell.
8. Post-merge: watch the Render deploy of the API and the Cloudflare build of the web app; run the smoke checks in `docs/operations/deployment-checklist.md`; re-measure nothing further.

## Verification

```bash
cd /home/schult_v/projects/redtape/apps/api
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
uv run pytest tests/test_locations_repository.py tests/test_document_service.py tests/test_controller_params_characterization.py
cd ../discovery-ingest && uv run ruff format --check . && uv run ruff check . && uv run mypy discovery_ingest
cd ../web && npx tsc --noEmit && npx eslint "src/**/*.{ts,tsx}" && npm test -- src/architecture.test.ts
cd /home/schult_v/projects/redtape && ./ci.sh
```

## Parallel notes

- G2 runs last (batch 4, after I4 and G1); nothing runs beside it.
- G2 edits config files that T1, T2 and T3 also edit; by construction those chapters have merged, so the only conflicts are with a late rebase. Do not edit `apps/web/CLAUDE.md`, `apps/api/app` files other than the three in the table, or any chapter document.
- Files G2 must not touch: `.github/workflows/**`, `ci.sh`, lock files, `scripts/start.sh` (B6 owns the Saxony step), `.plans/**` other than the ledger.
- Core-doc inconsistencies to report: the audit and the task name `app.services.openplz_client` as one of the four override modules, but B6 moves it; `docs/planning/STATUS.md:59` names a `.draft` file that is already gone and a `LocationPicker.tsx` path that has moved.

## Git workflow

```bash
git checkout feat/plans-codebase-audit && git pull
git checkout -b chore/close-baselines
```

```text
chore(api): remove the mypy ignore_errors override and fix the typing it hid
chore: verify and delete the empty lint and architecture baselines
docs: correct the stale dead-file line in STATUS.md
docs(plans): record final measure_code_rules numbers in the audit ledger
```

Open the chapter PR into `feat/plans-codebase-audit`, not `main`. The release PR to `main` is opened by the chief of staff, never by this chapter.
