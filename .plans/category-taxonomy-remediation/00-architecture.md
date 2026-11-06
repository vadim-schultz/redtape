# Category taxonomy remediation — Architecture

**Suite:** this folder · **Rollout:** [01-rollout.md](01-rollout.md) · **Gaps and decisions:** [gaps-and-decisions.md](gaps-and-decisions.md) · **Ledger:** [run-ledger.md](run-ledger.md) · **Chapters:** [chapters/README.md](chapters/README.md)

**Reviewed suite:** [../category-taxonomy-migration/00-architecture.md](../category-taxonomy-migration/00-architecture.md)
**Loop branch:** `feat/plans-category-taxonomy-migration` (shared with PR 370; see D-R6)
**Release branch:** `main`

**Status:** planned. This file is documentation only. It implies no code change.

## Purpose

The review of the category taxonomy migration found one high-severity risk (H1: destructive retirement without a verified recovery path), eight medium findings (M1 to M8), and eight low findings (L1 to L8). This suite schedules their remediation.

It keeps the earlier architecture: one category tree, immutable ASCII codes, PVOG identifiers preserved as external classifications, and the completeness and accordion decisions from the earlier suite. It changes the parts the review found weak.

## Target shape

| Concern | Target | Chapter |
| --- | --- | --- |
| Category vocabulary source | One artifact, `apps/api/app/shared/taxonomy/category_contract_v1.json`, read by one lazy, cached loader. `app` does not import `scripts`; `scripts` imports `app`. | C1 |
| PVOG leaf crosswalk for ingest | Served by the machine taxonomy endpoint with its source version. Ingest fetches it once per harvest and validates it. No ingest module references an artifact path. | C4 |
| Frozen sections | The category inventory and the legacy crosswalk are frozen at v1. Migrations read only those. PVOG leaf states may be amended with a reason and an `accepted_on` date. | C1, C9 |
| Replay of legacy links | A legacy projection never overwrites a non-legacy row. Confidence becomes the maximum of the stored value and the projection. | C2 |
| Retirement | Read-only preflight first. Then a migration that archives each table, verifies count and checksum in the same transaction, replays the backfill, and drops legacy tables only when verification passes. | C3 |
| Worker categories | Accepted automatically when the LLM-only score is at or above `MIN_SUGGESTED_SCORE` (0.05). Confidence is stored. No human step. | Existing rule, amended by D-R3 |
| Completeness | Four flags: `has_category`, `has_edges`, `has_snapshot`, `has_screenshot`. Denominator still open (D-R4). | C5 |
| Chips and empty states | No confidence encoded in chip opacity. No staged or completeness wording in empty states. | C6 |
| Ingest inputs | Category codes only. `domain_codes` and `situation_codes` are rejected by field name. | C7 |
| Test database | `ci.sh` runs pytest against `redtape_pytest`, which it drops and recreates on each run. Tests never touch the developer's `redtape` database. | C0 |

## Recovery model (D-R1)

The free tier has no backups. The archive schema `legacy_taxonomy_archive`, in the same database, is the only recovery source for retired rows.

- It protects against an accidental drop and against a bad backfill.
- It does not protect against loss of the database itself. That risk is out of scope here and needs its own infrastructure decision.
- Integrity is proven by count and content checksum, compared per table inside the migration transaction. Any mismatch aborts the migration.
- The earlier `pg_dump` rehearsal requirement is superseded by this model.
- The archive owner and the drop date are open. See [gaps-and-decisions.md](gaps-and-decisions.md).

## Frozen-artifact rule (D-R5)

- Migrations read only the frozen sections: the category inventory and the legacy crosswalk.
- The C9 edit to PVOG leaf states must leave the hash of the frozen sections unchanged. C9 checks this before and after its edit.
- A change to a frozen section needs a new artifact version and its own migration. This suite does not define that version.

## Worker vocabulary rule (D-R3)

- Codes suggested by worker models are accepted automatically when their LLM-only score is at or above `MIN_SUGGESTED_SCORE` (0.05, `apps/api/app/features/discovery/tags.py`).
- Accepted codes carry their confidence in storage.
- No gate, parity check, or backfill requires a human to accept a worker code.
- Confidence calibration is deferred to a later suite.
- Manual mentions (`extractor == "manual"`) keep their existing override of consensus.

## Invariants

1. One category vocabulary source, under `apps/api`.
2. Ingest reads no repository file. It fetches the crosswalk from the API and refuses to start when the fetch or validation fails.
3. Migrations read only frozen sections of the artifact.
4. A replay never lowers a confidence. It never overwrites the source or provenance of a non-legacy row.
5. A legacy table is dropped only after its archive copy matches the source by count and checksum, in the same transaction.
6. An unknown or retired code produces a diagnosable 422 that names the code. It never produces an empty result that looks valid.
7. Category chips do not encode confidence in opacity.
8. Public copy has no staged or completeness wording.
9. Tests never run against the developer's `redtape` database.
10. Every PVOG leaf has a disposition with a reason and a date. Review-state leaves stay published (D-R9).

## Execution model

- The chief of staff owns scheduling, integration, live gates, and the ledger.
- Each chapter-implementer owns one chapter in an isolated worktree on the loop branch.
- Chapters integrate serially into the loop branch in the order fixed in [01-rollout.md](01-rollout.md), even when implementation ran in parallel.
- Live production checks (C8, C13) and release steps (C14) stay with the chief of staff.
- Every implementer assignment includes the corporate build block: [corporate-build-env.md](../../.cursor/skills/chief-of-staff/corporate-build-env.md).
- The chief-of-staff skill names `.plans/PLAN_TEMPLATE.md`, which this repository does not have (D-R10). This suite follows the shape of [category-taxonomy-migration](../category-taxonomy-migration/01-rollout.md).

## Out of scope

- Confidence calibration (D-R3).
- Embeddings, entities, and ranking models (earlier decision D13).
- Backups, or a change of hosting tier.
- Production deploy, merge to `main`, or any release operation in this session (D-R7).
- Creating `.plans/PLAN_TEMPLATE.md` (D-R10).
- Compatibility code for old bookmarked URLs (D-R8).

## Findings map

| Finding | Summary | Chapter |
| --- | --- | --- |
| Baseline (no review ID) | Seeded round-trip test fails on an empty database; tests share the developer database | C0 |
| H1 | Destructive retirement without a verified recovery path | C3 (preflight run in C13) |
| M1 | Replay overwrites promotion-written rows | C2 |
| M2 | Contract artifact lives under `.plans/` and ingest reads it | C1, C4 |
| M3 | Completeness denominator and public order | C5 |
| M4 | Chip opacity encodes confidence | C6 |
| M5 | Reference scan exemptions are whole files and miss ingest | C10 |
| M6 | Legacy axis translators remain in ingest | C7 |
| M7 | Compatibility window for old workers and cached bundles | C8 |
| M8 | Review-state PVOG leaves | C9 |
| L1, L2 | Stale C9 and C10 statuses; stale worktree copies of `.plans` | C12 |
| L3 | Docs wording for STATUS, discovery-online, and ingest README | C12 |
| L4 | "Staged" empty-state copy | C6 |
| L5, L6, L7 | SourceCard decision; duplicated `flattenCategoryCodes`; `candidates_api` docstring | C11 |
| L8 | Archive owner and drop date unassigned | C12 (recorded), C13 (confirmed) |
| Chip size wording | Chip size is `sm` in code; docs say otherwise | C12 |
