---
name: "A2 — Single emit pipeline"
overview: "Both emit flows submit through one submit_or_skip that turns suggestion-rule failures into reported skips; skip reasons become one SkipReason StrEnum; a duplicate or bad claim no longer aborts the whole catalogue emit."
todos:
  - id: characterise
    content: "Characterise DiscoveryEmitService (no direct tests today) and pin the idempotency key formats and skip strings"
    status: pending
  - id: red
    content: "Red: duplicate and invalid claims skip instead of aborting; SkipReason vocabulary; submit_or_skip mapping"
    status: pending
  - id: green
    content: "SkipReason, emit_submit.submit_or_skip, both flows use it, schema fields typed"
    status: pending
isProject: false
---

# A2 — Single emit pipeline

**Repo:** `redtape` · **Branch:** `fix/single-emit-pipeline` · **Status:** planned

**Depends on:** none (batch 1) · **Architecture:** [../00-audit-report.md](../00-audit-report.md) (C2, T5 skip reasons) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-codebase-audit` · **Release branch:** `main`

**Touches:** `api/features/discovery/{emit,candidate_emit*}`. **After:** none.

**Findings:** C2, T5 (skip reasons part).

## Goal

The claim emit (`DiscoveryEmitService`, machine route `POST /api/v1/discovery/machine/catalogue/{id}/emit`) and the candidate emit (`DiscoveryCandidateEmitService`, `POST .../machine/candidates/emit`) share one way to submit a suggestion and one vocabulary for "not emitted". A suggestion-rule failure on one item becomes a reported skip for that item; the rest of the batch still runs. Today the claim path lets `DuplicateSuggestionError` and friends escape, so one duplicate aborts the whole catalogue emit (500, whole session rolled back, earlier created suggestions lost).

## Intentional API change (the only behavioural change)

`POST /machine/catalogue/{id}/emit`: a claim whose suggestion is a duplicate, has an unknown taxonomy code, an invalid body, or a document outside the jurisdiction used to fail the request with 500. It is now `200` with that item `skip_reason` set (`duplicate` or `invalid_payload`; `no_source_url` for `MissingSourceUrlError`) and `suggestion_id: null`; the remaining claims are emitted and counted. Wire strings of every existing skip reason are unchanged. In the OpenAPI schema `skip_reason` changes from `string` to an enum of the same strings; the ingest client models keep accepting plain strings (I5 pins the contract). Candidate-emit behaviour is unchanged.

## Verified facts

| Fact | Evidence |
| --- | --- |
| Claim path has no handling | `emit.py:95-108` `_create` calls `self._suggestions.create(...)` bare; `_emit_one_claim` (84-93) only handles `missing_entity` and the preview skip. |
| Candidate path converts two errors | `candidate_emit.py:83-93` (`_create`: `DuplicateSuggestionError` -> `EmitSkip("duplicate", conflicts)`, `UnknownTaxonomyCodeError` -> `EmitSkip("invalid_payload")`); `95-105` `_previewed_request` repeats the taxonomy mapping and the conflicts-to-duplicate rule. The audit cites lines 90-101; the code is at 83-105. |
| Body validation is also unhandled on the claim path | `emit.py:24-33` `SuggestionCreate.model_validate(...)` raises `pydantic.ValidationError` (for example `official_url` not http(s)); the candidate path catches it in `candidate_emit_request.py:35-38`. |
| Two idempotency-key helpers | `emit.py:20-21` `_idempotency_key_for_claim` -> `"discovery-emit:{claim_id}"`; `candidate_emit_results.py:12-14` `idempotency_key` -> `"discovery-candidate-emit:{candidate_id}"`. Stored keys must not change (replay depends on them). |
| Skip vocabulary is bare strings in two places | `candidate_emit_skip.py:10` `SkipReason = Literal[...]` (6 values); `emit_preview.py:23-43` returns `"metadata_not_emitted"`, `"invalid_new_document_payload"`, `"unresolved_requirement_documents"`; `emit.py:87` and `emit_preview.py:74` use `"missing_entity"`; the schema fields are `str | None` (`schema/discovery/emit.py:15`, `candidate_emit.py:47`, `read.py:210`). |
| No direct service test | `grep -rn "DiscoveryEmitService\|emit_catalogue" tests` finds nothing; the flow is covered only through `tests/test_discovery_emit.py` (5 HTTP tests, lines 78-168). The audit statement "no test references `DiscoveryEmitService`" is literally true; HTTP coverage exists but pins none of the skip branches below. |
| `missing_entity` is defensive | `list_catalogue_claims` joins entities of the same catalogue (`repository/claims.py:40-48`), so the entity always exists; the branch is only reachable if the two repository calls disagree. |
| `already_emitted` has no test | no test file contains the string; only `candidate_emit.py:97` raises it (preview of an emitted candidate). |

## Files

| File | Change |
| --- | --- |
| `apps/api/app/schema/discovery/emit.py` | add `SkipReason(StrEnum)` (ten members below); `EmitOutcome.skip_reason: SkipReason \| None`. `tally_outcomes` is unchanged. |
| `apps/api/app/schema/discovery/candidate_emit.py` (line 47) and `read.py` (line 210) | type `skip_reason` as `SkipReason \| None` (one word each). |
| `apps/api/app/features/discovery/emit_submit.py` (new) | `submit_or_skip`, the exception-to-skip table, `idempotency_key(kind, item_id)`. |
| `apps/api/app/features/discovery/emit.py` | claim flow uses `submit_or_skip` and a validating request builder; reasons become `SkipReason` members. |
| `apps/api/app/features/discovery/candidate_emit.py` | `_create` and `_previewed_request` use the shared table. |
| `apps/api/app/features/discovery/candidate_emit_skip.py` | `EmitSkip.reason: SkipReason`; the `Literal` is deleted. |
| `apps/api/app/features/discovery/candidate_emit_results.py` | drop `idempotency_key` (moved). |
| `apps/api/app/features/discovery/emit_preview.py` | `_SKIP_CHECKS`, `claim_to_suggestion_payload`, `_preview_one`, `EmitPreviewItem.skip_reason` use `SkipReason`. |
| New tests | `apps/api/tests/test_discovery_emit_service.py`; additions to `test_discovery_emit.py`, `test_discovery_candidate_emit.py`, `test_discovery_emit_preview.py`. |

Touches gaps to report (both are safe because no other batch-1 chapter edits them): `emit_preview.py` and the three `schema/discovery/*` one-word type edits are not named in the table's Touches for A2. B3 owns `schema/discovery` in batch 2 and starts after A2 merges, so the `SkipReason` home in `schema/discovery/emit.py` also gives B3 a finished type instead of a second one to invent (the enum belongs in the schema layer because the wire shape uses it; `features` importing it is the allowed direction).

`SkipReason` members (the wire strings, unchanged):

| Member | Value | Used by |
| --- | --- | --- |
| `NOT_FOUND` | `not_found` | candidate emit, unknown candidate id |
| `NO_MENTIONS` | `no_mentions` | candidate request builder |
| `NO_SOURCE_URL` | `no_source_url` | candidate builder; claim path for `MissingSourceUrlError` (new) |
| `INVALID_PAYLOAD` | `invalid_payload` | both flows |
| `DUPLICATE` | `duplicate` | both flows (claim: new) |
| `ALREADY_EMITTED` | `already_emitted` | candidate preview |
| `MISSING_ENTITY` | `missing_entity` | claim emit and claim preview |
| `METADATA_NOT_EMITTED` | `metadata_not_emitted` | claim preview/emit |
| `INVALID_NEW_DOCUMENT_PAYLOAD` | `invalid_new_document_payload` | claim preview/emit |
| `UNRESOLVED_REQUIREMENT_DOCUMENTS` | `unresolved_requirement_documents` | claim preview/emit |

`submit_or_skip` (signature to implement, three parameters plus the service):

```python
def submit_or_skip(
    suggestions: SuggestionService, *, submitter: SubmitterRef, request: SuggestionCreate, idempotency_key: str
) -> SubmissionResult:
    """Create the suggestion, or raise EmitSkip when the suggestion rules reject this one item."""
```

Mapping table (one dict keyed by exception type, shared by `submit_or_skip` and the candidate preview path): `DuplicateSuggestionError` -> `DUPLICATE` (keep `exc.conflicts` on the `EmitSkip`), `UnknownTaxonomyCodeError`, `UnknownDocumentError`, `CycleError` -> `INVALID_PAYLOAD`, `MissingSourceUrlError` -> `NO_SOURCE_URL`. Anything else, including `UnknownJurisdictionError` (it would mean a catalogue row points at a vanished jurisdiction, a data-integrity bug) and unexpected `ValueError`s, propagates: this chapter must not hide bugs. The claim flow builds its request through a function that turns `pydantic.ValidationError` into `EmitSkip(INVALID_PAYLOAD)`, as the candidate builder already does.

Left separate on purpose (rule of three, total arms for the decision, pre-existing included): `_tally` in `emit.py` and `tally` in `candidate_emit_results.py` are one-liners over `tally_outcomes` for two different response models; the item builders `_skipped` and `skipped` build two different result models. Two uses each: not extracted, recorded in the PR.

## TDD loop

### Characterise first (all green before any production change)

New file `tests/test_discovery_emit_service.py`, service level (no HTTP), building `DiscoveryEmitService(DiscoveryRepository(db_session), SuggestionService(...))` the way `test_discovery_candidate_emit.py:296-302` builds the candidate service (taxonomy seeded with `seed_taxonomy`), reusing `_catalogue` from `test_discovery_admin_api` and a claim helper copied from `test_discovery_emit.py:56-75`:

1. `test_emit_catalogue_creates_one_pending_suggestion_per_emit_ready_claim` (happy path, two claims, `created_count == 2`).
2. `test_emit_catalogue_reports_a_metadata_claim_as_skipped` -> `"metadata_not_emitted"`.
3. `test_emit_catalogue_reports_a_new_document_claim_without_a_url_as_skipped` -> `"invalid_new_document_payload"`.
4. `test_emit_catalogue_reports_a_requirement_claim_without_documents_as_skipped` -> `"unresolved_requirement_documents"` (the HTTP test at `test_discovery_emit.py:105` already pins it; this version asserts the totals).
5. `test_emit_catalogue_reports_a_claim_without_its_entity_as_skipped` -> `"missing_entity"` (monkeypatch `repo.list_catalogue_entities` to return `[]`).
6. `test_emit_catalogue_replays_a_claim_emitted_before` (second call: `replayed_count == 1`, no new row).
7. `test_emit_catalogue_records_the_emit_attempted_event_with_the_counts`.
8. `test_idempotency_keys_keep_their_stored_format` — a created claim suggestion has `idempotency_key == f"discovery-emit:{claim.id}"`; a created candidate suggestion has `f"discovery-candidate-emit:{candidate.id}"`. This is the guard that the key move changes nothing stored.
9. In `test_discovery_candidate_emit.py`: `test_emit_preview_of_an_emitted_candidate_reports_already_emitted` (closes the `already_emitted` gap).

### Red

1. `test_emit_catalogue_skips_a_duplicate_claim_and_emits_the_rest` — three claims, the second with the same title and URL as the first: `created_count == 2`, `skipped_count == 1`, the skipped item has `skip_reason == "duplicate"` and `suggestion_id is None`, and the earlier suggestion is still in the database. Fails today with `DuplicateSuggestionError`.
2. `test_emit_catalogue_skips_a_claim_with_an_unknown_taxonomy_code` (`domain_codes: ["no-such-domain"]`) -> `invalid_payload`.
3. `test_emit_catalogue_skips_a_claim_whose_body_does_not_validate` (`official_url: "ftp://example.gov/x"`) -> `invalid_payload` (today a `ValidationError`).
4. `test_emit_catalogue_skips_a_requirement_claim_pointing_outside_the_jurisdiction` -> `invalid_payload` via `UnknownDocumentError` (recipe: `tests/test_suggestion_requirement_kind.py`).
5. HTTP: `test_post_emit_answers_200_with_a_skipped_duplicate_not_500` in `test_discovery_emit.py`.
6. `test_skip_reason_values_are_the_ten_wire_strings` — `{m.value for m in SkipReason}` equals the table above (guards accidental renames; fails with `ImportError` until the enum exists).
7. `test_submit_or_skip_maps_each_suggestion_rule_error` (parametrised over the five mapped exceptions with a stub service whose `create` raises it; asserts reason and, for duplicate, `conflicts`). Negative paths: `test_submit_or_skip_lets_unknown_jurisdiction_propagate` and `test_submit_or_skip_lets_an_unexpected_value_error_propagate`. Happy path: `test_submit_or_skip_returns_the_submission_result_on_success`.

Run the narrow suite; confirm 1-7 fail for the stated reasons and the characterisation set passes. Record before/after counts.

### Green

1. Add `SkipReason` and retype the three schema fields; add `emit_submit.py` with the table, `submit_or_skip` and `idempotency_key`; add the claim request builder that maps `ValidationError`.
2. `emit.py`: `_emit_one_claim` wraps the create in `try/except EmitSkip` and returns `_skipped(claim, skip.reason)`; reasons use the enum.
3. `candidate_emit.py`: `_create` calls `submit_or_skip`; `_previewed_request` uses the same table for its taxonomy error; `EmitSkip` carries `SkipReason`.
4. Delete the `Literal`, `_idempotency_key_for_claim` and `candidate_emit_results.idempotency_key`. Update `emit_preview.py`.
5. Re-run the narrow suite until green; then the discovery API tests.

### Refactor

**Refactor gate.** Smells to look for: two callers repeating a try/except ladder (this chapter removes it), string constants for one concept (removed by the enum), an exception used as control flow (`EmitSkip` is raised inside the flow and caught at the item boundary in both services; keep it, it is the existing pattern and a return-value alternative would thread `Result` types through four helpers for no gain). Judge by responsibility, not line count: `emit_submit.py` is "map suggestion-rule failures to skips" and nothing else; the services keep orchestration (claims or candidates), the builders keep payload building. One nesting level, no new parameters beyond the three keyword arguments; the `EmitSkip` constructor keeps two. Docstrings for every new public symbol in imperative mood stating intent (`SkipReason`, `submit_or_skip`, `idempotency_key`, the table); `emit.py` and `candidate_emit*.py` are rewritten files, so their missing docstrings are written here and their T1 baseline entries removed if the directory slice allows (the directory-wide `features/discovery` line is removed by T1 A-S1). No new `Any`, `cast` or `# type: ignore`; `dict[str, object]` bodies stay (their typing belongs to B3's read models).

## Not in scope (open seams)

- `SuggestionService._insert` calls `self._repo.rollback()` on an `IntegrityError` (`suggestions/service.py:187-188`), which rolls back the whole session, including suggestions created earlier in the same emit batch. It only fires on an idempotency-key unique race. Fix with a savepoint in B2.
- Tightening `payload`/`claims` typing of the pipeline response (`list[dict[str, object]]`) is B3.

## Verification

```bash
cd apps/api
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
uv run pytest tests/test_discovery_emit_service.py tests/test_discovery_emit.py tests/test_discovery_emit_preview.py tests/test_discovery_candidate_emit.py tests/test_discovery_candidate_emit_payload.py tests/test_discovery_error_responses.py tests/test_discovery_machine_api.py
cd ../..
./ci.sh
```

The machine and admin API files are slow: run them in the background. Report `Refactor gate: smells found -> ..., refactorings applied -> ...` and the before/after counts in the PR.

## Git workflow

```bash
git checkout feat/plans-codebase-audit && git pull
git checkout -b fix/single-emit-pipeline
```

```text
test(api): characterise DiscoveryEmitService and pin skip strings and idempotency keys
test(api): red for claim emit that aborts on duplicate or invalid claims
fix(api): share submit_or_skip between both emit flows and type skip reasons as SkipReason
```

Open the chapter PR into `feat/plans-codebase-audit`, not `main`.

## Parallel notes

Runs in batch 1 beside T1 step 1, T2, T3, A1, A3, A4, B1, B6, W1, W2. Files this chapter must not touch: `features/voting/*` and `features/suggestions/*` (A1; B2 later), `lifespan.py` (A4), `routes.py`, `shared/locale.py`, `locale_resolution.py`, `i18n_resolution.py` (B1), `services/openplz_client.py` and `scripts/` (B6), ruff/mypy config (T1, T2), `tests/test_architecture.py` and `apps/web` (T3, W1, W2). The only `schema/discovery/*` edits are the three one-word `skip_reason` types plus the new enum; B3 (batch 2, `After: A2`) rebases onto them. B3, B4 and B5 later edit `features/discovery/*`; T1 slice A-S1 waits for B3 and B4.
