"""A translate call under a meter: reserve the estimate, call the engine, settle with the actual usage.

Every limit becomes the :class:`StopDrain` the drains already act on; the engine itself stays free of metering.
"""

from __future__ import annotations

from discovery_ingest.translation.engine import TranslationEngine
from discovery_ingest.translation.errors import QuotaExceeded, TranslationEngineError, Unauthorised, UnusableOutputError
from discovery_ingest.translation.meter import UsageDenied, UsageMeter, UsageReservation
from discovery_ingest.translation.units import TranslationBatch, TranslationOutcome
from discovery_ingest.worker.stop import StopDrain

DENIAL_TEXT = {
    "run_budget": "the run's usage budget is used up",
    "ledger": "the day's usage ledger is used up",
    "ledger_unavailable": "the usage ledger did not answer",
    "floor": "the usage kept for query embedding would be used",
}


class MeteredTranslator:
    """Translate batches through ``engine``, reserving from ``meter`` before and settling after each call."""

    def __init__(self, engine: TranslationEngine, meter: UsageMeter) -> None:
        """Keep the engine and the meter chosen for its usage unit."""
        self._engine = engine
        self._meter = meter

    def translate(self, batch: TranslationBatch) -> TranslationOutcome:
        """Return the outcome; raise :class:`StopDrain` when the meter denies the call or the provider stops it."""
        reservation = self._reserve(batch)
        try:
            outcome = self._engine.translate(batch)
        except TranslationEngineError as err:
            stop = self._refused(reservation, err)
            if stop is None:
                raise
            raise stop from err
        self._meter.settle(reservation, outcome.usage)
        return outcome

    def _refused(self, reservation: UsageReservation, err: TranslationEngineError) -> StopDrain | None:
        """Return the stop a refused call ends the drain with, or ``None`` when only the batch fails.

        An unusable answer was billed, so its reservation stays; any other refused call was not, so it is refunded.
        """
        match err:
            case QuotaExceeded():
                return self._quota_stop(reservation, err)
            case Unauthorised():
                return self._auth_stop(reservation, err)
            case UnusableOutputError():
                return None
            case _:
                self._meter.refund(reservation)
                return None

    def _reserve(self, batch: TranslationBatch) -> UsageReservation:
        answer = self._meter.reserve(self._engine.estimate(batch), self._engine.name)
        if isinstance(answer, UsageDenied):
            raise StopDrain("llm_budget", DENIAL_TEXT[answer.reason])
        return answer

    def _quota_stop(self, reservation: UsageReservation, err: QuotaExceeded) -> StopDrain:
        self._meter.refund(reservation)
        self._meter.exhaust()
        return StopDrain("llm_quota", str(err))

    def _auth_stop(self, reservation: UsageReservation, err: Unauthorised) -> StopDrain:
        self._meter.refund(reservation)
        return StopDrain("error", f"the translation provider rejected the credentials: {err}")
