"""Translate the tasks of one locale: one prompt, validate, repair the failures once, post what is valid."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from discovery_ingest.translation.errors import TranslationEngineError
from discovery_ingest.translation.glossary import load_glossary
from discovery_ingest.translation.repair import Checked, Translator, check_outcome, repair_once
from discovery_ingest.translation.units import TranslationBatch, TranslationUnit
from discovery_ingest.translation_models import ClaimedTranslationTask
from discovery_ingest.worker.tally import Tally
from discovery_ingest.worker.translate_settle import BatchState, GroupSettler, failure_of

SOURCE_LOCALE = "de"
Tasks = list[ClaimedTranslationTask]


def by_locale(tasks: Sequence[ClaimedTranslationTask]) -> list[Tasks]:
    """Group ``tasks`` by target locale, in the order the locales first appear and each group in claim order."""
    groups: dict[str, Tasks] = {}
    for task in tasks:
        groups.setdefault(task.locale, []).append(task)
    return list(groups.values())


def _batch_of(group: Tasks) -> TranslationBatch:
    units = tuple(TranslationUnit(str(task.task_id), task.title, task.description) for task in group)
    return TranslationBatch(SOURCE_LOCALE, group[0].locale, units, load_glossary(group[0].locale))


@dataclass(frozen=True, slots=True)
class GroupRun:
    """One locale group in flight: the translator, the batch it asks for, its settler and the tally."""

    translator: Translator
    batch: TranslationBatch
    settler: GroupSettler
    tally: Tally


def _translate_group(run: GroupRun) -> None:
    checked = check_outcome(run.batch, run.translator.translate(run.batch))
    run.settler.post([item for item in checked if item.valid])
    failed = [item for item in checked if not item.valid]
    if failed:
        _repair(run, failed)


def _repair(run: GroupRun, failed: list[Checked]) -> None:
    repaired = repair_once(run.translator, run.batch, failed)
    fixed = [item for item in repaired if item.valid]
    run.tally.repaired += len(fixed)
    run.settler.post(fixed)
    run.settler.fail_invalid([item for item in repaired if not item.valid])


def settle_group(translator: Translator, state: BatchState, group: Tasks) -> None:
    """Translate ``group`` (the tasks of one locale) and settle every task it can; engine errors fail the rest."""
    settler = GroupSettler(state, group)
    try:
        _translate_group(GroupRun(translator, _batch_of(group), settler, state.tally))
    except TranslationEngineError as err:
        settler.fail_unfinished(failure_of(err))
