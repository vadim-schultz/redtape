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
- Status: orchestration metadata recorded; implementation pending
- Conflicts/failures: none recorded

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

- Alembic upgrade: pending
- Alembic downgrade/forward-only decision: pending
- Category row count: pending
- Document-category link count: pending
- External PVOG classification count: pending
- Backfill rerun is idempotent: pending
- Old/new projection parity report: pending

### Chapter 3 — API and backend filters

- Category-tree response: pending
- Machine taxonomy response: pending
- Parent descendant filter test: pending
- Subcategory exact filter test: pending
- Unknown-code rejection: pending
- Legacy parameter compatibility: pending
- Matrix reference status: pending

### Chapter 4 — Ingest and LLM contract

- Mention category payload validation: pending
- PVOG parent/leaf provenance: pending
- LLM schema enum digest: pending
- Unknown category handling: pending
- Confidence parity: pending
- Re-ingest/backfill behavior: pending

### Chapter 5 — Frontend category browsing

- Search-first layout: pending
- Category tree loading/error/empty states: pending
- Red semantic chip token: pending
- Top-level chip href: pending
- Subcategory chip href: pending
- No nested interactive markup: pending
- Legacy URL behavior: pending

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
