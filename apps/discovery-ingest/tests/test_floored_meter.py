"""Floor · a floor names a ledger resource and an amount; the neuron floor keeps its old behaviour."""

from __future__ import annotations

import pytest
from discovery_ingest.translation.character_meter import CharacterMeter
from discovery_ingest.translation.meter import UsageDenied, UsageReservation
from discovery_ingest.translation.metered import MeteredTranslator
from discovery_ingest.translation.units import Usage
from discovery_ingest.worker.floored_meter import Floor, FlooredMeter
from discovery_ingest.worker.stop import StopDrain
from discovery_ingest.worker.translate_meter import MeterPlan, open_run_meter

from ledger_fakes import CHARACTERS, FakeLedger, guard_for
from translate_fakes import ScriptedEngine
from translation_fakes import RecordingMeter, batch, unit


def test_a_reservation_that_would_leave_remaining_below_the_floor_is_denied_for_a_monthly_resource(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Floor · a reservation that would leave remaining below the floor is denied for a monthly resource."""
    ledger = FakeLedger(9000.0, characters=800_000.0)
    guard = guard_for(monkeypatch, ledger)
    meter = FlooredMeter(CharacterMeter(guard), guard, Floor(CHARACTERS, 760_000.0))

    assert meter.reserve(Usage("characters", 50_000.0), "azure-translator") == UsageDenied("floor")
    assert ledger.characters is not None and ledger.characters.remaining == 800_000.0

    granted = meter.reserve(Usage("characters", 40_000.0), "azure-translator")

    assert isinstance(granted, UsageReservation) and ledger.characters.remaining == 760_000.0


def test_the_neuron_floor_behaves_exactly_as_before(monkeypatch: pytest.MonkeyPatch) -> None:
    """Floor · the neuron floor behaves exactly as before (parity test)."""
    ledger = FakeLedger(905.0)
    meter = open_run_meter("neurons", MeterPlan(guard_for(monkeypatch, ledger), 1000.0, 900.0, {}))

    assert meter is not None
    assert meter.reserve(Usage("neurons", 6.0), "llm") == UsageDenied("floor")
    assert ledger.remaining == 905.0
    assert isinstance(meter.reserve(Usage("neurons", 5.0), "llm"), UsageReservation)
    assert ledger.remaining == 900.0


def test_a_floor_denial_stops_the_drain_with_the_generic_usage_text() -> None:
    """Floor · a floor denial stops the drain with the generic usage text, not the query-embedding one."""
    engine = ScriptedEngine(unit="characters")

    with pytest.raises(StopDrain) as stop:
        MeteredTranslator(engine, RecordingMeter(deny=UsageDenied("floor"))).translate(batch(unit("a", "Antrag")))

    assert stop.value.reason == "llm_budget"
    assert "the usage kept for other work would be used" in str(stop.value)
    assert engine.batches == []
