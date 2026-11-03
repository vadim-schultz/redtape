"""The llm_extract part of a drain: the neuron meter opened for the run and the handler that spends from it."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from discovery_ingest.budget import BudgetGuard
from discovery_ingest.extract.llm.meter import NeuronMeter, open_neuron_meter
from discovery_ingest.schemas import DiscoveryTaskKind
from discovery_ingest.worker.batch import TaskHandler
from discovery_ingest.worker.llm_extract import AfterExtract, LlmExtractHandler
from discovery_ingest.worker.llm_runtime import LlmResources
from discovery_ingest.worker.policy import DrainPolicy
from discovery_ingest.worker.tally import Tally


@dataclass(frozen=True, slots=True)
class LlmDrain:
    """The handler of ``llm_extract`` and the meter that counts what it spends."""

    handler: LlmExtractHandler
    meter: NeuronMeter

    def handlers(self) -> Mapping[DiscoveryTaskKind, TaskHandler]:
        """The kind-to-handler entry of this drain."""
        return {"llm_extract": self.handler}

    def record(self, tally: Tally) -> None:
        """Copy the neurons spent and the model calls made into ``tally``."""
        tally.neurons_used = round(self.meter.used_neurons, 1)
        tally.llm_calls = self.handler.llm_calls


def open_llm_drain(
    policy: DrainPolicy, guard: BudgetGuard, llm: LlmResources | None, after_extract: AfterExtract
) -> LlmDrain | None:
    """Return the llm part of a drain, or ``None`` when the policy drains no llm kind or no neuron can be spent today."""
    if not policy.drains_llm_kinds or policy.neuron_budget is None:
        return None
    if llm is None:
        raise ValueError("LLM resources are required to drain llm_extract")
    meter = open_neuron_meter(policy.neuron_budget, guard)
    return None if meter is None else LlmDrain(LlmExtractHandler(llm, meter, after_extract), meter)
