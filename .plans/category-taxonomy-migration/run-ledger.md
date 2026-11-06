# Category taxonomy migration — Run ledger

**Suite:** [00-architecture.md](00-architecture.md) · [01-rollout.md](01-rollout.md)
**Purpose:** Record implementation and post-deploy evidence. This file is a ledger template; no production checks are implied by its creation.

## Orchestration

- Loop branch: `feat/plans-category-taxonomy-migration`
- Release branch: `main`
- Local CI: `./ci.sh`
- Implementation order: `C1 → C2 → C3 → C4 → C5 → C6 → C7 → C8 → C9`
- Integration order: `C1 → C2 → C3 → C4 → C5 → C6 → C7 → C8 → C9 → C10`
- Parallel batches: `B1=C1`, `B2=C2`, `B3=C3`, `B4=C4`, `B5=C5`, `B6=C6`, `B7=C7`, `B8=C8`, `B9=C9`, `B10=C10`
- Environment: web installs use `npm ci` against the corporate npm mirror through the documented proxy (see `.cursor/skills/chief-of-staff/corporate-build-env.md`); `./ci.sh` runs `uv run`, which rewrites `apps/discovery-ingest/uv.lock` to the corporate PyPI mirror. Revert that file before committing.
- Status: C1-C10 integrated; C4 and C5 gates repaired and merged (`fb069c9`, `adf9435`); C6 integrated from `feat/category-admin-cutover` after full `./ci.sh` passed with Docker (`d9d6dd1`), including the regenerated machine-contract fixture; C7 integrated from `feat/public-document-metadata-cleanup` after full CI passed (`0d5b4c0`); C8 integrated from `feat/accordion-document-view` after full CI passed (`777502f`); C9 integrated at `d9c9e7b` and merged at `c0919a5` after the full root gate passed. C10 documentation and validation completed on 2026-11-06.
- Conflicts/failures: none open at the loop branch. The C4 entry had not recorded its discovery-ingest failures (44 tests across 11 files). They were repaired as fixture and contract drift plus one real validation gap (manual curation silently accepted unknown legacy codes).
- Current work: C10 evidence is recorded; the deployed API is still on a pre-cutover version and must be redeployed before the category-specific live gate can pass.

## Baseline

| Check | Expected evidence | Recorded |
| --- | --- | --- |
| Category inventory | Versioned roots, subcategories, localized text, parent IDs, and PVOG crosswalk | pending |
| Legacy code crosswalk | Every domain/situation code is mapped, intentionally unmapped, or manual-review | pending |
| PVOG vocabulary | Snapshot version, root/parent/leaf counts, and mapping coverage | pending |
| Existing database | Row counts for old taxonomy tables and link tables | pending |
| Existing confidence | Distribution and null counts for old link confidence | pending |
| Public contracts | API/OpenAPI/worker/frontend fixtures captured before change | pending |
| UI baseline | Existing category chips, progress circle, detail sections, and source list behavior | pending |

## Chapter evidence

### Chapter 1 — PVOG taxonomy contract

- Status: integrated at `769019c` (`feat(taxonomy): add the PVOG-grounded category vocabulary`)
- Vocabulary artifact: `category-contract-v1`; 12 roots and 22 subcategories, 34 categories total
- PVOG tree/source version: PVOG `v7`; 118 total leaves, 56 citizen leaves, 62 business leaves
- Root/subcategory review: recorded in `.plans/category-taxonomy-migration/category-contract-v1.json`
- Old-code crosswalk coverage: 31 entries covering 13 domain and 18 life-situation codes
- Ambiguous/unmapped review list: 14 PVOG review leaves and 10 citizen source-only leaves; business leaves remain excluded
- Score-combination rule: `max`
- Paired tests: taxonomy integrity/cycle rejection, PVOG path preservation/missing-parent handling, and crosswalk target/duplicate rejection pass
- Narrow checks: API checks pass; PVOG tests, format, lint, and targeted mypy pass; full ingest mypy is blocked by missing `typer`
- Full CI: `./ci.sh` blocked by unavailable Docker; remote web build failed
- Refactor gate: mixed contract loading/validation and mapping concerns were extracted into typed contract and PVOG mapping loaders; no unresolved integration conflict

