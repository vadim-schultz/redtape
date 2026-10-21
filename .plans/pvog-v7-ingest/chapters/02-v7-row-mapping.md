---
name: "Chapter 2 — v7 row mapping"
overview: "map_pvog_record for live v7 fields; update CLI integration tests and legacy fixtures as needed."
todos:
  - id: map
    content: "external_id leika/lb; portal_url from links; name title"
    status: pending
  - id: cli
    content: "test_pvog_cli mocks for v7 URLs + 400 negative"
    status: pending
isProject: false
---

# Chapter 2 — v7 row mapping

**Repo:** `redtape` (`apps/discovery-ingest`) · **Branch:** `feat/pvog-v7-row-mapping` · **Status:** planned

**Depends on:** [01](01-v7-tree-walk-client.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-pvog-v7-ingest`

---

## Goal

Map live v7 Suchdienst rows to `CatalogueBatchItem` so `pvog run` posts batches that upsert without mapping skips.

## Design decisions

Per [../gaps-and-decisions.md](../gaps-and-decisions.md) D7.

| Field | Source |
| --- | --- |
| `external_id` | `pvog:leika:{leikakeys[0]}` or `pvog:lb:{id}` |
| `title_i18n.de` | `name` |
| `description_i18n` | `description` or `teaser` |
| `portal_url` | `onlineServiceLinks[].uri` or `sourcePortals[].uri` |

## Files

| Path | Change |
| --- | --- |
| [`apps/discovery-ingest/discovery_ingest/pvog/client.py`](../../../apps/discovery-ingest/discovery_ingest/pvog/client.py) | `map_pvog_record` helpers |
| [`apps/discovery-ingest/tests/fixtures/pvog/live_shape_row.json`](../../../apps/discovery-ingest/tests/fixtures/pvog/live_shape_row.json) | Minimal live-shaped row |
| [`apps/discovery-ingest/tests/test_pvog_client.py`](../../../apps/discovery-ingest/tests/test_pvog_client.py) | Mapping happy + negative |
| [`apps/discovery-ingest/tests/test_pvog_cli.py`](../../../apps/discovery-ingest/tests/test_pvog_cli.py) | Full CLI path with v7 mocks |

## TDD loop

| Test | Asserts |
| --- | --- |
| `test_map_pvog_record_live_shape_leika_and_portal_url` | LeiKa id + URI from `onlineServiceLinks` |
| `test_map_pvog_record_rejects_row_without_id_and_leika` | `PvogMappingError` |
| `test_pvog_cli · sends mapped batch with source pvog` | Updated URL/query mocks (happy) |
| `test_pvog_cli_exits_nonzero_on_400` | Mock PVOG 400 → exit 1 |

## Refactor gate

Audit `map_pvog_record` and `_external_id_for_row` / `_portal_url_from_row`; report outcome.

## Verification

```bash
cd apps/discovery-ingest && uv run pytest tests/test_pvog_client.py tests/test_pvog_cli.py -q
./ci.sh
```

## PR

Target loop branch only.
