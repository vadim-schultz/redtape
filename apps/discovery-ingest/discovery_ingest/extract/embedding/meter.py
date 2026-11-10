"""Neuron metering of embedding calls: reserve before a batch, settle to the reported usage, refund a refused call."""

from __future__ import annotations

from collections.abc import Sequence

from discovery_ingest.budget import BudgetGuard
from discovery_ingest.extract.embedding.client import EmbeddingResult
from discovery_ingest.extract.embedding.pricing import reported_neurons
from discovery_ingest.extract.llm.meter import Denied, LedgerUnavailable, NeuronMeter, Reservation, open_neuron_meter
from discovery_ingest.extract.llm.prices import estimate_embedding


class EmbeddingMeter:
    """Meter the embedding batches of one run on the shared neuron ledger through a :class:`NeuronMeter`."""

    def __init__(self, meter: NeuronMeter, model: str) -> None:
        """Keep the run's meter and the embedding ``model`` whose price every reservation uses."""
        self._meter = meter
        self._model = model

    @property
    def used_neurons(self) -> float:
        """Neurons this run has reserved, corrected by the usage the provider reported."""
        return self._meter.used_neurons

    @property
    def ledger_unavailable(self) -> bool:
        """Whether the ledger has failed to answer at any point of this run."""
        return self._meter.ledger_unavailable

    def reserve(self, texts: Sequence[str]) -> Reservation | Denied:
        """Reserve the conservative estimate (characters over three) for embedding ``texts``, or return the denial.

        A ledger that stops answering after the start is dropped once and the run budget carries on.
        """
        neurons = estimate_embedding(self._model, sum(len(text) for text in texts))
        answer = self._meter.reserve_neurons(self._model, neurons)
        if isinstance(answer, LedgerUnavailable):
            self._meter.stop_using_ledger()
            answer = self._meter.reserve_neurons(self._model, neurons)
        return answer if isinstance(answer, Reservation | Denied) else Denied("ledger")

    def settle(self, reservation: Reservation, result: EmbeddingResult) -> None:
        """Replace the reservation by the neurons ``result`` reported (or its tokens priced); keep it without usage."""
        actual = reported_neurons(result)
        if actual is not None:
            self._meter.settle_neurons(reservation, actual)

    def refund(self, reservation: Reservation) -> None:
        """Give back a reservation for a call the provider refused, so nothing was billed."""
        self._meter.refund(reservation)

    def exhaust(self) -> None:
        """Tell the ledger the day's neurons are gone (a provider quota error)."""
        self._meter.exhaust()


def open_embedding_meter(limit: float, guard: BudgetGuard, model: str) -> EmbeddingMeter | None:
    """Return the meter for a run capped by ``limit`` and what the ledger has left today; ``None`` when nothing is left.

    Raises :class:`UnknownModelError` for a model without an embedding price.
    """
    estimate_embedding(model, 0)
    meter = open_neuron_meter(limit, guard)
    return None if meter is None else EmbeddingMeter(meter, model)
