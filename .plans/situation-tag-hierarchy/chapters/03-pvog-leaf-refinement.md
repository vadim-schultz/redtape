---
name: "Chapter 3 — PVOG leaf refinement and domain-hint recovery"
overview: "Extend the already-shipped PVOG situation signal three ways: pair each of the 32 mapped leaves with a mapping-clarity weight so chapter 1's scoring can use it; recover a domain-axis hint for 14 of the 24 unmapped citizen leaves that are domain-shaped rather than situation-shaped; and thread the raw leaf code itself through to the published document as an optional, non-empty-only refinement facet."
todos:
  - id: step-0
    content: "Human spot-check of the new 14-leaf domain-hint table before it ships (new, not previously reviewed)"
    status: pending
  - id: clarity-table
    content: "Add PERSONAL_MATTER_CLARITY (32 entries, 0.95 clean / 0.65 ambiguous) to situation_mapping.py"
    status: pending
  - id: domain-hint-table
    content: "Add domain_mapping.py: PERSONAL_MATTER_TO_DOMAIN (14 entries) + flat 0.8 clarity"
    status: pending
  - id: harvest-threading
    content: "Thread leaf code, situation confidence, domain codes/confidence into MentionDraft via _draft()"
    status: pending
  - id: mention-draft-fields
    content: "Add direct_situation_confidence, direct_domain_confidence, pvog_leaf_code to MentionDraft"
    status: pending
  - id: leaf-column
    content: "Migration: nullable pvog_leaf_code on document_life_situation (depends on chapter 1's confidence column)"
    status: pending
  - id: payload-threading
    content: "Add NewDocumentPayload.situation_leaf_codes; thread through suggested_tags()/_resolve_tags()/_link_terms()"
    status: pending
  - id: tests
    content: "Table shape/key-parity tests, harvest threading tests, payload validator test, persistence test"
isProject: false
---

# Chapter 3 — PVOG leaf refinement and domain-hint recovery

**Repo:** `redtape` (`apps/discovery-ingest`, plus the small `apps/api` seam already used by the PVOG signal) · **Branch:** `feat/situation-tag-hierarchy-pvog-leaf-refinement` · **Status:** planned — domain-hint half blocked on Step 0

**Depends on:** Chapter 1 ([01-confidence-scoring-engine.md](01-confidence-scoring-engine.md)) — the `direct_situation_confidence`/`direct_domain_confidence` mention columns this chapter populates, and the `document_life_situation.confidence` migration this chapter's own migration follows · **Decisions:** D4 (`../gaps-and-decisions.md`) — PVOG ships now, as committed scope · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-situation-tag-hierarchy`

**Correction to the rollout's dependency graph:** this chapter has a real schema dependency on chapter 1 (both touch `document_life_situation`), so it is *not* parallel with chapter 1 the way the original design session assumed — see `../gaps-and-decisions.md` D10.

## Blocking prerequisite — Step 0, domain-hint table only

The mapping-clarity weights (below) annotate leaves PVOG's own `lr3-personal-matters-mapping.md` sign-off (T4, `situation-tag-coverage/gaps-and-decisions.md`) already reviewed — only the two numeric weights (0.95/0.65) are new, and those are tunable later via chapter 5, not gated here. The **domain-hint table is different: it has never been reviewed by anyone**, AI or human — it is this chapter's own first pass. Per house convention (the same Step 0 the precedent PVOG chapter required), **the domain-hint half of this chapter may not ship until a human spot-checks it**, recorded in `../gaps-and-decisions.md`. The situation-axis work (clarity weights, leaf-refinement facet) is not blocked by this and may ship independently.

## Goal

Three extensions to the already-shipped PVOG situation signal (`situation-tag-activation` chapter 3):

1. Pair each of the 32 `PERSONAL_MATTER_TO_SITUATION` leaves with a mapping-clarity weight, so chapter 1's scoring engine can treat a clean leaf's assertion as more confident than an ambiguous one.
2. Recover a `domain_codes` hint for the domain-shaped subset of the 24 currently-unmapped citizen leaves, so a PVOG-catalogued procedure that gets nothing at all on the situation axis can still contribute to the domain axis.
3. Thread the raw PVOG leaf code (already discovered and already stashed as `_personal_matter_code`, per the existing `map_pvog_record()`) one step further than today — through the mention and onto the published document — as an optional, non-empty-only refinement facet under a situation.

## Design

**Mapping-clarity weights**, `apps/discovery-ingest/discovery_ingest/pvog/situation_mapping.py`: add `PERSONAL_MATTER_CLARITY: dict[str, float]`, the same 32 keys as `PERSONAL_MATTER_TO_SITUATION`, `0.95` for the 18 leaves `lr3-personal-matters-mapping.md` marks "clean", `0.65` for the 14 marked "ambiguous" — citing that table's verdict column directly rather than re-judging it. A key-parity test (below) keeps the two tables from drifting apart.

**Domain-hint recovery**, new `apps/discovery-ingest/discovery_ingest/pvog/domain_mapping.py`: `PERSONAL_MATTER_TO_DOMAIN: dict[str, list[str]]`, 14 entries recovering the domain-shaped subset of the 24 unmapped citizen leaves:

