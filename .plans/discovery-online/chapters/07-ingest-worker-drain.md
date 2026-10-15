---
name: "Chapter 7 — Ingest worker drain"
overview: "discovery_ingest worker drain claims tasks, fetches URLs, logs, completes; GHA-safe limits."
todos:
  - id: client
    content: "Machine client claim/complete/fetch methods"
    status: pending
  - id: drain
    content: "worker drain CLI + polite fetcher"
    status: pending
  - id: workflow
    content: "Add drain step to discovery job"
    status: pending
isProject: false
---

# Chapter 7 — Ingest worker drain

**Repo:** `redtape` (`apps/discovery-ingest`) · **Branch:** `feat/discovery-online-worker-drain` · **Status:** planned

**Depends on:** [6](06-task-lease-reclaim.md) · **Partial:** [discovery-layer ch.20](../../../.plans/discovery-layer/chapters/20-crawler-frontier-adapter.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-online`

---

## Goal

`python -m discovery_ingest worker drain --max-tasks 50` claims pending tasks via machine API, performs polite HTTP GET on `target_url`, posts fetch logs, marks complete or fail, prints JSON report. Wired into platform-maintenance discovery job after catalogue ingest.

## Design decisions

**Fetcher:** httpx with timeout, per-host delay (port rate-limit pattern from OpenPLZ client conceptually — local helper in ingest package, no `apps/api` import).

**Task kinds in v1:** `fetch_url` fully handled; `enrich_metadata` delegated to chapter 8 (may no-op or short-circuit in drain loop).

**Machine client** extend [`api_client.py`](../../../apps/discovery-ingest/discovery_ingest/api_client.py): `claim_tasks`, `append_fetch`, `complete_task`, `fail_task`.

**Exit code:** non-zero if claim API fails; zero if individual fetch fails but reported (per-task fail).

## Files

| Path | Change |
| --- | --- |
| `apps/discovery-ingest/discovery_ingest/worker/drain.py` | Drain loop |
| `apps/discovery-ingest/discovery_ingest/worker/fetcher.py` | Polite GET |
| `apps/discovery-ingest/discovery_ingest/cli.py` | `worker drain` subcommand |
| `apps/discovery-ingest/discovery_ingest/api_client.py` | Machine task methods |
| `apps/discovery-ingest/tests/test_worker_drain.py` | MockTransport |
| `.github/workflows/platform-maintenance.yml` | Run drain after ingest |

## TDD loop

| Test | Asserts |
| --- | --- |
| `worker drain · claims task posts fetch log and completes` | Happy path |
| `worker drain · marks fail when GET times out` | Negative path |

## Refactor gate

Drain loop dispatches per task kind to named handlers. Report outcome.

## Verification

```bash
cd apps/discovery-ingest && pytest tests/test_worker_drain.py
cd ../.. && ./ci.sh
```

## PR

Target loop branch.
