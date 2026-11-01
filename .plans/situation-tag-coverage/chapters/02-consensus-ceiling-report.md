---
name: "Chapter 2 — Consensus ceiling report"
overview: "A tested pure function (plus a thin script) that reports what share of discovery candidates could ever clear the 2-procedure consensus floor, independent of model accuracy."
todos:
  - id: module
    content: "Add consensus_ceiling.py with procedure_counts_by_candidate and consensus_ceiling"
    status: pending
  - id: script
    content: "Add the scripts/consensus_ceiling_report.py CLI entry point"
    status: pending
  - id: tests
    content: "Add fixture-style tests for the pure function, independent of any database"
    status: pending
isProject: false
---

# Chapter 2 — Consensus ceiling report

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/situation-tag-coverage-consensus-ceiling-report` · **Status:** planned

**Depends on:** none · **Decisions:** X8 (`.plans/extraction/gaps-and-decisions.md`) — the axis-blind 2-procedure consensus rule this chapter measures; S2 (`.plans/situation-tag-coverage/00-architecture.md` §4) — "measure the consensus ceiling" · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-situation-tag-coverage`

## Goal

Build a small, tested function that reports, across all discovery candidates, how many distinct procedures (`catalogue_service_id`) mention each one, and summarises what share have at least 2 distinct procedures — the consensus floor `tags.py`'s `DEFAULT_MIN_PROCEDURES` imposes — versus exactly 1 or 0. This proves (or disproves) that the consensus rule itself, not model accuracy, is the structural blocker for the situation axis: a candidate mentioned by fewer than 2 distinct procedures cannot clear the floor on *any* axis no matter what the model says about it. Running this against production data is this suite's live run LR2 (`../02-live-runs.md`), not part of this chapter's own test gate.

## Design

