---
name: "Chapter 12 — FIM key fix"
overview: "Make FIM enrichment fire by deriving the steckbrief key from leika_key / leikakeys, verify the assumption with a live probe, and record what the steckbrief actually contains."
todos:
  - id: probe
    content: "fim probe CLI and a manual workflow that report status and top-level keys for sample keys"
    status: pending
  - id: fanout
    content: "Fanout derives the key from fim_id, leistungsschluessel, leika_key or leikakeys"
    status: pending
  - id: fixture
    content: "Replace the five-key steckbrief fixture with a real sanitized response"
    status: pending
  - id: findings
    content: "Record which steckbrief fields could feed document mentions"
    status: pending
isProject: false
---

# Chapter 12 — FIM key fix

**Repo:** `redtape` (`apps/api` fanout, `apps/discovery-ingest`, `.github/workflows`) · **Branch:** `feat/crawlers-fim-key-fix` · **Status:** planned

**Depends on:** [03](03-kind-filtered-claim.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/crawlers`

## Goal

`_fim_enrich_spec` in [fanout.py](../../../apps/api/app/features/discovery/fanout.py) enqueues `enrich_metadata` only for GovData rows whose `raw_payload` contains `fim_id`. Production has 893 GovData rows and none carries `fim_id`; all carry `leika_key`. Zero enrichment tasks exist, so there are zero entities and zero claims. In FIM the steckbrief key is the Leistungsschlüssel, which is also the LeiKa key, and PVOG rows expose `leikakeys`. That equivalence is an assumption until the probe confirms it.

## Contract

**Probe.** `python -m discovery_ingest fim probe --keys <comma list>` fetches `GET {FIM}/api/v1/leistung-steckbriefe/{key}` for each key through the hardened fetcher and prints, per key, the HTTP status and the top-level JSON keys (never the full body). A manual workflow `discovery-fim-probe.yml` takes `keys` (default: one GovData `leika_key` and one PVOG key from the census, F3) and writes the output to the job summary.

**Decision gate.** If at least four of every five sampled keys return 200 with a `leistungsschluessel` field, proceed. Otherwise stop, record the finding in [gaps-and-decisions.md](../gaps-and-decisions.md), and choose between the LeiKa stammtext route (helpers already exist in [enrich.py](../../../apps/discovery-ingest/discovery_ingest/enrich.py)) and dropping FIM enrichment for those rows.

**Fanout.** The key resolver tries, in order: `fim_id`, `leistungsschluessel`, `leika_key`, then the first element of `leikakeys`. A key must match `^\d{14}$`; anything else yields no task. The rule now applies to GovData and PVOG rows. The task keeps priority 200 and the steckbrief URL. Rows already staged get their tasks on the next catalogue run, as for chapter 7.

**Worker.** `fim_id_from_catalogue` in `enrich.py` uses the same resolution order so CLI and fanout agree. The enrich handler is otherwise unchanged. Its claims remain a `metadata` claim (`kurztext`) and the service-level `new_document` claim, which stays staged and excluded from the document-first path (decision D5).

**Findings.** The probe output lists the top-level steckbrief keys. If any names documents, forms or evidence, add a guarded mapping to mentions in a second loop (extractor `fim-steckbrief`); otherwise record in the gaps document that the steckbrief carries no document fields. The sanitized real response replaces `tests/fixtures/fim/steckbrief.json`, which currently has five keys.

## TDD loops

### Loop A — Fanout

**Red** (`apps/api/tests/test_discovery_fanout.py`)

1. `govdata row with leika_key enqueues an enrich task for that steckbrief url`.
2. `pvog row with leikakeys enqueues an enrich task for the first key`.
3. `fim_id takes precedence over leika_key`.
4. `malformed or missing keys enqueue nothing` — negative table.
5. `re-fanout is idempotent`.

**Green:** a small `steckbrief_key(raw_payload)` function used by the rule.

**Refactor:** the ingest helper and the API rule both call equivalent, tested resolvers; note the duplication and keep them in lockstep with a shared fixture table.

### Loop B — Probe

**Red** (`apps/discovery-ingest/tests/test_fim_probe.py`)

1. `probe prints status and top-level keys without the body`.
2. `probe reports a 404 and a timeout per key without aborting`.

**Green:** CLI function using the fetcher; JSON parsing guarded.

**Refactor:** share URL construction with the enrich helpers.

### Loop C — Findings mapping (conditional)

Only if the probe shows document-bearing fields: **Red** fixture-driven tests that a steckbrief with such fields yields mentions and one without yields none; **Green** a pure mapper registered as another harvester; **Refactor** reuse the noise filter from chapter 7.

## Verification

```bash
cd apps/api && python -m pytest tests/test_discovery_fanout.py
cd apps/discovery-ingest && python -m pytest tests/test_fim_probe.py tests/test_enrich_metadata_worker.py tests/test_fim_leika_enrich.py
gh pr checks --watch
gh workflow run discovery-fim-probe.yml -f keys=99154021000000,99070016261000
gh run view --log
gh workflow run platform-maintenance.yml -f job=discovery
gh workflow run discovery-drain.yml -f kinds=enrich_metadata -f max_batches=3
```

Live gate: the probe passes the decision gate; after the drain, the admin pipeline view of one GovData row shows an entity, claims and stage T3. Record run ids and the row.

## Out of scope

Emitting service-level claims, LeiKa stammtext enrichment unless the decision gate fails, changing claim payload shapes.
