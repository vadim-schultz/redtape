"""The llm_extract kind: never a default, needs a neuron budget, and its stop reasons and report fields (chapter E6, C)."""

from __future__ import annotations

from dataclasses import asdict

import pytest
from discovery_ingest.schemas import LLM_TASK_KINDS, TASK_KINDS, WORKER_DEFAULT_TASK_KINDS, DrainReport
from discovery_ingest.worker.policy import DrainPolicy
from discovery_ingest.worker.tally import Tally
from pydantic import ValidationError


def _report(**fields: object) -> DrainReport:
    base: dict[str, object] = {"claimed": 0, "completed": 0, "failed": 0, "skipped": 0, "stop_reason": "queue_empty"}
    return DrainReport.model_validate({**base, **fields})


def test_llm_extract_is_a_known_kind_but_never_a_default_kind() -> None:
    """kinds · llm_extract is claimable on request; the default worker kinds and the plain policy never include it."""
    assert LLM_TASK_KINDS == ("llm_extract",)
    assert "llm_extract" in TASK_KINDS
    assert "llm_extract" not in WORKER_DEFAULT_TASK_KINDS
    assert DrainPolicy().drains_llm_kinds is False


def test_a_policy_that_drains_llm_extract_needs_a_positive_neuron_budget() -> None:
    """policy · llm_extract without a neuron budget, or with zero, is rejected; with one it drains the kind."""
    with pytest.raises(ValueError, match="neuron_budget is required"):
        DrainPolicy(kinds=("llm_extract",))
    with pytest.raises(ValueError, match="neuron_budget must be positive"):
        DrainPolicy(kinds=("llm_extract",), neuron_budget=0)

    assert DrainPolicy(kinds=("llm_extract",), neuron_budget=800).drains_llm_kinds is True
    assert DrainPolicy(neuron_budget=800).drains_llm_kinds is False


def test_the_drain_report_carries_neurons_calls_released_and_the_llm_stop_reasons() -> None:
    """report · neurons_used and llm_calls default to zero; llm_budget and llm_quota are stop reasons, others are not."""
    empty = _report()
    assert (empty.neurons_used, empty.llm_calls, empty.released, empty.ledger_unavailable) == (0.0, 0, 0, False)

    for reason in ("llm_budget", "llm_quota", "db_limit"):
        assert _report(stop_reason=reason, neurons_used=12.5, llm_calls=3).llm_calls == 3
    with pytest.raises(ValidationError):
        _report(stop_reason="llm_coffee")


def test_the_tally_counts_neurons_and_calls_into_the_report_fields() -> None:
    """tally · its llm fields are a subset of the report's, so asdict(tally) still builds a report."""
    tally = Tally(neurons_used=3.5, llm_calls=2)

    report = _report(**asdict(tally))

    assert (report.neurons_used, report.llm_calls) == (3.5, 2)