### Chapter 2 — Schema and data migration

- Status: integrated via C2 commits `0fad542`, `4f40bdd`, and `87dea89`; loop merge recorded on the current branch
- Alembic upgrade: Postgres-backed migration checks pass after shortening revision IDs to fit `alembic_version.version_num VARCHAR(32)`
- Alembic downgrade/forward-only decision: documented as additive schema downgrade plus forward-only data projection
- Category row count: 34 planned rows; Postgres migration/backfill tests pass
- Document-category link count: covered by backfill tests; production count pending
- External PVOG classification count: covered by backfill tests; production count pending
- Backfill rerun is idempotent: verified by the Postgres-backed focused suite
- Old/new projection parity report: backfill projection/conflict tests pass; production report pending
- Static checks: format, ruff, and mypy pass
- Paired tests: 35 focused Postgres tests pass; migration-retry regression passes
- Refactor gate: transformation, persistence, reporting, and rollback boundaries remain named and separate; no additional extraction justified
- Full `./ci.sh`: API phase passes; web phase stops at pre-existing Prettier failure in `apps/web/src/features/discovery-admin/containers/DiscoveryPipelinePage.tsx` (outside C2 touches)

### Chapter 3 — API and backend filters

- Status: integrated; category API/filter commits are on the loop branch
- Category-tree response: 12 frozen roots with localized children and German fallback
- Machine taxonomy response: active canonical category codes with source-parent metadata; PVOG leaves excluded
- Parent descendant filter test: pass; root selections include direct and descendant links
- Subcategory exact filter test: pass
- Unknown-code rejection: pass with 422 diagnostics
- Legacy parameter compatibility: pass; conflicting group/situation mappings return diagnostics
- Matrix reference status: endpoint remains characterized for C9 retirement
- Paired tests: 89 Postgres-backed API tests pass; 37 web contract tests pass plus 1 expected failure
- Static checks: API format, ruff, and mypy pass
- Refactor gate: legacy translation is isolated in `LegacyTaxonomyAdapter`; category resolution/descendant expansion remains centralized
- Full `./ci.sh`: known unrelated Prettier failure remains in `apps/web/src/features/discovery-admin/containers/DiscoveryPipelinePage.tsx`

### Chapter 4 — Ingest and LLM contract

- Status: integrated at `ab33b64` (`feat(ingest): emit category-backed PVOG and LLM mentions`, followed by test-contract corrections)
- Mention category payload validation: canonical `category_codes` accepted; bounded legacy axis input translates once at the request boundary; stale canonical codes are counted and dropped
- PVOG parent/leaf provenance: PVOG `v7` path, leaf, source version, and direct category confidence survive mapping and mention writes
- LLM schema enum digest: `644ba461`; schema emits only active category codes
- Unknown category handling: API and ingest negative-path tests cover rejection, counting, and no invented category when source mapping is absent
- Confidence parity: Python/SQL category-score parity passes; 102 focused API tests and 94 focused ingest tests pass, with 262 ingest tests reported by the implementer
- Re-ingest/backfill behavior: mention upsert remains idempotent; no automatic historical backfill was added because it is explicitly operator-controlled
- Static checks: API and ingest Ruff format/check and mypy pass
- Refactor gate: category validation, PVOG source capture, mapping, score aggregation, and compatibility translation remain named boundaries; no additional extraction justified
- Boundary note: shared candidate score reads, promotion writers, suggestion handlers, taxonomy compatibility, and catalogue orchestration were added to C4's declared touches because they are the canonical category read/write boundary, not unrelated edits
- Full `./ci.sh`: API format, lint, mypy, migrations, and all 1,577 API tests pass; web lint, typecheck, and build pass, while the pre-existing Prettier failure remains in `apps/web/src/features/discovery-admin/containers/DiscoveryPipelinePage.tsx`. The two web contract tests that expect the new category fields are deferred to C5, whose declared candidate/frontend touches own that consumer cutover.
- Discovery-ingest pytest (first recorded 2026-11-04 17:27, root `./ci.sh`): 44 failed, 1745 passed across 11 files. Repaired in `adf9435` (merge of `fix/category-c4-ingest-gate`): test fakes now answer with `category_codes` (the schema rejects legacy output, so every worker scenario settled as failed), the ingest vocabulary model matches the API contract (`is_active` and `minItems` dropped), unknown legacy codes in manual curation refuse the entry, and the prompt, eval, CLI and budget expectations match the ext-6 contract. Final: 1790 passed; ruff format, ruff check and mypy pass.
- Root `./ci.sh` at `db2a160` (2026-11-04 20:52): API 1577 passed; web lint, format, typecheck, Vitest 1054 passed (1 expected fail), build; discovery skills; discovery-ingest 1790 passed. Exit 0.

