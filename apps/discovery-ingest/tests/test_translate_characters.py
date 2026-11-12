"""translate drain · an azure-translator run is metered on azure_translator_chars: it settles to the billed characters, reports
them and never touches the neuron ledger; a 403001 stops it cleanly."""

from __future__ import annotations

import pytest
from discovery_ingest.operations.translate_drain import TranslateOptions, run_translate
from discovery_ingest.schemas import DrainReport
from discovery_ingest.translation.character_meter import CharacterMeter
from discovery_ingest.translation.settings import TranslationSettings
from discovery_ingest.translation.subscription_meter import SubscriptionMeter
from discovery_ingest.worker.translate_meter import own_meters_for

from azure_transport import failure as azure_failure
from azure_transport import faithful_answer
from ledger_fakes import CHARACTERS, CHARACTERS_CAP, FakeLedger, guard_for
from translate_fakes import Handler, TranslateApi, task, task_id

BILLED = 1000.0
"""What the service reports for the call, deliberately not the characters that were sent."""


@pytest.fixture(autouse=True)
def _azure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_TRANSLATOR_KEY", "azure-key-SECRET-0123456789")
    monkeypatch.setenv("AZURE_TRANSLATOR_REGION", "westeurope")
    monkeypatch.setattr("discovery_ingest.operations.translate_drain.TRANSLATE_MIN_INTERVAL_SECONDS", 0.0)


def _api() -> TranslateApi:
    queue = [task(number, "tr") for number in range(4)]
    return TranslateApi(queue, ledger=FakeLedger(9000.0, characters=float(CHARACTERS_CAP)))


def _run(monkeypatch: pytest.MonkeyPatch, api: TranslateApi, azure: Handler, *, max_batches: int = 5) -> DrainReport:
    api.install(monkeypatch, azure=azure)
    settings = TranslationSettings.model_validate({"TRANSLATION_ENGINE": "azure-translator"})
    return run_translate(TranslateOptions(max_batches=max_batches), settings, api.client())


def test_an_azure_translator_run_settles_to_the_billed_characters_and_reports_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Drain · an azure-translator run writes azure_translator_chars and reports characters_used, and never touches the neuron ledger."""
    api = _api()

    report = _run(monkeypatch, api, lambda request: faithful_answer(request, metered=BILLED))

    assert (report.stop_reason, report.succeeded, report.completed) == ("queue_empty", True, 4)
    assert report.characters_used == BILLED
    assert api.ledger.characters is not None and api.ledger.characters.remaining == CHARACTERS_CAP - BILLED
    assert "reserve" in api.ledger.writes_to(CHARACTERS)
    assert api.ledger.writes_to("neurons") == []
    assert (report.neurons_used, report.tokens_used) == (0.0, 0)


def test_a_403001_exhausts_the_monthly_ledger_once_releases_the_batch_and_fails_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Drain · a 403001 calls exhaust once, releases the batch and leaves attempt_count unchanged."""
    api = _api()

    report = _run(
        monkeypatch,
        api,
        lambda _request: azure_failure(403, "403001", "the free quota is used up"),
        max_batches=1,
    )

    assert (report.stop_reason, report.succeeded, report.released, report.completed) == ("llm_quota", True, 4, 0)
    assert api.ledger.writes_to(CHARACTERS).count("exhaust") == 1
    assert api.ledger.characters is not None and api.ledger.characters.exhausted
    assert api.bodies["release"][0]["task_ids"] == [task_id(number) for number in range(4)]
    assert not api.bodies["fail"] and api.ledger.writes_to("neurons") == []
    assert report.characters_used == 0


def test_only_an_engine_billed_in_a_unit_with_a_meter_of_its_own_gets_one(monkeypatch: pytest.MonkeyPatch) -> None:
    """Wiring · the own meter of a unit is built from the guard; a unit billed on the neuron ledger gets none."""
    guard = guard_for(monkeypatch, FakeLedger(9000.0, characters=1.0))

    characters = own_meters_for("characters", guard)
    subscription = own_meters_for("subscription", guard)

    assert set(characters) == {"characters"} and isinstance(characters["characters"], CharacterMeter)
    assert set(subscription) == {"subscription"} and isinstance(subscription["subscription"], SubscriptionMeter)
    assert own_meters_for("neurons", guard) == {}
