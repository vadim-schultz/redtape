---
name: "Chapter 13 — PVOG ingest CLI"
overview: "PVOG HTTP client and CLI upserting catalogue rows via discovery machine API."
todos:
  - id: pvog-client
    content: "pvog/client.py with fixture pagination"
    status: pending
  - id: cli
    content: "pvog subcommand"
    status: pending
isProject: false
---

# Chapter 13 — PVOG ingest CLI

**Repo:** `redtape` (`apps/discovery-ingest`) · **Branch:** `feat/discovery-layer-pvog-ingest` · **Status:** planned

**Depends on:** [12](12-govdata-ozg-ingest.md), [9](09-cos-pvog-skill.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-layer`

---

## Goal

Second ingest source: PVOG portals produce catalogue rows and enqueue fetch tasks the same way as GovData.

## Design decisions

Reuse `DiscoveryMachineClient` from chapter 12.

**Fixtures:** `tests/fixtures/pvog/page1.json` simulates paginated API.

**CLI:** `python -m discovery_ingest pvog run --jurisdiction-id <uuid>`.

## Files

| Path | Change |
| --- | --- |
| `apps/discovery-ingest/discovery_ingest/pvog/client.py` | Client |
| `apps/discovery-ingest/tests/fixtures/pvog/*.json` | Fixtures |
| `apps/discovery-ingest/tests/test_pvog_client.py` | Tests |
| `apps/discovery-ingest/tests/test_pvog_cli.py` | CLI tests |

## Red tests

| Test | Asserts |
| --- | --- |
| `PvogClient · follows next link in fixture pagination` | Happy path |
| `PvogClient · stops on empty page` | Happy path edge |
| `pvog CLI · sends mapped batch with source pvog` | Integration happy |
| `pvog CLI · exits non-zero on 422 validation` | Negative |

## Green

1. Pvog client + pagination; tests 1–2.
2. CLI subcommand; tests 3–4.

## Refactor gate

Shared `_post_catalogue_batches()` in `api_client.py` used by govdata and pvog CLIs. Report outcome.

## Verification

```bash
cd apps/discovery-ingest
python -m pytest tests/test_pvog_client.py tests/test_pvog_cli.py
cd ../.. && ./ci.sh
```

## Out of scope

FIM/LeiKa (chapter 17).

## Git workflow

```bash
git checkout feat/plans-discovery-layer && git pull
git checkout -b feat/discovery-layer-pvog-ingest
```

```text
test(ingest): pvog client pagination from fixtures

feat(ingest): add pvog ingest CLI
```

Open PR into `feat/plans-discovery-layer`.
