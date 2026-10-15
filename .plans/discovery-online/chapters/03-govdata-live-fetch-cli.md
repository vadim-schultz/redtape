---
name: "Chapter 3 — GovData live fetch CLI"
overview: "govdata fetch subcommand paginates CKAN package and batches to machine API; CI uses fixtures only."
todos:
  - id: client
    content: "CKAN package_show + resource download/paginate"
    status: pending
  - id: cli
    content: "govdata fetch --jurisdiction-id --max-pages"
    status: pending
  - id: tests
    content: "MockTransport tests"
    status: pending
isProject: false
---

# Chapter 3 — GovData live fetch CLI

**Repo:** `redtape` (`apps/discovery-ingest`) · **Branch:** `feat/discovery-online-govdata-fetch` · **Status:** planned

**Depends on:** [2](02-secrets-and-env-canon.md) · **Canon:** [government-data-sources.md](../../../docs/discovery/government-data-sources.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-online`

---

## Goal

`python -m discovery_ingest govdata fetch --jurisdiction-id <uuid>` downloads the OZG Leistungen export from GovData CKAN (configurable `GOVDATA_*` env), maps rows, and posts batches via `DiscoveryMachineClient` — no `--input` file required for scheduled runs.

## Design decisions

**Pagination / limits:** `--max-pages` (default high enough for MVP federal slice) and `--max-records` safety cap for GHA 60m timeout.

**Reuse** `_map_govdata_record` / batch posting from existing `govdata run`.

**Errors:** non-2xx CKAN → exit 1; partial batch failure surfaces API status.

**CI:** only fixture-backed tests; no live CKAN in `./ci.sh`.

## Files

| Path | Change |
| --- | --- |
| `apps/discovery-ingest/discovery_ingest/govdata/ckan.py` | CKAN HTTP client |
| `apps/discovery-ingest/discovery_ingest/cli.py` | `govdata fetch` subcommand |
| `apps/discovery-ingest/tests/test_govdata_fetch.py` | MockTransport tests |
| `scripts/ci.sh` | Include new tests if needed |

## TDD loop

| Test | Asserts |
| --- | --- |
| `govdata fetch · maps CKAN page and posts batch with API key` | Happy path |
| `govdata fetch · exits 1 when CKAN returns 500` | Negative path |

## Refactor gate

Extract CKAN fetch from CLI orchestration; keep `cli.py` dispatch thin. Report outcome.

## Verification

```bash
cd apps/discovery-ingest && pytest tests/test_govdata_fetch.py
cd ../.. && ./ci.sh
```

## PR

Target loop branch.
