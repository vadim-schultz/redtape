---
name: "Chapter 8 — Suggestion event log"
overview: "suggestion_event table recording every vote, transition and promotion as an immutable row; transition_to and VoteService.cast are extended to log, never to update or delete a past event."
todos:
  - id: model
    content: "SuggestionEvent model, EventType enum, migration"
    status: pending
  - id: logging
    content: "EventLogService.record, called from voting and transition_to"
    status: pending
isProject: false
---

# Chapter 8 — Suggestion event log

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/voting-event-log` · **Status:** planned

**Depends on:** [6](06-promote-new-document.md), [7](07-promote-requirement-edge.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §3, §7 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Every vote and every status change leaves a permanent, queryable trace, so a disputed decision can be
reconstructed exactly (the `social-moderation` strand's "full trace for disputes").

## Design decisions

**Append-only by construction, not just convention** (D7): `SuggestionEvent` has no update path anywhere in
the code — `EventLogService` exposes only `record(...)` and `list_for(suggestion_id)`. There is deliberately
no `EventLogRepository.update` or `.delete` method to accidentally call.

**One record call per meaningful action**, added at the existing call sites rather than a generic
before/after diff:
- `VoteService.cast` → `event_type="voted"`, `data={"value": value}`, `actor_user_id=user_id`.
- `SuggestionService.transition_to` → `event_type="status_changed"`, `data={"from": old, "to": new}`.
- The promotion handlers (chapters 6–7) → `event_type="promoted"`, `data={"created_id": str(id), "table":
  "document" | "document_requirement"}`, recorded inside `transition_to` right after a successful `promote`
  call, in the same transaction.
- The `submitted` event is backfilled: suggestion-interface's `create` (chapter 3) gains one call too, in
  this chapter (not retroactively — existing suggestions before this ships simply have no `submitted`
  event, documented as an open seam).

**Actor is nullable on both sides**: a `submitted`/`voted` event has `actor_user_id` or `actor_api_key_id`
(mirroring the suggestion's own submitter constraint, D-review); a `status_changed` event from an automatic
threshold crossing has **no actor** (both null) — it is what happened, not who did it; a
`moderator_override` event (chapter 9) is the one place `actor_user_id` is required.

**Layering**: `EventLogService` lives in its own small feature, `features/events/`, depended on by voting
and suggestions as a service (never the other way around — it has no opinion about what a "vote" or
"promotion" means, only records what it is told).

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/models/suggestion_event.py`, `apps/api/app/models/__init__.py` | Model, `EventType` |
| `apps/api/alembic/versions/<yyyymmdd>_suggestion_event.py` | Migration |
| `apps/api/app/features/events/{repository,service,dependencies}.py` | `EventLogService` |
| `apps/api/app/features/voting/service.py`, `apps/api/app/features/suggestions/service.py` | Call `record` |
| `apps/api/tests/test_suggestion_event_log.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `EventLogService · record and list_for round-trip an event` | Basic |
| `EventLogService · has no method that updates or deletes an event` | Introspection assertion on the class's public methods |
| `VoteService.cast · logs a voted event with the value and the voter` | Data shape |
| `transition_to · logs a status_changed event with from and to` | Data shape |
| `transition_to · an automatic transition logs no actor` | Both actor columns null |
| `promote (new_document) · logs a promoted event with the created document id` | Data shape |
| `promote (new_requirement) · logs a promoted event with the created requirement id` | Data shape |
| `SuggestionService.create · logs a submitted event` | Present from creation |
| `events · list_for returns events in chronological order` | Order |
| `events · list_for an unknown suggestion returns an empty list, not an error` | Negative |

## Green

1. Model, migration, service skeleton; tests 1, 2, 9, 10.
2. Wire into vote casting; test 3.
3. Wire into transitions; tests 4, 5.
4. Wire into both promotion handlers; tests 6, 7.
5. Wire into suggestion creation; test 8.

## Refactor gate

`EventLogService.record` stays a single insert; each call site adds one line, not a wrapper class per
caller. Report the outcome.

## Verification

```bash
cd apps/api
python -m pytest tests/test_suggestion_event_log.py tests/test_vote_service.py tests/test_suggestion_transitions.py tests/test_promote_new_document.py tests/test_promote_requirement_edge.py
alembic upgrade head && alembic downgrade -1 && alembic upgrade head
cd ../.. && ./ci.sh
```

## Out of scope

Exposing events over HTTP (chapter 9's `GET .../events`), retention/archival policy.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/voting-event-log
```

```text
test(api): describe the append-only suggestion event log

feat(api): record vote, transition and promotion events
```
