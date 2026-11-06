---
id: C7
depends_on:
  - C4
  - C8
touches:
  - apps/discovery-ingest/discovery_ingest/mentions.py
  - apps/discovery-ingest/discovery_ingest/curation.py
  - apps/discovery-ingest/discovery_ingest/extract/llm/evaluation/gold.py
  - apps/discovery-ingest/discovery_ingest/pvog/domain_mapping.py
  - apps/discovery-ingest/discovery_ingest/pvog/situation_mapping.py
  - apps/discovery-ingest/tests/test_pvog_domain_mapping.py
  - apps/discovery-ingest/tests/test_pvog_situation_mapping.py
  - apps/discovery-ingest/tests/fixtures/gold/*.gold.json
execution: chapter-implementer
todos:
  - ch07-ingest-legacy-removal
---

# Chapter 7 — Ingest legacy removal (M6)

**Suite:** [README](README.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md) · **Ledger:** [../run-ledger.md](../run-ledger.md)
**Decisions:** O4 in [../gaps-and-decisions.md](../gaps-and-decisions.md)

**Batch:** B3 · **Execution:** chapter-implementer · **Status:** planned (after C8)

## Goal

Remove the legacy axes from ingest. Mentions, curation, and gold fixtures accept category codes only. The `domain_codes` and `situation_codes` translators, and the legacy PVOG domain and situation code paths, are deleted.

## Preconditions

- C8 is integrated. Its ledger entry shows that no deployed worker sends `domain_codes` or `situation_codes`. If any worker still sends them, this chapter is blocked until that worker is updated or drained.
- C4 is integrated. Leaf mapping reads the fetched crosswalk, not a file.
- C9 is integrated before this chapter. Both edit `test_pvog_situation_mapping.py`.

## Boundaries

- `depends_on`: C4, C8.
- `touches`: `mentions.py`, `curation.py`, `extract/llm/evaluation/gold.py`, `pvog/domain_mapping.py` (deleted), `pvog/situation_mapping.py`, `test_pvog_domain_mapping.py` (deleted), `test_pvog_situation_mapping.py`, and the gold fixtures.
- Do not change the category contract or the API.

## Red

- **Happy path:** mention, curation, and gold inputs accept category codes only, and they produce the same category links as before for the same codes.
- **Negative path (two cases):**
  - `domain_codes` or `situation_codes` in a mentions or curation file fail with a validation error that names the field;
  - the removed modules no longer import (an import test checks this).

## Green

- Delete the `domain_codes` and `situation_codes` translators in `mentions.py` and `curation.py`.
- Delete `pvog/domain_mapping.py` and its test.
- In `situation_mapping.py`, remove the legacy situation-table code path. Leaf mapping reads the crosswalk from C4.
- Convert the gold fixtures with one script. Commit the script's output, not a manual edit.

## Refactor

- One validation path for category codes. Mentions and curation call the same validator.
- Refactor audit: `mentions.py`, `curation.py`, and `situation_mapping.py`, because they share the code-normalisation path.
- Re-run the ingest test set after each extraction.

## Gate

- Ingest: in `apps/discovery-ingest`, `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy discovery_ingest`, and `uv run pytest` for the mentions, curation, gold, and situation tests.
- Then `./ci.sh`.
- Record results in [the ledger](../run-ledger.md).
- Corporate build block: [corporate-build-env.md](../../../.cursor/skills/chief-of-staff/corporate-build-env.md).

## Notes

- Do not start this chapter until C8 is recorded in the ledger (M7).
- C10 widens the reference scan to ingest. It depends on this chapter, so it runs after the removal.
