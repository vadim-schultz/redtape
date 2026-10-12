---
name: "Chapter 17 — FIM + LeiKa enrich"
overview: "FIM and LeiKa clients upsert enrich_metadata tasks and entity/claim rows via machine API."
todos:
  - id: fim
    content: "fim client + enrich subcommand"
    status: pending
  - id: leika
    content: "leika client + enrich subcommand"
    status: pending
  - id: machine-entities
    content: "Wire POST /entities and /claims if not done"
    status: pending
isProject: false
---

# Chapter 17 — FIM + LeiKa enrich

**Repo:** `redtape` (`apps/discovery-ingest`, `apps/api`) · **Branch:** `feat/discovery-layer-fim-enrich` · **Status:** planned

**Depends on:** [12](12-govdata-ozg-ingest.md), [7a](07a-government-data-sources-canon.md), [10](10-cos-fim-skill.md), [11](11-cos-leika-skill.md) · **Contract:** [../02-staging-model-and-api.md](../02-staging-model-and-api.md) §4 machine entities/claims · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-layer`

---

## Goal

After catalogue ingest, enrich CLIs fetch FIM/LeiKa metadata for existing `catalogue_service` rows and record
`discovery_entity` + `discovery_claim` rows (metadata / new_document stubs) without crawlers.

## Design decisions

**Machine endpoints** `POST /entities` and `POST /claims` implemented here if not added in chapter 3.

**Enrich flow:** CLI accepts `catalogue_service_id` or batches by `source=govdata` filter via admin export
fixture in tests.

**Env:** `FIM_PORTAL_BASE_URL` default `https://fimportal.de`. Map subcommands to endpoints in
[docs/discovery/government-data-sources.md](../../../docs/discovery/government-data-sources.md) § FIM / LeiKa.
Manual FIM calls: corporate proxy per [corporate-build-env.md](../../../.cursor/skills/chief-of-staff/corporate-build-env.md) (D15).

**Task kind:** `enrich_metadata` tasks may be enqueued by fanout (chapter 14) — CLI completes them via
machine API.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/discovery/machine_controller.py` | Entity + claim handlers |
| `apps/api/tests/test_discovery_machine_entities.py` | API tests |
| `apps/discovery-ingest/discovery_ingest/fim/client.py` | FIM client |
| `apps/discovery-ingest/discovery_ingest/leika/client.py` | LeiKa client |
| `apps/discovery-ingest/tests/test_fim_leika_enrich.py` | Ingest tests |

## Red tests

| Test | Asserts |
| --- | --- |
| `POST /entities · upserts entity under catalogue service` | API happy |
| `POST /claims · records new_document claim payload` | API happy |
| `POST /claims · returns 422 for invalid payload shape` | API negative |
| `fim enrich CLI · posts entity and claim from fixture` | Ingest happy |
| `leika enrich CLI · exits 1 when catalogue id unknown` | Ingest negative |

## Green

1. Machine entity/claim endpoints; tests 1–3.
2. FIM client + CLI; test 4.
3. LeiKa client + CLI; test 5.

## Refactor gate

Claim payload validation via Pydantic models per `discovery_claim_kind`. Report outcome.

## Verification

```bash
cd apps/api
python -m pytest tests/test_discovery_machine_entities.py
cd ../discovery-ingest
python -m pytest tests/test_fim_leika_enrich.py
cd ../.. && ./ci.sh
```

## Out of scope

Evidence attachments (chapter 16 deferred), crawler fetch (chapter 20).

## Git workflow

```bash
git checkout feat/plans-discovery-layer && git pull
git checkout -b feat/discovery-layer-fim-enrich
```

```text
test(api): discovery machine entity and claim endpoints

feat(ingest): add fim and leika enrich CLIs
```

Open PR into `feat/plans-discovery-layer`.