| Domain | Leaves |
| --- | --- |
| `taxes-finance` | `1060100`, `1060200`, `1060300`, `1060800` |
| `identity-civil-status` | `1070100`, `1070200` |
| `law-justice` | `1150100`, `1150200`, `1150300`, `1150400` |
| `social-benefits` | `1160100`, `1160200` |
| `education` | `1040100` |
| `family-children` | `1020200` |

The remaining 10 unmapped citizen leaves (civic engagement `1100100`/`1100200`, hobbies `1110100`–`1110300`, travel `1120100`–`1120300`, environment `1170100`/`1170200`) have no clean analogue among the 13 existing domains and stay unmapped — not forced into a bucket they don't fit. `PERSONAL_MATTER_DOMAIN_CLARITY: dict[str, float]` gives all 14 a flat `0.8` — lower than the situation axis's reviewed `0.95`, reflecting that this table is a first pass pending Step 0, not yet human-confirmed.

**Harvest threading**, `apps/discovery-ingest/discovery_ingest/harvest/pvog.py`: add `_situation_confidence(raw_payload) -> float | None` (reads `_personal_matter_code` through `PERSONAL_MATTER_CLARITY`), `_domain_codes`/`_domain_confidence(raw_payload)` (through the new domain-mapping table), and `_leaf_code(raw_payload) -> str | None` (the bare `_personal_matter_code`, exposed under its own name since it's no longer only an internal stash — it's now a value other code reads directly). Thread all four into `_draft()` alongside the existing `_situation_codes()` call.

**`MentionDraft`**, `apps/discovery-ingest/discovery_ingest/mentions.py`: add `direct_situation_confidence: float | None`, `direct_domain_confidence: float | None`, `pvog_leaf_code: str | None` — the same `Field(default=None)` shape the existing `domain_codes`/`situation_codes` fields already use. `_items()` in `worker/harvest.py` needs no change, per the existing confirmed `model_dump()` unpack (`situation-tag-activation/00-architecture.md §3`) — any field added to `MentionDraft` flows through automatically, the same guarantee that chapter relied on.

**Persisting the leaf code onto the document.** The facet only matters if it survives promotion. `apps/api/app/schema/suggestion/payload.py::NewDocumentPayload`: add `situation_leaf_codes: dict[str, str] | None = None` (situation code → leaf code, only present for codes that came from a PVOG mention), validated the same way `tag_confidence`'s keys already are (must be a subset of `situation_codes`). `apps/api/app/features/discovery/candidate_emit_payload.py::suggested_tags()`/`new_document_payload()`: thread the leaf code from whichever mention supplied a given situation code's `direct_situation_confidence` (when more than one PVOG mention asserts the same code with different leaves — rare, not observed in production per the prior suite's near-zero PVOG/LLM overlap finding — take the first, deterministically sorted). `apps/api/app/models/taxonomy.py`: new Alembic migration adding `pvog_leaf_code: str | None` (nullable) to `document_life_situation` only — not `document_domain`, since the refinement facet is situation-only (§ "Out of scope"). `DocumentService._resolve_tags()`/`DocumentRepository._link_terms()`: thread an optional `{id: leaf_code}` map alongside the existing confidence map, written into the new column at the same insert.

## Tests

- `PERSONAL_MATTER_CLARITY` key-parity test: exactly the same key set as `PERSONAL_MATTER_TO_SITUATION`, every value one of `{0.95, 0.65}`.
- `PERSONAL_MATTER_TO_DOMAIN`/`PERSONAL_MATTER_DOMAIN_CLARITY`: 14 entries, every value a known domain code, no key overlapping `PERSONAL_MATTER_TO_SITUATION` by coincidence (the two mappings are allowed to be disjoint or overlapping — a leaf can recover both a situation and a domain hint — just confirm neither table silently drops a leaf the other expects).
- `harvest_pvog_payload()`: a clean-leaf payload's `MentionDraft` carries `direct_situation_confidence=0.95` and the right `pvog_leaf_code`; an ambiguous bundled leaf carries `0.65` on both emitted situation codes; a domain-hint-only leaf (no situation mapping) carries `direct_domain_confidence=0.8` and no situation codes at all; a leaf in neither table carries nothing on either axis, as today.
- `NewDocumentPayload` validator test: a `situation_leaf_codes` key not present in `situation_codes` is rejected.
- `DocumentRepository._link_terms()`/promotion test: the leaf code round-trips onto the `document_life_situation` row.

## Verification

```bash
cd apps/discovery-ingest && ./ci.sh
cd apps/api && ./ci.sh
```

## Refactor gate

Confirm `grep -rn "_personal_matter_code" apps/discovery-ingest` shows it read in exactly the four `_*()` helpers above, not duplicated inline anywhere else.

## Commits

- `feat(discovery-ingest): pair the PVOG situation mapping with a mapping-clarity weight`
- `feat(discovery-ingest): recover a domain-axis hint for 14 of the 24 unmapped PVOG citizen leaves`
- `feat(discovery-ingest,api): thread the PVOG leaf code through to the published document's situation tags`

## Out of scope

Leaf refinement on the domain axis (the facet is situation-only; a domain hint only ever contributes to scoring, never to a browsable facet); the remaining 10 unmapped citizen leaves (no clean domain fits); any UI rendering of the facet (chapter 4); the group taxonomy (chapter 2); growing the 18-code situation taxonomy to match PVOG's 56 (still out of scope per `situation-tag-activation` T2, unchanged by this chapter).
