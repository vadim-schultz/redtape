---
name: "Chapter 6 — Admin and suggestion contract cutover"
overview: "Move discovery-admin, manual curation, candidate detail, and suggestion contracts to canonical category codes while keeping internal completeness behavior isolated for the next chapter."
depends_on:
  - 03-category-api-and-backend-filters
  - 04-ingest-and-llm-category-contract
  - 05-frontend-category-browsing
touches:
  - apps/api/app/features/discovery/
  - apps/api/app/features/suggestions/
  - apps/api/app/schema/discovery/
  - apps/api/app/schema/suggestion/
  - apps/api/tests/
  - apps/web/src/features/discovery-admin/
  - apps/web/src/features/suggestions/
  - apps/web/src/features/candidates/
  - apps/web/src/test/
execution: chapter-implementer
todos:
  - id: admin-reads
    content: "Render canonical category names and confidence in discovery-admin and candidate surfaces."
    status: pending
  - id: suggestion-contract
    content: "Move suggestion and manual curation payloads to category codes with compatibility diagnostics."
    status: pending
  - id: completeness-boundary
    content: "Keep any required internal completeness computation separate from public category/tag presentation."
    status: pending
  - id: tests
    content: "Update admin, suggestion, candidate, contract fixture, unknown-code, and provenance tests."
    status: pending
---

# Chapter 6 — Admin and suggestion contract cutover

**Repo:** `redtape` (`apps/api`, `apps/web`)
**Depends on:** [Chapter 3](03-category-api-and-backend-filters.md), [Chapter 4](04-ingest-and-llm-category-contract.md), [Chapter 5](05-frontend-category-browsing.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

## Goal

Make internal review and machine-facing candidate contracts use the same canonical category vocabulary as the public document list. The admin can still show confidence and evidence needed for curation, but it must not create a second taxonomy or display raw PVOG leaves as product chips.

This chapter preserves any completeness calculation that still affects ranking or operational queues. Chapter 7 removes user-facing staging/completeness disclosure and prunes public fields that no longer have a consumer.

## Design decisions

- Discovery-admin reads category names through the taxonomy service/API and renders category tags with confidence and source context.
- Suggestion, manual-curation, candidate mention, and candidate read contracts use `category_codes`.
- Compatibility reads for old `domain_codes`/`situation_codes` are translated once at the boundary and report dropped/ambiguous values.
- Internal `has_domain`, `has_situation`, `complete`, or completeness counts are not renamed into a new user-facing category concept. They remain internal only until chapter 7 removes unnecessary public fields.
- Admin source evidence may show PVOG source identifiers in a provenance context, but not as canonical category chips.
- OpenAPI and frontend contract allowlists are updated together; no permissive `Record<string, unknown>` bypass is acceptable.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/discovery/candidate_admin_service.py` | Resolve and expose canonical category labels/evidence for admin reads. |
| `apps/api/app/features/discovery/candidate_list_items.py` | Map category tags and confidence into admin/card DTOs. |
| `apps/api/app/features/discovery/read_mappers.py` | Replace dual-axis names with category names while keeping provenance. |
| `apps/api/app/features/discovery/candidate_codes.py` | Validate category codes at the machine boundary. |
| `apps/api/app/features/suggestions/service.py` | Accept/resolve canonical category payloads and preserve compatibility diagnostics. |
| `apps/api/app/features/suggestions/handlers.py` | Map suggestion category data into the existing workflow without reintroducing axis logic. |
| `apps/api/app/schema/discovery/candidates.py` | Update mention/admin payloads and category limits. |
| `apps/api/app/schema/suggestion/payload.py` | Update suggestion payload read/write models. |
| `apps/api/tests/test_discovery_admin_api.py` | Test category labels, confidence, source context, and unknown codes. |
| `apps/api/tests/test_suggestions_submit.py` | Test canonical category submission and compatibility rejection. |
| `apps/api/tests/test_suggestion_payload.py` | Test category payload shape and limits. |
| `apps/web/src/features/discovery-admin/hooks/useTagNames.ts` | Load canonical category tree/labels. |
| `apps/web/src/features/discovery-admin/components/DocumentTagsPanel.tsx` | Render category tags and provenance distinctly. |
| `apps/web/src/features/discovery-admin/containers/DocumentTagsSection.tsx` | Pass canonical category data through admin sections. |
| `apps/web/src/features/discovery-admin/types/candidate.ts` | Replace dual-axis fields with category fields. |
| `apps/web/src/features/suggestions/types/index.ts` | Update suggestion types. |
| `apps/web/src/features/candidates/types/index.ts` | Align candidate tags with category responses. |
| `apps/web/src/test/contract/contract.test.ts` | Update field allowlists and forbidden legacy fields. |
| `apps/web/src/test/contract/openapi.schemas.json` | Update generated contract fixtures. |

## Red tests

### Happy path

- `admin · displays localized canonical category names with confidence` asserts category labels come from the active taxonomy.
- `suggestion · accepts category codes and preserves source evidence` asserts payloads round-trip without losing quotes, extractor, or PVOG metadata.
- `manual curation · accepts only active categories` asserts the same machine vocabulary is used by admin and workers.
- `candidate detail · exposes category tags but not PVOG leaves as product tags` asserts public shape.

### Negative path

- `admin · unknown category is shown as a diagnosable validation error` asserts no blank tag or silently dropped proposal.
- `suggestion · legacy axis fields are rejected after compatibility expiry` asserts the cutoff is enforceable.
- `contract · old domain/situation fields are not accepted in new payloads` asserts fixture allowlists catch drift.
- `completeness · internal score remains usable without rendering a public checklist` asserts chapter 7 can remove presentation without breaking ranking.

## Green

1. Update API/admin DTOs and mappers to use category tags.
2. Update web admin and candidate surfaces to consume the category tree.
3. Update suggestion/manual curation validation and compatibility diagnostics.
4. Update contract fixtures and translations.
5. Confirm completeness calculations have no dependency on public category field names.

## Refactor gate

Audit the whole admin/suggestion boundary:

- one category-name lookup path is shared;
- admin provenance and product category labels are separate view models;
- compatibility conversion happens at the request boundary;
- internal completeness is not threaded through every public DTO;
- no `domain`/`situation` boolean mode survives in handlers;
- source and category data are not clumped into untyped dictionaries;
- web admin components do not import network services directly.

Report the refactor outcome and rerun the narrow suite after each extraction.

## Verification

```bash
cd apps/api
uv run pytest tests/test_discovery_admin_api.py tests/test_suggestions_submit.py \
  tests/test_suggestion_payload.py tests/test_discovery_candidate_emit_payload.py
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts

cd ../web
npm test -- src/features/discovery-admin src/features/suggestions src/features/candidates
npm run lint && npm run format:check && npm run typecheck
cd ../..
./ci.sh
```

Record admin/suggestion contract parity and internal-completeness checks in [../run-ledger.md](../run-ledger.md).

## Out of scope

Removing the public staging/completeness presentation, accordion detail layout, deleting old schema, embeddings, entity identification, and unrelated admin redesign.

## Git workflow

```bash
git checkout feat/plans-category-taxonomy-migration && git pull
git checkout -b feat/category-admin-cutover
```

```text
test(api): describe category-backed admin and suggestion contracts
feat(api): cut over discovery review to canonical categories
feat(web): render canonical categories in discovery admin
```
