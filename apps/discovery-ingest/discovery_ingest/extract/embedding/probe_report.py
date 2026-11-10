"""The ``embed probe`` report: a typed model, printed as one JSON object."""

from __future__ import annotations

from pydantic import BaseModel, Field, computed_field

from discovery_ingest.extract.embedding.client import EmbeddingResult
from discovery_ingest.extract.embedding.pricing import neurons_of


class DimensionCheck(BaseModel):
    """One try of the ``dimensions`` parameter: accepted only when the vectors came back with that length."""

    requested: int
    returned: int | None
    accepted: bool
    reason: str | None = None


class BatchCheck(BaseModel):
    """One try of a batch size: accepted with its wall time, or rejected with the provider's reason."""

    size: int
    accepted: bool
    latency_ms: int | None = None
    reason: str | None = None


class EmbedProbeReport(BaseModel):
    """What the probe learned about one embedding model; ``stopped`` says why it ended early (else ``None``)."""

    model: str
    dimension: int | None = None
    latency_ms: int | None = None
    dimension_checks: list[DimensionCheck] = Field(default_factory=list)
    batch_checks: list[BatchCheck] = Field(default_factory=list)
    tokens: int = 0
    neurons: float = 0.0
    stopped: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def accepted_dimensions(self) -> list[int]:
        """The reduced dimensions the model honoured."""
        return [check.requested for check in self.dimension_checks if check.accepted]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def largest_accepted_batch(self) -> int | None:
        """The biggest batch size answered, or ``None`` when none was."""
        return max((check.size for check in self.batch_checks if check.accepted), default=None)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def first_rejected_batch(self) -> int | None:
        """The batch size where the ladder stopped, or ``None`` when every size was answered."""
        return next((check.size for check in self.batch_checks if not check.accepted), None)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def neurons_per_1k_tokens(self) -> float | None:
        """Neurons per thousand input tokens over the whole probe, or ``None`` when no tokens were reported."""
        return self.neurons / self.tokens * 1000 if self.tokens else None

    def add_usage(self, result: EmbeddingResult) -> None:
        """Count the tokens and neurons of one answered call."""
        self.tokens += result.input_tokens or 0
        self.neurons += neurons_of(result)
