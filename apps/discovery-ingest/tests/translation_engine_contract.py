"""The adapter conformance suite: every registered translation engine must pass every check before it can be selected.

Each check takes an :class:`AdapterHarness` (a real adapter over a fake transport) and raises ``AssertionError`` when the
adapter breaks the contract. ``test_translation_registry.py`` runs them over the registry; a deliberately broken fake
proves they fail when they should.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

import pytest
from discovery_ingest.translation.errors import (
    PermanentError,
    QuotaExceeded,
    TransientError,
    TranslationEngineError,
    Unauthorised,
    UnusableOutputError,
)
from discovery_ingest.translation.locale_codes import DEFAULT_TARGET_LOCALES, provider_code
from discovery_ingest.translation.metered import MeteredTranslator
from discovery_ingest.translation.units import TranslationBatch
from discovery_ingest.translation.validate import token_findings

from translation_fakes import RecordingMeter, batch, unit
from translation_harnesses import FAILURES, AdapterHarness, Behaviour

SAMPLE = batch(
    unit(
        "a",
        "Antrag nach § 35 SGB II",
        "Gebühr 12,50 Euro bis 01.03.2025 unter https://example.org/antrag?x=1, Nr. {case_id}.",
    ),
    unit("b", "Bürgeramt Mitte", ""),
    unit("c", "Wohngeld", "Art. 5 Abs. 2 gilt nicht für 3 Monate."),
)

ERROR_CATEGORIES: dict[Behaviour, type[TranslationEngineError]] = {
    Behaviour.QUOTA: QuotaExceeded,
    Behaviour.TRANSIENT: TransientError,
    Behaviour.UNAUTHORISED: Unauthorised,
    Behaviour.PERMANENT: PermanentError,
}


def _translate(harness: AdapterHarness, behaviour: Behaviour = Behaviour.FAITHFUL, what: TranslationBatch = SAMPLE):  # noqa: ANN202
    return harness.build(behaviour).translate(what)


def one_result_per_unit_in_order(harness: AdapterHarness) -> None:
    """The outcome has exactly one result per unit, in the order of the batch."""
    outcome = _translate(harness)

    assert [result.key for result in outcome.results] == [source.key for source in SAMPLE.units]


def a_short_response_is_an_error(harness: AdapterHarness) -> None:
    """A provider answer with fewer units than asked raises an unusable-output error; nothing is dropped silently."""
    with pytest.raises(UnusableOutputError):
        _translate(harness, Behaviour.SHORT)


def tokens_survive_a_faithful_round_trip(harness: AdapterHarness) -> None:
    """Placeholders, numbers, dates, URLs and legal citations of the source are all in the translation."""
    outcome = _translate(harness)

    for source, result in zip(SAMPLE.units, outcome.results, strict=True):
        assert token_findings(source.title, result.title) == []
        assert token_findings(source.description, result.description) == []


def every_target_locale_maps(harness: AdapterHarness) -> None:
    """The engine has a provider code for every target locale."""
    for locale in DEFAULT_TARGET_LOCALES:
        assert provider_code(harness.name, locale)


def usage_is_in_the_declared_unit_and_settles_on_actuals(harness: AdapterHarness) -> None:
    """The outcome and the estimate use the engine's unit, and the drain settles the reservation with the actual usage."""
    engine, meter = harness.build(Behaviour.FAITHFUL), RecordingMeter()

    outcome = MeteredTranslator(engine, meter).translate(SAMPLE)

    assert outcome.usage.unit == engine.usage_unit == engine.estimate(SAMPLE).unit
    assert outcome.usage.amount > 0
    assert meter.settled == [outcome.usage]


def failures_map_to_the_drain_categories(harness: AdapterHarness) -> None:
    """Quota, transient, unauthorised and permanent provider failures raise their own category."""
    for behaviour in FAILURES:
        with pytest.raises(ERROR_CATEGORIES[behaviour]):
            _translate(harness, behaviour)


def the_secret_never_appears_in_errors_or_logs(harness: AdapterHarness, caplog: pytest.LogCaptureFixture) -> None:
    """No error message, traceback text or log record contains the provider secret."""
    caplog.set_level(logging.DEBUG)
    for behaviour in FAILURES:
        with pytest.raises(TranslationEngineError) as raised:
            _translate(harness, behaviour)
        assert harness.secret not in str(raised.value)
        assert harness.secret not in repr(raised.value)
    assert harness.secret not in caplog.text


CONTRACT: tuple[Callable[..., None], ...] = (
    one_result_per_unit_in_order,
    a_short_response_is_an_error,
    tokens_survive_a_faithful_round_trip,
    every_target_locale_maps,
    usage_is_in_the_declared_unit_and_settles_on_actuals,
    failures_map_to_the_drain_categories,
    the_secret_never_appears_in_errors_or_logs,
)
"""Every check; the log check also takes ``caplog``."""


def run_contract_check(harness: AdapterHarness, check: Callable[..., None], caplog: pytest.LogCaptureFixture) -> None:
    """Run one check; the log check also gets ``caplog``."""
    if check is the_secret_never_appears_in_errors_or_logs:
        check(harness, caplog)
    else:
        check(harness)


def run_contract(harness: AdapterHarness, caplog: pytest.LogCaptureFixture) -> None:
    """Run every check against ``harness``; the first broken promise raises ``AssertionError``."""
    for check in CONTRACT:
        run_contract_check(harness, check, caplog)
