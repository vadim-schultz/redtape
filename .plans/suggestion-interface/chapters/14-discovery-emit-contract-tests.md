---
name: "Chapter 14 — Discovery emit contract tests"
overview: "Staging claim mapper output validates as SuggestionCreate / payload schemas."
isProject: false
---

# Chapter 14 — Discovery emit contract tests

**Status:** shipped (discovery bridge)

**Depends on:** [02-new-document-payload-schema.md](02-new-document-payload-schema.md)

## Goal

Lock the boundary between `discovery_claim` payloads and the public suggestion API before discovery ch.18 emit ships.

## Delivered

- `app/schema/discovery/claim_payload.py` — claim payload models.
- `app/features/discovery/emit_mapper.py` — `claim_to_create_body`.
- `tests/test_discovery_suggestion_contract.py`.
