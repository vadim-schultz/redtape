---
name: "Chapter 12 — GovData OZG ingest"
overview: "discovery-ingest GovData client + CLI batching catalogue upserts to the machine API from fixtures."
todos:
  - id: package
    content: "apps/discovery-ingest skeleton + DiscoveryMachineClient"
    status: pending
  - id: govdata
    content: "govdata client + fixture-driven tests"
    status: pending
  - id: cli
    content: "python -m discovery_ingest govdata run"
    status: pending
isProject: false
---

# Chapter 12 — GovData OZG ingest

**Repo:** `redtape` (`apps/discovery-ingest`, `apps/api` tests) · **Branch:** `feat/discovery-layer-govdata-ingest` · **Status:** planned

**Depends on:** [3](03-task-auto-enqueue-claim.md), [7a](07a-government-data-sources-canon.md), [8](08-cos-govdata-skill.md) · **Contract:** [../02-staging-model-and-api.md](../02-staging-model-and-api.md) §7 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-layer`

---

## Goal

Operators run a CLI that reads GovData/OZG exports (or fixture files in CI) and upserts catalogue rows via
the machine API, producing visible tasks in admin.

## Design decisions

**New package** `apps/discovery-ingest/` (D12); add to root `ci.sh` if not already.

**GovData client** loads JSON from `tests/fixtures/govdata/` in tests; live URL only in manual runs. Fixture
shape must mirror OZG **Leistungen** JSON from
[docs/discovery/government-data-sources.md](../../../docs/discovery/government-data-sources.md) § GovData.

**Batch size** 50; uses `POST /catalogue/batch`.

**Env:** `DISCOVERY_API_URL`, `DISCOVERY_API_KEY`; optional `GOVDATA_CKAN_BASE_URL`, `GOVDATA_PACKAGE_ID` (canon). Manual live CKAN: set corporate `HTTP_PROXY` / `HTTPS_PROXY` per [corporate-build-env.md](../../../.cursor/skills/chief-of-staff/corporate-build-env.md).

## Files

| Path | Change |
| --- | --- |
| `apps/discovery-ingest/pyproject.toml` | Package deps: httpx, pydantic |
| `apps/discovery-ingest/discovery_ingest/api_client.py` | Machine client |
| `apps/discovery-ingest/discovery_ingest/govdata/client.py` | Parser + mapper |
| `apps/discovery-ingest/discovery_ingest/cli.py` | `govdata` subcommand |
| `apps/discovery-ingest/tests/test_govdata_client.py` | Client tests |
| `apps/discovery-ingest/tests/test_govdata_cli.py` | CLI with respx against API |
| `scripts/ci.sh` | Include discovery-ingest when present |

## Red tests

| Test | Asserts |
| --- | --- |
| `GovDataClient · maps fixture row to batch upsert DTO` | Happy path |
| `GovDataClient · rejects row without external id` | Negative |
| `govdata CLI · posts batch to machine API with API key header` | Integration happy |
| `govdata CLI · exits 1 when API returns 401` | Negative |

## Green

1. Package skeleton + `DiscoveryMachineClient`; test client wiring with respx.
2. GovData mapper; tests 1–2.
3. CLI; tests 3–4.

## Refactor gate

Mapping table as pure function `_map_govdata_record()`. Report outcome.

## Verification

```bash
cd apps/discovery-ingest
ruff format --check . && ruff check . && mypy discovery_ingest
python -m pytest tests/test_govdata_client.py tests/test_govdata_cli.py
cd ../.. && ./ci.sh
```

## Out of scope

PVOG (chapter 13), FIM/LeiKa enrich (chapter 17).

## Git workflow

```bash
git checkout feat/plans-discovery-layer && git pull
git checkout -b feat/discovery-layer-govdata-ingest
```

```text
test(ingest): govdata client maps fixture to catalogue batch

feat(ingest): add govdata ingest CLI for discovery machine API
```

Open PR into `feat/plans-discovery-layer`.
