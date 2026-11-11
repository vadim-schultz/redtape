"""What a failed embedding call means for its batch: a limit stops the drain, a provider error fails the tasks."""

from __future__ import annotations

from discovery_ingest.extract.embedding.meter import EmbeddingMeter
from discovery_ingest.extract.llm.errors import (
    LlmAuthError,
    LlmError,
    LlmInvalidOutput,
    LlmQuotaExceeded,
    LlmRequestError,
)
from discovery_ingest.extract.llm.meter import Reservation
from discovery_ingest.worker.lease_settle import Failure
from discovery_ingest.worker.stop import StopDrain


def _quota_stop(meter: EmbeddingMeter, reservation: Reservation, err: LlmQuotaExceeded) -> StopDrain:
    meter.refund(reservation)
    meter.exhaust()
    return StopDrain("llm_quota", str(err))


def _auth_stop(meter: EmbeddingMeter, reservation: Reservation, err: LlmAuthError) -> StopDrain:
    meter.refund(reservation)
    return StopDrain("error", f"Cloudflare rejected the Workers AI credentials: {err}")


def _request_failure(meter: EmbeddingMeter, reservation: Reservation, err: LlmRequestError) -> Failure:
    meter.refund(reservation)
    return Failure(str(err), retryable=err.retryable)


def refusal(meter: EmbeddingMeter, reservation: Reservation, err: LlmError) -> Failure:
    """Return the failure of a batch the provider refused, or raise the :class:`StopDrain` that ends the drain.

    An unusable answer was billed, so its reservation stays; a refused request was not, so it is refunded.
    """
    match err:
        case LlmQuotaExceeded():
            raise _quota_stop(meter, reservation, err) from err
        case LlmAuthError():
            raise _auth_stop(meter, reservation, err) from err
        case LlmRequestError():
            return _request_failure(meter, reservation, err)
        case LlmInvalidOutput():
            return Failure(str(err), retryable=True)
        case _:
            raise err
