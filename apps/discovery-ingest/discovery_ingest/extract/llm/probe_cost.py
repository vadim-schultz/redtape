"""Probe item 4: the cost of the call, from the usage the API reported and from the price table."""

from __future__ import annotations

from discovery_ingest.extract.llm.envelope import ReportedUsage, read_usage
from discovery_ingest.extract.llm.errors import LlmInvalidOutput
from discovery_ingest.extract.llm.prices import NEURON_PRICES, cost
from discovery_ingest.extract.llm.probe_calls import RawCall
from discovery_ingest.extract.llm.probe_report import ProbeRow

NO_PRICE = "n/a (no price row: the meter would refuse this model)"


def usage_of(call: RawCall) -> ReportedUsage | None:
    """Return the usage a native answer reported, even when its answer text is unusable; ``None`` without a result."""
    if call.response is None or not call.ok:
        return None
    try:
        return read_usage(call.response)
    except LlmInvalidOutput:
        return None


def tokens_of(call: RawCall) -> tuple[int, int] | None:
    """Return the (input, output) tokens of a native answer, or ``None`` without usage."""
    usage = usage_of(call)
    if usage is None or usage.input_tokens is None or usage.output_tokens is None:
        return None
    return usage.input_tokens, usage.output_tokens


def neurons_of(model: str, call: RawCall) -> float:
    """Return the neurons ``call`` cost by the price table, or 0 without usage or a price row."""
    tokens = tokens_of(call)
    return cost(model, *tokens) if tokens is not None and model in NEURON_PRICES else 0.0


def _reported(call: RawCall) -> str:
    usage = usage_of(call)
    return "" if usage is None or usage.neurons is None else f" reported_neurons={usage.neurons:.2f}"


def cost_row(model: str, call: RawCall) -> ProbeRow:
    """Report tokens in and out, the neurons they cost by the price table, those the API reported and the wall time."""
    tokens = tokens_of(call)
    neurons = f"{neurons_of(model, call):.2f}" if model in NEURON_PRICES else NO_PRICE
    seen = f"tokens_in={tokens[0]} tokens_out={tokens[1]}" if tokens else "tokens n/a (no usage block)"
    return ProbeRow(model, "cost", f"{seen} neurons={neurons}{_reported(call)} wall_ms={call.wall_ms}")