### Chapter 5 — Frontend category browsing

- Status: integrated at `6598ba1` via merge into the loop branch; C5 implementation commit is `6598ba1`
- Category client: canonical tree query and centralized category query key added
- Browse/filter behavior: search-first document browsing, repeated canonical `category` parameters, root/subcategory selection, and legacy URL reads
- Category chips: shared compact red linked chip used by document and candidate/detail surfaces; nested interactive markup removed
- Contract cutover: candidate/detail web types and fixtures now use canonical category fields
- Paired tests: category-tree success/failure, root/subcategory serialization, unknown-category handling, chip links/focus/non-nesting, and card navigation were added or updated
- Refactor gate: query ownership, URL encoding, root expansion, and chip rendering are centralized; no boolean legacy/category switch or click-propagation workaround remains
- Verification (2026-11-04, repaired in `b6995c1`, `fdf097d`, `2255d86`, merged `fb069c9`): the earlier blocker was the wrong npm registry, not missing access. With the corporate mirror, `npm ci` succeeded. The first real run found what the blocker had hidden: a typecheck import error, 11 Prettier-unformatted files, 6 failing tests, and a seed/fallback translation parity failure. All were repaired. Web now passes lint (0 errors, 3 pre-existing fast-refresh warnings), format, typecheck, Vitest (1054 passed, 1 expected fail), and build.
- Repairs: the empty-state clear action has its own `documents.empty_clear` copy because it also clears the search; the toolbar `Clear filters` still clears only chips. Chip size is not verifiable in jsdom (Chakra's sm recipe styles do not reach computed style), so the chip test asserts the red palette token only.

### Chapter 6 — Admin and suggestion cutover

- Status: integrated from `feat/category-admin-cutover`; full root CI passed after Docker became available
- Admin category labels: tag names come from the canonical category tree through `useCategoryNames`; a code without a name shows as the code; a failed tree query still lists the suggested codes. The admin API deliberately keeps labels out of the mention DTO: the category tree is the single localized label source, while the mention DTO carries codes, evidence, and diagnostics.
- Admin unknown-category diagnostics: stored canonical or mapped legacy values remain in `category_codes`; stale or unmapped values are returned as `unknown_category_codes` and rendered in the mentions table instead of being silently dropped.
- Suggestion payload category codes: web type is `category_codes` only (`0dbc1f5`), matching what the API serializes. The API accepts canonical codes, translates legacy input once at the boundary, rejects mixed legacy/canonical payloads, and reports stale codes.
- Malformed tree response: a non-array category tree no longer throws during admin render (`8dce30a`, found by the admin integration suite).
- Refactor note: the web category-name lookup is one path (`categoryNamesByCode`). `flattenCategoryCodes` in documents `filterParams` is a second traversal that returns codes, not names. Left separate because a cross-feature import of a taxonomy util is blocked by the feature-boundary lint rule. Revisit in C9.
- Legacy taxonomy queries (`useDomainsQuery`, `useLifeSituationsQuery`, `useLifeSituationGroupsQuery`) have no production consumers after this chapter. They are retained until C9 retirement.
- Manual curation contract: canonical `category_codes` are validated against the machine vocabulary; unknown codes are rejected and the API boundary reports compatibility errors.
- Machine contract fixture: canonical category payloads, PVOG provenance, leaf exclusion, and OpenAPI field parity pass.
- Completeness/staging internal-only audit: pass; completeness remains on internal/admin paths and no public DTO or presentation path was introduced for the diagnostic field.
- Paired tests: full API suite passed (1,588 tests), and the web admin/suggestion/candidate suite, contract tests, lint, typecheck, format, and build pass.
- Refactor gate: `CanonicalCodeResolution` centralizes stored-value projection and unknown diagnostics; the admin uses one category-tree label lookup; provenance remains separate from product labels; no boolean taxonomy mode, untyped category/source clump, or completeness threading was added. No further extraction justified.
- Full `./ci.sh` (2026-11-05): passed after Docker became available; the stale machine-contract fixture was regenerated before the successful rerun.

### Chapter 7 — Public metadata cleanup

- Status: integrated from `feat/public-document-metadata-cleanup` at `0d5b4c0`; full CI passed
- Staged/unreviewed notice absent: verified in loaded, loading, retryable-error, and not-found detail states; banner translations and component removed.
- Completeness section absent: verified; checklist, count, and public completeness presentation are removed from the detail composition.
- Public DTO fields removed or justified: public `CandidateCard`/`CandidateDetail` no longer expose `status`, `completeness`, `complete`, or `flags`; admin candidate DTOs retain their internal readiness fields.
- Progress circle still present: `confidence` remains in the public card contract and the document card continues to render `ConfidenceCircle`.
- Ranking/operations regression check: completeness remains in private repository query projections for ranking and filters; the full API suite passes.
- Paired tests: public API preserves confidence/categories and omits staging/completeness fields; web detail absence tests pass across all query states; confidence-circle and candidate suites pass.
- Refactor gate: public card mapping no longer receives completeness data; private ranking projections remain behind the repository boundary; the detail shell only dispatches query states; no banner/checklist imports or translation references remain. No further extraction justified.
- Full `./ci.sh` (2026-11-05): passed with Docker enabled.

### Chapter 8 — Accordion view and source cards

- Status: integrated from `feat/accordion-document-view` at `777502f`; full CI passed
- Five accordion items present: verified for ingress, egress, flow, evidence, and sources.
- First three expanded by default: verified for ingress, egress, and flow.
- Evidence and sources collapsed by default: verified while their triggers remain available.
- Keyboard interaction: source expansion via Enter is covered; the Chakra accordion supplies the accessible trigger/content contract.
- Empty states: neighbour and flow empty states remain covered; source cards render one article per source.
- One subordinate source card per source: verified with role, excerpt, optional condition/marker, and one article per source.
- External source links: portal URLs remain target-blank, noreferrer links; missing URLs remain readable text.
- Responsive flow: flow content is no longer hidden below the ``md`` breakpoint; the parent accordion keeps the item discoverable.
- Refactor gate: the parent owns one accordion and all five stable values; neighbour, flow, evidence, and source components own content only; source mapping and card rendering remain separate; no nested accordion or nested links were introduced. No further extraction justified.
- Full `./ci.sh` (2026-11-05): passed with Docker enabled.

### Chapter 9 — Legacy retirement

- Status: integrated at `d9c9e7b`, merged into the loop branch at `c0919a5`.
- Runtime and contract reference scan: `test_legacy_reference_scan.py` passes (`2 passed`); active API/web code, contracts, fixtures, and active docs carry no retired route/parameter consumers. Discovery-ingest compatibility readers remain intentionally outside C9 scope.
- Paired tests: category-only browse, retired route/input rejection, migration/provenance preservation, score parity, OpenAPI and machine-contract fixtures, and web taxonomy retirement pass.
- Migration gate: disposable `redtape_c9` upgrade/downgrade/upgrade and `alembic check` pass. The local `redtape` database was aligned to the existing additive schema, then upgraded to `20261105_retire_legacy_taxonomy`; final `alembic current` and `alembic check` pass.
- Local migration evidence: 34 canonical categories, 0 document-category links, 0 external classifications, and 6 archive retirement-evidence rows; legacy public taxonomy tables are absent. Downgrade remains schema-only and does not claim to restore dropped data; the archive is the recovery source.
- Compatibility behavior: expired public/admin `domain`, `group`, and `situation` inputs return diagnostic 422 responses instead of widening queries. Category-only filtering remains available, and PVOG leaf provenance remains preserved in the canonical projection.
- Full `./ci.sh` (2026-11-05): passed after the local database was aligned to the C9 head; API, web, discovery-skill, discovery-ingest, migration, lint, typecheck, tests, and build gates are green.
- Refactor gate: stale legacy web clients, scripts, routes, models, and matrix tests were removed; rejection stays at the request boundary; canonical category paths contain no compatibility branches. No further extraction justified.
- Follow-up outside C9 scope: discovery-ingest still translates legacy axis inputs on the client side (`mentions.py`, `curation.py`, `extract/llm/schema.py`, `pvog/category_mapping.py`).

### Chapter 10 — Docs sync and live validation

- Status: integrated on 2026-11-06; documentation changes remain on the loop branch pending the release commit.
- Documentation sync: active master, data-model, discovery-source, discovery-operations, admin-table, candidate-view, deployment, backend, frontend, and mobile pointers now describe the canonical category tree, search-first/category-secondary discovery, red canonical chips, separate PVOG provenance, internal-only staging/completeness, five document accordions, subordinate source cards, and embeddings/entity identification as future work. Historical matrix plans remain unchanged.
- Link check: a relative-link check over 11 changed suite and active documentation files passed; all relative targets resolved.
- Contract/reference checks: `cd apps/api && PYTHONPATH=. DATABASE_URL=sqlite:///test.db uv run pytest -q tests/test_legacy_reference_scan.py tests/test_openapi_snapshot.py tests/test_machine_contract_fixture.py` passed (7 tests, one deprecation warning). The web contract and translation checks passed (64 tests, 1 expected failure); Vitest emitted a worker-termination `EACCES` warning but exited 0. `git diff --check` passed.
- Full CI: `./ci.sh` passed on 2026-11-06 with Docker/Postgres; the migration round trip and drift check passed, the full API/web/discovery-skill gates passed, and discovery-ingest passed (1,789 tests). Final output: `✅ All CI checks passed!`.
- Read-only live validation (2026-11-06 08:07 +01:00, isolated fetch path): the web shell returned `200`; `/health` returned `200 {"status":"ok"}`; `/api/v1/documents` returned `200` with an empty list. The deployed API is pre-cutover: `/api/v1/categories` returned `404`, the category-filtered candidate request returned `422`, and an unfiltered candidate response still exposed `domains`, `situations`, and completeness fields. The machine taxonomy request returned `401` without a machine key. No production write or ingest was attempted.
- UI/PVOG/data-parity observation: browser-level visual checks and live PVOG provenance checks remain pending because the deployed API does not contain C9 and no production credentials were used. The live drift is a deployment-version mismatch, not evidence of a local category mapping loss.
- Refactor gate: smells found -> active operator and planning docs still described the old public disclosure, taxonomy boundary, or pre-C8 detail behavior; refactorings applied -> updated those active references, retained historical records, and kept validation read-only/repeatable. No additional code refactor was needed.

## Post-deploy validation

- Status: partial; local C1-C9 gates are green, but the current deployment predates the cutover.
- Deployment/version: API healthy and web shell reachable; deployed API version is not the C9 release.
- Category-tree API parity: blocked by deployed `404` on `/api/v1/categories`.
- Document counts before/after: local C9 evidence is 34 canonical categories, 0 document-category links, 0 external classifications, and 6 retirement-evidence rows; production counts remain pending.
- Search without category: deployed unfiltered candidate list returned `200`; the response shape is pre-cutover and must be rechecked after release.
- Root and subcategory filtering: blocked by deployed `422` for `filter[category]`.
- Category chip navigation: pending browser-level check after web/API redeploy.
- Old URL behavior: pending post-cutover live check; local C9 tests cover diagnostic rejection.
- No staging/completeness disclosure: pending live UI/API check; deployed candidate data still exposes old fields.
- Accordion defaults: local component tests pass; browser smoke pending after redeploy.
- Source cards and source links: local component tests pass; browser smoke pending after redeploy.
- PVOG provenance on new ingest: local contract tests pass; live ingest validation pending and no production write was attempted.
- Unexpected taxonomy loss: no local loss observed; production comparison is pending because the deployed API is stale.
- Follow-up issue/plan: release and deploy the integrated C9/C10 loop branch, then rerun the read-only API, web, category-filter, UI accordion/chip, and PVOG provenance checks.
