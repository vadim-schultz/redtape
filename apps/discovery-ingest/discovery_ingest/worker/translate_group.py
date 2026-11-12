"""Translate the calls of a batch: one call per locale and at most ``units_per_call`` units, validated, repaired once, settled.

A call runs in a worker thread and touches only the engine. Posting and failing tasks happen afterwards, on the drain's
thread, through :func:`settle_call`, so the API client and the tally are never shared between threads.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from discovery_ingest.translation.errors import TranslationEngineError
from discovery_ingest.translation.glossary import load_glossary
from discovery_ingest.translation.repair import Checked, Translator, check_outcome, repair_once
from discovery_ingest.translation.units import TranslationBatch, TranslationUnit
from discovery_ingest.translation_models import ClaimedTranslationTask
from discovery_ingest.worker.stop import StopDrain
from discovery_ingest.worker.translate_settle import BatchState, GroupSettler, failure_of

SOURCE_LOCALE = "de"
Tasks = list[ClaimedTranslationTask]


def by_locale(tasks: Sequence[ClaimedTranslationTask]) -> list[Tasks]:
    """Group ``tasks`` by target locale, in the order the locales first appear and each group in claim order."""
    groups: dict[str, Tasks] = {}
    for task in tasks:
        groups.setdefault(task.locale, []).append(task)
    return list(groups.values())


def by_call(tasks: Sequence[ClaimedTranslationTask], units_per_call: int) -> list[Tasks]:
    """Cut each locale's tasks, in claim order, into calls of at most ``units_per_call`` units."""
    return [
        group[start : start + units_per_call]
        for group in by_locale(tasks)
        for start in range(0, len(group), units_per_call)
    ]


def batch_of(group: Tasks) -> TranslationBatch:
    """Return the translation request for one call: its units and the glossary of their locale."""
    units = tuple(TranslationUnit(str(task.task_id), task.title, task.description) for task in group)
    return TranslationBatch(SOURCE_LOCALE, group[0].locale, units, load_glossary(group[0].locale))


@dataclass(frozen=True, slots=True)
class CallResult:
    """What one call came to: every unit checked, the repairs that worked, and any error or stop that ended a repair.

    A unit still invalid after its repair is listed as checked; when a repair errored, those units fail with that error.
    """

    checked: tuple[Checked, ...]
    repaired: int = 0
    repair_failure: TranslationEngineError | StopDrain | None = None


def translate_call(translator: Translator, batch: TranslationBatch) -> CallResult:
    """Translate ``batch`` in one call, validate it and repair the failed units once, if the engine can repair.

    An error of the first call propagates: nothing of it is usable. An error of the repair is kept, so the units that
    were already valid can still be posted. An engine that cannot repair is not asked again: its invalid units are
    returned as they are and fail when settled.
    """
    checked = check_outcome(batch, translator.translate(batch))
    failed = [item for item in checked if not item.valid]
    if not failed or not translator.repairs:
        return CallResult(tuple(checked))
    try:
        repaired = repair_once(translator, batch, failed)
    except (TranslationEngineError, StopDrain) as err:
        return CallResult(tuple(checked), repair_failure=err)
    return CallResult(_with_repairs(checked, repaired), repaired=sum(item.valid for item in repaired))


def _with_repairs(checked: list[Checked], repaired: list[Checked]) -> tuple[Checked, ...]:
    """Put each repaired unit in the place of the translation it repaired."""
    by_key = {item.source.key: item for item in repaired}
    return tuple(by_key.get(item.source.key, item) for item in checked)


def settle_call(state: BatchState, group: Tasks, answer: CallResult) -> None:
    """Post the valid units of a call, then settle the rest.

    A stop is raised, so the rest is released; an error fails the rest with its category; no error fails the invalid
    units after their repair.
    """
    settler = GroupSettler(state, group)
    settler.post([item for item in answer.checked if item.valid])
    state.tally.repaired += answer.repaired
    failure = answer.repair_failure
    if isinstance(failure, StopDrain):
        raise failure
    if failure is not None:
        settler.fail_unfinished(failure_of(failure))
    else:
        settler.fail_invalid([item for item in answer.checked if not item.valid])


def settle_failed_call(state: BatchState, group: Tasks, err: TranslationEngineError) -> None:
    """Fail the tasks of a call the engine could not translate, retryably or not as the error says."""
    GroupSettler(state, group).fail_unfinished(failure_of(err))