Read first: `apps/api/app/features/discovery/tags.py` (`DEFAULT_MIN_PROCEDURES = 2`, line 10; `_procedures_by_code`, lines 31-36 — the private helper this chapter's public function mirrors at the candidate level instead of the code level), `candidate_tags.py` (how `TaggedMention`/`ProvenancedMention` plain-data tuples are already the house pattern for passing mention data into pure functions), and the `DiscoveryCandidateMention` model (`apps/api/app/models/discovery/discovery_candidate_mention.py`, lines 36-44: `candidate_id` and `catalogue_service_id`, both `Mapped[uuid.UUID]`, each a foreign key — exactly the two columns this chapter counts).

**New module: `apps/api/app/features/discovery/consensus_ceiling.py`.**

```python
CandidateMention = tuple[UUID, UUID]
"""A mention as plain data: the candidate it was found on and the procedure (catalogue row) that carries it."""


class ConsensusCeiling(NamedTuple):
    """How many of all candidates have enough distinct procedures to ever clear the consensus floor."""

    total_candidates: int
    at_or_above_floor: int
    exactly_one: int
    zero: int

    @property
    def share_at_or_above_floor(self) -> float: ...
    @property
    def share_exactly_one(self) -> float: ...
    @property
    def share_zero(self) -> float: ...


def procedure_counts_by_candidate(mentions: Iterable[CandidateMention]) -> dict[UUID, int]:
    """Return the number of distinct procedures that mention each candidate, counting each procedure once."""


def consensus_ceiling(
    candidate_ids: Collection[UUID],
    mentions: Iterable[CandidateMention],
    *,
    min_procedures: int = DEFAULT_MIN_PROCEDURES,
) -> ConsensusCeiling:
    """Return how many of candidate_ids have at least min_procedures distinct procedures mentioning them."""
```

`min_procedures` defaults to `tags.py`'s `DEFAULT_MIN_PROCEDURES` (imported, not duplicated), so the ceiling always reports against the same floor `aggregate_tags` actually enforces, never a value that could silently drift from it.

This follows `TagSupport`'s own shape in `tags.py` (a `NamedTuple` of counts plus derived properties) rather than inventing a new convention, and mirrors `candidate_tags.py`'s `TaggedMention`/`ProvenancedMention` pattern of passing plain `tuple[UUID, ...]` data into a pure function instead of ORM rows — the same separation `apps/api/scripts/measure_code_rules.py` uses between `measure_file` (does file IO) and `summarise(reports: Iterable[FileReport], ...)` (pure, unit-tested without touching a filesystem). Here the DB-touching half is the script below; `consensus_ceiling` and `procedure_counts_by_candidate` never import `sqlalchemy` or see a session, so this chapter's test gate needs no database.

`candidate_ids` is taken as its own parameter — the full universe of candidate ids — rather than inferred from `mentions`, because a candidate with zero mentions (an orphaned or not-yet-mentioned row) cannot otherwise be told apart from "didn't happen to appear in this particular call's data"; passing the universe explicitly is what lets `zero` mean something real instead of always being 0 by construction.

**New script: `apps/api/scripts/consensus_ceiling_report.py`**, following `seed_taxonomy.py`'s convention exactly (docstring states the invocation, a `main()` with a `with SessionLocal() as session:` block, no `session.commit()` needed since this script only reads):

```python
"""Report the consensus ceiling over production discovery candidates (chapter 2, situation-tag-coverage, LR2).

Run from `apps/api`:
  python -m scripts.consensus_ceiling_report
"""

def _candidate_ids(session: Session) -> list[uuid.UUID]:
    return list(session.scalars(sa.select(DiscoveryDocumentCandidate.id)))


def _mentions(session: Session) -> list[tuple[uuid.UUID, uuid.UUID]]:
    return list(
        session.execute(
            sa.select(DiscoveryCandidateMention.candidate_id, DiscoveryCandidateMention.catalogue_service_id)
        )
    )


def main() -> None:
    with SessionLocal() as session:
        ceiling = consensus_ceiling(_candidate_ids(session), _mentions(session))
    print(
        f"consensus ceiling: {ceiling.total_candidates} candidates, "
        f"{ceiling.at_or_above_floor} ({ceiling.share_at_or_above_floor:.1%}) at or above the floor, "
        f"{ceiling.exactly_one} ({ceiling.share_exactly_one:.1%}) at exactly one procedure, "
        f"{ceiling.zero} ({ceiling.share_zero:.1%}) at zero"
    )


if __name__ == "__main__":
    main()
```

The script is deliberately thin: two `SELECT`s and one print, no business logic duplicated from `consensus_ceiling.py`. Running it against the real database (`python -m scripts.consensus_ceiling_report` from `apps/api`) is LR2, executed once all five chapters of this suite are built (per `../01-rollout.md`'s invariant 4), not part of this chapter's own verification.

## Tests

New file: `apps/api/tests/test_consensus_ceiling.py`, following `test_discovery_tags.py`'s fixture style exactly (`C1, C2, C3, C4 = (uuid.uuid4() for _ in range(4))` for candidates, `P1, P2, P3` for procedures — plain tuples, no database, no model instances):

- `test_procedure_counts_by_candidate_counts_distinct_procedures_not_mentions` — `mentions = [(C1, P1), (C1, P1), (C1, P2), (C2, P1)]`; assert `procedure_counts_by_candidate(mentions) == {C1: 2, C2: 1}` (the repeated `(C1, P1)` mention counts once, mirroring `tags.py`'s own `test_aggregate_counts_distinct_procedures_not_mentions`).
- `test_consensus_ceiling_buckets_candidates_by_whether_they_can_ever_clear_the_floor` — `C1` has 2 distinct procedures, `C2` has 1, `C3` has 3, `C4` has none; assert `consensus_ceiling([C1, C2, C3, C4], mentions) == ConsensusCeiling(total_candidates=4, at_or_above_floor=2, exactly_one=1, zero=1)`.
- `test_a_candidate_absent_from_mentions_counts_as_zero_not_as_a_missing_key` — `consensus_ceiling([C1, C4], [(C1, P1), (C1, P2)])`; assert `(ceiling.at_or_above_floor, ceiling.zero) == (1, 1)` — `C4` never appears in `mentions` at all and must still be counted, which is exactly why `candidate_ids` is a separate parameter.
- `test_consensus_ceiling_shares_divide_by_the_full_candidate_universe` — same four-candidate, one-tagged-candidate setup; assert `ceiling.share_at_or_above_floor == pytest.approx(0.25)` and `ceiling.share_zero == pytest.approx(0.75)`.
- `test_an_empty_candidate_universe_has_full_shares_not_a_division_by_zero` — `consensus_ceiling([], []) == ConsensusCeiling(0, 0, 0, 0)` and all three share properties return `0.0`/`1.0` without raising (mirrors `metrics.py`'s own no-items-is-a-full-rate convention, adapted: here there is nothing to report, so the shares are defined as empty rather than vacuously "agreeing").
- `test_the_default_floor_is_two_procedures_matching_tags_pys_consensus_rule` — `consensus_ceiling([C1], [(C1, P1), (C1, P2)]).at_or_above_floor == 1` and `consensus_ceiling([C1], [(C1, P1)]).at_or_above_floor == 0` with `.exactly_one == 1` on the second — pins the default to `DEFAULT_MIN_PROCEDURES` without re-importing it, so a future change to that constant's value in `tags.py` would be caught here too.

Red: all of the above fail today — `app.features.discovery.consensus_ceiling` does not exist. Green: after the module is written as designed; no fixture needs a database, a candidate mention row, or any other ORM object.

## Verification

```bash
cd apps/api && ./ci.sh
pytest tests/test_consensus_ceiling.py -v
```

Running the script itself (`python -m scripts.consensus_ceiling_report` against a real database) is LR2, deliberately out of this chapter's own gate — this chapter is done when the pure function and its tests are green, regardless of what production data later shows.

## Refactor gate

Check that `consensus_ceiling.py` imports `DEFAULT_MIN_PROCEDURES` from `tags.py` rather than redefining `2` as a local literal, and that the script has no logic beyond the two queries and the print — any bucketing or percentage math belongs in the tested module, not the script.

## Commits

- `feat(api): add the consensus ceiling report for discovery candidate mentions`

## Out of scope

Running the report against production (LR2, executed once per `../01-rollout.md`'s invariant 4, after all five chapters are merged); changing `DEFAULT_MIN_PROCEDURES` or any consensus behaviour (that is S4/chapter 4's territory, pending T-PENDING); per-axis ceilings (this chapter is deliberately axis-blind — it reports the ceiling either axis is bound by, since the underlying mention count is the same regardless of which axis's codes are being counted).
