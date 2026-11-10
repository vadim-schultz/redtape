"""The repair step of the translation core: check an outcome, re-ask once with the broken rules, never loop (search-first C15)."""

from __future__ import annotations

import json

import pytest
from discovery_ingest.translation.adapters.cloudflare_prompt import build_messages
from discovery_ingest.translation.errors import TransientError, UnusableOutputError
from discovery_ingest.translation.repair import Checked, check_outcome, repair_batch, repair_once
from discovery_ingest.translation.units import Correction, TranslationOutcome, TranslationUnit, Usage

from translation_fakes import batch, unit

GOOD = unit("good", "Reisepass beantragen", "Der Reisepass kostet 60 Euro.")
BAD = unit("bad", "Wohnsitz anmelden 3", "Frist: 14 Tage.")
BATCH = batch(GOOD, BAD)


def _outcome(*units: TranslationUnit) -> TranslationOutcome:
    return TranslationOutcome(units, Usage("neurons", 3.0), "m")


def _first() -> TranslationOutcome:
    """The good unit is kept whole; the bad one lost its numbers."""
    return _outcome(
        unit("good", "[en] Reisepass beantragen", "[en] Der Reisepass kostet 60 Euro."),
        unit("bad", "[en] Wohnsitz anmelden", "[en] Frist: Tage."),
    )


class _Repairer:
    """A translator that answers a repair batch with the numbers restored, or raises, and counts its calls."""

    def __init__(self, *, restore: bool = True, error: Exception | None = None) -> None:
        self.restore, self.error = restore, error
        self.batches: list[object] = []

    def translate(self, asked: object) -> TranslationOutcome:
        self.batches.append(asked)
        if self.error is not None:
            raise self.error
        text = "[en] Wohnsitz anmelden 3" if self.restore else "[en] Wohnsitz anmelden"
        return _outcome(unit("bad", text, "[en] Frist: 14 Tage." if self.restore else "[en] Frist: Tage."))


def test_check_outcome_pairs_each_source_with_its_translation_and_the_findings_of_the_validators() -> None:
    """repair · a unit that keeps its numbers is valid; one that loses them carries a finding for each field."""
    checked = check_outcome(BATCH, _first())

    assert [item.valid for item in checked] == [True, False]
    assert checked[1].source == BAD and checked[1].translated.title == "[en] Wohnsitz anmelden"
    assert checked[1].problems() == (
        "title: numbers not preserved: 3",
        "description: numbers not preserved: 14",
    )


@pytest.mark.parametrize(
    "results",
    [(unit("good", "a", "b"),), (unit("bad", "a", "b"), unit("good", "a", "b"))],
    ids=["short", "wrong-order"],
)
def test_an_outcome_that_does_not_answer_every_unit_in_order_is_unusable(results: tuple[TranslationUnit, ...]) -> None:
    """repair · fewer results than units, or the wrong keys, raises UnusableOutputError instead of pairing by luck."""
    with pytest.raises(UnusableOutputError):
        check_outcome(BATCH, _outcome(*results))


def test_the_repair_batch_holds_only_the_failed_units_with_the_rules_they_broke() -> None:
    """repair · the repair request keeps locale and glossary, drops the passing unit and names each broken rule."""
    failed = [item for item in check_outcome(BATCH, _first()) if not item.valid]

    asked = repair_batch(BATCH, failed)

    assert asked.units == (BAD,) and asked.target_locale == "en" and asked.glossary == BATCH.glossary
    assert asked.corrections == (
        Correction("bad", ("title: numbers not preserved: 3", "description: numbers not preserved: 14")),
    )


def test_the_prompt_states_the_violated_rule_only_for_a_repair() -> None:
    """repair · the Workers AI prompt carries the problems of a repair unit; a plain batch prompt is unchanged."""
    failed = [item for item in check_outcome(BATCH, _first()) if not item.valid]

    plain = build_messages(BATCH, "English")
    repair = build_messages(repair_batch(BATCH, failed), "English")

    assert "problems" not in plain[1]["content"] and "previous translation" not in plain[0]["content"]
    units = json.loads(repair[1]["content"])["units"]
    assert units[0]["problems"] == ["title: numbers not preserved: 3", "description: numbers not preserved: 14"]
    assert "previous translation" in repair[0]["content"]


def test_repair_once_asks_once_and_returns_the_rechecked_units() -> None:
    """repair · one repair call for the failed units; a unit that now keeps its numbers is valid."""
    failed = [item for item in check_outcome(BATCH, _first()) if not item.valid]
    translator = _Repairer()

    repaired = repair_once(translator, BATCH, failed)

    assert len(translator.batches) == 1 and [item.valid for item in repaired] == [True]
    assert repaired[0].translated.title == "[en] Wohnsitz anmelden 3"


def test_a_unit_that_still_fails_after_the_repair_is_returned_invalid_and_never_asked_again() -> None:
    """repair · a second failure is final: the unit comes back invalid with its problems, and no third call is made."""
    failed = [item for item in check_outcome(BATCH, _first()) if not item.valid]
    translator = _Repairer(restore=False)

    repaired = repair_once(translator, BATCH, failed)

    assert len(translator.batches) == 1 and [item.valid for item in repaired] == [False]
    assert repaired[0].problems()[0] == "title: numbers not preserved: 3"


def test_an_engine_error_during_the_repair_propagates_for_the_caller_to_settle() -> None:
    """repair · a transient error of the repair call is not swallowed (the drain fails the unit retryably)."""
    failed = [item for item in check_outcome(BATCH, _first()) if not item.valid]

    with pytest.raises(TransientError):
        repair_once(_Repairer(error=TransientError("503")), BATCH, failed)


def test_checked_reports_valid_only_without_findings() -> None:
    """repair · Checked.valid follows the findings, problems() is empty for a valid unit."""
    valid = Checked(GOOD, GOOD, ())

    assert valid.valid and valid.problems() == ()
