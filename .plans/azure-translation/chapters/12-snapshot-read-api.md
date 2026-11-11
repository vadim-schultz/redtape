---
name: "Chapter 12 — Snapshot read API and coverage rows"
overview: "Expose a candidate's translated document as a read-only route with an ETag, resolving the candidate's best mention to its procedure page. Add snapshot rows to the translation coverage endpoint. The read never translates, enqueues or writes."
id: AZ12
depends_on:
  - AZ06
  - AZ08
touches:
  - apps/api/app/features/candidates/controller.py
  - apps/api/app/features/candidates/repository/descriptions.py
  - apps/api/app/features/translation/document_read_service.py
  - apps/api/app/features/translation/admin_read.py
  - apps/api/app/schema/candidate/document_translation.py
  - apps/api/app/features/translation/repository.py
  - apps/api/tests/
  - openapi.schemas.json
  - apps/api/tests/test_openapi_snapshot.py
execution: chapter-implementer
---

# Chapter 12 — Snapshot read API and coverage rows

**Repo:** `redtape` (`apps/api`) · **Depends on:** [Chapter 06](06-admin-translator-coverage.md), [Chapter 08](08-snapshot-machine-api.md) · **Decisions:** [D7](../gaps-and-decisions.md#d7--eager-queue-driven-translation-reads-never-translate) · **Rules:** [../../../CLAUDE.md](../../../CLAUDE.md) (package registries) · **Status:** planned

## Goal

A candidate's detail page can ask for its document in a locale and receive the translated blocks, the source link, and whether the copy is stale. Coverage shows snapshot status per locale beside the card status.

## Scope

- In: the public route, its service and schema, the best-mention extension, snapshot coverage rows, the OpenAPI snapshot.
- Out: the accordion (13), any write, any translation work.

## Design

1. **Route.** `GET /api/v1/candidates/{id}/document-translation?locale=`. The candidate's best mention is chosen by the existing role-rank order (`candidates/repository/descriptions.py`), now also returning `catalogue_service_id` and `source_url`. The snapshot index row for (catalogue row, locale) is then read.
2. **Answers.**
   - Unknown candidate: 404, `code: "candidate_not_found"`.
   - No mention with a snapshot: 404, `code: "no_document"`.
   - Row missing or no object yet: 404, `code: "translation_pending"`.
   - Row skipped: 404, `code: "skipped"`, with `reason`.
   - Ready: 200 with `{locale, source_url, truncated, stale, blocks}`. `stale` is true when the index's `artifact_sha256` differs from the latest snapshot's sha.
   - Store not configured: 503. An object missing after a replacement race is `translation_pending`, logged, not a 500.
3. **Caching.** ETag is the content hash. A matching `If-None-Match` gets 304. `Cache-Control` matches the card translation route.
4. **Layering.** Controller → read service → repositories. The controller holds no queries. The read service calls the discovery service for the best mention and the latest snapshot sha, not the discovery repository.
5. **Coverage rows.** `GET /api/v1/admin/translations/coverage` gains a `snapshot` block per locale: translated, unchanged, skipped, stale, pending, failed. The denominator is the number of procedure pages with a usable snapshot.
6. **OpenAPI.** The snapshot is regenerated for the new route and schema.

## Files

| Path | Change |
| --- | --- |
| `candidates/controller.py` | the new route |
| `candidates/repository/descriptions.py` | best mention returns catalogue id and source URL |
| `translation/document_read_service.py` (new) | read logic |
| `schema/candidate/document_translation.py` (new) | response and codes |
| `translation/admin_read.py`, `repository.py` | snapshot coverage rows |
| `openapi.schemas.json` | regenerated |
| `apps/api/tests/test_document_translation*.py` (new) | route tests |

## Red tests

**Happy path**
- `Read · a translated page returns its blocks in the requested locale, with an ETag`
- `Read · a second request with a matching If-None-Match gets 304`
- `Read · the best mention picks the page, in the same order the card excerpt uses`
- `Read · stale is true when the latest snapshot sha differs from the stored one`
- `Coverage · snapshot rows count translated, unchanged, skipped, stale, pending and failed per locale`

**Negative path**
- `Read · a candidate with no snapshot answers 404 no_document`
- `Read · a pending translation answers 404 translation_pending`
- `Read · a skipped page answers 404 skipped with the reason`
- `Read · an unconfigured object store answers 503`
- `Read · an object missing after a replacement race answers translation_pending and does not raise`
- `Read · an unknown locale is refused with the existing locale error`
- `Read · the route writes nothing and enqueues nothing`

## Green

The smallest change for each red test, starting with the not-found codes so the contract is pinned before the success path.

## Refactor gate

- The route is a single controller function of about 5 lines. The read service maps outcomes to answers through a table, not a chain.
- The best-mention query changes shape once: extend the existing row type; do not add a second query.
- No query keys or SQL in the controller.
- House rules: about 100 lines per file, at most 3 parameters, no `Any`.

## Verification

```bash
cd apps/api
REQUIRE_DB=1 .venv/bin/python -m pytest -q tests/test_document_translation*.py tests/test_candidate_*.py tests/test_translation_admin*.py
.venv/bin/python -m scripts.export_openapi
REQUIRE_DB=1 .venv/bin/python -m pytest -q tests/test_openapi_snapshot.py
cd ../.. && ./ci.sh
```

## Out of scope

The accordion and its states (13), any write path, changing the card read route.

## Operator steps after merge

None.

## Git workflow

```bash
git checkout feat/plans-azure-translation && git pull
git checkout -b feat/azure-12-snapshot-read
# test(api): ... (red), feat(api): ... (green), refactor(api): ... (gate), chore(api): regenerate openapi snapshot
git push -u origin HEAD
# PR into feat/plans-azure-translation
```
