---
name: "Chapter 11 — Candidate emit"
overview: "Emit a staged document candidate as a pending new_document suggestion, manually and idempotently, after making official_url optional on that suggestion kind."
todos:
  - id: optional-url
    content: "Make NewDocumentPayload.official_url optional; skip URL conflict checks when absent"
    status: pending
  - id: emit-service
    content: "Candidate emit service with idempotency key, conflict reporting and candidate status update"
    status: pending
  - id: routes
    content: "Machine emit route and admin emit preview route"
    status: pending
  - id: cli
    content: "candidates emit CLI with dry-run, limit and minimum mentions"
    status: pending
isProject: false
---

# Chapter 11 — Candidate emit

**Repo:** `redtape` (`apps/api`, `apps/discovery-ingest`) · **Branch:** `feat/crawlers-candidate-emit` · **Status:** planned

**Depends on:** [06](06-candidate-staging-model-and-api.md), [07](07-pvog-payload-harvester.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/crawlers`

## Goal

Turn reviewed candidates into pending `new_document` suggestions so the existing votes and promotion can create real `document` rows. Emit stays a deliberate operator action ([discovery-operations D12](../../discovery-operations/gaps-and-decisions.md)).

## The URL problem (decision D8)

`NewDocumentPayload.official_url` is required ([payload.py](../../../apps/api/app/schema/suggestion/payload.py)), and duplicates are detected on `slug` or normalized `official_url` per jurisdiction, against both documents and pending suggestions ([handlers.py](../../../apps/api/app/features/suggestions/handlers.py), `find_pending_by_url`). `normalize_url` drops fragments, so using the procedure page as a fallback URL would reject every second document found on that page. Many candidates ("Personalausweis") have no URL at all. The fix is additive:

- `official_url: str | None = None` in `NewDocumentPayload`; when present it is validated exactly as today (an empty string is still invalid);
- `NewDocumentHandler.normalized_url` returns `None` when absent; `conflicts` and `_check_still_free` compare the slug only; `find_pending_by_url` is skipped for `None`;
- `suggestion.normalized_url` is already nullable and `Document.official_url` is already nullable; `DocumentService._build_document` passes the value through;
- provenance travels in `suggestion.source_url`, the page the candidate was found on.

This relaxes the public submit path too (a human may omit the URL). The web submit form is unchanged and still sends one. The change is noted in [suggestion-interface](../../suggestion-interface/gaps-and-decisions.md) by the docs sync.

## Contract

**Emit service.** `DiscoveryCandidateEmitService.emit(candidate_id, api_key)` in `apps/api/app/features/discovery/`:

- build `{kind: new_document, jurisdiction_id, source_url, payload: {title_i18n, official_url?}}`; `source_url` is the `portal_url` of the candidate's first mention's procedure;
- call `SuggestionService.create` with `SubmitterRef("crawler", api_key.id)` and idempotency key `discovery-candidate-emit:{candidate_id}`, the same pattern as [emit.py](../../../apps/api/app/features/discovery/emit.py);
- on success set `status = emitted` and `suggestion_id`; a replay returns the existing suggestion with `replayed = true`;
- on `DuplicateSuggestionError` return a per-candidate result `skip_reason = "duplicate"` with the conflicts; the candidate stays `staged`; this is a reported outcome, not an error;
- an already `emitted` candidate returns its suggestion without calling the service again.

**Routes.**

- `POST /api/v1/discovery/machine/candidates/emit` with `{candidate_ids: [...]}` (at most 50), returning one result per id: `created`, `replayed`, or skipped with a reason; unknown ids are reported per item.
- `GET /api/v1/discovery/admin/candidates/{id}/emit-preview`: read-only, returns the suggestion body or a skip reason, never writes.

**CLI.** `python -m discovery_ingest candidates emit` with `--id` (repeatable) or `--all-staged`, plus `--min-mentions`, `--limit` (default 10, maximum 50) and `--dry-run` (calls the preview route only). The command prints counts and suggestion ids. There is no scheduled emit.

## TDD loops

### Loop A — Optional URL

**Red** (`test_suggestion_payload.py`, `test_suggestion_duplicates.py`, `test_suggestion_service.py`)

1. `new_document payload without official_url is valid`.
2. `new_document payload with a blank or malformed official_url is still invalid` — negative guard.
3. `two url-less documents with different slugs do not conflict`.
4. `same slug still conflicts without a url`.
5. `a url-less document promotes with a null official_url` (`test_promote_new_document.py`).

**Green:** make the field optional and thread `None` through the handler.

**Refactor:** keep the conflict predicate in one pure function; no `if url is None` scattered across layers.

### Loop B — Emit service

**Red** (`apps/api/tests/test_discovery_candidate_emit.py`)

1. `emit creates a pending suggestion and marks the candidate emitted` — source url from the first mention.
2. `emit replay is idempotent` — same suggestion id, `replayed = true`.
3. `emit reports a slug conflict as a skipped candidate` — status unchanged.
4. `emit of an unknown candidate is reported per item`.
5. `emit preview never writes` — no suggestion, no status change.
6. `emit requires the machine key; preview requires an admin`.

**Green:** one small service plus controller methods.

**Refactor:** share the result type with the existing catalogue emit response where fields overlap.

### Loop C — CLI

**Red** (`apps/discovery-ingest/tests/test_candidates_cli.py`)

1. `emit --dry-run calls only the preview route`.
2. `emit applies min-mentions and limit` and `rejects a limit over 50 before any call`.
3. `emit prints created replayed and skipped counts`.

**Green:** CLI function using the client; no business logic in the CLI.

**Refactor:** keep selection (which candidates) separate from emission.

## Verification

```bash
cd apps/api && python -m pytest tests/test_suggestion_payload.py tests/test_suggestion_duplicates.py tests/test_promote_new_document.py tests/test_discovery_candidate_emit.py
cd apps/discovery-ingest && python -m pytest tests/test_candidates_cli.py
gh pr checks --watch
```

Live gate (operator routine S10): dry-run, emit five candidates with the highest mention counts, open the pending suggestions through the API, then decide whether to emit more. Record counts and suggestion ids. Never bulk-emit before the first five are reviewed.

## Out of scope

Edge (`new_requirement`) emit, automatic emit, merging candidates, the web voting UI, attaching artifacts as suggestion evidence.
