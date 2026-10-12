---
name: "Chapter 15 — Discovery entity dedup"
overview: "Normalize canonical_url and merge duplicate discovery_entity rows under a catalogue service."
todos:
  - id: normalize
    content: "URL normalization shared with suggestions"
    status: pending
  - id: dedup
    content: "Upsert entity merges on normalized URL"
    status: pending
isProject: false
---

# Chapter 15 — Discovery entity dedup

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/discovery-layer-entity-dedup` · **Status:** planned

**Depends on:** [17](17-fim-leika-enrich.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-layer`

---

## Goal

Multiple enrich passes cannot create parallel entities for the same URL; claims attach to one entity id.

## Design decisions

**Normalization** reuses suggestion URL rules ([suggestion-interface](../suggestion-interface/00-architecture.md) §2).

**On conflict:** update `label` if newer non-empty; reassign claims only in tests — production claims stay on
winning entity (no merge of claim rows in v1).

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/discovery/url_normalize.py` | Normalizer |
| `apps/api/app/features/discovery/service.py` | Entity upsert dedup |
| `apps/api/tests/test_discovery_entity_dedup.py` | Tests |

## Red tests

| Test | Asserts |
| --- | --- |
| `normalize_url · strips trailing slash and utm params` | Unit happy |
| `entity upsert · returns same id for equivalent URLs` | Happy path |
| `entity upsert · rejects invalid URL` | Negative 422 |
| `entity upsert · keeps distinct paths as distinct entities` | Negative distinct |

## Green

1. Normalizer; test 1.
2. Upsert dedup logic; tests 2–4.

## Refactor gate

Single `normalize_canonical_url()` used by entity upsert and emit preview. Report outcome.

## Verification

```bash
cd apps/api
python -m pytest tests/test_discovery_entity_dedup.py
cd ../.. && ./ci.sh
```

## Out of scope

Cross-catalogue dedup (open seam).

## Git workflow

```bash
git checkout feat/plans-discovery-layer && git pull
git checkout -b feat/discovery-layer-entity-dedup
```

```text
test(api): discovery entity URL dedup

feat(api): deduplicate discovery entities by canonical URL
```

Open PR into `feat/plans-discovery-layer`.
