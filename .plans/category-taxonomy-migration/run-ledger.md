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
- Status: C1-C4 integrated; C5 in progress
- Conflicts/failures: C5 frontend verification is tooling-blocked; unrelated web Prettier failure remains
- Current work: C5 is integrated; C6 is not scheduled until the frontend dependency environment is restored and C5's blocked verification can be rerun.

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

### Chapter 5 — Frontend category browsing

- Status: integrated at `6598ba1` via merge into the loop branch; C5 implementation commit is `6598ba1`
- Category client: canonical tree query and centralized category query key added
- Browse/filter behavior: search-first document browsing, repeated canonical `category` parameters, root/subcategory selection, and legacy URL reads
- Category chips: shared compact red linked chip used by document and candidate/detail surfaces; nested interactive markup removed
- Contract cutover: candidate/detail web types and fixtures now use canonical category fields
- Paired tests: category-tree success/failure, root/subcategory serialization, unknown-category handling, chip links/focus/non-nesting, and card navigation were added or updated
- Refactor gate: query ownership, URL encoding, root expansion, and chip rendering are centralized; no boolean legacy/category switch or click-propagation workaround remains
- Verification blocker: Vitest, ESLint, Prettier, TypeScript, build, and `./ci.sh` could not run in the isolated worktree because frontend dependencies were unavailable; npm install repeatedly failed with its internal “Exit handler never called” error, and the environment's certificate chain prevented alternate package-manager downloads

### Chapter 6 — Admin and suggestion cutover

- Admin category labels: pending
- Suggestion payload category codes: pending
- Manual curation contract: pending
- Machine contract fixture: pending
- Completeness/staging internal-only audit: pending

### Chapter 7 — Public metadata cleanup

- Staged/unreviewed notice absent: pending
- Completeness section absent: pending
- Public DTO fields removed or justified: pending
- Progress circle still present: pending
- Ranking/operations regression check: pending

### Chapter 8 — Accordion view and source cards

- Five accordion items present: pending
- First three expanded by default: pending
- Evidence and sources collapsed by default: pending
- Keyboard interaction: pending
- Empty states: pending
- One subordinate source card per source: pending
- External source links: pending

### Chapter 9 — Legacy retirement

- Runtime reference scan: pending
- Contract reference scan: pending
- Legacy migration execution: pending
- Compatibility redirect expiry: pending
- Backup/rollback evidence: pending

## Post-deploy validation

- Deployment/version: pending
- Category-tree API parity: pending
- Document counts before/after: pending
- Search without category: pending
- Root and subcategory filtering: pending
- Category chip navigation: pending
- Old URL behavior: pending
- No staging/completeness disclosure: pending
- Accordion defaults: pending
- Source cards and source links: pending
- PVOG provenance on new ingest: pending
- Unexpected taxonomy loss: pending
- Follow-up issue/plan: pending
