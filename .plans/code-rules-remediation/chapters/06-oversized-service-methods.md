---
name: "Chapter 6 — Oversized service methods"
overview: "Re-measure with a script, then shrink the remaining over-limit classes and methods; add strict types and docstrings to touched code."
todos:
  - id: measure
    content: "Script that reports class lines, method lines, and parameter counts for apps/api/app"
    status: pending
  - id: shrink
    content: "Extract helpers from the worst offenders"
    status: pending
  - id: types-docs
    content: "No Any/object in annotations; docstrings on public symbols touched"
    status: pending
isProject: false
---

# Chapter 6 — Oversized service methods

**Repo:** `redtape` · **Branch:** `refactor/oversized-service-methods` · **Status:** planned

**Depends on:** chapters 2, 4, 5 · **Architecture:** [../00-architecture.md](../00-architecture.md) B6 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-code-rules-remediation` · **Release branch:** `main`

## Goal

After chapters 1-5, shrink what is still over the limits. The audit counts below were read by eye; the first task is a measuring script that gives real numbers (decision D9).

## Audit starting point (verify with the script)

Classes over about 100 lines: `DocumentService` (`documents/service.py:46`, 187), `SuggestionService` (`suggestions/service.py:98`, 154), `DiscoveryMachineService` (`discovery/service.py:243`, 145), `DocumentRepository` (`documents/repository.py:24`, 133), `OpenPLZClient` (`app/services/openplz_client.py:39`, 131), `DiscoveryEmitService` (`discovery/emit.py:35`, 107).

Longest methods: `_emit_one_claim` (`emit.py:101`, 33), `get_document_detail` (`documents/service.py:159`, 31), `DiscoveryMachineService.append_claim` (`service.py:333`, 30), `emit_catalogue` (`emit.py:42`, 29), `build_emit_preview_items` (`emit_preview.py:59`, 27), `claim_to_suggestion_payload` (`emit_preview.py:22`, 27), `apply_fanout_for_service` (`fanout.py:67`, 24). Also module-level helpers in `service.py` that take `repo` (`_enqueue_tasks_for_service`, `_claim_pending_tasks`) belong on a collaborator.

Duplication: the four `_fetch_log_dict`, `_entity_dict`, `_claim_dict`, `_event_dict` helpers (`service.py:69-110`) repeat one mapping shape that read schemas already provide as `from_row`.

## Files

- `apps/api/scripts/measure_code_rules.py` (new; reports per class lines, per method lines, parameter counts; exits 0, informational) plus a short test.
- The modules above.

## TDD loop

### Red

1. Measuring script test: given a small fixture module, the script reports the expected class and method sizes (happy path) and fails clearly on unparsable input (negative path).
2. Per refactored unit: characterization tests exist before editing (pin behaviour; most already exist for documents and suggestions). Add the missing happy and negative pair where a unit has none.

### Green

Extract named helpers or collaborators, one unit at a time, rerunning the narrow suite after each extraction. Use `from_row` instead of the `_xxx_dict` helpers. Move the module-level `repo` helpers onto a service or collaborator. Keep each commit to one unit.

### Refactor

For every touched class: about 100 lines, methods about 5 lines, at most 3 parameters, rule of three (total arms), no boolean flags. Replace any `Any` or `object` annotations in touched code, add docstrings (ruff pydocstyle) to public symbols. Report the script's before and after totals: classes over 100 lines, methods over 5 lines, methods over 3 parameters. Record any exceptions with a reason (for example thin glue).

## Verification

```bash
cd apps/api
uv run python scripts/measure_code_rules.py
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
uv run pytest
cd ../..
./ci.sh
```

## Git workflow

```bash
git checkout feat/plans-code-rules-remediation && git pull
git checkout -b refactor/oversized-service-methods
```

```text
chore(api): add a script that measures class and method sizes
refactor(api): extract helpers from the longest service and emit methods
```

Open the chapter PR into `feat/plans-code-rules-remediation`, not `main`. If the unit list is too large for one PR, split into several PRs against the loop branch and note them in the final report.
