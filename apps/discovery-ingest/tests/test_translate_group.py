"""The drain's translate call · one repair when the engine can repair, none when it cannot, and the wrappers pass that on."""

from __future__ import annotations

import httpx
from discovery_ingest.translation.adapters.cloudflare_llm import LlmTranslator
from discovery_ingest.translation.metered import MeteredTranslator
from discovery_ingest.translation.units import TranslationBatch, TranslationOutcome, TranslationUnit, Usage
from discovery_ingest.worker.translate_group import translate_call

from azure_transport import engine as azure_engine
from translation_fakes import RecordingMeter, batch, unit
from translation_harnesses import HARNESSES, Behaviour

BATCH = batch(
    unit("good", "Reisepass beantragen", "Der Reisepass kostet 60 Euro."),
    unit("bad", "Wohnsitz anmelden 3", "Frist: 14 Tage."),
)


def _answer(source: TranslationUnit, restored: bool) -> TranslationUnit:
    """The first answer loses the numbers of the ``bad`` unit; the repair keeps them."""
    if source.key == "bad" and not restored:
        return unit(source.key, f"[en] {source.title}", "[en] Frist: Tage.")
    return unit(source.key, f"[en] {source.title}", f"[en] {source.description}")


class _ScriptedEngine:
    """A translator that answers each call through :func:`_answer` and counts its calls; ``repairs`` is its declaration."""

    def __init__(self, *, repairs: bool) -> None:
        self.repairs = repairs
        self.calls: list[TranslationBatch] = []

    def translate(self, batch: TranslationBatch) -> TranslationOutcome:
        self.calls.append(batch)
        restored = len(self.calls) > 1
        results = tuple(_answer(source, restored) for source in batch.units)
        return TranslationOutcome(results, Usage("neurons", 1.0), "scripted")


def test_an_invalid_unit_is_not_resent_when_the_engine_cannot_repair() -> None:
    """Repair · an invalid unit is not resent when repairs is false (exactly one call)."""
    translator = _ScriptedEngine(repairs=False)

    result = translate_call(translator, BATCH)

    assert len(translator.calls) == 1
    assert [item.valid for item in result.checked] == [True, False]
    assert result.repaired == 0 and result.repair_failure is None


def test_an_engine_that_can_repair_is_asked_once_more_and_the_unit_is_restored() -> None:
    """Repair · llm still repairs once when repairs is true: one repair call, and the unit comes back valid."""
    translator = _ScriptedEngine(repairs=True)

    result = translate_call(translator, BATCH)

    assert len(translator.calls) == 2
    assert [item.valid for item in result.checked] == [True, True]
    assert result.repaired == 1


def test_the_llm_adapter_and_the_claude_code_engine_declare_that_they_can_repair() -> None:
    """Repair · the Workers AI adapter and the Claude Code engine both repair once."""
    llm = HARNESSES["llm"].build(Behaviour.FAITHFUL)
    claude = HARNESSES["claude-code"].build(Behaviour.FAITHFUL)

    assert isinstance(llm, LlmTranslator) and llm.repairs is True
    assert claude.repairs is True


def _never_called(request: httpx.Request) -> httpx.Response:
    raise AssertionError("no request is expected: only the declaration is read")


def test_the_metering_wrapper_passes_the_engines_repair_declaration_through() -> None:
    """Repair · MeteredTranslator reports its engine's repairs, so the drain sees the engine's choice."""
    meter = RecordingMeter()

    assert MeteredTranslator(azure_engine(_never_called), meter).repairs is False
    assert MeteredTranslator(HARNESSES["llm"].build(Behaviour.FAITHFUL), meter).repairs is True
