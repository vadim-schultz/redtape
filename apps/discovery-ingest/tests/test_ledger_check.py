"""Ledger · the start check reads the resource that matches the engine's unit; a unit without a resource is skipped."""

from __future__ import annotations

import pytest
from discovery_ingest.operations.translate_drain import check_ledger
from discovery_ingest.worker.llm_setup import EXIT_NOT_READY, LlmSetupError

from ledger_fakes import FakeLedger, guard_for
from translate_fakes import ScriptedEngine


def test_the_check_reads_the_resource_matching_the_engine_unit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ledger · the check reads the resource matching the engine's unit."""
    check_ledger(ScriptedEngine(unit="characters"), guard_for(monkeypatch, FakeLedger(9000.0, characters=1_900_000.0)))
    neurons_only = FakeLedger(9000.0)
    check_ledger(ScriptedEngine(unit="neurons"), guard_for(monkeypatch, neurons_only))

    with pytest.raises(LlmSetupError, match="azure_translator_chars") as refused:
        check_ledger(ScriptedEngine(unit="characters"), guard_for(monkeypatch, neurons_only))

    assert refused.value.exit_code == EXIT_NOT_READY


@pytest.mark.parametrize("unit", ["subscription", "bananas"])
def test_an_unknown_unit_has_no_resource_and_is_skipped_not_an_error(
    monkeypatch: pytest.MonkeyPatch, unit: str
) -> None:
    """Ledger · an unknown unit has no resource and is skipped, not an error."""
    ledger = FakeLedger(9000.0, down=True)

    check_ledger(ScriptedEngine(unit=unit), guard_for(monkeypatch, ledger))  # type: ignore[arg-type]

    assert ledger.calls == []
