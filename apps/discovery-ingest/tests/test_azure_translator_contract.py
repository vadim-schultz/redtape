"""Azure conformance · the shared adapter suite passes for the Azure harness, a fake that answers like API 2026-06-06."""

from __future__ import annotations

import pytest
from discovery_ingest.translation.adapters.azure_translator import NAME, AzureTranslator

import translation_engine_contract as contract
from translation_harnesses import HARNESSES


def test_azure_conformance_suite_passes_for_the_adapter_harness(caplog: pytest.LogCaptureFixture) -> None:
    """Azure · conformance suite passes for the adapter's harness."""
    contract.run_contract(HARNESSES[NAME], caplog)


def test_azure_cannot_repair_so_an_invalid_unit_is_never_resent() -> None:
    """Azure · the adapter declares repairs = False, so the drain and the UI never ask it for a second, identical call."""
    assert AzureTranslator.repairs is False
