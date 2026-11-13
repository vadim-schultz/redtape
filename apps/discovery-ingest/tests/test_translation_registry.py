"""Engine registry, locale maps, meters by unit, settings and the conformance suite over every registered engine."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from discovery_ingest.translation.adapters.cloudflare_llm import LlmTranslator
from discovery_ingest.translation.engine import TranslationEngine
from discovery_ingest.translation.errors import (
    PermanentError,
    QuotaExceeded,
    TransientError,
    TranslationEngineError,
    Unauthorised,
    UnusableOutputError,
)
from discovery_ingest.translation.locale_codes import (
    DEFAULT_TARGET_LOCALES,
    UnmappedLocaleError,
    provider_code,
    register_locale_map,
    unregister_locale_map,
)
from discovery_ingest.translation.meter import NeuronUsageMeter, NoMeterForUnitError, meter_for_unit
from discovery_ingest.translation.registry import (
    EngineConfig,
    UnknownEngineError,
    build_engine,
    register_engine,
    registered_engines,
    unregister_engine,
)
from discovery_ingest.translation.settings import TranslationSettings
from discovery_ingest.translation.units import TranslationBatch, TranslationOutcome, TranslationUnit, Usage
from pydantic import ValidationError

import translation_engine_contract as contract
from ledger_fakes import FakeLedger, guard_for
from translation_fakes import batch, unit
from translation_harnesses import HARNESSES, AdapterHarness, Behaviour

FAKE = "fake-chars"


class CharacterEngine:
    """A second provider: billed in characters, with its own locale codes. Proves the seam, not a real adapter."""

    name = FAKE
    usage_unit = "characters"

    def translate(self, request: TranslationBatch) -> TranslationOutcome:
        """Echo every unit and bill its characters."""
        done = tuple(TranslationUnit(u.key, f"{request.target_locale}:{u.title}", u.description) for u in request.units)
        return TranslationOutcome(done, self.estimate(request), None)

    def estimate(self, request: TranslationBatch) -> Usage:
        """Count the characters of every title and description."""
        return Usage("characters", float(sum(len(u.title) + len(u.description) for u in request.units)))


@pytest.fixture
def fake_engine() -> Iterator[None]:
    """Register the fake second engine and its locale map for one test."""
    register_engine(FAKE, lambda _config: CharacterEngine())
    register_locale_map(FAKE, {code: f"{code}-XX" for code in DEFAULT_TARGET_LOCALES})
    yield
    unregister_engine(FAKE)
    unregister_locale_map(FAKE)


def test_build_engine_returns_the_registered_cloudflare_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    """registry · build_engine returns the registered adapter for its name; llm is registered out of the box."""
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "acc0123456789abcdef")
    monkeypatch.setenv("CLOUDFLARE_AI_API_TOKEN", "tok-fake-1234")

    engine = build_engine("llm", EngineConfig(model="@cf/meta/llama-3.1-8b-instruct"))

    assert "llm" in registered_engines()
    assert isinstance(engine, LlmTranslator) and (engine.name, engine.usage_unit) == ("llm", "neurons")


def test_an_unknown_engine_name_fails_and_lists_the_registered_names() -> None:
    """registry · an unknown name raises UnknownEngineError that names the registered engines."""
    with pytest.raises(UnknownEngineError, match=r"registered: .*llm"):
        build_engine("deepl", EngineConfig())


def test_an_unknown_translation_engine_setting_fails_at_load_and_lists_the_registered_names() -> None:
    """registry · an unknown TRANSLATION_ENGINE fails at load and lists the registered names."""
    with pytest.raises(ValidationError, match=r"registered: .*llm"):
        TranslationSettings.model_validate({"TRANSLATION_ENGINE": "deepl"})


def test_the_engine_setting_defaults_to_azure_translator_and_the_model_is_optional() -> None:
    """settings · TRANSLATION_ENGINE defaults to azure-translator; the model is optional."""
    settings = TranslationSettings.model_validate({})

    assert (settings.translation_engine, settings.translation_model) == ("azure-translator", None)


def test_a_second_adapter_with_its_own_unit_and_locale_map_is_selected_without_changes_elsewhere(
    fake_engine: None,
) -> None:
    """registry · a fake second adapter (characters unit, its own locale map) is registered and selected, then run through the contract pieces."""
    settings = TranslationSettings.model_validate({"TRANSLATION_ENGINE": FAKE})

    engine = build_engine(settings.translation_engine, EngineConfig())
    outcome = engine.translate(batch(unit("a", "Antrag"), target="tr"))

    assert isinstance(engine, CharacterEngine) and engine.usage_unit == "characters"
    assert provider_code(FAKE, "tr") == "tr-XX"
    assert outcome.usage == Usage("characters", 6.0) and outcome.results[0].title == "tr:Antrag"


def test_an_engine_whose_locale_map_misses_a_target_locale_cannot_be_built() -> None:
    """registry · build_engine refuses an engine whose locale map does not cover every target locale."""
    register_engine(FAKE, lambda _config: CharacterEngine())
    register_locale_map(FAKE, {"en": "en-XX"})
    try:
        with pytest.raises(UnmappedLocaleError, match="tr"):
            build_engine(FAKE, EngineConfig())
    finally:
        unregister_engine(FAKE)
        unregister_locale_map(FAKE)


def test_the_meter_is_chosen_by_the_engine_unit(monkeypatch: pytest.MonkeyPatch) -> None:
    """meter · neurons get the neuron meter over the existing NeuronMeter."""
    meter = meter_for_unit("neurons", NeuronUsageMeter(guard_for(monkeypatch, FakeLedger(remaining=100)), run_limit=50))

    assert isinstance(meter, NeuronUsageMeter)


def test_asking_for_a_characters_meter_raises_a_clear_no_meter_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """meter · asking for a characters meter raises a clear no-meter error until a character-billed adapter ships."""
    neurons = NeuronUsageMeter(guard_for(monkeypatch, FakeLedger(remaining=100)), run_limit=50)

    with pytest.raises(NoMeterForUnitError, match="no meter for unit characters"):
        meter_for_unit("characters", neurons)


@pytest.mark.parametrize("check", contract.CONTRACT, ids=lambda check: check.__name__)
@pytest.mark.parametrize("engine_name", registered_engines())
def test_every_registered_engine_passes_every_conformance_check(
    engine_name: str, check: object, caplog: pytest.LogCaptureFixture
) -> None:
    """registry · the conformance suite passes for every registered engine; an engine without a harness cannot be selected."""
    harness = HARNESSES[engine_name]

    contract.run_contract_check(harness, check, caplog)  # type: ignore[arg-type]


class BrokenHarness:
    """A deliberately broken adapter: ``flaw`` names the promise it breaks."""

    name = "llm"
    secret = "sk-secret"

    def __init__(self, flaw: str) -> None:
        self._flaw = flaw

    def build(self, behaviour: Behaviour) -> TranslationEngine:
        """Return an engine that breaks the contract in the way ``flaw`` says."""
        return _BrokenEngine(self._flaw, behaviour, self.secret)


_FAILURE_TYPES: dict[Behaviour, type[TranslationEngineError]] = {
    Behaviour.QUOTA: QuotaExceeded,
    Behaviour.TRANSIENT: TransientError,
    Behaviour.UNAUTHORISED: Unauthorised,
    Behaviour.PERMANENT: PermanentError,
    Behaviour.SHORT: UnusableOutputError,
}


class _BrokenEngine:
    """Maps every failure to the right category, so only the named ``flaw`` breaks the suite."""

    name = "llm"
    usage_unit = "neurons"

    def __init__(self, flaw: str, behaviour: Behaviour, secret: str) -> None:
        self._flaw, self._behaviour, self._secret = flaw, behaviour, secret

    def estimate(self, request: TranslationBatch) -> Usage:
        return Usage("neurons", 1.0)

    def translate(self, request: TranslationBatch) -> TranslationOutcome:
        if self._behaviour in _FAILURE_TYPES:
            message = f"provider said no, key {self._secret}" if self._flaw == "leak" else "provider said no"
            raise _FAILURE_TYPES[self._behaviour](message)
        units = request.units[:-1] if self._flaw == "drop" else request.units
        return TranslationOutcome(tuple(self._mangled(u) for u in units), Usage("neurons", 1.0), None)

    def _mangled(self, source: TranslationUnit) -> TranslationUnit:
        if self._flaw != "mangle":
            return source
        return TranslationUnit(source.key, source.title.replace("§ 35", "sec 35"), source.description.replace("{", "<"))


@pytest.mark.parametrize("flaw", ["drop", "mangle", "leak"])
def test_an_adapter_that_drops_a_unit_mangles_a_placeholder_or_leaks_the_token_fails_the_suite(
    flaw: str, caplog: pytest.LogCaptureFixture
) -> None:
    """conformance · a deliberately broken fake fails the suite (checked with a dropped unit, a mangled placeholder and a leaked token)."""
    with pytest.raises(AssertionError):
        contract.run_contract(BrokenHarness(flaw), caplog)


def test_the_contract_is_not_vacuous_a_correct_fake_passes_each_check_it_can(caplog: pytest.LogCaptureFixture) -> None:
    """conformance · the real adapter's harness passes the whole suite in one go."""
    harness: AdapterHarness = HARNESSES["llm"]

    contract.run_contract(harness, caplog)
