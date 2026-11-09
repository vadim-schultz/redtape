---
id: C5
depends_on:
  - C0
touches:
  - apps/api/app/features/discovery/repository/candidate_completeness_flags.py
  - apps/api/app/features/discovery/repository/candidate_completeness.py
  - apps/api/app/features/candidates/repository/public_order.py
  - apps/api/tests/test_candidate_completeness.py
  - apps/api/tests/test_candidate_completeness_tags.py
  - docs/operations/candidate-view.md
execution: chapter-implementer
todos:
  - ch05-completeness-decision
---

# Chapter 5 — Completeness decision and parity (M3)

**Suite:** [README](README.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md) · **Ledger:** [../run-ledger.md](../run-ledger.md)
**Decisions:** D-R4 in [../gaps-and-decisions.md](../gaps-and-decisions.md)

**Batch:** B1 or B3, once unblocked · **Execution:** chapter-implementer · **Status:** blocked (D-R4)

## Goal

Record the completeness denominator and pin the public order and the `complete` value with a parity test. The earlier suite moved from five completeness flags to four (`has_category` replaces `has_domain` and `has_situation`) without a recorded decision. This chapter makes that decision explicit.

## Blocked until

- The user confirms D-R4: four flags (default) or five flags.
- Do not start this chapter before that confirmation. The ledger row stays `blocked (D-R4)`.

## Boundaries

- `depends_on`: C0.
- `touches`: the completeness flags and repository, `public_order.py`, the two completeness test files, and `docs/operations/candidate-view.md`.
- Do not change the progress circle or the category tree.
- Do not change public DTO fields other than the completeness disclosure.

## Pre-work (before red)

- Produce a before-and-after ordering report for the fixture set: public order under five flags and under four flags. Record it in the ledger row for C5. The report is the input to the decision.

## Red

- **Happy path:** a parity test pins public order and the `complete` value to a fixture built from the chosen rule. The fixture is generated from the chosen rule's definition, not hand-edited.
- **Negative path:** an invalid `filter[complete]` value still returns 422, and the response names the parameter.

Confirm both fail for the right reason before implementing.

## Green

- If four flags are accepted: record the decision in [../gaps-and-decisions.md](../gaps-and-decisions.md), then update the fixture and `docs/operations/candidate-view.md`.
- If five flags are chosen: restore `has_domain` and `has_situation` as separate checks, and update the fixture and the doc to match.

## Refactor

- None expected. State that in the ledger row. If the refactor audit finds a branch chain in the containing repository class, extract a named unit and re-run the parity test after each step.

## Gate

- Backend: in `apps/api`, `uv run pytest tests/test_candidate_completeness.py tests/test_candidate_completeness_tags.py`, plus ruff and mypy.
- Then `./ci.sh`.
- Record results and the ordering report in [the ledger](../run-ledger.md).
- Corporate build block: [corporate-build-env.md](../../../.cursor/skills/chief-of-staff/corporate-build-env.md).

## Notes

- This chapter can integrate at any point after D-R4 and C0. Its integration position is last among the B3 members in [../01-rollout.md](../01-rollout.md).
- C12 records the decision in the earlier suite's status files.
