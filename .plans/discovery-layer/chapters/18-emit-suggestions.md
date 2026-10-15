---
name: "Chapter 18 — Emit suggestions"
overview: "Machine endpoint POST emit creates pending suggestions via SuggestionService with idempotency."
todos:
  - id: emit-service
    content: "DiscoveryEmitService"
    status: pending
  - id: endpoint
    content: "POST /catalogue/{id}/emit"
    status: pending
isProject: false
---

# Chapter 18 — Emit suggestions

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/discovery-layer-emit` · **Status:** planned

**Depends on:** [7](07-emit-preview-panel.md), [15](15-discovery-entity-dedup.md), [17](17-fim-leika-enrich.md) · **Contract:** [../02-staging-model-and-api.md](../02-staging-model-and-api.md) §6 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-layer`

---

## Goal

Operators or automation trigger emit for one catalogue row; emit-ready claims become `pending` suggestions
through the existing suggestion API internals. Voting is not involved.

## Design decisions

**Auth:** machine `X-API-Key` on `POST /api/v1/discovery/machine/catalogue/{id}/emit`.

**Skips** unresolved `new_requirement` claims (same as preview); counts returned in response body.

**Idempotency:** `discovery-emit:{claim_id}` per key — replay returns same suggestion id (200).

Reference tests: [test_suggestions_machine_submit.py](../../apps/api/tests/test_suggestions_machine_submit.py).

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/discovery/emit.py` | Emit service |
| `apps/api/app/features/discovery/machine_controller.py` | Emit route |
| `apps/api/tests/test_discovery_emit.py` | Tests |

## Red tests

| Test | Asserts |
| --- | --- |
| `emit · creates pending new_document suggestion for emit-ready claim` | Happy path |
| `emit · skips requirement claim without resolved document UUIDs` | Skip path |
| `emit · replays same suggestion for duplicate idempotency key` | Happy idempotent |
| `emit · returns 401 without API key` | Negative |
| `emit · records emit_attempted discovery_event` | Lineage |

## Green

1. `emit.py` using shared preview mapper; tests 1–2.
2. Endpoint + idempotency; tests 3–5.

## Refactor gate

Preview and emit share payload builder; no duplicate mapping logic. Report outcome.

## Verification

```bash
cd apps/api
python -m pytest tests/test_discovery_emit.py
cd ../.. && ./ci.sh
```

## Out of scope

Voting, promotion, evidence (chapters 16 deferred).

## Git workflow

```bash
git checkout feat/plans-discovery-layer && git pull
git checkout -b feat/discovery-layer-emit
```

```text
test(api): discovery emit to suggestions

feat(api): add machine emit endpoint for staging claims
```

Open PR into `feat/plans-discovery-layer`.
