---
name: "G1 — Test gaps"
overview: "Fill only the test gaps that the earlier chapters leave open. Most audit 'zero references' claims turned out to be covered or owned; what remains is direct tests for four web utilities, the seed_i18n script, a CLI-versus-workflow contract test, and verification that A2 and A3 delivered their negative paths."
todos:
  - id: remeasure
    content: "Re-run the coverage greps on the loop branch and cross out every gap an earlier chapter closed"
    status: pending
  - id: web-utils
    content: "Direct tests for safeHttpUrl, hostOf, localizedTitle, translateOrRaw (and isDiscoveryAdminUnavailable if still uncovered)"
    status: pending
  - id: seed-i18n
    content: "tests/test_seed_i18n.py for the flatten, load and idempotent upsert paths"
    status: pending
  - id: cli-contract
    content: "Ingest test that every `python -m discovery_ingest` call in the workflows and runbooks parses"
    status: pending
  - id: verify-owned
    content: "Confirm A2 and A3 shipped their negative-path tests; add what is missing"
    status: pending
isProject: false
---

# G1 — Test gaps

**Repo:** `redtape` · **Branch:** `test/audit-test-gaps` · **Status:** planned

**Depends on:** B5, I4, W3, W4 (and, transitively, A2, A3, B1, B4, W1, W2) · **Architecture:** [../00-audit-report.md](../00-audit-report.md) section 3.5 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-codebase-audit` · **Release branch:** `main`

**Touches:** tests only (`apps/api/tests`, `apps/discovery-ingest/tests`, `apps/web/src/**/*.test.ts[x]`).
**After:** B5, I4, W3, W4.

**Findings:** hygiene item "Test-coverage gaps".

## Goal

Add tests, change no production code. The audit listed 17 "zero references" gaps. Checking each one with `grep` over the tests (2026-11-02, `main` at `0e713cc`) shows the list is much shorter than claimed, because a symbol with no test *reference* is often exercised through its HTTP route or its component. This chapter lists what is verified, what an earlier chapter already covers, and the short remainder it writes. Re-run the greps at the start (they are in Verification) and drop anything an earlier chapter has since closed.

## Verification of every gap in the audit

| Audit gap | Verified today | Covered or owned by | G1 action |
| --- | --- | --- | --- |
| API `DiscoveryEmitService` | **Not zero.** No test names the class, but `tests/test_discovery_emit.py` drives `POST /catalogue/{id}/emit` (happy path, skipped requirement claim, idempotent replay, 401, emitted event) and `tests/test_discovery_emit_preview.py` the preview. | The failure branches (duplicate suggestion, unknown taxonomy code aborting the batch, finding C2) belong to **A2**. | Drop. Check the A2 PR has a duplicate and an invalid-code case on the claim-emit path; add `test_emit_catalogue_skips_a_duplicate_without_aborting_the_batch` only if absent. |
| API `advance_stage` / `derive_stage_for` | **Not zero.** Stored stages are asserted through the API: `test_discovery_machine_entities.py` (T1 after batch upsert, T3 and T4 after claims). Only the pure `derive_pipeline_stage` has unit tests (`test_discovery_pipeline.py`). | **B4** adds `tests/test_discovery_stage_sync.py` (all stages, "never lowers", unknown id, call-site pins). | Drop. |
| API `/locales`, `/translations`, `resolve_locale` | True: no test references `list_locales`, `translations_bundle`, `resolve_locale`, or sends `?locale=`. Locale choice is only covered through `Accept-Language` in four API tests. | **B1** adds `test_locale_resolution.py`, `test_locales_api.py`, `test_i18n_resolution.py`. | Drop. |
| API `seed_i18n` | True: `scripts/seed_i18n.py` is run by `scripts/start.sh:15` on every boot and no test imports it. | None. | **Write** (below). |
| Web `safeHttpUrl` (security) | Zero direct tests. Behavioural coverage: `DiscoveryDocumentPage.test.tsx` checks one `https` URL and one `javascript:` URL through `DocumentHeader`. Edge cases are unpinned. | None (W2 and W4 do not touch it). | **Write**. |
| Web `hostOf`, `localizedTitle`, `translateOrRaw` | Zero direct tests; used by column and cell components that have tests, but the fallback orders and malformed inputs are unpinned. | W2 changes `translateOrRaw` call sites only in its optional enum-label commit and adds no unit test. | **Write**. |
| Web `discoveryAdminProbeErrors` | Zero direct tests. `discoveryAdminProbeErrorOutcome` is exercised by the table W2 adds for `discoveryAdminGuardOutcome`. `isDiscoveryAdminUnavailable` (used by `DiscoveryAdminMenuLinks`) is not. | **W2** (outcome mapping). | Write only `isDiscoveryAdminUnavailable` if still unpinned. |
| Web `discoveryAdminGuardOutcome` | Zero direct tests today. | **W2** adds the outcome table. | Drop. |
| Web "four admin query hooks" | Ten of the twelve hooks have no hook-level test, but all are used by page tests that assert their requests. | **W1** adds `discoveryAdminQueries.test.tsx`, a table over all 12 hooks (URL, bearer token, signed-out and missing-id negatives). | Drop. |
| Ingest `cli._build_parser` | **False.** `tests/test_cli_worker.py` and `tests/test_cli_worker_llm.py` import `_build_parser`. The function disappears with the Typer CLI (**I4**). | **I3** and **I4** characterise commands through `main()` and the Typer app. | Replace by the contract test below. |
| Ingest non-API exception path of `run_recorded_drain` | True today: `tests/test_worker_run.py` covers success, batch limit, claim API error and a failing `start_run`, but not a handler bug or `httpx.HTTPError`. | **A3** (finding C3) must add it. | Verify only. |

## Files

| File | Change |
| --- | --- |
| `apps/web/src/features/discovery-admin/utils/safeHttpUrl.test.ts` | New. |
| `apps/web/src/features/discovery-admin/utils/hostOf.test.ts` | New. |
| `apps/web/src/features/discovery-admin/utils/localizedTitle.test.ts` | New. |
| `apps/web/src/features/discovery-admin/utils/translateOrRaw.test.ts` | New. |
| `apps/web/src/features/discovery-admin/utils/discoveryAdminProbeErrors.test.ts` | New, only the `isDiscoveryAdminUnavailable` cases W2 did not cover. |
| `apps/api/tests/test_seed_i18n.py` | New. Imports `scripts.seed_i18n` (as `tests/test_document_service.py` imports `scripts.seed_taxonomy`); uses `db_session` (PostgreSQL, the file's `pg_insert ... on_conflict_do_update` is Postgres-only). |
| `apps/discovery-ingest/tests/test_cli_workflow_contract.py` | New. Reads `.github/workflows/discovery-*.yml` and `docs/operations/*.md` (path built from `Path(__file__).resolve().parents[3]`, as `test_drain_workflow_budget.py` does). |
| `apps/discovery-ingest/tests/test_worker_run.py`, `apps/api/tests/test_discovery_emit.py` | Extended only if the A3 or A2 check finds the negative path missing. |

## TDD loop

These are characterisation tests of code that already exists, so they are green when first written. "Red" here means proving each test bites: for every new test file, apply the one-line mutation named below to the unit locally, confirm the test fails, and revert (throwaway, never committed).

### Red (mutation checks) and tests to write

**`safeHttpUrl`** (mutation: allow any protocol, i.e. return `url` after the `try`)
- happy: `safeHttpUrl · returns an https URL unchanged`, `· returns an http URL unchanged`, `· accepts an upper-case scheme` (`HTTP://A.GOV`);
- negative: `· rejects javascript:, data:, file:, ftp:, mailto: and vbscript:` (`it.each`), `· rejects a script scheme hidden by leading whitespace or a tab inside the scheme` (`" javascript:alert(1)"`, `"java\tscript:alert(1)"` both resolve to `javascript:` in the WHATWG parser), `· rejects relative, protocol-relative and scheme-less strings` (`/x`, `//evil.example`, `example.gov`), `· returns null for null, undefined and the empty string`;
- pin, do not fix: `· returns the original string, not the normalised URL` (a leading space survives) and `http:x` is accepted. If the operator wants these tightened, that is a separate production change.

**`hostOf`** (mutation: return `url`)
- happy: host without path or query; keeps the port (`https://a.gov:8080/x` gives `a.gov:8080`); drops user info;
- negative: malformed text, `mailto:a@b`, null, undefined and empty give `""`.

**`localizedTitle`** (mutation: swap the `en` and `de` fallbacks)
- happy: requested locale wins; falls back to `en`, then `de`, then any other key; an empty object gives `""`;
- negative: an empty-string value for the requested locale is returned as `""` (the function uses `??`, so it does not fall through; pin it, because `|| "—"` at the call sites in `candidateColumns` and `mentionColumns` depends on it).

**`translateOrRaw`** (mutation: always return `raw`)
- happy: returns the translation when `t` resolves the key; returns `raw` when `t` echoes the key back (the bundle's missing-key behaviour);
- negative: an empty `raw` with a missing key returns `""`; an empty translation is returned as is, not replaced by `raw` (the function only compares against the key).

**`isDiscoveryAdminUnavailable`** (only if W2 left it unpinned)
- 503 and 500 `ApiRequestError`s and a network `TypeError` are unavailable; 401 and 403 are not (the menu shows nothing for them).

**`seed_i18n`** (mutation: replace `on_conflict_do_update` with `on_conflict_do_nothing` for translations)
- `seed_i18n · _flatten_dict joins nested keys with dots and stringifies leaf values` (happy), `· _load_nested_json rejects a JSON array root with TypeError` (negative, via `tmp_path`);
- `seed_i18n · seed_supported_locales creates de and en and is idempotent` (two runs, two rows), `· restores a changed name_native on re-run`;
- `seed_i18n · seed_ui_translations stores every key of both seed files` (row count equals the flattened key count of `scripts/seed_data/translations/{de,en}.json`, currently 360 each) and `· a second run changes no row count but overwrites an edited value`;
- `seed_i18n · de and en seed files have the same keys` (the symmetric difference is empty today; this pins the seed side, the web side is pinned by `fallback.test.ts`).

**CLI contract** (`test_cli_workflow_contract.py`; mutation: rename a flag in a copy of a workflow string)
- happy: `test_every_workflow_and_runbook_command_is_a_known_command` — extract each `python -m discovery_ingest <group> <command> [--flags]` with `shlex`, skip shell expansions (`"${args[@]}"`, `$(...)`) and check `<group> <command> --help` exits 0 and that every literal `--flag` appears in that help text. Run through `python -m discovery_ingest` in a subprocess so the test survives the argparse-to-Typer change.
- negative: `test_the_checker_rejects_an_unknown_flag_and_an_unknown_command` on two literal strings, so a regression in the extractor cannot make the test vacuous; `test_the_extractor_finds_the_known_workflow_commands` asserts at least `budget show`, `budget report-minutes`, `govdata fetch`, `pvog run`, `worker drain`, `llm probe`, `browser probe`, `artifacts list`, `artifacts download` and `fim probe` are found (the verified set today).
- Skip this file if the I4 PR already added an equivalent; check `git log --stat` on `apps/discovery-ingest/tests` first.

### Green

Nothing to implement; the tests pass against the loop branch. If a test fails for a real reason (for example a workflow uses a flag the new CLI dropped), that is a defect in the owning chapter: stop, report it to the chief of staff, and do not weaken the test.

### Refactor

Judge by responsibility: one test file per unit; table-driven (`it.each`, `@pytest.mark.parametrize`) where the cases share a shape; no helper used by one test. Rule of three for fixtures: a third test file that builds the same `ApiRequestError` or `t` stub gets a shared helper in `src/test/`, not before. No `any`, no casts, no `# type: ignore`, no new `Any`. Report `Refactor gate: smells found -> …, refactorings applied -> …` with the number of gaps closed against the rows of the verification table.

## Verification

```bash
# re-measure the gaps (read-only); a symbol with an empty test list and an empty owning chapter is a G1 gap
cd /home/schult_v/projects/redtape/apps/web/src
for s in safeHttpUrl hostOf localizedTitle translateOrRaw isDiscoveryAdminUnavailable; do
  echo "$s: $(grep -rl "$s" --include=*.test.ts --include=*.test.tsx . | tr '\n' ' ')"; done
cd /home/schult_v/projects/redtape/apps/api
for s in seed_i18n resolve_locale list_locales; do echo "$s: $(grep -rl "$s" tests | tr '\n' ' ')"; done

# run the new tests
cd /home/schult_v/projects/redtape/apps/web
npx tsc --noEmit && npx eslint "src/**/*.{ts,tsx}"
npm test -- src/features/discovery-admin/utils
cd /home/schult_v/projects/redtape/apps/api && uv run pytest tests/test_seed_i18n.py
cd /home/schult_v/projects/redtape/apps/discovery-ingest && uv run pytest tests/test_cli_workflow_contract.py tests/test_worker_run.py
cd /home/schult_v/projects/redtape && ./ci.sh
```

The API run needs the local Postgres (`docker compose up -d --wait db`, or `./ci.sh` starts it). Use your own scratch database for the pytest run: agents never share the local dev database (rollout, parallel batches).

## Parallel notes

- G1 runs alone in batch 4, after I4 and before G2. Nothing runs beside it, but G1 reads outputs of A2, A3, B1, B4, W1, W2, W3, W4 and I4; if any of them is missing a promised test, G1 reports it rather than silently adding a duplicate.
- Files G1 must not touch: any non-test file (including `pyproject.toml`, `eslint.config.js`, `package.json`, lock files), `docs/`, the run ledger.
- Side finding for the chief of staff, not a G1 action: only `DocumentHeader.tsx` filters its link through `safeHttpUrl`. Other components render API-provided URLs as `href` without it: `features/documents/components/DocumentDetailView/OfficialSourceSection.tsx:18`, `features/suggestions/components/SuggestionDetailView/NewDocumentPayloadView.tsx:14`, `features/candidates/components/CandidateDetailView/CandidateSources.tsx:15`. The API validates submitted URLs (`apps/api/app/schema/suggestion/payload.py:40`, `create.py:37-40`), so this is defence in depth only; decide whether to apply `safeHttpUrl` (a production change, outside this chapter).
- Core-doc inconsistencies to report: the audit's gap list names `cli._build_parser` and `DiscoveryEmitService` as unreferenced; both are exercised (see the table).

## Git workflow

```bash
git checkout feat/plans-codebase-audit && git pull
git checkout -b test/audit-test-gaps
```

```text
test(web): pin safeHttpUrl, hostOf, localizedTitle and translateOrRaw
test(api): cover the i18n seed script
test(ingest): check every workflow and runbook command against the CLI
```

Open the chapter PR into `feat/plans-codebase-audit`, not `main`.
